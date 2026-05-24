"""
WhatsApp Business Cloud API Service.
Handles outgoing WhatsApp messages through Meta Graph API.
"""
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import httpx
from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

# 24-hour customer service window. WhatsApp allows free-form text only within
# 24h of the last incoming message from the client. We use 23h to leave margin.
WA_24H_WINDOW_SECONDS = 23 * 3600


class WhatsAppCloudService:
    """Service for WhatsApp Business Cloud API integration."""

    def __init__(self):
        self.api_url = settings.whatsapp_api_url.rstrip('/')
        self.api_version = settings.whatsapp_api_version
        self.phone_number_id = settings.whatsapp_phone_number_id
        self.access_token = settings.whatsapp_access_token

        if self.access_token and self.phone_number_id:
            logger.info(f"📱 WhatsAppCloudService initialized with phone_number_id: {self.phone_number_id}")
        else:
            logger.warning("⚠️ WhatsApp Business Cloud API credentials are not configured")

    @staticmethod
    def normalize_phone_number(phone: str) -> str:
        """Normalize a phone number to international digits for WhatsApp Cloud API.
        
        Handles formats:
        - +77012345678  → 77012345678
        - 77012345678   → 77012345678  (Kazakhstan, 11 digits)
        - 87012345678   → 77012345678  (starts with 8, 11 digits)
        - 7012345678    → 77012345678  (10 digits, KZ)
        - whatsapp:+77012345678 → 77012345678
        """
        if not phone:
            return ""
        phone = phone.strip()
        # Remove whatsapp: prefix
        if phone.startswith("whatsapp:"):
            phone = phone[len("whatsapp:"):]
        # Keep only digits
        cleaned = ''.join(ch for ch in phone if ch.isdigit())
        # 8XXXXXXXXXX → 7XXXXXXXXXX (Russian/KZ format with leading 8)
        if cleaned.startswith('8') and len(cleaned) == 11:
            cleaned = f'7{cleaned[1:]}'
        # XXXXXXXXXX → 7XXXXXXXXXX (10 digits without country code)
        elif len(cleaned) == 10:
            cleaned = f'7{cleaned}'
        # 77XXXXXXXXX or 76XXXXXXXXX — already correct KZ format
        elif cleaned.startswith('7') and len(cleaned) == 11:
            cleaned = cleaned
        return cleaned

    def is_configured(self) -> bool:
        return bool(self.access_token and self.phone_number_id)

    async def _send_raw(self, to: str, message: str) -> dict:
        """Low-level send. Returns raw API response dict."""
        url = f"{self.api_url}/{self.api_version}/{self.phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {"body": message}
        }
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(url, headers=headers, json=payload)
        return response.status_code, response.json()

    @staticmethod
    def _alternative_formats(phone: str) -> list[str]:
        """Generate alternative number formats to retry on 131030."""
        alts = []
        # 77XXXXXXXXX → 787XXXXXXXXX (insert 8 after country code)
        if len(phone) == 11 and phone.startswith('7'):
            alts.append(f"78{phone[1:]}")
        # 787XXXXXXXXX → 77XXXXXXXXX (remove the extra 8)
        if len(phone) == 12 and phone.startswith('78'):
            alts.append(f"7{phone[2:]}")
        return alts

    async def send_whatsapp_message(self, to: str, message: str) -> dict:
        if not self.is_configured():
            logger.error("❌ WhatsApp Business Cloud API is not configured")
            return {"error": "WhatsApp Business Cloud API is not configured"}

        normalized_to = self.normalize_phone_number(to)
        if not normalized_to or not normalized_to.isdigit():
            logger.error(f"❌ Invalid recipient phone number: {to}")
            return {"error": f"Invalid recipient phone number: {to}"}

        logger.info("📤 Sending WhatsApp Business Cloud API message")
        logger.info(f"   To: {normalized_to}")
        logger.info(f"   Message: {message[:100]}...")

        try:
            status_code, response_data = await self._send_raw(normalized_to, message)

            # On 131030 - try alternative number formats automatically
            if status_code >= 400:
                error_payload = response_data.get("error", {})
                if isinstance(error_payload, dict) and error_payload.get("code") == 131030:
                    logger.warning(f"⚠️ 131030 for {normalized_to}, trying alternative formats...")
                    for alt_phone in self._alternative_formats(normalized_to):
                        logger.info(f"   Retrying with: {alt_phone}")
                        status_code, response_data = await self._send_raw(alt_phone, message)
                        if status_code < 400:
                            logger.info(f"✅ Success with alternative format: {alt_phone}")
                            messages = response_data.get("messages", [])
                            message_id = messages[0].get("id") if messages else None
                            return {"sid": message_id, "status": "sent", "to": alt_phone}
                    logger.error(f"❌ All number formats failed for: {to}")
                    return {"error": "Recipient phone number not in allowed list. Add the recipient in Meta Dashboard."}
                logger.error(f"❌ WhatsApp Business Cloud API error: {error_payload}")
                return {"error": str(error_payload)}

            message_id = None
            if isinstance(response_data, dict):
                messages = response_data.get("messages")
                if isinstance(messages, list) and messages:
                    message_id = messages[0].get("id")

            logger.info(f"✅ Message sent: {message_id}")
            return {"sid": message_id, "status": "sent", "to": normalized_to}

        except Exception as e:
            logger.error(f"❌ Error sending WhatsApp Business Cloud API message: {e}")
            return {"error": str(e)}

    # ─── Template Message Methods ─────────────────────────────────────────────

    async def send_template_message(self, to: str, template_name: str,
                                     language_code: str = 'ru',
                                     body_params: list[str] | None = None) -> dict:
        """Send an approved WhatsApp template message."""
        if not self.is_configured():
            return {"error": "WhatsApp Business Cloud API is not configured"}

        normalized_to = self.normalize_phone_number(to)
        url = f"{self.api_url}/{self.api_version}/{self.phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        components = []
        if body_params:
            components.append({
                "type": "body",
                "parameters": [{"type": "text", "text": p} for p in body_params]
            })
        payload = {
            "messaging_product": "whatsapp",
            "to": normalized_to,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": language_code},
                "components": components,
            }
        }
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.post(url, headers=headers, json=payload)
            data = response.json()
            if response.status_code >= 400:
                logger.error(f"❌ Template send error: {data}")
                return {"error": str(data.get("error", data))}
            messages = data.get("messages", [])
            message_id = messages[0].get("id") if messages else None
            logger.info(f"✅ Template '{template_name}' sent to {normalized_to}: {message_id}")
            return {"sid": message_id, "status": "sent", "to": normalized_to}
        except Exception as e:
            logger.error(f"❌ Template send exception: {e}")
            return {"error": str(e)}

    async def submit_template_to_meta(self, name: str, body_text: str,
                                       category: str = "MARKETING",
                                       language: str = "ru",
                                       buttons: list[dict] | None = None) -> dict:
        """Submit a new message template to Meta for approval.

        Args:
            name: template name (must be lowercase + underscores, unique within WABA)
            body_text: body text with optional {{1}}, {{2}}... placeholders
            category: MARKETING | UTILITY | AUTHENTICATION
            language: language code (ru, en, kk, etc.)
            buttons: optional list of buttons. Each item:
                {"type": "QUICK_REPLY", "text": "Записаться"}
                {"type": "URL", "text": "Открыть сайт", "url": "https://..."}
                {"type": "PHONE_NUMBER", "text": "Позвонить", "phone_number": "+7..."}
                Limits: up to 10 Quick Reply, up to 2 URL/PHONE_NUMBER (mixed up to 10 total).

        Requires WHATSAPP_WABA_ID to be configured.
        """
        waba_id = settings.whatsapp_waba_id
        if not waba_id:
            return {"error": "WHATSAPP_WABA_ID not configured in .env"}
        if not self.access_token:
            return {"error": "WHATSAPP_ACCESS_TOKEN not configured"}

        url = f"{self.api_url}/{self.api_version}/{waba_id}/message_templates"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }

        components: list[dict] = [
            {"type": "BODY", "text": body_text}
        ]

        # Optional buttons component
        if buttons:
            meta_buttons = []
            for btn in buttons[:10]:  # Meta hard limit: 10 buttons
                btype = (btn.get("type") or "QUICK_REPLY").upper()
                text = (btn.get("text") or "").strip()
                if not text or len(text) > 25:
                    # Meta requires text ≤ 25 chars
                    continue
                entry = {"type": btype, "text": text}
                if btype == "URL" and btn.get("url"):
                    entry["url"] = btn["url"]
                elif btype == "PHONE_NUMBER" and btn.get("phone_number"):
                    entry["phone_number"] = btn["phone_number"]
                meta_buttons.append(entry)
            if meta_buttons:
                components.append({"type": "BUTTONS", "buttons": meta_buttons})

        payload = {
            "name": name,
            "category": category,
            "allow_category_change": True,
            "language": language,
            "components": components,
        }
        logger.info(f"📤 Submitting template '{name}' to Meta with {len(components)} components")

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.post(url, headers=headers, json=payload)
            data = response.json()
            if response.status_code >= 400:
                error = data.get("error", {})
                logger.error(f"❌ Template submission error: {error}")
                return {"error": str(error.get("message", error))}
            meta_id = data.get("id")
            meta_status = data.get("status", "PENDING")
            logger.info(f"✅ Template '{name}' submitted to Meta: id={meta_id} status={meta_status}")
            return {"meta_id": meta_id, "meta_status": meta_status, "name": name}
        except Exception as e:
            logger.error(f"❌ Template submission exception: {e}")
            return {"error": str(e)}

    async def get_meta_templates(self) -> dict:
        """Fetch all message templates from Meta for this WABA."""
        waba_id = settings.whatsapp_waba_id
        if not waba_id:
            return {"error": "WHATSAPP_WABA_ID not configured in .env", "templates": []}
        if not self.access_token:
            return {"error": "WHATSAPP_ACCESS_TOKEN not configured", "templates": []}

        url = f"{self.api_url}/{self.api_version}/{waba_id}/message_templates"
        params = {"access_token": self.access_token, "limit": 100,
                  "fields": "id,name,status,category,language,components"}
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.get(url, params=params)
            data = response.json()
            if response.status_code >= 400:
                return {"error": str(data.get("error", data)), "templates": []}
            templates = data.get("data", [])
            return {"templates": templates}
        except Exception as e:
            return {"error": str(e), "templates": []}

    async def delete_meta_template(self, name: str) -> dict:
        """Delete a template from Meta by name."""
        waba_id = settings.whatsapp_waba_id
        if not waba_id or not self.access_token:
            return {"error": "WABA not configured"}
        url = f"{self.api_url}/{self.api_version}/{waba_id}/message_templates"
        params = {"access_token": self.access_token, "name": name}
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.delete(url, params=params)
            if response.status_code >= 400:
                return {"error": str(response.json())}
            return {"success": True}
        except Exception as e:
            return {"error": str(e)}

    # ─── Reminder helpers ────────────────────────────────────────────────────
    #
    # All three reminders are BUSINESS-INITIATED messages sent to clients who
    # are likely outside the 24-hour reply window. WhatsApp policy requires
    # APPROVED message templates for such messages.
    #
    # Strategy: try the configured template first; if it fails (not configured,
    # not approved yet, or any API error) fall back to plain text — which only
    # works if the 24h window is still open, but is useful during development
    # and as a graceful degradation.
    # ─────────────────────────────────────────────────────────────────────────

    async def _send_template_or_fallback(
        self,
        to: str,
        template_name: str,
        body_params: list[str],
        fallback_text: str,
    ) -> dict:
        """Try sending an approved template; on failure, fall back to plain text.

        Before falling back to plain text, checks the 24-hour customer service
        window — if closed, returns an error without spending a doomed Meta call.
        """
        # Path A: template configured → try it first
        if template_name:
            result = await self.send_template_message(
                to=to,
                template_name=template_name,
                language_code=settings.template_language,
                body_params=body_params,
            )
            if "error" not in result:
                return result
            logger.warning(
                f"⚠️ Template '{template_name}' failed ({result.get('error')}). "
                f"Falling back to plain text if 24h window is open."
            )

        # ── Path B: plain text fallback — check 24h window first ────────────
        if not self._is_24h_window_open(to):
            logger.warning(
                f"📭 24h window closed for {to} — skipping plain text send. "
                f"Configure an approved template for this reminder type."
            )
            return {
                "error": "24h_window_closed",
                "detail": "Cannot send free-form text outside the 24-hour customer service window. Use an approved template."
            }

        return await self.send_whatsapp_message(to, fallback_text)

    @staticmethod
    def _is_24h_window_open(phone: str) -> bool:
        """Check if the WhatsApp 24-hour session window is still open for `phone`.

        Returns True if the last incoming user message was within ~23h.
        Returns True (permissive) if we have no record — first contact, can't be sure.
        """
        # Local import to avoid circular dep (database → ... → whatsapp_service)
        from app.database import get_last_user_message_at
        try:
            last_at = get_last_user_message_at(phone)
        except Exception as e:
            logger.warning(f"⚠️ Could not check 24h window for {phone}: {e}")
            return True  # fail-open: don't block legitimate sends on DB error
        if last_at is None:
            return False  # never spoke to us → window not open
        elapsed = (datetime.now() - last_at).total_seconds()
        return elapsed < WA_24H_WINDOW_SECONDS

    async def send_one_hour_reminder(self, to: str, client_name: str, master_name: str, datetime_str: str) -> dict:
        """Send 1-hour-before-appointment reminder.
        Template body should have 3 placeholders: {{1}}=name, {{2}}=master, {{3}}=time
        """
        fallback = (
            f"⏳ Ждём вас через час!\n\n"
            f"👤 {client_name}, до вашей записи осталось 60 минут.\n"
            f"💈 Мастер: {master_name}\n"
            f"⏰ Время: {datetime_str}\n"
            f"📍 Адрес: Момышулы 55\n\n"
            f"Если вы не успеваете — позвоните нам, мы перенесём запись."
        )
        return await self._send_template_or_fallback(
            to=to,
            template_name=settings.template_one_hour_reminder,
            body_params=[client_name, master_name, datetime_str],
            fallback_text=fallback,
        )

    async def send_revisit_reminder(self, to: str, client_name: str, last_visit_date: str) -> Dict[str, Any]:
        """Send 20-days-after-visit revisit reminder.
        Template body should have 2 placeholders: {{1}}=name, {{2}}=last_visit_date
        """
        fallback = (
            f"💈 Привет, {client_name}!\n\n"
            f"Прошло 20 дней с вашего последнего визита {last_visit_date}. "
            f"Пришло время записаться снова.\n\n"
            f"Просто напишите нам в WhatsApp — бот подберёт удобное время.\n\n"
            f"Ждём вас в KHAN Barbershop! 👋"
        )
        return await self._send_template_or_fallback(
            to=to,
            template_name=settings.template_revisit_reminder,
            body_params=[client_name, last_visit_date],
            fallback_text=fallback,
        )

    async def send_nps_request(self, to: str, client_name: str, master_name: str) -> Dict[str, Any]:
        """Send NPS rating request ~1h after appointment ends.
        Template body should have 2 placeholders: {{1}}=name, {{2}}=master
        """
        fallback = (
            f"Здравствуйте, {client_name}! ✂️\n\n"
            f"Вы недавно посетили KHAN Barbershop у мастера {master_name}.\n"
            f"Пожалуйста, оцените вашу стрижку от 1 до 5!\n\n"
            f"(Отправьте цифру в ответ на это сообщение)"
        )
        return await self._send_template_or_fallback(
            to=to,
            template_name=settings.template_nps_request,
            body_params=[client_name, master_name],
            fallback_text=fallback,
        )


whatsapp_service = WhatsAppCloudService()