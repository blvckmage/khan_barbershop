import sqlite3
from datetime import datetime
from typing import Optional
import json

import os

# Путь к базе данных (относительно директории backend, откуда запускается uvicorn)
DATABASE_PATH = "khan_barbershop.db"

def get_db():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    # Users table for admin auth
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Settings table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            shop_name TEXT DEFAULT 'KHAN Barbershop',
            phone TEXT DEFAULT '+77771234567',
            address TEXT DEFAULT 'г. Алматы, ул. Примерная, 1',
            working_hours TEXT DEFAULT 'Пн-Вс: 10:00 - 21:00',
            welcome_message TEXT DEFAULT 'Добро пожаловать в KHAN Barbershop!'
        )
    ''')
    
    # AI Prompt
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ai_prompt (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prompt TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Chat logs
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone TEXT NOT NULL,
            message TEXT NOT NULL,
            response TEXT NOT NULL,
            intent TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Broadcasts
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS broadcasts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message TEXT NOT NULL,
            recipients_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Masters
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS masters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            position TEXT DEFAULT 'Барбер',
            schedule TEXT DEFAULT 'Пн-Сб',
            status TEXT DEFAULT 'available',
            is_active INTEGER DEFAULT 1
        )
    ''')
    
    # Notification logs (to prevent duplicate sending)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notification_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            appointment_id TEXT NOT NULL,
            phone TEXT NOT NULL,
            type TEXT NOT NULL,
            message_sid TEXT,
            status TEXT NOT NULL,
            error TEXT,
            note TEXT,
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            
            UNIQUE(appointment_id, type)
        )
    ''')
    
    # Insert default admin if not exists
    cursor.execute("SELECT * FROM users WHERE username = 'admin'")
    if not cursor.fetchone():
        cursor.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            ('admin', 'admin123')  # In production, use proper hash!
        )
    
    # Insert default settings if not exists
    cursor.execute("SELECT * FROM settings")
    if not cursor.fetchone():
        cursor.execute("INSERT INTO settings DEFAULT VALUES")
    
    # Insert default prompt if not exists
    cursor.execute("SELECT * FROM ai_prompt")
    if not cursor.fetchone():
        default_prompt = """Ты — AI-ассистент барбершопа KHAN. Твоя задача помогать клиентам записываться на услуги и отвечать на вопросы о барбершопе.

Информация о барбершопе:
- Название: KHAN Barbershop
- Адрес: г. Алматы
- Время работы: ежедневно 10:00-21:00

Услуги:
- Стрижка мужская: 5000 ₸
- Стрижка детская: 3500 ₸
- Бородка: 3000 ₸
- Комплекс (стрижка + борода): 7000 ₸

Отвечай дружелюбно и кратко. Помогай клиентам записаться на удобное время."""
        cursor.execute("INSERT INTO ai_prompt (prompt) VALUES (?)", (default_prompt,))
    
    # Insert sample masters if not exists
    cursor.execute("SELECT * FROM masters")
    if not cursor.fetchone():
        masters = [
            ('Арман', 'Топ-барбер', 'Пн-Сб', 'available', 1),
            ('Дима', 'Барбер', 'Пн-Вс', 'available', 1),
            ('Кирилл', 'Барбер', 'Вт-Вс', 'busy', 1),
        ]
        cursor.executemany(
            "INSERT INTO masters (name, position, schedule, status, is_active) VALUES (?, ?, ?, ?, ?)",
            masters
        )
    
    conn.commit()
    conn.close()


# Database operations
def get_settings():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM settings LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else {}

def update_settings(data: dict):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE settings SET 
            shop_name = ?, phone = ?, address = ?, working_hours = ?, welcome_message = ?
    ''', (data.get('shop_name'), data.get('phone'), data.get('address'), 
          data.get('working_hours'), data.get('welcome_message')))
    conn.commit()
    conn.close()
    return get_settings()

def get_prompt():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT prompt FROM ai_prompt ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    return {'prompt': row['prompt'] if row else ''}

def update_prompt(prompt: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE ai_prompt SET prompt = ?, updated_at = ?", 
                   (prompt, datetime.now()))
    conn.commit()
    conn.close()
    return get_prompt()

def get_logs(page: int = 1, limit: int = 50):
    conn = get_db()
    cursor = conn.cursor()
    offset = (page - 1) * limit
    
    cursor.execute("SELECT COUNT(*) as count FROM chat_logs")
    total = cursor.fetchone()['count']
    
    cursor.execute('''
        SELECT id, phone, message, response, intent as type, 
               datetime(created_at, 'localtime') as timestamp
        FROM chat_logs 
        ORDER BY created_at DESC 
        LIMIT ? OFFSET ?
    ''', (limit, offset))
    
    items = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return {'items': items, 'total': total, 'page': page, 'limit': limit}

def add_log(phone: str, message: str, response: str, intent: Optional[str] = None):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO chat_logs (phone, message, response, intent) VALUES (?, ?, ?, ?)",
        (phone, message, response, intent)
    )
    conn.commit()
    conn.close()

def get_broadcasts():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, message, recipients_count, 
               datetime(created_at, 'localtime') as created_at
        FROM broadcasts ORDER BY created_at DESC
    ''')
    items = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return items

def add_broadcast(message: str, recipients_count: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO broadcasts (message, recipients_count) VALUES (?, ?)",
        (message, recipients_count)
    )
    conn.commit()
    conn.close()

def get_masters():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM masters ORDER BY name")
    items = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return items

def update_master(master_id: int, data: dict):
    conn = get_db()
    cursor = conn.cursor()
    if 'is_active' in data:
        cursor.execute("UPDATE masters SET is_active = ? WHERE id = ?", 
                       (data['is_active'], master_id))
    conn.commit()
    conn.close()
    return get_masters()

def verify_user(username: str, password: str) -> Optional[str]:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM users WHERE username = ? AND password_hash = ?",
        (username, password)
    )
    user = cursor.fetchone()
    conn.close()
    if user:
        return f"token_{username}_{datetime.now().timestamp()}"
    return None


# Notification log operations
def add_notification_log(appointment_id: str, phone: str, type: str, message_sid: str = None, status: str = 'sent', error: str = None, note: str = None):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO notification_logs 
            (appointment_id, phone, type, message_sid, status, error, note)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (appointment_id, phone, type, message_sid, status, error, note))
        conn.commit()
    except sqlite3.IntegrityError:
        # Already exists
        pass
    conn.close()


def has_notification_been_sent(appointment_id: str, type: str) -> bool:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id FROM notification_logs 
        WHERE appointment_id = ? AND type = ? AND status IN ('sent', 'skipped')
        LIMIT 1
    ''', (appointment_id, type))
    exists = cursor.fetchone() is not None
    conn.close()
    return exists
