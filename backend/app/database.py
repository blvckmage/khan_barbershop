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
            welcome_message TEXT DEFAULT 'Добро пожаловать в KHAN Barbershop!',
            broadcast_enabled INTEGER DEFAULT 0,
            broadcast_phone_numbers TEXT DEFAULT '',
            broadcast_message_template TEXT DEFAULT '',
            broadcast_schedule TEXT DEFAULT 'manual',
            broadcast_send_time TEXT DEFAULT '10:00'
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
            sent_count INTEGER DEFAULT 0,
            failed_count INTEGER DEFAULT 0,
            status TEXT DEFAULT 'pending',
            recipients TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP,
            scheduled_at TIMESTAMP
        )
    ''')
    
    # Broadcast logs
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS broadcast_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            broadcast_id INTEGER NOT NULL,
            phone TEXT NOT NULL,
            message_sid TEXT,
            status TEXT NOT NULL,
            error TEXT,
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
    
    # WABA Templates (WhatsApp Business API approved templates)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS waba_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            body_text TEXT NOT NULL,
            category TEXT DEFAULT 'MARKETING',
            language TEXT DEFAULT 'ru',
            meta_status TEXT DEFAULT 'PENDING',
            meta_id TEXT,
            buttons TEXT,                 -- JSON list of buttons (optional)
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Migrate waba_templates: add buttons column if missing
    cursor.execute("PRAGMA table_info(waba_templates)")
    tmpl_columns = {row[1] for row in cursor.fetchall()}
    if 'buttons' not in tmpl_columns:
        cursor.execute("ALTER TABLE waba_templates ADD COLUMN buttons TEXT")

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
            master_name TEXT,
            client_name TEXT,
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            UNIQUE(appointment_id, type)
        )
    ''')

    # Webhook dedup — store WhatsApp message IDs to prevent duplicate processing
    # if Meta retries the webhook (it does, up to 7 days on failure).
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS webhook_dedup (
            message_id TEXT PRIMARY KEY,
            received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_webhook_dedup_received ON webhook_dedup(received_at)')

    # OpenAI usage tracking (per-day aggregated cost)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS openai_usage (
            date TEXT PRIMARY KEY,             -- YYYY-MM-DD
            input_tokens INTEGER DEFAULT 0,
            output_tokens INTEGER DEFAULT 0,
            cost_usd REAL DEFAULT 0,
            calls INTEGER DEFAULT 0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # NPS ratings (collected from WhatsApp button replies after appointments)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS nps_ratings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            appointment_id TEXT,
            phone TEXT NOT NULL,
            master_name TEXT,
            client_name TEXT,
            rating INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
            comment TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            UNIQUE(appointment_id)
        )
    ''')

    # Alter notification_logs if needed (master/client name added later)
    cursor.execute("PRAGMA table_info(notification_logs)")
    notif_columns = {row[1] for row in cursor.fetchall()}
    if 'master_name' not in notif_columns:
        cursor.execute("ALTER TABLE notification_logs ADD COLUMN master_name TEXT")
    if 'client_name' not in notif_columns:
        cursor.execute("ALTER TABLE notification_logs ADD COLUMN client_name TEXT")
    
    # Alter existing broadcast table if necessary
    cursor.execute("PRAGMA table_info(broadcasts)")
    existing_columns = {row[1] for row in cursor.fetchall()}
    if 'sent_count' not in existing_columns:
        cursor.execute("ALTER TABLE broadcasts ADD COLUMN sent_count INTEGER DEFAULT 0")
    if 'failed_count' not in existing_columns:
        cursor.execute("ALTER TABLE broadcasts ADD COLUMN failed_count INTEGER DEFAULT 0")
    if 'status' not in existing_columns:
        cursor.execute("ALTER TABLE broadcasts ADD COLUMN status TEXT DEFAULT 'pending'")
    if 'recipients' not in existing_columns:
        cursor.execute("ALTER TABLE broadcasts ADD COLUMN recipients TEXT")
    if 'completed_at' not in existing_columns:
        cursor.execute("ALTER TABLE broadcasts ADD COLUMN completed_at TIMESTAMP")
    if 'scheduled_at' not in existing_columns:
        cursor.execute("ALTER TABLE broadcasts ADD COLUMN scheduled_at TIMESTAMP")
    
    # Alter existing settings table if necessary
    cursor.execute("PRAGMA table_info(settings)")
    settings_columns = {row[1] for row in cursor.fetchall()}
    if 'broadcast_enabled' not in settings_columns:
        cursor.execute("ALTER TABLE settings ADD COLUMN broadcast_enabled INTEGER DEFAULT 0")
    if 'broadcast_phone_numbers' not in settings_columns:
        cursor.execute("ALTER TABLE settings ADD COLUMN broadcast_phone_numbers TEXT DEFAULT ''")
    if 'broadcast_message_template' not in settings_columns:
        cursor.execute("ALTER TABLE settings ADD COLUMN broadcast_message_template TEXT DEFAULT ''")
    if 'broadcast_schedule' not in settings_columns:
        cursor.execute("ALTER TABLE settings ADD COLUMN broadcast_schedule TEXT DEFAULT 'manual'")
    if 'broadcast_send_time' not in settings_columns:
        cursor.execute("ALTER TABLE settings ADD COLUMN broadcast_send_time TEXT DEFAULT '10:00'")
    if 'chatbot_enabled' not in settings_columns:
        cursor.execute("ALTER TABLE settings ADD COLUMN chatbot_enabled INTEGER DEFAULT 1")
    if 'excluded_master_ids' not in settings_columns:
        cursor.execute("ALTER TABLE settings ADD COLUMN excluded_master_ids TEXT DEFAULT '[]'")
    # Per-reminder enable flags (1 = enabled, 0 = disabled)
    if 'enable_one_hour_reminder' not in settings_columns:
        cursor.execute("ALTER TABLE settings ADD COLUMN enable_one_hour_reminder INTEGER DEFAULT 1")
    if 'enable_revisit_reminder' not in settings_columns:
        cursor.execute("ALTER TABLE settings ADD COLUMN enable_revisit_reminder INTEGER DEFAULT 1")
    if 'enable_nps_request' not in settings_columns:
        cursor.execute("ALTER TABLE settings ADD COLUMN enable_nps_request INTEGER DEFAULT 1")

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
    # Переворачиваем чтобы внутри чата старые сообщения были сверху, новые снизу
    items.reverse()
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

def get_broadcasts(page: int = 1, limit: int = 50):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as count FROM broadcasts")
    total = cursor.fetchone()['count']
    offset = (page - 1) * limit
    
    cursor.execute('''
        SELECT id, message, recipients_count, sent_count, failed_count, status, recipients,
               datetime(created_at, 'localtime') as created_at,
               datetime(completed_at, 'localtime') as completed_at,
               datetime(scheduled_at, 'localtime') as scheduled_at
        FROM broadcasts
        ORDER BY created_at DESC
        LIMIT ? OFFSET ?
    ''', (limit, offset))
    items = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return {'items': items, 'total': total, 'page': page, 'limit': limit}


def add_broadcast(message: str, recipients_count: int, recipients_json: str = '[]', status: str = 'pending', scheduled_at: Optional[str] = None) -> int:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO broadcasts (message, recipients_count, sent_count, failed_count, status, recipients, scheduled_at) VALUES (?, ?, 0, 0, ?, ?, ?)",
        (message, recipients_count, status, recipients_json, scheduled_at)
    )
    broadcast_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return broadcast_id


def get_due_scheduled_broadcasts(current_time_str: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, message, recipients_count, recipients
        FROM broadcasts
        WHERE status = 'scheduled' AND scheduled_at <= ?
    ''', (current_time_str,))
    items = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return items


