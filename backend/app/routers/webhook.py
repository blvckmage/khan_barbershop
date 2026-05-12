import logging
import os
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse, JSONResponse
from app.models.schemas import ManyChatRequest, ChatResponse
from app.services.ai_agent_service import ai_agent_service
from app.services.whatsapp_service import whatsapp_service
from app.config import get_settings
from app.database import add_log

router = APIRouter(prefix="/webhook", tags=["webhook"])
logger = logging.getLogger(__name__)
settings = get_settings()

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
            from app.routers.websocket import manager
            await manager.broadcast({"type": "NEW_CHAT", "data": {"phone": request.user_phone, "message": request.user_input, "response": response, "intent": "manychat", "timestamp": datetime.now().isoformat()}})
        except Exception as e:
            logger.error(f"   ⚠️ Failed to save log to DB or broadcast: {e}")
        
        logger.info(f"   ✅ Response sent: {response[:100]}...")
        return ChatResponse(output=response)
    
    except Exception as e:
        logger.error(f"   ❌ Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/whatsapp")
async def whatsapp_webhook_verify(
    hub_mode: str | None = Query(None, alias="hub.mode"),
    hub_verify_token: str | None = Query(None, alias="hub.verify_token"),
    hub_challenge: str | None = Query(None, alias="hub.challenge")
):
    """Webhook verification endpoint for WhatsApp Business Cloud API."""
    if hub_mode == "subscribe" and hub_verify_token == settings.whatsapp_verify_token:
        return PlainTextResponse(content=hub_challenge or "")
    raise HTTPException(status_code=400, detail="Webhook verification failed")


@router.post("/whatsapp")
async def whatsapp_webhook(request: Request):
    """Incoming WhatsApp Business Cloud API webhook."""
    logger.info("📲 WhatsApp Business Cloud API webhook received")
    write_log("INFO", "📲 WhatsApp Business Cloud API webhook received")

    try:
        payload = await request.json()
        logger.debug(f"WhatsApp webhook payload: {payload}")

        entries = payload.get("entry", [])
        if not entries:
            raise HTTPException(status_code=400, detail="Invalid webhook payload")

        phone = None
        message_text = None
        for entry in entries:
            for change in entry.get("changes", []):
                value = change.get("value", {})
                for message in value.get("messages", []):
                    if message.get("type") == "text":
                        phone = message.get("from")
                        message_text = message.get("text", {}).get("body", "")
                        break
                if message_text:
                    break
            if message_text:
                break

        if not phone or not message_text:
            logger.info("📭 Incoming webhook does not contain a text message or phone number")
            return JSONResponse(status_code=200, content={"success": True, "skipped": True})

        logger.info(f"   From: {phone}")
        logger.info(f"   Body: {message_text}")
        write_log("INFO", f"From: {phone}, Body: {message_text}")

        session_id = phone
        response = await ai_agent_service.chat(
            user_input=message_text,
            session_id=session_id,
            user_phone=phone
        )

        logger.info(f"   ✅ Response: {response[:100]}...")
        write_log("INFO", f"Response: {response[:100]}...")

        try:
            add_log(phone=phone, message=message_text, response=response, intent="whatsapp")
            from app.routers.websocket import manager
            await manager.broadcast({"type": "NEW_CHAT", "data": {"phone": phone, "message": message_text, "response": response, "intent": "whatsapp", "timestamp": datetime.now().isoformat()}})
        except Exception as e:
            logger.error(f"   ⚠️ Failed to save log to DB or broadcast: {e}")

        result = await whatsapp_service.send_whatsapp_message(to=phone, message=response)
        if "error" in result:
            logger.error(f"   ❌ Failed to send reply: {result['error']}")
            return JSONResponse(status_code=200, content={"success": False, "error": result["error"]})

        return JSONResponse(status_code=200, content={"success": True})

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"   ❌ Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


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
    logger.info("📤 Send notification request")

    try:
        phone = request.get("phone")
        if not phone:
            raise HTTPException(status_code=400, detail="Phone number required")

        message = request.get("message", "").strip()
        if not message:
            raise HTTPException(status_code=400, detail="Message text is required")

        result = await whatsapp_service.send_whatsapp_message(
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
        
        try:
            from app.routers.websocket import manager
            await manager.broadcast({"type": "NEW_CHAT", "data": {"phone": user_phone or session_id, "message": message, "response": response, "intent": "generic", "timestamp": datetime.now().isoformat()}})
        except Exception as e:
            pass
            
        logger.info(f"   ✅ Response sent: {response[:100]}...")
        return ChatResponse(output=response)
    
    except Exception as e:
        logger.error(f"   ❌ Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
