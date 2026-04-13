import os
import logging
import asyncio
import json
from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from ..database import (
    init_db, get_logs, get_broadcasts, add_broadcast, update_broadcast_summary,
    add_broadcast_log, delete_broadcast, verify_user, get_broadcast_settings,
    update_broadcast_settings
)
from ..services.alteegio_service import alteegio_service
from ..services.twilio_service import twilio_service

# Путь к файлу логов (относительно директории backend, откуда запускается uvicorn)
LOG_FILE = os.path.join("logs", "app.log")

router = APIRouter(prefix="/api/admin", tags=["admin"])

# Initialize database on startup
init_db()

# Pydantic models
class LoginRequest(BaseModel):
    username: str
    password: str

class BroadcastCreate(BaseModel):
    message: str
    recipients: list[str]

class MasterUpdate(BaseModel):
    is_active: bool

class BroadcastSettingsUpdate(BaseModel):
    enabled: bool
    phoneNumbers: str
    messageTemplate: str
    schedule: str
    sendTime: str

# Simple token verification
def verify_token(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized")
    token = authorization.replace("Bearer ", "")
    if not token.startswith("token_"):
        raise HTTPException(status_code=401, detail="Invalid token")
    return token

# Routes
@router.post("/login")
async def login(data: LoginRequest):
    token = verify_user(data.username, data.password)
    if not token:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"token": token, "username": data.username}

@router.get("/stats")
async def get_stats(token: str = Depends(verify_token)):
    """
    Получает статистику из Alteegio API:
    - todayAppointments: количество записей за сегодня
    - todayChats: количество чатов из локальной БД
    - totalClients: уникальные клиенты за сегодня
    - totalMasters: количество мастеров
    - recentAppointments: последние 5 записей
    - recentChats: последние 5 чатов
    """
    try:
        # Get today's records from Alteegio
        today = datetime.now().strftime("%Y-%m-%d")
        records = await alteegio_service.get_records(today)
        
        # Calculate stats - ONLY appointments created via chatbot
        bot_appointments = []
        unique_clients = set()
        
        for r in (records or []):
            # Filter only appointments created by bot (have special comment)
            comment = r.get("comment", "") or ""
            if "ЧЕРЕЗ БОТА" in comment or "бота" in comment.lower():
                bot_appointments.append(r)
                client = r.get("client") or {}
                if client.get("phone"):
                    unique_clients.add(client["phone"])
        
        today_appointments = len(bot_appointments)
        
        # Get staff count
        staff = await alteegio_service.get_staff()
        staff_count = len(staff) if staff else 0
        
        # Get logs from database for chat count and recent chats
        logs = get_logs(1, 1000)
        log_items = logs.get("items", [])
        total_logs = logs.get("total", 0)
        
        today_str = datetime.now().strftime("%Y-%m-%d")
        recent_logs = log_items[-5:]
        today_logs = [log for log in log_items if (log.get("timestamp") or "").startswith(today_str)]
        unique_clients_logs = {log.get("phone") for log in log_items if log.get("phone")}
        active_chats = 0
        try:
            now = datetime.now()
            recent_24h = []
            for log in log_items:
                ts = log.get("timestamp") or ""
                if ts:
                    log_dt = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
                    if (now - log_dt).total_seconds() <= 24 * 3600:
                        recent_24h.append(log)
            active_chats = len({log.get("phone") for log in recent_24h if log.get("phone")})
        except Exception:
            active_chats = len(unique_clients_logs)
        
        # Format recent appointments safely - ONLY bot appointments
        recent_appointments = []
        for r in bot_appointments[:5]:
            try:
                dt = r.get("datetime") or ""
                time_str = dt.split("T")[1][:5] if "T" in dt else ""
                staff_info = r.get("staff") or {}
                client_info = r.get("client") or {}
                services = r.get("services") or []
                
                recent_appointments.append({
                    "time": time_str,
                    "master": staff_info.get("name", "Unknown"),
                    "client": client_info.get("phone", ""),
                    "service": services[0].get("name", "") if services else ""
                })
            except:
                pass
        
        # Format recent chats
        recent_chats = []
        for log in recent_logs:
            try:
                ts = log.get("timestamp") or ""
                recent_chats.append({
                    "phone": log.get("phone", ""),
                    "lastMessage": (log.get("message") or "")[:50],
                    "time": ts.split(" ")[1][:5] if " " in ts else ""
                })
            except:
                pass
 
        return {
            "appointments_today": today_appointments,
            "today_chats": len(today_logs),
            "messages_processed": total_logs,
            "avg_response_time": 0.0,
            "successful_chats": len(unique_clients_logs),
            "active_chats": active_chats,
            "total_clients": len(unique_clients),
            "total_masters": staff_count,
             "recentAppointments": recent_appointments,
             "recentChats": recent_chats
         }
    except Exception as e:
        # Fallback to mock data if Alteegio fails
        return {
            "todayAppointments": 0,
            "recentAppointments": [],
            "recentChats": [],
            "error": str(e)
        }