def update_broadcast_summary(broadcast_id: int, sent_count: int, failed_count: int, status: str, completed_at: Optional[str] = None):
    conn = get_db()
    cursor = conn.cursor()
    if completed_at:
        cursor.execute(
            "UPDATE broadcasts SET sent_count = ?, failed_count = ?, status = ?, completed_at = ? WHERE id = ?",
            (sent_count, failed_count, status, completed_at, broadcast_id)
        )
    else:
        cursor.execute(
            "UPDATE broadcasts SET sent_count = ?, failed_count = ?, status = ? WHERE id = ?",
            (sent_count, failed_count, status, broadcast_id)
        )
    conn.commit()
    conn.close()


def add_broadcast_log(broadcast_id: int, phone: str, message_sid: Optional[str], status: str, error: Optional[str] = None):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO broadcast_logs (broadcast_id, phone, message_sid, status, error) VALUES (?, ?, ?, ?, ?)",
        (broadcast_id, phone, message_sid, status, error)
    )
    conn.commit()
    conn.close()


def delete_broadcast(broadcast_id: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM broadcast_logs WHERE broadcast_id = ?", (broadcast_id,))
    cursor.execute("DELETE FROM broadcasts WHERE id = ?", (broadcast_id,))
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
def add_notification_log(
    appointment_id: str,
    phone: str,
    type: str,
    message_sid: str = None,
    status: str = 'sent',
    error: str = None,
    note: str = None,
    master_name: str = None,
    client_name: str = None,
):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO notification_logs
            (appointment_id, phone, type, message_sid, status, error, note, master_name, client_name)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (appointment_id, phone, type, message_sid, status, error, note, master_name, client_name))
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


