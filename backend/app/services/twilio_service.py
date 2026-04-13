"""
Twilio Service for WhatsApp and SMS integration.
Handles incoming WhatsApp messages and outgoing notifications.
"""
import logging
import asyncio
from typing import Optional
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse
from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class TwilioService:
    """Service for Twilio WhatsApp and SMS integration"""
    
    def __init__(self):
        self.account_sid = settings.twilio_account_sid
        self.auth_token = settings.twilio_auth_token
        self.phone_number = settings.twilio_phone_number
        
        if self.account_sid and self.auth_token:
            self.client = Client(self.account_sid, self.auth_token)
            logger.info(f"📱 TwilioService initialized with phone: {self.phone_number}")
        else:
            self.client = None
            logger.warning("⚠️ Twilio credentials not configured")

    @staticmethod
    def normalize_phone_number(phone: str) -> str:
        """Normalize a phone number to international E.164-like format."""
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

    def is_configured(self) -> bool:
        """Check if Twilio is properly configured"""
        return self.client is not None
    
    async def send_whatsapp_message(
        self, 
        to: str, 
        message: str
    ) -> dict:
        """
        Send WhatsApp message via Twilio.
        
        Args:
            to: Recipient phone number (e.g., whatsapp:+77071234567)
            message: Message text
        
        Returns:
            Dict with message SID and status
        """
        if not self.is_configured():
            logger.error("❌ Twilio not configured")
            return {"error": "Twilio not configured"}
        
        normalized = self.normalize_phone_number(to)
        if not normalized or not normalized.startswith('+'):
            logger.error(f"❌ Invalid recipient phone number: {to}")
            return {"error": f"Invalid recipient phone number: {to}"}
        
        if not normalized.startswith("whatsapp:"):
            to = f"whatsapp:{normalized}"
        else:
            to = normalized
        
        logger.info(f"📤 Sending WhatsApp message")
        logger.info(f"   To: {to}")
        logger.info(f"   Message: {message[:100]}...")
        
        try:
            msg = await asyncio.to_thread(
                self.client.messages.create,
                from_=self.phone_number,
                body=message,
                to=to
            )
            
            logger.info(f"   ✅ Message sent: {msg.sid}")
            return {
                "sid": msg.sid,
                "status": msg.status,
                "to": to
            }
        except Exception as e:
            logger.error(f"   ❌ Error sending message: {e}")
            return {"error": str(e)}
    
    async def send_sms(
        self, 
        to: str, 
        message: str
    ) -> dict:
        """
        Send SMS via Twilio.
        
        Args:
            to: Recipient phone number (e.g., +77071234567)
            message: Message text (max 1600 chars)
        
        Returns:
            Dict with message SID and status
        """
        if not self.is_configured():
            logger.error("❌ Twilio not configured")
            return {"error": "Twilio not configured"}
        
        # Remove WhatsApp prefix if present
        if to.startswith("whatsapp:"):
            to = to.replace("whatsapp:", "")
        
        # Use regular phone number for SMS
        from_number = self.phone_number.replace("whatsapp:", "") if self.phone_number.startswith("whatsapp:") else self.phone_number
        
        logger.info(f"📤 Sending SMS")
        logger.info(f"   To: {to}")
        logger.info(f"   Message: {message[:100]}...")
        
        try:
            msg = await asyncio.to_thread(
                self.client.messages.create,
                from_=from_number,
                body=message,
                to=to
            )
            
            logger.info(f"   ✅ SMS sent: {msg.sid}")
            return {
                "sid": msg.sid,
                "status": msg.status,
                "to": to
            }
        except Exception as e:
            logger.error(f"   ❌ Error sending SMS: {e}")
            return {"error": str(e)}
    
    async def send_one_hour_reminder(
        self,
        to: str,
        client_name: str,
        master_name: str,
        datetime_str: str
    ) -> dict:
        """
        Send reminder 1 hour before appointment via WhatsApp.
        
        Args:
            to: Client phone number
            client_name: Client name
            master_name: Master name
            datetime_str: Appointment date and time
        
        Returns:
            Dict with message SID and status
        """
        message = f"""⏳ Ждем вас через час!

👤 {client_name}, до вашей записи осталось 60 минут.

💈 Мастер: {master_name}
⏰ Время: {datetime_str}
📍 Адрес: Момышулы 55

Если вы не успеваете - позвоните нам, мы перенесем вашу запись.

До встречи! ✂️"""
        
        return await self.send_whatsapp_message(to, message)

    async def send_revisit_reminder(
        self,
        to: str,
        client_name: str,
        last_visit_date: str
    ) -> dict:
        """
        Send reminder to come back after 20 days since last visit.
        
        Args:
            to: Client phone number
            client_name: Client name
            last_visit_date: Date of last haircut
        
        Returns:
            Dict with message SID and status
        """
        message = f"""💈 Привет {client_name}!

Прошло уже 20 дней с вашего последнего визита {last_visit_date}. Время обновить стрижку!

Запишитесь прямо сейчас через WhatsApp бот или позвоните нам по номеру 87071272796.

Ждем вас в KHAN Barbershop! 👋"""
        
        return await self.send_whatsapp_message(to, message)
    
    def parse_webhook_data(self, form_data: dict) -> dict:
        """
        Parse incoming Twilio webhook data.
        
        Args:
            form_data: Form data from Twilio webhook
        
        Returns:
            Dict with parsed message data
        """
        return {
            "message_sid": form_data.get("MessageSid", ""),
            "account_sid": form_data.get("AccountSid", ""),
            "from_number": form_data.get("From", ""),  # whatsapp:+77071234567
            "to_number": form_data.get("To", ""),
            "body": form_data.get("Body", ""),
            "num_media": int(form_data.get("NumMedia", 0)),
            "media_urls": [
                form_data.get(f"MediaUrl{i}", "") 
                for i in range(int(form_data.get("NumMedia", 0)))
            ],
            "profile_name": form_data.get("ProfileName", ""),  # WhatsApp profile name
            "wa_id": form_data.get("WaId", ""),  # WhatsApp ID (phone without +)
        }
    
    def create_response(self, message: str) -> str:
        """
        Create TwiML response for webhook.
        
        Args:
            message: Response message
        
        Returns:
            TwiML XML string
        """
        response = MessagingResponse()
        response.message(message)
        return str(response)


# Singleton instance
twilio_service = TwilioService()