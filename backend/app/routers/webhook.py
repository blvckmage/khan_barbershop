import logging
import os
from datetime import datetime
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import PlainTextResponse
from app.models.schemas import ManyChatRequest, ChatResponse
from app.services.ai_agent_service import ai_agent_service
from app.services.twilio_service import twilio_service
from app.database import add_log

router = APIRouter(prefix="/webhook", tags=["webhook"])
logger = logging.getLogger(__name__)

# Путь к файлу логов
LOG_FILE = os.path.join("logs", "app.log")

def write_log(level: str, message: str):
    """Прямая запись лога в файл"""
    try:
        os.makedirs("logs", exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"{timestamp} - app.webhook - {level} - {message}\n")
    except Exception as e:
        logger.error(f"Failed to write log: {e}")

def flush_logs():
    """Принудительно сбрасывает буфер логов в файл"""
    for handler in logging.root.handlers:
        if hasattr(handler, 'flush'):
            handler.flush()


@router.post("/wa_khan_main_chatbot", response_model=ChatResponse)
async def mannychat_webhook(request: ManyChatRequest):
    """
    Main webhook for ManyChat integration.
    Receives user input and phone number, returns AI response.
    
    Corresponds to "Webhook for Main Chatbot" in n8n.
    Endpoint: POST /webhook/wa_khan_main_chatbot
    """
    logger.info(f"📩 ManyChat webhook received")
    logger.info(f"   user_input: {request.user_input}")
    logger.info(f"   user_phone: {request.user_phone}")
    
    try:
        # Use phone number as session ID for conversation memory
        session_id = request.user_phone
        
        response = await ai_agent_service.chat(
            user_input=request.user_input,
            session_id=session_id,
            user_phone=request.user_phone
        )
        
        # Сохраняем лог в базу данных
        try:
            add_log(phone=request.user_phone, message=request.user_input, response=response, intent="manychat")
        except Exception as e:
            logger.error(f"   ⚠️ Failed to save log to DB: {e}")
        
        logger.info(f"   ✅ Response sent: {response[:100]}...")
        return ChatResponse(output=response)
    
    except Exception as e:
        logger.error(f"   ❌ Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/twilio/whatsapp")
async def twilio_whatsapp_webhook(request: Request):
    """
    Webhook for Twilio WhatsApp messages.
    Twilio sends data as form-urlencoded.
    
    Endpoint: POST /webhook/twilio/whatsapp
    
    Setup in Twilio Console:
    1. Go to Messaging > Try it out > Send a WhatsApp message
    2. Or configure WhatsApp Business API
    3. Set webhook URL: https://your-domain.com/webhook/twilio/whatsapp
    """
    logger.info(f"📲 Twilio WhatsApp webhook received")
    write_log("INFO", "📲 Twilio WhatsApp webhook received")
    
    try:
        # Parse form data from Twilio
        form_data = await request.form()
        data = twilio_service.parse_webhook_data(dict(form_data))
        
        logger.info(f"   From: {data['from_number']}")
        logger.info(f"   Profile: {data['profile_name']}")
        logger.info(f"   Body: {data['body']}")
        write_log("INFO", f"From: {data['from_number']}, Body: {data['body']}")
        
        # Extract phone number (remove whatsapp: prefix)
        phone = data['from_number'].replace('whatsapp:', '')
        
        # Use phone as session ID
        session_id = phone
        
        # Get AI response
        response = await ai_agent_service.chat(
            user_input=data['body'],
            session_id=session_id,
            user_phone=phone
        )
        
        logger.info(f"   ✅ Response: {response[:100]}...")
        write_log("INFO", f"Response: {response[:100]}...")
        
        # Сохраняем лог в базу данных
        try:
            add_log(phone=phone, message=data['body'], response=response, intent="whatsapp")
        except Exception as e:
            logger.error(f"   ⚠️ Failed to save log to DB: {e}")
        
        # Return TwiML response
        twiml = twilio_service.create_response(response)
        logger.info(f"   📤 TwiML response: {twiml}")
        
        return PlainTextResponse(content=twiml, media_type="application/xml")
    
    except Exception as e:
        logger.error(f"   ❌ Error: {e}", exc_info=True)
        # Return error message as TwiML
        twiml = twilio_service.create_response("Извините, произошла ошибка. Попробуйте позже.")
        return PlainTextResponse(content=twiml, media_type="application/xml")


@router.post("/twilio/sms")
async def twilio_sms_webhook(request: Request):
    """
    Webhook for Twilio SMS messages.
    
    Endpoint: POST /webhook/twilio/sms
    """
    logger.info(f"📱 Twilio SMS webhook received")
    
    try:
        form_data = await request.form()
        data = twilio_service.parse_webhook_data(dict(form_data))
        
        logger.info(f"   From: {data['from_number']}")
        logger.info(f"   Body: {data['body']}")
        
        phone = data['from_number']
        session_id = phone
        
        response = await ai_agent_service.chat(
            user_input=data['body'],
            session_id=session_id,
            user_phone=phone
        )
        
        twiml = twilio_service.create_response(response)
        return PlainTextResponse(content=twiml, media_type="application/xml")
    
    except Exception as e:
        logger.error(f"   ❌ Error: {e}", exc_info=True)
        twiml = twilio_service.create_response("Произошла ошибка. Попробуйте позже.")
        return PlainTextResponse(content=twiml, media_type="application/xml")


@router.post("/send-notification")
async def send_notification(request: dict):
    """
    Send WhatsApp notification to client.
    
    Request body:
    {
        "phone": "+77071234567",
        "message": "Ваше сообщение для клиента"
    }
    """
    logger.info(f"📤 Send notification request")
    
    try:
        phone = request.get("phone")
        notification_type = request.get("type", "confirmation")
        
        if not phone:
            raise HTTPException(status_code=400, detail="Phone number required")
        
        message = request.get("message", "").strip()
        if not message:
            raise HTTPException(status_code=400, detail="Message text is required")

        result = await twilio_service.send_whatsapp_message(
            to=phone,
            message=message
        )
        
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        
        return {"status": "sent", "sid": result.get("sid")}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"   ❌ Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat", response_model=ChatResponse)
async def generic_chat(request: dict):
    """
    Generic chat endpoint for testing or other integrations.
    
    Request body:
    {
        "message": "user message",
        "session_id": "unique_session_id",
        "user_phone": "optional phone number"
    }
    """
    logger.info(f"💬 Generic chat received")
    logger.info(f"   request: {request}")
    
    try:
        message = request.get("message", "")
        session_id = request.get("session_id", "default")
        user_phone = request.get("user_phone")
        
        response = await ai_agent_service.chat(
            user_input=message,
            session_id=session_id,
            user_phone=user_phone
        )
        
        logger.info(f"   ✅ Response sent: {response[:100]}...")
        return ChatResponse(output=response)
    
    except Exception as e:
        logger.error(f"   ❌ Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
