"""
WhatsApp Business Cloud API Service.
Handles outgoing WhatsApp messages through Meta Graph API.
"""
import logging
import asyncio
from typing import Optional, Dict, Any
import httpx
from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


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

    async def send_one_hour_reminder(self, to: str, client_name: str, master_name: str, datetime_str: str) -> dict:
        message = f"""
⏳ Ждём вас через час!

👤 {client_name}, до вашей записи осталось 60 минут.
💈 Мастер: {master_name}
⏰ Время: {datetime_str}
📍 Адрес: Момышулы 55

Если вы не успеваете - позвоните нам, мы перенесём запись.
"""
        return await self.send_whatsapp_message(to, message.strip())

    async def send_revisit_reminder(self, to: str, client_name: str, last_visit_date: str) -> Dict[str, Any]:
        message = f"""💈 Привет, {client_name}!

Прошло 20 дней с вашего последнего визита {last_visit_date}. Пришло время записаться снова.

Напишите нам в WhatsApp или позвоните по номеру +7XXXXXXXXXX.

Ждём вас в KHAN Barbershop! 👋"""
        return await self.send_whatsapp_message(to, message)

    async def send_nps_request(self, to: str, client_name: str, master_name: str) -> Dict[str, Any]:
        message = f"""Здравствуйте, {client_name}! ✂️

Вы недавно посетили KHAN Barbershop у мастера {master_name}.
Пожалуйста, оцените вашу стрижку от 1 до 5!

(Отправьте цифру в ответ на это сообщение)"""
        return await self.send_whatsapp_message(to, message)


whatsapp_service = WhatsAppCloudService()