# ─── NPS ratings ─────────────────────────────────────────────────────────────

def get_last_nps_context(phone: str, hours: int = 72) -> Optional[dict]:
    """Find the most recent unanswered NPS request for this phone.

    Returns context (appointment_id, master_name, client_name) so the rating
    can be linked to the right appointment+master. Returns None if there's no
    pending NPS request within the last `hours` window.
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT nl.appointment_id, nl.master_name, nl.client_name, nl.sent_at
        FROM notification_logs nl
        WHERE nl.phone = ?
          AND nl.type = 'nps_request'
          AND nl.status = 'sent'
          AND datetime(nl.sent_at) >= datetime('now', '-' || ? || ' hours')
          AND NOT EXISTS (
              SELECT 1 FROM nps_ratings nr WHERE nr.appointment_id = nl.appointment_id
          )
        ORDER BY nl.sent_at DESC
        LIMIT 1
    ''', (phone, hours))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def add_nps_rating(
    phone: str,
    rating: int,
    appointment_id: Optional[str] = None,
    master_name: Optional[str] = None,
    client_name: Optional[str] = None,
    comment: Optional[str] = None,
) -> bool:
    """Save NPS rating. Returns True if saved, False if duplicate appointment."""
    if rating < 1 or rating > 5:
        return False
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO nps_ratings
            (appointment_id, phone, master_name, client_name, rating, comment)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (appointment_id, phone, master_name, client_name, rating, comment))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        # Duplicate appointment_id — rating already recorded
        return False
    finally:
        conn.close()


def get_nps_stats(days: int = 30) -> dict:
    """Aggregate NPS statistics over the last N days for the dashboard."""
    from datetime import timedelta
    cutoff_str = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')

    conn = get_db()
    cursor = conn.cursor()

    # Distribution + total + weighted average
    cursor.execute('''
        SELECT rating, COUNT(*) as count
        FROM nps_ratings
        WHERE created_at >= ?
        GROUP BY rating
    ''', (cutoff_str,))
    distribution = {str(r): 0 for r in range(1, 6)}
    total = 0
    weighted_sum = 0
    for row in cursor.fetchall():
        distribution[str(row['rating'])] = row['count']
        total += row['count']
        weighted_sum += row['rating'] * row['count']
    avg_rating = round(weighted_sum / total, 2) if total > 0 else 0.0

    # By master
    cursor.execute('''
        SELECT master_name, AVG(rating) as avg_rating, COUNT(*) as count
        FROM nps_ratings
        WHERE created_at >= ? AND master_name IS NOT NULL AND master_name != ''
        GROUP BY master_name
        ORDER BY avg_rating DESC, count DESC
    ''', (cutoff_str,))
    by_master = [
        {
            "master": row['master_name'],
            "avg": round(row['avg_rating'], 2),
            "count": row['count'],
        }
        for row in cursor.fetchall()
    ]

    # Daily trend
    cursor.execute('''
        SELECT date(created_at) as day, AVG(rating) as avg_rating, COUNT(*) as count
        FROM nps_ratings
        WHERE created_at >= ?
        GROUP BY date(created_at)
        ORDER BY day
    ''', (cutoff_str,))
    trend = [
        {
            "day": row['day'],
            "avg": round(row['avg_rating'], 2),
            "count": row['count'],
        }
        for row in cursor.fetchall()
    ]

    # Recent ratings for "fresh feedback" list
    cursor.execute('''
        SELECT rating, master_name, client_name, comment,
               datetime(created_at, 'localtime') as created_at
        FROM nps_ratings
        WHERE created_at >= ?
        ORDER BY created_at DESC
        LIMIT 10
    ''', (cutoff_str,))
    recent = [dict(row) for row in cursor.fetchall()]

    conn.close()
    return {
        "total_responses": total,
        "avg_rating": avg_rating,
        "distribution": distribution,
        "by_master": by_master,
        "trend": trend,
        "recent": recent,
        "period_days": days,
    }

def get_broadcast_settings():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT broadcast_enabled, broadcast_phone_numbers, broadcast_message_template, broadcast_schedule, broadcast_send_time
        FROM settings LIMIT 1
    ''')
    row = cursor.fetchone()
    conn.close()
    return {
        'enabled': bool(row['broadcast_enabled']) if row else False,
        'phoneNumbers': row['broadcast_phone_numbers'] if row else '',
        'messageTemplate': row['broadcast_message_template'] if row else '',
        'schedule': row['broadcast_schedule'] if row else 'manual',
        'sendTime': row['broadcast_send_time'] if row else '10:00'
    }


def update_broadcast_settings(data: dict):
    current = get_broadcast_settings()
    enabled = 1 if data.get('enabled', current['enabled']) else 0
    phone_numbers = data.get('phoneNumbers', current['phoneNumbers'])
    message_template = data.get('messageTemplate', current['messageTemplate'])
    schedule = data.get('schedule', current['schedule'])
    send_time = data.get('sendTime', current['sendTime'])

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE settings SET
            broadcast_enabled = ?,
            broadcast_phone_numbers = ?,
            broadcast_message_template = ?,
            broadcast_schedule = ?,
            broadcast_send_time = ?
    ''', (enabled, phone_numbers, message_template, schedule, send_time))
    conn.commit()
    conn.close()
    return get_broadcast_settings()


# ─── Bot settings (chatbot on/off + excluded masters) ───────────────────────

def get_bot_settings() -> dict:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT chatbot_enabled, excluded_master_ids FROM settings LIMIT 1')
    row = cursor.fetchone()
    conn.close()
    if not row:
        return {'chatbot_enabled': True, 'excluded_master_ids': []}
    try:
        excluded = json.loads(row['excluded_master_ids'] or '[]')
    except Exception:
        excluded = []
    return {
        'chatbot_enabled': bool(row['chatbot_enabled']),
        'excluded_master_ids': excluded,
    }


def update_bot_settings(chatbot_enabled: bool, excluded_master_ids: list) -> dict:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE settings SET chatbot_enabled = ?, excluded_master_ids = ?',
        (1 if chatbot_enabled else 0, json.dumps(excluded_master_ids))
    )
    conn.commit()
    conn.close()
    return get_bot_settings()


# ─── Reminder enable/disable flags ────────────────────────────────────────────

def get_reminder_settings() -> dict:
    """Return enable flags for each automated reminder type."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT enable_one_hour_reminder, enable_revisit_reminder, enable_nps_request
        FROM settings LIMIT 1
    ''')
    row = cursor.fetchone()
    conn.close()
    if not row:
        return {
            'enable_one_hour_reminder': True,
            'enable_revisit_reminder': True,
            'enable_nps_request': True,
        }
    return {
        'enable_one_hour_reminder': bool(row['enable_one_hour_reminder']),
        'enable_revisit_reminder': bool(row['enable_revisit_reminder']),
        'enable_nps_request': bool(row['enable_nps_request']),
    }


def update_reminder_settings(
    enable_one_hour_reminder: bool,
    enable_revisit_reminder: bool,
    enable_nps_request: bool,
) -> dict:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE settings SET
            enable_one_hour_reminder = ?,
            enable_revisit_reminder = ?,
            enable_nps_request = ?
    ''', (
        1 if enable_one_hour_reminder else 0,
        1 if enable_revisit_reminder else 0,
        1 if enable_nps_request else 0,
    ))
    conn.commit()
    conn.close()
    return get_reminder_settings()


