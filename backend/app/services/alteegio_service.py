import httpx
import logging
import json
import asyncio
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Any
from app.config import get_settings
from app.utils.circuit_breaker import alteegio_breaker, CircuitOpenError

# Часовой пояс Алматы (UTC+5) — используется для нормализации дат из Alteegio
ALMATY_TZ = timezone(timedelta(hours=5))

# Default HTTP timeout (seconds) for ALL Alteegio calls.
# Webhooks must answer Meta within ~20s — keep this under that.
DEFAULT_TIMEOUT = 15.0
# Rate-limit safety: pause between consecutive batch calls
BATCH_CALL_DELAY = 0.3
# Retry config for transient errors (429, 5xx)
MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 0.5  # seconds: 0.5, 1.0, 2.0

settings = get_settings()

# Настройка логирования
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


class AlteegioService:
    """Service for interacting with Alteegio API"""
    
    BASE_URL = "https://api.alteg.io/api/v1"
    
    def __init__(self):
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/vnd.api.v2+json",
            "Authorization": settings.alteegio_auth_header
        }
        self.company_id = settings.alteegio_company_id
        logger.info(f" AlteegioService initialized with company_id: {self.company_id}")

    async def _request(self, method: str, url: str, **kwargs) -> httpx.Response:
        """Wrapped HTTP request with timeout + retry on 429/5xx + circuit breaker.

        Retries up to MAX_RETRIES with exponential backoff.
        Does NOT retry on 4xx other than 429 (those are programming errors).
        Wrapped by circuit breaker → after 5 consecutive failures, all calls
        fail-fast for 60 seconds.
        """
        return await alteegio_breaker.call(self._raw_request, method, url, **kwargs)

    async def _raw_request(self, method: str, url: str, **kwargs) -> httpx.Response:
        """Inner request — actual HTTP work with retry."""
        kwargs.setdefault("headers", self.headers)
        timeout = kwargs.pop("timeout", DEFAULT_TIMEOUT)

        last_exc: Exception | None = None
        for attempt in range(MAX_RETRIES + 1):
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    response = await client.request(method, url, **kwargs)

                # Retry on 429 (rate limit) or 5xx (server error)
                if response.status_code == 429 or response.status_code >= 500:
                    if attempt < MAX_RETRIES:
                        delay = RETRY_BACKOFF_BASE * (2 ** attempt)
                        logger.warning(
                            f"⚠️ Alteegio {response.status_code} on {url} — "
                            f"retry {attempt + 1}/{MAX_RETRIES} after {delay}s"
                        )
                        await asyncio.sleep(delay)
                        continue
                return response

            except (httpx.TimeoutException, httpx.NetworkError) as e:
                last_exc = e
                if attempt < MAX_RETRIES:
                    delay = RETRY_BACKOFF_BASE * (2 ** attempt)
                    logger.warning(
                        f"⚠️ Alteegio network error on {url} ({type(e).__name__}) — "
                        f"retry {attempt + 1}/{MAX_RETRIES} after {delay}s"
                    )
                    await asyncio.sleep(delay)
                    continue
                logger.error(f"❌ Alteegio request failed after {MAX_RETRIES} retries: {e}")
                raise

        if last_exc:
            raise last_exc
        # All retries exhausted but no exception: return last response
        return response  # type: ignore[return-value]
    
    async def get_available_dates(
        self, 
        staff_id: str, 
        service_ids: List[str]
    ) -> Dict[str, Any]:
        """
        Get available dates for booking for a specific barber.
        Corresponds to "Get Available Dates" tool in n8n.
        """
        url = f"{self.BASE_URL}/book_dates/{self.company_id}"
        params = {
            "staff_id": staff_id,
            "service_ids[]": service_ids
        }
        
        logger.debug(f"📅 get_available_dates called")
        logger.debug(f"   URL: {url}")
        logger.debug(f"   Params: {params}")

        response = await self._request("GET", url, params=params)
        logger.debug(f"   Status: {response.status_code}")
        logger.debug(f"   Response: {response.text[:500]}")
        return response.json()
    
    async def get_available_times(
        self,
        staff_id: str,
        date: str,
        service_ids: List[str]
    ) -> Dict[str, Any]:
        """
        Get available times for a specific date and barber.
        Corresponds to "Get Available Times" tool in n8n.
        
        Args:
            staff_id: ID of the staff member
            date: Date in ISO format (e.g., 2025-12-04T10:00:00)
            service_ids: List of service IDs
        """
        url = f"{self.BASE_URL}/book_times/{self.company_id}/{staff_id}/{date}"
        params = {
            "service_ids[]": service_ids
        }
        
        logger.debug(f"🕐 get_available_times called")
        logger.debug(f"   URL: {url}")
        logger.debug(f"   Params: {params}")

        response = await self._request("GET", url, params=params)
        logger.debug(f"   Status: {response.status_code}")
        logger.debug(f"   Response: {response.text[:500]}")
        return response.json()
    
    async def get_available_masters(
        self,
        datetime: str
    ) -> List[Dict[str, Any]]:
        """
        Get available masters for a specific datetime.
        Corresponds to "Get Available Masters for Date/time" tool in n8n.
        
        Args:
            datetime: Full datetime in ISO format (e.g., 2025-12-09T10:00:00)
        
        Returns:
            List of available masters with bookable status
        """
        url = f"{self.BASE_URL}/book_staff/{self.company_id}"
        params = {
            "datetime": datetime
        }
        
        logger.debug(f"👥 get_available_masters called")
        logger.debug(f"   URL: {url}")
        logger.debug(f"   Params: {params}")

        response = await self._request("GET", url, params=params)
        logger.debug(f"   Status: {response.status_code}")
        logger.debug(f"   Response: {response.text[:500]}")
        data = response.json()

        # Extract data from response (can be list or {"success": true, "data": [...]})
        if isinstance(data, dict) and "data" in data:
            masters = data["data"]
        elif isinstance(data, list):
            masters = data
        else:
            masters = []

        # Filter only bookable masters and simplify response
        bookable_masters = []
        for m in masters:
            if m.get("bookable", False):
                bookable_masters.append({
                    "id": m.get("id"),
                    "name": m.get("name"),
                    "specialization": m.get("specialization"),
                    "rating": m.get("rating"),
                    "bookable": True
                })

        logger.info(f"   Bookable masters found: {len(bookable_masters)}")
        return bookable_masters
    
    async def create_appointment(
        self,
        staff_id: str,
        service_id: str,
        client_phone: str,
        client_name: str,
        datetime: str,
        seance_length: str,
        comment: str = "ЗАПИСЬ СДЕЛАНА ЧЕРЕЗ БОТА!!!"
    ) -> Dict[str, Any]:
        """
        Create a new appointment in Alteegio.
        Corresponds to "Create a New Appointment" tool in n8n.
        """
        url = f"{self.BASE_URL}/records/{self.company_id}"
        
        payload = {
            "staff_id": staff_id,
            "services": [
                {
                    "id": service_id,
                    "amount": 1
                }
            ],
            "client": {
                "phone": client_phone,
                "name": client_name
            },
            "datetime": datetime,
            "seance_length": seance_length,
            "comment": comment
        }
        
        logger.info(f"📝 create_appointment called")
        logger.info(f"   URL: {url}")
        logger.info(f"   Payload: {json.dumps(payload, ensure_ascii=False, indent=2)}")

        response = await self._request("POST", url, json=payload)
        logger.info(f"   Status: {response.status_code}")
        logger.info(f"   Response: {response.text}")

        try:
            result = response.json()
            logger.info(f"   Parsed result: {json.dumps(result, ensure_ascii=False, indent=2)}")
            return result
        except Exception as e:
            logger.error(f"   Failed to parse JSON response: {e}")
            return {"error": str(e), "status_code": response.status_code, "text": response.text}
    
    async def get_services(self) -> List[Dict[str, Any]]:
        """Get all services from Alteegio"""
        url = f"{self.BASE_URL}/services/{self.company_id}"
        response = await self._request("GET", url)
        data = response.json()
        if isinstance(data, dict) and "data" in data:
            return data["data"]
        return data if isinstance(data, list) else []

    async def get_staff(self) -> List[Dict[str, Any]]:
        """Get all staff members from Alteegio"""
        url = f"{self.BASE_URL}/company/{self.company_id}/staff"

        logger.info(f"👥 get_staff called")
        logger.info(f"   URL: {url}")

        response = await self._request("GET", url)
        logger.info(f"   Status: {response.status_code}")
        data = response.json()

        # Extract staff from response
        if isinstance(data, dict) and "data" in data:
            staff = data["data"]
        elif isinstance(data, list):
            staff = data
        else:
            staff = []

        logger.info(f"   Staff found: {len(staff)}")
        return staff
    
    async def get_records(self, date: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get records/appointments from Alteegio"""
        url = f"{self.BASE_URL}/records/{self.company_id}"
        
        if date:
            params = {"date": date}
        else:
            from datetime import datetime
            params = {"date": datetime.now().strftime("%Y-%m-%d")}
        
        logger.info(f"📋 get_records called")
        logger.info(f"   URL: {url}")
        logger.info(f"   Params: {params}")

        response = await self._request("GET", url, params=params)
        logger.info(f"   Status: {response.status_code}")
        data = response.json()

        # Extract records from response
        if isinstance(data, dict) and "data" in data:
            records = data["data"]
        elif isinstance(data, list):
            records = data
        else:
            records = []

        logger.info(f"   Records found: {len(records)}")
        return records
            
    async def get_appointments_for_period(self, start_time: datetime, end_time: datetime) -> List[Dict[str, Any]]:
        """Get all appointments between start and end time"""
        logger.info(f"🔍 Getting appointments between {start_time} and {end_time}")
        
        # Get records for today and tomorrow
        appointments = []
        for date in [start_time.date(), end_time.date()]:
            date_str = date.strftime("%Y-%m-%d")
            day_records = await self.get_records(date_str)
            
            for record in day_records:
                try:
                    dt_str = record.get('datetime', '')
                    if not dt_str:
                        continue
                    record_datetime = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
                    # FIX: если Alteegio вернул datetime без TZ (naive) — считаем Алматы
                    if record_datetime.tzinfo is None:
                        record_datetime = record_datetime.replace(tzinfo=ALMATY_TZ)
                    if start_time <= record_datetime <= end_time:
                        appointments.append({
                            'id': record.get('id'),
                            'client_phone': record.get('client', {}).get('phone', ''),
                            'client_name': record.get('client', {}).get('name', 'Клиент'),
                            'master_name': record.get('staff', {}).get('name', 'Мастер'),
                            'datetime': record.get('datetime', ''),
                            'service_name': record.get('services', [{}])[0].get('title', '')
                        })
                except Exception as e:
                    logger.error(f"❌ Error parsing record: {e}")
                    continue
        
        logger.info(f"✅ Found {len(appointments)} appointments in period")
        return appointments
        
    async def get_past_appointments_for_date(self, target_date: datetime.date) -> List[Dict[str, Any]]:
        """Get all completed appointments for specific past date"""
        logger.info(f"🔍 Getting past appointments for date: {target_date}")
        
        date_str = target_date.strftime("%Y-%m-%d")
        records = await self.get_records(date_str)
        
        appointments = []
        for record in records:
            try:
                appointments.append({
                    'id': record.get('id'),
                    'client_phone': record.get('client', {}).get('phone', ''),
                    'client_name': record.get('client', {}).get('name', 'Клиент'),
                    'datetime': record.get('datetime', ''),
                    'service_name': record.get('services', [{}])[0].get('title', '')
                })
            except Exception as e:
                logger.error(f"❌ Error parsing record: {e}")
                continue
        
        logger.info(f"✅ Found {len(appointments)} past appointments")
        return appointments
        
    async def client_has_future_appointment(self, phone: str) -> bool:
        """Check if client already has any future appointment.

        NOTE: Kept for backwards-compatibility.
        For batch use (e.g. revisit reminders loop) prefer
        get_clients_with_future_appointments() to avoid N×29 API calls.
        """
        logger.info(f"🔍 Checking future appointments for client: {phone}")

        # Check next 14 days (reduced from 30 — barbershop rebook cycle)
        for i in range(1, 15):
            check_date = datetime.now().date() + timedelta(days=i)
            records = await self.get_records(check_date.strftime("%Y-%m-%d"))

            for record in records:
                client_phone = record.get('client', {}).get('phone', '')
                if client_phone and phone in client_phone:
                    logger.info(f"✅ Client {phone} has future appointment on {check_date}")
                    return True

        logger.info(f"❌ Client {phone} has no future appointments in next 14 days")
        return False

    async def get_clients_with_future_appointments(self, days_ahead: int = 14) -> set:
        """Return set of all phone numbers that have appointments in the next N days.

        FIX: replaces the old pattern of calling client_has_future_appointment()
        per-client in the revisit-reminder loop, which caused N×29 API calls.
        Now we fetch days_ahead dates ONCE and share the result across all clients.

        Args:
            days_ahead: how many days forward to scan (default 14).

        Returns:
            Set of raw phone strings as returned by Alteegio.
        """
        future_phones: set = set()
        today = datetime.now().date()
        for i in range(1, days_ahead + 1):
            check_date = today + timedelta(days=i)
            try:
                records = await self.get_records(check_date.strftime("%Y-%m-%d"))
                for record in records or []:
                    phone = (record.get('client') or {}).get('phone', '')
                    if phone:
                        future_phones.add(phone)
            except Exception as e:
                logger.warning(f"⚠️ Could not fetch records for {check_date}: {e}")
            finally:
                # Throttle: prevent Alteegio rate-limit on batch loops
                await asyncio.sleep(BATCH_CALL_DELAY)
        logger.info(f"   📋 {len(future_phones)} unique phones with future appointments (next {days_ahead}d)")
        return future_phones
    
    def normalize_phone_number(self, phone: str) -> str:
        """Normalize client phone numbers for customer base and broadcasts."""
        if not phone:
            return ""
        phone = phone.strip()
        if phone.startswith("whatsapp:"):
            phone = phone[len("whatsapp:"):]
        cleaned = ''.join(ch for ch in phone if ch.isdigit() or ch == '+')
        if cleaned.startswith('+'):
            return cleaned
        if cleaned.startswith('8') and len(cleaned) == 11:
            return f'+7{cleaned[1:]}'
        if len(cleaned) == 10:
            return f'+7{cleaned}'
        if len(cleaned) >= 11 and cleaned.startswith('7'):
            return f'+{cleaned}'
        return cleaned

    async def get_clients(self, days: int = 30) -> List[Dict[str, str]]:
        """Get unique clients from Alteegio records for the last N days."""
        unique_clients: dict[str, Dict[str, str]] = {}
        now = datetime.now()
        for offset in range(days):
            day = (now - timedelta(days=offset)).strftime("%Y-%m-%d")
            try:
                records = await self.get_records(day)
            except Exception:
                records = []
            for record in records or []:
                client = record.get("client") or {}
                phone = (client.get("phone") or "").strip()
                name = (client.get("name") or "Клиент").strip()
                normalized = self.normalize_phone_number(phone)
                if normalized:
                    unique_clients[normalized] = {
                        "phone": normalized,
                        "name": name or "Клиент"
                    }
            # Throttle: spread Alteegio load on long batch loops
            await asyncio.sleep(BATCH_CALL_DELAY)

        return list(unique_clients.values())


# Singleton instance
alteegio_service = AlteegioService()