@router.get("/masters")
async def list_masters(token: str = Depends(verify_token)):
    """
    Получает список мастеров из Alteegio API.
    Поля: id, name, position, schedule, status, is_active, rating
    """
    try:
        staff = await alteegio_service.get_staff()
        return [
            {
                "id": s.get("id"),
                "name": s.get("name"),
                "position": s.get("specialization", "Барбер"),
                "schedule": f"{s.get('work_time', {}).get('start', '10:00')} - {s.get('work_time', {}).get('end', '21:00')}",
                "status": "available" if s.get("bookable", False) else "busy",
                "is_active": s.get("bookable", False),
                "rating": s.get("rating", 5.0)
            }
            for s in staff
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/masters/{master_id}")
async def edit_master(master_id: int, data: MasterUpdate, token: str = Depends(verify_token)):
    """
    Изменяет активность мастера.
    ВНИМАНИЕ: Alteegio API не поддерживает изменение статуса мастера!
    Этот эндпоинт просто возвращает успех, но НЕ меняет данные в Alteegio.
    Для реальной функциональности нужно использовать Alteegio Admin Panel.
    """
    # Note: Alteegio API does not support updating staff status
    # This would require direct database access or Alteegio admin panel
    return {
        "success": False,
        "master_id": master_id, 
        "is_active": data.is_active,
        "message": "Alteegio API не поддерживает изменение статуса мастера. Используйте панель администратора Alteegio."
    }

@router.get("/logs")
async def list_logs(page: int = 1, limit: int = 50, token: str = Depends(verify_token)):
    """Получает логи чатов из локальной SQLite БД."""
    return get_logs(page, limit)

@router.get("/broadcasts")
async def list_broadcasts(page: int = 1, limit: int = 50, token: str = Depends(verify_token)):
    """
    Получает историю рассылок из локальной SQLite БД.
    """
    items = get_broadcasts(page, limit)
    return {
        "items": [
            {
                "id": item.get("id"),
                "message": item.get("message"),
                "recipientCount": item.get("recipients_count", 0),
                "sentCount": item.get("sent_count", 0),
                "failedCount": item.get("failed_count", 0),
                "status": item.get("status", "pending"),
                "createdAt": item.get("created_at"),
                "completedAt": item.get("completed_at"),
            }
            for item in items.get("items", [])
        ],
        "total": items.get("total", 0),
        "page": items.get("page", 1),
        "limit": items.get("limit", limit)
    }


@router.post("/broadcasts")
async def create_broadcast(data: BroadcastCreate, token: str = Depends(verify_token)):
    """
    Создает рассылку и отправляет сообщения получателям через Twilio.
    """
    normalized_recipients = []
    invalid_recipients = []
    for phone in data.recipients:
        normalized = twilio_service.normalize_phone_number(phone)
        if normalized and normalized.startswith('+') and len([d for d in normalized if d.isdigit()]) >= 10:
            normalized_recipients.append(normalized)
        else:
            invalid_recipients.append(phone)

    recipients = list(dict.fromkeys(normalized_recipients))
    if not recipients:
        raise HTTPException(status_code=400, detail="Recipients list cannot be empty or contain only invalid phone numbers")

    broadcast_id = add_broadcast(
        data.message,
        len(recipients),
        recipients_json=json.dumps(recipients),
        status='sending'
    )

    sent_count = 0
    failed_count = 0
    errors = []

    if invalid_recipients:
        for invalid in invalid_recipients:
            add_broadcast_log(broadcast_id, invalid, None, 'failed', 'Invalid phone format')
            errors.append({"phone": invalid, "error": "Invalid phone format"})

    if not twilio_service.is_configured():
        update_broadcast_summary(broadcast_id, 0, len(recipients), 'failed', datetime.now().isoformat())
        for phone in recipients:
            add_broadcast_log(broadcast_id, phone, None, 'failed', 'Twilio is not configured')
        raise HTTPException(status_code=500, detail="Twilio is not configured. Broadcast was recorded but not sent.")

    for recipient in recipients:
        try:
            result = await twilio_service.send_whatsapp_message(recipient, data.message)
            if 'error' in result:
                failed_count += 1
                errors.append({"phone": recipient, "error": result.get('error')})
                add_broadcast_log(broadcast_id, recipient, None, 'failed', result.get('error'))
            else:
                sent_count += 1
                add_broadcast_log(broadcast_id, recipient, result.get('sid'), 'sent')
        except Exception as e:
            failed_count += 1
            errors.append({"phone": recipient, "error": str(e)})
            add_broadcast_log(broadcast_id, recipient, None, 'failed', str(e))
        finally:
            await asyncio.sleep(1)

    status = 'completed' if sent_count > 0 and failed_count == 0 else 'failed' if sent_count == 0 else 'completed'
    update_broadcast_summary(broadcast_id, sent_count, failed_count, status, datetime.now().isoformat())

    return {
        "success": True,
        "broadcastId": broadcast_id,
        "recipientCount": len(recipients),
        "sentCount": sent_count,
        "failedCount": failed_count,
        "status": status,
        "invalidRecipients": invalid_recipients,
        "errors": errors
    }

@router.delete("/broadcasts/{broadcast_id}")
async def delete_broadcast_route(broadcast_id: int, token: str = Depends(verify_token)):
    """Удаляет запись рассылки из локальной базы данных."""
    try:
        delete_broadcast(broadcast_id)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/backend-logs")
async def get_backend_logs(
    page: int = 1,
    limit: int = 100,
    token: str = Depends(verify_token)
):
    """Читает логи бэкенда из файла с пагинацией."""
    try:
        if not os.path.exists(LOG_FILE):
            return {"logs": [], "total": 0, "page": page, "limit": limit}

        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            all_lines = f.readlines()

        total = len(all_lines)
        # Пагинация: page 1 = последние limit строк, page 2 = предыдущие limit и т.д.
        start = max(total - page * limit, 0)
        end = total - (page - 1) * limit
        paged_lines = all_lines[start:end]

        logs = []
        for line in paged_lines:
            line = line.strip()
            if not line:
                continue
            try:
                parts = line.split(' - ')
                if len(parts) >= 4:
                    time_str = parts[0].split(',')[0]
                    level = parts[2]
                    message = ' - '.join(parts[3:])
                    logs.append({
                        "time": time_str,
                        "level": level,
                        "message": message
                    })
                elif len(parts) >= 3:
                    time_str = parts[0].split(',')[0]
                    level = parts[1]
                    message = ' - '.join(parts[2:])
                    logs.append({
                        "time": time_str,
                        "level": level,
                        "message": message
                    })
                else:
                    logs.append({
                        "time": "",
                        "level": "INFO",
                        "message": line
                    })
            except:
                logs.append({
                    "time": "",
                    "level": "INFO",
                    "message": line
                })

        return {"logs": logs[::-1], "total": total, "page": page, "limit": limit}  # новые сверху
    except Exception as e:
        return {"logs": [], "error": str(e), "total": 0, "page": page, "limit": limit}

@router.get("/broadcast-settings")
async def get_broadcast_settings_route(token: str = Depends(verify_token)):
    """Возвращает текущие настройки рассылки из базы данных."""
    return get_broadcast_settings()


@router.put("/broadcast-settings")
async def update_broadcast_settings_route(data: BroadcastSettingsUpdate, token: str = Depends(verify_token)):
    """Сохраняет настройки рассылки из админской панели."""
    return update_broadcast_settings(data.model_dump())

@router.get("/broadcast-clients")
async def list_broadcast_clients(days: int = 30, token: str = Depends(verify_token)):
    """Возвращает уникальный список клиентов из Alteegio для рассылки."""
    try:
        clients = await alteegio_service.get_clients(days)
        return {"items": clients, "count": len(clients)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
