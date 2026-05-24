import logging
import os
import re
import json
import hmac
import hashlib
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse, JSONResponse
from app.models.schemas import ManyChatRequest, ChatResponse
from app.services.ai_agent_service import ai_agent_service
from app.services.whatsapp_service import whatsapp_service
from app.config import get_settings
from app.database import (
    add_log, add_nps_rating, get_last_nps_context,
    is_webhook_processed, mark_webhook_processed,
)

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


def _extract_incoming_message(payload: dict) -> tuple[str | None, str | None, str | None, str | None]:
    """Extract (phone, text, payload, message_id) from any supported WhatsApp message type.

    Supports:
      - text             → user typed
      - button           → Quick Reply button in a TEMPLATE (legacy field)
      - interactive      → button_reply / list_reply in interactive messages

    Returns (phone, text, payload, message_id):
      - phone: sender's number
      - text: human-readable text of the message/button
      - payload: machine-readable id/payload of the button (None for free text)
      - message_id: WhatsApp wamid for idempotency (None if Meta didn't include it)
    """
    for entry in payload.get("entry", []) or []:
        for change in entry.get("changes", []) or []:
            value = change.get("value", {}) or {}
            for message in value.get("messages", []) or []:
                msg_type = message.get("type")
                phone = message.get("from")
                wamid = message.get("id")  # wamid.HBg... — globally unique

                if msg_type == "text":
                    body = (message.get("text") or {}).get("body", "")
                    return phone, body, None, wamid

                if msg_type == "button":
                    btn = message.get("button", {}) or {}
                    return phone, btn.get("text", ""), btn.get("payload"), wamid

                if msg_type == "interactive":
                    interactive = message.get("interactive", {}) or {}
                    itype = interactive.get("type")
                    if itype == "button_reply":
                        br = interactive.get("button_reply", {}) or {}
                        return phone, br.get("title", ""), br.get("id"), wamid
                    if itype == "list_reply":
                        lr = interactive.get("list_reply", {}) or {}
                        return phone, lr.get("title", ""), lr.get("id"), wamid

    return None, None, None, None


def _verify_meta_signature(raw_body: bytes, signature_header: str, app_secret: str) -> bool:
    """Verify X-Hub-Signature-256 header from Meta against raw request body.

    Meta sends signature in format: "sha256=<hex>"
    """
    if not signature_header or not app_secret:
        return False
    expected = hmac.new(
        app_secret.encode("utf-8"),
        msg=raw_body,
        digestmod=hashlib.sha256
    ).hexdigest()
    expected_header = f"sha256={expected}"
    # Use compare_digest to prevent timing attacks
    return hmac.compare_digest(expected_header, signature_header)


def _detect_nps_rating(text: str | None, payload: str | None) -> int | None:
    """Detect an NPS rating 1-5 from button payload or message text.

    Priority:
      1. payload like "nps_5" or "rating_3" → exact rating
      2. text exactly "1", "2", "3", "4", "5" → rating
      3. text like "5/5", "5 из 5" → rating
    """
    # 1. Payload-based (most reliable for template buttons)
    if payload:
        m = re.match(r'^(?:nps|rating)[_\-]?([1-5])$', payload, re.IGNORECASE)
        if m:
            return int(m.group(1))

    if not text:
        return None
    t = text.strip()

    # 2. Plain digit "1"–"5"
    if t in {"1", "2", "3", "4", "5"}:
        return int(t)

    # 3. Patterns like "5/5", "5 из 5", "оценка 5"
    m = re.match(r'^([1-5])\s*(?:/\s*5|из\s+5|балл)?$', t, re.IGNORECASE)
    if m:
        return int(m.group(1))

    return None