# ─── WABA Templates ──────────────────────────────────────────────────────────

def get_waba_templates() -> list:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, name, body_text, category, language, meta_status, meta_id, buttons,
               datetime(created_at, 'localtime') as created_at
        FROM waba_templates ORDER BY created_at DESC
    ''')
    items = []
    for row in cursor.fetchall():
        item = dict(row)
        # Parse buttons JSON back to list for frontend
        if item.get('buttons'):
            try:
                item['buttons'] = json.loads(item['buttons'])
            except Exception:
                item['buttons'] = []
        else:
            item['buttons'] = []
        items.append(item)
    conn.close()
    return items


def add_waba_template(name: str, body_text: str, category: str, language: str,
                      meta_status: str = 'PENDING', meta_id: str = None,
                      buttons: Optional[list] = None) -> dict:
    conn = get_db()
    cursor = conn.cursor()
    buttons_json = json.dumps(buttons) if buttons else None
    cursor.execute('''
        INSERT INTO waba_templates (name, body_text, category, language, meta_status, meta_id, buttons)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (name, body_text, category, language, meta_status, meta_id, buttons_json))
    row_id = cursor.lastrowid
    conn.commit()
    conn.close()
    items = get_waba_templates()
    return next((t for t in items if t['id'] == row_id), {})


