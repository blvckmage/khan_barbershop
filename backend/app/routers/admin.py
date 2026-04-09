import os
import logging
from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from ..database import (
    init_db, get_logs, get_broadcasts, add_broadcast, verify_user
)
from ..services.alteegio_service import alteegio_service

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
        
        # Calculate stats
        today_appointments = len(records) if records else 0
        
        # Get total unique clients from records
        unique_clients = set()
        for r in (records or []):
            client = r.get("client") or {}
            if client.get("phone"):
                unique_clients.add(client["phone"])
        
        # Get staff count
        staff = await alteegio_service.get_staff()
        staff_count = len(staff) if staff else 0
        
        # Get logs from database for chat count
        logs = get_logs(1, 1000)
        
        # Format recent appointments safely
        recent_appointments = []
        for r in (records or [])[:5]:
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
        for log in logs.get("items", [])[:5]:
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
            "todayAppointments": today_appointments,
            "todayChats": logs.get("total", 0),
            "totalClients": len(unique_clients),
            "totalMasters": staff_count,
            "rating": "4.9",
            "recentAppointments": recent_appointments,
            "recentChats": recent_chats
        }
    except Exception as e:
        # Fallback to mock data if Alteegio fails
        return {
            "todayAppointments": 0,
            "todayChats": 0,
            "totalClients": 0,
            "totalMasters": 0,
            "rating": "4.9",
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
async def list_broadcasts(token: str = Depends(verify_token)):
    """Получает историю рассылок из локальной SQLite БД."""
    return get_broadcasts()

@router.post("/broadcasts")
async def create_broadcast(data: BroadcastCreate, token: str = Depends(verify_token)):
    """
    Создаёт рассылку. 
    ВНИМАНИЕ: Реальная отправка SMS через Twilio ещё не реализована!
    """
    add_broadcast(data.message, len(data.recipients))
    # TODO: Actually send SMS via Twilio
    return {
        "success": True, 
        "recipients_count": len(data.recipients),
        "message": "Рассылка сохранена, но SMS отправка ещё не реализована. Требуется интеграция с Twilio."
    }

@router.get("/backend-logs")
async def get_backend_logs(lines: int = 100, token: str = Depends(verify_token)):
    """Читает логи бэкенда из файла."""
    try:
        if not os.path.exists(LOG_FILE):
            return {"logs": []}
        
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            all_lines = f.readlines()
        
        # Берем последние N строк
        recent_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
        
        logs = []
        for line in recent_lines:
            line = line.strip()
            if not line:
                continue
            try:
                # Формат из main.py: 2024-01-01 12:00:00,123 - module - LEVEL - message
                # Разделяем по " - " 
                parts = line.split(' - ')
                if len(parts) >= 4:
                    time_str = parts[0].split(',')[0]  # Убираем миллисекунды
                    level = parts[2]
                    message = ' - '.join(parts[3:])
                    
                    logs.append({
                        "time": time_str,
                        "level": level,
                        "message": message
                    })
                elif len(parts) >= 3:
                    # Альтернативный формат
                    time_str = parts[0].split(',')[0]
                    level = parts[1]
                    message = ' - '.join(parts[2:])
                    
                    logs.append({
                        "time": time_str,
                        "level": level,
                        "message": message
                    })
                else:
                    # Если не можем распарсить, просто добавляем как есть
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
        
        return {"logs": logs}
    except Exception as e:
        return {"logs": [], "error": str(e)}