@router.post("/whatsapp")
async def whatsapp_webhook(request: Request):
    """Incoming WhatsApp Business Cloud API webhook.

    Handles 3 message types:
      - text:        passed to AI agent
      - button:      template Quick Reply (e.g., "Записаться" → AI agent;
                     NPS 1-5 → saved to nps_ratings, thanks reply, no AI)
      - interactive: button_reply / list_reply (same logic as button)
    """
    logger.info("📲 WhatsApp Business Cloud API webhook received")
    write_log("INFO", "📲 WhatsApp Business Cloud API webhook received")

    try:
        # Read raw body FIRST — required for HMAC verification before JSON parse
        raw_body = await request.body()

        # ── Verify Meta signature (HMAC-SHA256) ──────────────────────────────
        if settings.whatsapp_app_secret:
            signature_header = request.headers.get("X-Hub-Signature-256", "")
            if not _verify_meta_signature(raw_body, signature_header, settings.whatsapp_app_secret):
                logger.warning(f"⚠️ Webhook signature invalid — possible spoof attempt from {request.client.host if request.client else '?'}")
                raise HTTPException(status_code=401, detail="Invalid signature")
        else:
            logger.warning("⚠️ WHATSAPP_APP_SECRET not configured — webhook signature NOT verified (insecure)")

        try:
            payload = json.loads(raw_body)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON")

        logger.debug(f"WhatsApp webhook payload: {payload}")

        entries = payload.get("entry", [])
        if not entries:
            raise HTTPException(status_code=400, detail="Invalid webhook payload")

        phone, message_text, button_payload, message_id = _extract_incoming_message(payload)

        if not phone or (not message_text and not button_payload):
            logger.info("📭 Incoming webhook does not contain a supported message")
            return JSONResponse(status_code=200, content={"success": True, "skipped": True})

        # ── Idempotency: drop duplicate webhooks from Meta retries ───────────
        if message_id and is_webhook_processed(message_id):
            logger.info(f"⏭️  Duplicate webhook (wamid={message_id}) — already processed, skipping")
            return JSONResponse(status_code=200, content={"success": True, "duplicate": True})

        # Mark as processed BEFORE any heavy work, so concurrent retries also bail
        if message_id:
            mark_webhook_processed(message_id)

        logger.info(f"   From: {phone}")
        logger.info(f"   Text: {message_text!r}   Payload: {button_payload!r}")
        write_log("INFO", f"From: {phone}, Text: {message_text!r}, Payload: {button_payload!r}")

        # ── NPS rating handling ──────────────────────────────────────────────
        # If this looks like an NPS rating AND there's an unanswered NPS
        # request for this phone in the last 72h — save the rating and skip AI.
        rating = _detect_nps_rating(message_text, button_payload)
        if rating is not None:
            ctx = get_last_nps_context(phone)
            if ctx:
                saved = add_nps_rating(
                    phone=phone,
                    rating=rating,
                    appointment_id=ctx.get("appointment_id"),
                    master_name=ctx.get("master_name"),
                    client_name=ctx.get("client_name"),
                )
                client_name = ctx.get("client_name") or ""
                greet = f", {client_name}" if client_name else ""
                if saved:
                    logger.info(f"   ⭐ NPS rating {rating} saved for {phone} (master={ctx.get('master_name')})")
                    thanks = (
                        f"Спасибо за оценку{greet}! 🙏\n"
                        f"Ваш отзыв помогает нам становиться лучше. Ждём вас снова! ✂️"
                    )
                else:
                    logger.info(f"   ⏭️  NPS rating {rating} already exists for appointment {ctx.get('appointment_id')}")
                    thanks = f"Мы уже получили вашу оценку{greet}, спасибо! 🙏"

                await whatsapp_service.send_whatsapp_message(to=phone, message=thanks)

                # Mirror in chat log for the admin
                try:
                    add_log(
                        phone=phone,
                        message=f"[NPS RATING] {rating}/5",
                        response=thanks,
                        intent="nps_rating",
                    )
                    from app.routers.websocket import manager
                    await manager.broadcast({
                        "type": "NEW_CHAT",
                        "data": {
                            "phone": phone,
                            "message": f"⭐ Оценка: {rating}/5",
                            "response": thanks,
                            "intent": "nps_rating",
                            "timestamp": datetime.now().isoformat(),
                        },
                    })
                except Exception as e:
                    logger.error(f"   ⚠️ Failed to save NPS log: {e}")

                return JSONResponse(status_code=200, content={"success": True, "nps_saved": saved, "rating": rating})
            else:
                # Looks like a rating but no recent NPS request → fall through to AI
                # (might just be the client saying "5 человек" or similar)
                logger.info(f"   ℹ️  Looks like a rating but no pending NPS request — passing to AI")

        # ── Normal flow: pass to AI agent ────────────────────────────────────
        # button_payload may contain machine-readable id (e.g., "book_now") —
        # we pass the human-readable text to the AI; the AI will treat it as
        # user input and trigger booking flow naturally.
        user_input = message_text or button_payload or ""

        session_id = phone
        response = await ai_agent_service.chat(
            user_input=user_input,
            session_id=session_id,
            user_phone=phone,
        )

        logger.info(f"   ✅ Response: {response[:100]}...")
        write_log("INFO", f"Response: {response[:100]}...")

        try:
            add_log(phone=phone, message=user_input, response=response, intent="whatsapp")
            from app.routers.websocket import manager
            await manager.broadcast({
                "type": "NEW_CHAT",
                "data": {
                    "phone": phone,
                    "message": user_input,
                    "response": response,
                    "intent": "whatsapp",
                    "timestamp": datetime.now().isoformat(),
                },
            })
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