def update_waba_template_status(name: str, meta_status: str, meta_id: str = None):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE waba_templates SET meta_status = ?, meta_id = ?, updated_at = ? WHERE name = ?',
        (meta_status, meta_id, datetime.now().isoformat(), name)
    )
    conn.commit()
    conn.close()


def delete_waba_template(template_id: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM waba_templates WHERE id = ?', (template_id,))
    conn.commit()
    conn.close()


# ─── Webhook dedup ────────────────────────────────────────────────────────────

def is_webhook_processed(message_id: str) -> bool:
    """Check if we already processed this WhatsApp message id (wamid).
    Returns True → caller should return 200 OK without re-processing.
    """
    if not message_id:
        return False
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT 1 FROM webhook_dedup WHERE message_id = ? LIMIT 1', (message_id,))
    exists = cursor.fetchone() is not None
    conn.close()
    return exists


def mark_webhook_processed(message_id: str):
    """Mark a webhook message as processed. Silently ignores duplicates."""
    if not message_id:
        return
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute('INSERT INTO webhook_dedup (message_id) VALUES (?)', (message_id,))
        conn.commit()
    except sqlite3.IntegrityError:
        pass
    conn.close()


# ─── OpenAI usage tracking ────────────────────────────────────────────────────

def record_openai_usage(
    input_tokens: int,
    output_tokens: int,
    cost_usd: float,
    date_str: Optional[str] = None,
):
    """Increment today's OpenAI usage counters."""
    date_str = date_str or datetime.now().strftime('%Y-%m-%d')
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO openai_usage (date, input_tokens, output_tokens, cost_usd, calls, updated_at)
        VALUES (?, ?, ?, ?, 1, CURRENT_TIMESTAMP)
        ON CONFLICT(date) DO UPDATE SET
            input_tokens = input_tokens + excluded.input_tokens,
            output_tokens = output_tokens + excluded.output_tokens,
            cost_usd = cost_usd + excluded.cost_usd,
            calls = calls + 1,
            updated_at = CURRENT_TIMESTAMP
    ''', (date_str, input_tokens, output_tokens, cost_usd))
    conn.commit()
    conn.close()


def get_openai_usage_today() -> dict:
    """Return today's aggregated usage."""
    date_str = datetime.now().strftime('%Y-%m-%d')
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM openai_usage WHERE date = ?', (date_str,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return {'date': date_str, 'input_tokens': 0, 'output_tokens': 0, 'cost_usd': 0.0, 'calls': 0}
    return dict(row)


def get_openai_usage_history(days: int = 30) -> list:
    """Return per-day usage for the last N days."""
    from datetime import timedelta
    cutoff = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT * FROM openai_usage WHERE date >= ? ORDER BY date DESC',
        (cutoff,)
    )
    items = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return items


# ─── Data retention cleanup ───────────────────────────────────────────────────

def cleanup_old_data(log_days: int = 90, webhook_hours: int = 24) -> dict:
    """Delete old rows from logs / dedup tables. Returns counts of deleted rows."""
    conn = get_db()
    cursor = conn.cursor()
    deleted = {}

    cursor.execute(
        "DELETE FROM chat_logs WHERE created_at < datetime('now', ? )",
        (f'-{log_days} days',)
    )
    deleted['chat_logs'] = cursor.rowcount

    cursor.execute(
        "DELETE FROM broadcast_logs WHERE created_at < datetime('now', ? )",
        (f'-{log_days} days',)
    )
    deleted['broadcast_logs'] = cursor.rowcount

    cursor.execute(
        "DELETE FROM notification_logs WHERE sent_at < datetime('now', ? )",
        (f'-{log_days} days',)
    )
    deleted['notification_logs'] = cursor.rowcount

    cursor.execute(
        "DELETE FROM webhook_dedup WHERE received_at < datetime('now', ? )",
        (f'-{webhook_hours} hours',)
    )
    deleted['webhook_dedup'] = cursor.rowcount

    # Vacuum to actually reclaim disk space
    conn.commit()
    cursor.execute("VACUUM")
    conn.close()

    return deleted


# ─── WhatsApp 24-hour window tracker ──────────────────────────────────────────

def get_last_user_message_at(phone: str) -> Optional[datetime]:
    """Return timestamp of the most recent INCOMING user message from `phone`.

    Used to check if the WhatsApp 24-hour session window is still open before
    sending plain-text (non-template) messages.
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT created_at FROM chat_logs
        WHERE phone = ?
          AND intent IN ('whatsapp', 'manychat', 'nps_rating')
        ORDER BY created_at DESC
        LIMIT 1
    ''', (phone,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    try:
        return datetime.fromisoformat(row['created_at'].replace(' ', 'T'))
    except Exception:
        return None
