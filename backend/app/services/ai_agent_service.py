import json
import logging
import random
import string
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
from openai import OpenAI
from app.config import get_settings
from app.services.alteegio_service import alteegio_service
from app.services.sheets_service import sheets_service

settings = get_settings()

# Настройка логирования
logger = logging.getLogger(__name__)

# Random session prefix that changes on each server restart
SESSION_PREFIX = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
logger.info(f"🔄 New session prefix generated: {SESSION_PREFIX}")

# Часовой пояс Almaty (UTC+5)
ALMATY_TZ = timezone(timedelta(hours=5))


def format_datetime_human(dt_str: str) -> str:
    """Format datetime string to human-readable format in Russian.
    
    Examples:
        "2026-03-07 14:00:00" -> "7 марта в 14:00"
        "2026-03-07T14:00:00" -> "7 марта в 14:00"
    """
    months_ru = {
        1: 'января', 2: 'февраля', 3: 'марта', 4: 'апреля', 5: 'мая', 6: 'июня',
        7: 'июля', 8: 'августа', 9: 'сентября', 10: 'октября', 11: 'ноября', 12: 'декабря'
    }
    
    try:
        dt_str = dt_str.strip()
        if 'T' in dt_str:
            dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        else:
            dt = datetime.strptime(dt_str, '%Y-%m-%d %H:%M:%S')
        
        day = dt.day
        month = months_ru.get(dt.month, str(dt.month))
        hour = dt.hour
        minute = dt.minute
        
        return f"{day} {month} в {hour:02d}:{minute:02d}"
    except Exception as e:
        logger.error(f"Error formatting datetime '{dt_str}': {e}")
        return dt_str


def get_system_prompt() -> str:
    """Generate system prompt with current date/time context"""
    now = datetime.now(ALMATY_TZ)
    tomorrow = now + timedelta(days=1)
    
    days_ru = {
        'Monday': 'понедельник', 'Tuesday': 'вторник', 'Wednesday': 'среда',
        'Thursday': 'четверг', 'Friday': 'пятница', 'Saturday': 'суббота', 'Sunday': 'воскресенье'
    }
    today_name = days_ru.get(now.strftime('%A'), now.strftime('%A'))
    tomorrow_name = days_ru.get(tomorrow.strftime('%A'), tomorrow.strftime('%A'))
    
    return f"""Ты — виртуальный ассистент барбершопа «KHAN» по адресу Момышулы 55.
Твоя задача — консультировать клиентов и записывать их на свободные окошки мастеров.
Отвечай клиенту коротко, но уверенно.
Деньги указываешь в тенге.
Не отправляй staff_id и service_id клиенту.

ВАЖНО - НЕ ПОВТОРЯЙСЯ:
- НЕ представляйся повторно в каждом сообщении!
- Отвечай прямо на вопрос клиента без лишних вступлений.

МАСТЕРА И ИХ СПЕЦИАЛИЗАЦИЯ:
- Наргиза — ТОЛЬКО химическая завивка, маникюр и педикюр! НЕ предлагать её для стрижек (мужских, женских, детских)!
- Остальные мастера (Сухрабхан, Миша, Нурперзент, Эльбрус, Сундет, Нурдаулет) делают все виды стрижек.
- Если клиент спрашивает про стрижку — НЕ включай Наргизу в список!

ЗАПИСЬ НЕСКОЛЬКИХ ЧЕЛОВЕК:
- Если клиент говорит "двое детей", "два ребенка", "екі балаға", "на двоих" — нужно найти ДВУХ разных мастеров на одно время!
- Обе записи делаются на ОДНО И ТО ЖЕ имя клиента и на ОДНО И ТО ЖЕ время.
- Сначала вызови get_available_masters для указанного времени, получи двух свободных мастеров.
- Потом создай ДВЕ записи: каждому мастеру по записи на одно и то же время.

ВОПРОСЫ О МАСТЕРАХ (ОБЯЗАТЕЛЬНО ВЫЗЫВАЙ ИНСТРУМЕНТ!):
Когда клиент спрашивает "кто есть?", "какие мастера?", "кым бар?", "кто работает?" — ОБЯЗАТЕЛЬНО вызови get_all_staff и покажи список имён!

ВОПРОСЫ О СВОБОДНЫХ МАСТЕРАХ:
- Если клиент указывает И дату И время (например "завтра в 15:00", "5 апреля на 14:00") — вызывай get_available_masters
- Если клиент указывает ТОЛЬКО дату без времени (например "Миша завтра свободен?", "кто свободен 5 апреля?") — НЕ вызывай get_available_masters! Вместо этого:
  1. Сначала вызови get_services_by_staff_name для указанного мастера
  2. Затем вызови get_available_times для этой даты
  3. Покажи клиенту свободные окошки и спроси, на какое время хочет записаться

ПОСЛЕДОВАТЕЛЬНОСТЬ ЗАПИСИ:
ШАГ 1: Клиент называет мастера -> вызывай get_services_by_staff_name
ШАГ 2: Получил услуги -> вызывай get_available_times (услуга по умолчанию "Стрижка")
ШАГ 3: Показал слоты -> клиент выбрал время -> СПРОСИ "Как вас записать?"
ШАГ 4: Клиент назвал имя -> ВЫЗЫВАЙ create_appointment

Правила времени (русский и казахский):
- "На час"/"сағат бірге"/"бірге" = 13:00
- "На два"/"сағат екіге"/"екіге" = 14:00
- "На три"/"сағат үшке"/"үшке" = 15:00
- "На четыре"/"сағат төртке"/"төртке" = 16:00
- "На пять"/"сағат беске"/"беске" = 17:00
- "На 10" = 10:00, "На 11" = 11:00, "На 12" = 12:00
- "Обед" = 12:00-14:00
- "сағат N" или "сагат N" = N часов

ФОРМАТ ДАТЫ В ОТВЕТЕ:
При подтверждении записи указывай дату как "7 марта в 14:00"
НЕ используй технический формат типа "2026-03-07 14:00:00"!

ТЕКУЩЕЕ ВРЕМЯ:
- Сейчас: {now.strftime('%Y-%m-%d %H:%M:%S')} (Asia/Almaty, UTC+5)
- Сегодня: {now.strftime('%Y-%m-%d')} ({today_name})
- Завтра: {tomorrow.strftime('%Y-%m-%d')} ({tomorrow_name})"""


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_all_staff",
            "description": "Get list of all masters with their names. Use this when client asks 'who works?', 'what masters?', 'кто есть?', 'кым бар?'",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_services_by_staff_name",
            "description": "Get all services offered by a specific master. Use this AFTER client chooses a master. Returns service_id, service_name, price, seance_length needed for booking.",
            "parameters": {
                "type": "object",
                "properties": {"staff_name": {"type": "string", "description": "Name of the master (e.g., 'Миша', 'Нурдаулет')"}},
                "required": ["staff_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_services_by_name",
            "description": "Find services by name, optionally filtered by master. Use this when client specifies a service first (e.g., 'стрижка', 'борода'). Returns service_id, price, seance_length for booking.",
            "parameters": {
                "type": "object",
                "properties": {
                    "service_name": {"type": "string", "description": "Service name to search (e.g., 'Стрижка', 'Борода')"},
                    "staff_name": {"type": "string", "description": "Optional: filter by master name"}
                },
                "required": ["service_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_available_dates",
            "description": "Get available dates for booking",
            "parameters": {
                "type": "object",
                "properties": {
                    "staff_id": {"type": "string"},
                    "service_ids": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["staff_id", "service_ids"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_available_times",
            "description": "Get available time slots for a specific date",
            "parameters": {
                "type": "object",
                "properties": {
                    "staff_id": {"type": "string"},
                    "date": {"type": "string"},
                    "service_ids": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["staff_id", "date", "service_ids"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_available_masters",
            "description": "Get available masters for a SPECIFIC datetime with time. ONLY call this when client specifies BOTH date AND time (e.g., 'завтра в 15:00', '5 апреля на 14:00'). If client only specifies date without time, ask them for time first!",
            "parameters": {
                "type": "object",
                "properties": {"datetime": {"type": "string", "description": "Full datetime with time in ISO format, e.g., '2026-04-05T15:00:00'. Must include time, not just date!"}},
                "required": ["datetime"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_appointment",
            "description": "Create a new appointment",
            "parameters": {
                "type": "object",
                "properties": {
                    "staff_id": {"type": "string"},
                    "service_id": {"type": "string"},
                    "client_phone": {"type": "string"},
                    "client_name": {"type": "string"},
                    "datetime": {"type": "string"},
                    "seance_length": {"type": "string"}
                },
                "required": ["staff_id", "service_id", "client_phone", "client_name", "datetime", "seance_length"]
            }
        }
    }
]


class AIAgentService:
    def __init__(self):
        self.client = OpenAI(api_key=settings.openai_api_key)
        self.model = settings.openai_model
        self.conversations: Dict[str, List[Dict]] = {}
        self.booking_context: Dict[str, Dict] = {}
    
    def _get_booking_context(self, session_id: str) -> Dict:
        if session_id not in self.booking_context:
            self.booking_context[session_id] = {
                "staff_id": None, "service_id": None, "seance_length": None,
                "datetime": None, "waiting_for_name": False,
                "preferred_time": None, "requested_hour": None, "requested_minute": None, "date": None,
                "multi_booking_count": 1, "bookings_created": 0,
                "multi_booking_staff_ids": []  # ID мастеров для мульти-записи
            }
        return self.booking_context[session_id]
    
    def _set_booking_context(self, session_id: str, **kwargs):
        ctx = self._get_booking_context(session_id)
        ctx.update(kwargs)
        logger.info(f"   Updated booking context: {ctx}")
    
    def _get_history(self, session_id: str) -> List[Dict]:
        if session_id not in self.conversations:
            self.conversations[session_id] = []
        return self.conversations[session_id]
    
    def _save_messages(self, session_id: str, messages: List):
        """Save conversation history, properly handling tool calls.
        
        Tool messages must always follow an assistant message with tool_calls.
        We need to save: user messages, assistant messages (with or without tool_calls),
        and tool messages (only if preceded by assistant with tool_calls).
        """
        history = []
        last_assistant_had_tool_calls = False
        
        for msg in messages:
            if hasattr(msg, 'model_dump'):
                msg_dict = msg.model_dump()
            elif isinstance(msg, dict):
                msg_dict = msg
            else:
                continue
            
            role = msg_dict.get("role")
            
            # Skip system messages
            if role == "system":
                continue
            
            # Handle tool messages - only include if preceded by assistant with tool_calls
            if role == "tool":
                if last_assistant_had_tool_calls:
                    history.append(msg_dict)
                continue
            
            # Track if assistant message has tool_calls
            if role == "assistant":
                last_assistant_had_tool_calls = bool(msg_dict.get("tool_calls"))
            else:
                last_assistant_had_tool_calls = False
            
            history.append(msg_dict)
        
        # Keep last 20 messages to avoid context overflow
        self.conversations[session_id] = history[-20:]
    
    async def _execute_tool(self, name: str, args: Dict, session_id: str = None) -> Any:
        logger.info(f"Tool called: {name}, args: {json.dumps(args, ensure_ascii=False)}")
        
        try:
            if name == "get_all_staff":
                result = sheets_service.get_all_staff()
            elif name == "get_all_services":
                result = sheets_service.get_all_services()
            elif name == "get_services_by_staff_name":
                result = sheets_service.get_services_by_staff_name(args["staff_name"])
                if session_id and result and len(result) > 0:
                    self._set_booking_context(session_id, staff_id=str(result[0].get("staff_id")))
                    # Найти услугу "Стрижка" или первую с непустым именем
                    default_service = None
                    for svc in result:
                        svc_name = svc.get("service_name", "").lower()
                        if "стрижка" in svc_name or "haircut" in svc_name:
                            default_service = svc
                            break
                        if svc_name and not default_service:
                            default_service = svc
                    if default_service:
                        self._set_booking_context(session_id, 
                            service_id=str(default_service.get("service_id")),
                            seance_length=str(default_service.get("seance_length", "3600")))
                        logger.info(f"   Default service: {default_service.get('service_name')} (id={default_service.get('service_id')})")
            elif name == "get_services_by_name":
                result = sheets_service.get_services_by_name(
                    args["service_name"], 
                    args.get("staff_name")
                )
            elif name == "get_available_dates":
                result = await alteegio_service.get_available_dates(args["staff_id"], args["service_ids"])
            elif name == "get_available_times":
                # Использовать service_id из контекста если есть
                ctx = self._get_booking_context(session_id) if session_id else {}
                service_ids = args.get("service_ids")
                if not service_ids and ctx.get("service_id"):
                    service_ids = [ctx["service_id"]]
                    logger.info(f"   Using service_id from context: {ctx['service_id']}")
                result = await alteegio_service.get_available_times(args["staff_id"], args["date"], service_ids)
                if session_id and result and "data" in result and len(result["data"]) > 0:
                    first_slot = result["data"][0]
                    self._set_booking_context(session_id,
                        service_id=service_ids[0] if service_ids else None,
                        seance_length=str(first_slot.get("seance_length", "3600")),
                        date=args["date"])
            elif name == "get_available_masters":
                result = await alteegio_service.get_available_masters(args["datetime"])
                # При мульти-записи сохраняем первых N мастеров
                if session_id and result and len(result) > 0:
                    ctx = self._get_booking_context(session_id)
                    multi_count = ctx.get("multi_booking_count", 1)
                    if multi_count > 1:
                        # Сохраняем ID первых мастеров
                        staff_ids = [str(m["id"]) for m in result[:multi_count]]
                        datetime_str = args.get("datetime", "")
                        # Получаем service_id для первой услуги (по умолчанию стрижка)
                        first_master_name = result[0].get("name", "") if result else ""
                        services = sheets_service.get_services_by_staff_name(first_master_name) if first_master_name else []
                        default_service_id = None
                        default_seance_length = "3600"
                        for svc in services:
                            if "стрижка" in svc.get("service_name", "").lower():
                                default_service_id = str(svc.get("service_id"))
                                default_seance_length = str(svc.get("seance_length", "3600"))
                                break
                        if not default_service_id and services:
                            default_service_id = str(services[0].get("service_id"))
                            default_seance_length = str(services[0].get("seance_length", "3600"))
                        
                        self._set_booking_context(session_id, 
                            multi_booking_staff_ids=staff_ids,
                            service_id=default_service_id,
                            seance_length=default_seance_length,
                            datetime=datetime_str, 
                            date=datetime_str.split("T")[0] if datetime_str else None,
                            waiting_for_name=True)  # Сразу спрашиваем имя!
                        logger.info(f"   Multi-booking: saved {len(staff_ids)} staff_ids: {staff_ids}, service_id={default_service_id}")
            elif name == "create_appointment":
                result = await alteegio_service.create_appointment(
                    staff_id=args["staff_id"], service_id=args["service_id"],
                    client_phone=args["client_phone"], client_name=args["client_name"],
                    datetime=args["datetime"], seance_length=args["seance_length"])
                if session_id and result and result.get("success"):
                    self._set_booking_context(session_id, staff_id=None, service_id=None,
                        seance_length=None, datetime=None, waiting_for_name=False,
                        preferred_time=None, requested_hour=None, requested_minute=None, date=None,
                        multi_booking_count=1, bookings_created=0)
            else:
                result = {"error": f"Unknown tool: {name}"}
            
            logger.info(f"   Result: {json.dumps(result, ensure_ascii=False, default=str)[:500]}")
            return result
        except Exception as e:
            logger.error(f"   Error: {e}")
            return {"error": str(e)}
    
    def _detect_requested_time(self, text: str) -> Optional[tuple[int, int]]:
        """Detect explicit time like 13:30, 13.30 or '13 30'."""
        import re
        text_lower = text.lower()

        # Explicit hh:mm or hh.mm
        match = re.search(r'\b([01]?\d|2[0-3])\s*[:\.]\s*([0-5]\d)\b', text_lower)
        if match:
            return int(match.group(1)), int(match.group(2))

        # Space-separated time like '13 30' or '9 15'
        match = re.search(r'\b([01]?\d|2[0-3])\s+([0-5]\d)\b', text_lower)
        if match:
            return int(match.group(1)), int(match.group(2))

        return None

    def _detect_requested_hour(self, text: str) -> Optional[int]:
        """Detect hour from text like 'на час', 'на два', 'сағат бірге', 'сагат бирге'"""
        import re
        text_lower = text.lower()

        # If explicit minutes are present, return the exact hour part
        explicit_time = self._detect_requested_time(text)
        if explicit_time:
            return explicit_time[0]

        # Russian time words
        time_words_ru = {
            "час": 13, "два": 14, "три": 15, "четыре": 16, "пять": 17,
            "шесть": 18, "семь": 19, "восемь": 20, "девять": 21, "десять": 10,
            "одиннадцать": 11, "двенадцать": 12
        }
        
        # Kazakh time words (сағат = час, with transliteration support)
        time_words_kk = {
            "бірге": 13, "бирге": 13,  # 1 час
            "екіге": 14, "екиге": 14, "екige": 14,  # 2 часа
            "үшке": 15, "ушке": 15, "ушке": 15,  # 3 часа
            "төртке": 16, "тортке": 16, "тортке": 16,  # 4 часа
            "беске": 17,  # 5 часов
            "алтыға": 18, "алтыга": 18,  # 6 часов
            "жетіге": 19, "жетиге": 19,  # 7 часов
            "сегізге": 20, "сегизге": 20,  # 8 часов
            "тоғызға": 21, "тогызга": 21,  # 9 часов
            "онға": 10, "онга": 10,  # 10 часов
            "он бірге": 11, "он бирге": 11,  # 11 часов
            "он екіге": 12, "он екиге": 12,  # 12 часов
        }
        
        # Check Russian patterns
        for word, h in time_words_ru.items():
            if f"на {word}" in text_lower or f"в {word}" in text_lower:
                return h
        
        # Check Kazakh patterns (сағат/сагат + word, or just the word)
        for word, h in time_words_kk.items():
            if word in text_lower:
                return h
        
        # Check for "сағат N" or "сагат N" pattern (Kazakh)
        kazakh_num_match = re.search(r'саг?ат\s+(\d{1,2})(?!\d|\s*:\d)', text_lower)
        if kazakh_num_match:
            num = int(kazakh_num_match.group(1))
            if 1 <= num <= 7:
                return num + 12
            elif 8 <= num <= 23:
                return num
        
        # Check for "на N" or "в N" pattern (Russian)
        num_match = re.search(r'(?:на|в)\s+(\d{1,2})(?!\d|\s*:\d)', text_lower)
        if num_match:
            num = int(num_match.group(1))
            if 1 <= num <= 7:
                return num + 12
            elif 8 <= num <= 23:
                return num
        
        # Check for "HH:MM" pattern
        time_match = re.search(r'(\d{1,2}):(\d{2})', text)
        if time_match:
            return int(time_match.group(1))
        
        # Check for just a number (e.g., "давайте 10", "на 10", "10 часов")
        # Only if it looks like a time (1-21)
        just_num_match = re.search(r'\b(\d{1,2})\b', text_lower)
        if just_num_match:
            num = int(just_num_match.group(1))
            # 1-7 = afternoon (13:00 - 19:00), 8-21 = morning/evening (08:00 - 21:00)
            if 1 <= num <= 21:
                return num
        
        return None
    
    async def chat(self, user_input: str, session_id: str, user_phone: str = None) -> str:
        import re
        full_session_id = f"{SESSION_PREFIX}_{session_id}"
        
        logger.info(f"=" * 60)
        logger.info(f"Chat: {user_input}, session: {full_session_id}")
        
        # Проверка на команду "рестарт" - сброс всего контекста
        if user_input.strip().lower() == "рестарт":
            if full_session_id in self.conversations:
                del self.conversations[full_session_id]
            if full_session_id in self.booking_context:
                del self.booking_context[full_session_id]
            logger.info(f"   🔄 Session reset by user command 'рестарт'")
            return "Сессия сброшена. Начинаем заново! Чем могу помочь?"
        
        ctx = self._get_booking_context(full_session_id)
        logger.info(f"   Context: {ctx}")
        
        # Check if waiting for client name OR waiting for time confirmation
        if ctx.get("waiting_for_name") and ctx.get("datetime"):
            # Проверяем - может клиент указал ВРЕМЯ а не имя?
            requested_time = self._detect_requested_time(user_input)
            if requested_time is not None:
                requested_hour, requested_minute = requested_time
                date_str = ctx["date"].split("T")[0] if "T" in ctx["date"] else ctx["date"]
                new_datetime = f"{date_str}T{requested_hour:02d}:{requested_minute:02d}:00"
                self._set_booking_context(full_session_id, datetime=new_datetime, requested_hour=requested_hour, requested_minute=requested_minute)
                logger.info(f"   Client specified time {requested_hour:02d}:{requested_minute:02d}, updated datetime")
                return f"Отлично, записываем на {requested_hour:02d}:{requested_minute:02d}! Как вас записать?"

            requested_hour = self._detect_requested_hour(user_input)
            if requested_hour is not None:
                date_str = ctx["date"].split("T")[0] if "T" in ctx["date"] else ctx["date"]
                new_datetime = f"{date_str}T{str(requested_hour).zfill(2)}:00:00"
                self._set_booking_context(full_session_id, datetime=new_datetime, requested_hour=requested_hour, requested_minute=None)
                logger.info(f"   Client specified time {requested_hour}:00, updated datetime")
                return f"Отлично, записываем на {requested_hour}:00! Как вас записать?"
        
        # Для мульти-записи нужны multi_booking_staff_ids, для обычной - staff_id и service_id
        has_multi = ctx.get("multi_booking_count", 1) > 1 and ctx.get("multi_booking_staff_ids")
        has_single = ctx.get("staff_id") and ctx.get("service_id")
        
        # ВАЖНО: авто-создание записи ТОЛЬКО когда бот уже спросил имя (waiting_for_name=True)
        # Иначе "Давай в три" воспринималось как имя клиента!
        if ctx.get("waiting_for_name") and (has_multi or has_single):
            name = user_input.strip()
            name_match = re.search(r'(?:как|на имя)\s+(.+?)(?:\s*$|\s*\.|\s*,)', user_input, re.IGNORECASE)
            if name_match:
                name = name_match.group(1).strip()
            
            multi_count = ctx.get("multi_booking_count", 1)
            multi_staff_ids = ctx.get("multi_booking_staff_ids", [])
            logger.info(f"   Auto-creating {multi_count} appointment(s) for: {name}")
            
            results = []
            master_names = []
            
            for i in range(multi_count):
                # Для мульти-записи берём разные staff_id из списка
                if has_multi and i < len(multi_staff_ids):
                    staff_id = multi_staff_ids[i]
                else:
                    staff_id = ctx["staff_id"]
                
                result = await alteegio_service.create_appointment(
                    staff_id=staff_id, service_id=ctx["service_id"],
                    client_phone=user_phone or "", client_name=name,
                    datetime=ctx["datetime"], seance_length=ctx.get("seance_length", "3600")
                )
                results.append(result)
                if result and result.get("success"):
                    master_name = result.get("data", {}).get("staff", {}).get("name", "")
                    if master_name and master_name not in master_names:
                        master_names.append(master_name)
                logger.info(f"   Appointment {i+1}/{multi_count}: staff_id={staff_id}, {'success' if result and result.get('success') else 'failed'}")
            
            success_count = sum(1 for r in results if r and r.get("success"))
            
            if success_count == multi_count:
                self._set_booking_context(full_session_id, staff_id=None, service_id=None,
                    seance_length=None, datetime=None, waiting_for_name=False,
                    preferred_time=None, requested_hour=None, requested_minute=None, date=None,
                    multi_booking_count=1, bookings_created=0)
                master_name = results[0].get("data", {}).get("staff", {}).get("name", "мастер")
                time_raw = results[0].get("data", {}).get("date", "")
                time_formatted = format_datetime_human(time_raw) if time_raw else ""
                if multi_count > 1:
                    return f"Записал {multi_count} человека! {master_name} ждёт вас {time_formatted}. До встречи!"
                return f"Записал вас! {master_name} ждёт вас {time_formatted}. До встречи!"
            elif success_count > 0:
                self._set_booking_context(full_session_id, staff_id=None, service_id=None,
                    seance_length=None, datetime=None, waiting_for_name=False,
                    preferred_time=None, requested_hour=None, requested_minute=None, date=None,
                    multi_booking_count=1, bookings_created=0)
                return f"Записал {success_count} из {multi_count}. Остальные не удалось создать."
            else:
                return f"Не удалось создать запись: {results[0].get('error', 'Ошибка') if results[0] else 'Ошибка'}. Попробуйте ещё раз."
        
        messages = [{"role": "system", "content": get_system_prompt()}]
        
        for msg in self._get_history(full_session_id):
            messages.append(msg)
        
        # Detect and save time preferences
        user_lower = user_input.lower()
        
        # Detect multi-booking (двое детей, два ребенка, екі бала, на двоих)
        # Нормализуем казахские буквы к кириллице для надёжного сравнения
        kazakh_to_cyrillic = {
            'ә': 'а', 'ғ': 'г', 'қ': 'к', 'ң': 'н', 'ө': 'о', 'ұ': 'у', 'ү': 'у', 
            'һ': 'х', 'і': 'и', 'ш': 'ш', 'щ': 'щ', 'ы': 'ы', 'і': 'и'
        }
        normalized_lower = user_lower
        for kk, ru in kazakh_to_cyrillic.items():
            normalized_lower = normalized_lower.replace(kk, ru)
        
        logger.info(f"   Checking multi-booking in: '{user_lower}' -> normalized: '{normalized_lower}'")
        
        # Паттерны в НОРМАЛИЗОВАННОМ виде (все казахские буквы заменены на кириллицу)
        # ВАЖНО: "ы" не меняется при нормализации, поэтому добавляем варианты с "ы" и "и"
        multi_booking_patterns = [
            "двое дет", "два ребен", "двух дет", "двоих дет",
            # Казахский: екі (2) -> нормализовано в "eki" или "екы" в зависимости от буквы
            "еки бала", "еки балани", "еки балага", "еки балалар",
            "екы бала", "екы баланы", "екы балага", "екы балалар",  # С казахской "ы"
            "еки балан", "еки баланн",  # Дополнительные варианты
            "eki bala", "eki balany", "eki balaga",  # Latin
            "еки", "екы",  # Просто "2" на казахском
            "на двоих", "на двух", "двоих", "с сыном", "с дочер",
            "двоих сыновей", "двоих дочерей",
            "2 детей", "2 ребенка", "двоих детей",
            "2 бала", "2 баланы", "2 балани"
        ]
        detected_multi = False
        for pattern in multi_booking_patterns:
            if pattern in normalized_lower:
                self._set_booking_context(full_session_id, multi_booking_count=2)
                logger.info(f"   ✅ Detected multi-booking pattern '{pattern}': 2 appointments")
                detected_multi = True
                break
        
        if not detected_multi:
            logger.info(f"   Multi-booking NOT detected")
        
        # Также проверяем цифру 2 в контексте "детей" или "бала"
        if not detected_multi and ("бала" in user_lower or "дет" in user_lower or "ребен" in user_lower):
            import re
            if re.search(r'\b2\b', user_lower) or "два" in user_lower or "двое" in user_lower:
                self._set_booking_context(full_session_id, multi_booking_count=2)
                logger.info(f"   ✅ Detected multi-booking (numeric 2): 2 appointments")
        
        if "обед" in user_lower:
            self._set_booking_context(full_session_id, preferred_time="lunch")
        elif any(w in user_lower for w in ["утро", "утром"]):
            self._set_booking_context(full_session_id, preferred_time="morning")
        elif any(w in user_lower for w in ["вечер", "вечером"]):
            self._set_booking_context(full_session_id, preferred_time="evening")
        
        # Detect specific hour or exact time
        requested_time = self._detect_requested_time(user_input)
        requested_hour = None
        requested_minute = None
        if requested_time is not None:
            requested_hour, requested_minute = requested_time
            self._set_booking_context(full_session_id, requested_hour=requested_hour, requested_minute=requested_minute)
            logger.info(f"   Detected exact time: {requested_hour:02d}:{requested_minute:02d}")
        else:
            requested_hour = self._detect_requested_hour(user_input)
            if requested_hour is not None:
                self._set_booking_context(full_session_id, requested_hour=requested_hour, requested_minute=None)
                logger.info(f"   Detected hour: {requested_hour}")

        # АВТО-ЗАПИСЬ: Если в контексте есть staff_id, service_id, date и клиент указал время
        if ctx.get("staff_id") and ctx.get("service_id") and ctx.get("date") and requested_hour is not None:
            date_str = ctx["date"].split("T")[0] if "T" in ctx["date"] else ctx["date"]
            minute = requested_minute if requested_minute is not None else 0
            datetime_str = f"{date_str}T{str(requested_hour).zfill(2)}:{str(minute).zfill(2)}:00"
            self._set_booking_context(full_session_id, datetime=datetime_str, waiting_for_name=True)
            logger.info(f"   ✅ Auto-set datetime={datetime_str}, asking for name")
            if requested_minute is not None:
                return f"Отлично, записываем на {requested_hour:02d}:{requested_minute:02d}! Как вас записать?"
            return f"Отлично, записываем на {requested_hour}:00! Как вас записать?"

        # Build user message with context
        user_message = f"User Input: {user_input}"
        if user_phone:
            user_message += f"\nUser Phone: {user_phone}"
        
        ctx = self._get_booking_context(full_session_id)
        context_hints = []
        
        # Если в контексте есть staff_id, service_id и date — клиент уже выбрал мастера!
        # Добавляем подсказку чтобы AI НЕ предлагал других мастеров
        if ctx.get("staff_id") and ctx.get("service_id") and ctx.get("date"):
            staff_name = "выбранный мастер"
            # Попробуем найти имя мастера в последних сообщениях
            for msg in reversed(self._get_history(full_session_id)):
                if msg.get("role") == "assistant" and "Миша" in msg.get("content", ""):
                    staff_name = "Миша"
                    break
            context_hints.append(f"ВНИМАНИЕ: Клиент УЖЕ выбрал мастера (staff_id={ctx['staff_id']}) и услугу! Просто запиши его на указанное время, НЕ предлагай других мастеров и НЕ вызывай get_available_masters!")
        elif ctx.get("waiting_for_name") and ctx.get("datetime"):
            context_hints.append(f"Клиент ждет подтверждения записи на {format_datetime_human(ctx['datetime'])}. Спросите, как его записать.")
        
        if ctx.get("preferred_time"):
            hints = {"lunch": "Клиент хочет на обед (12:00-14:00)!", "morning": "Клиент хочет утром (09:00-12:00)!", "evening": "Клиент хочет вечером (17:00-20:00)!"}
            context_hints.append(hints.get(ctx['preferred_time'], ''))
        
        if ctx.get("requested_hour"):
            if ctx.get("requested_minute") is not None:
                context_hints.append(f"Клиент уже указал время: {ctx['requested_hour']:02d}:{ctx['requested_minute']:02d}! Ищи мастеров на это время!")
            else:
                context_hints.append(f"Клиент уже указал время: {ctx['requested_hour']}:00! Ищи мастеров на это время!")
        
        if context_hints:
            user_message += f"\n\nПРИМЕЧАНИЕ: {' '.join(context_hints)}"
        
        messages.append({"role": "user", "content": user_message})
        
        # Call OpenAI
        response = self.client.chat.completions.create(model=self.model, messages=messages, tools=TOOLS, tool_choice="auto")
        assistant_message = response.choices[0].message
        
        # Handle tool calls
        while assistant_message.tool_calls:
            messages.append(assistant_message)
            for tool_call in assistant_message.tool_calls:
                args = json.loads(tool_call.function.arguments)
                result = await self._execute_tool(tool_call.function.name, args, full_session_id)
                messages.append({"role": "tool", "tool_call_id": tool_call.id, "content": json.dumps(result, ensure_ascii=False, default=str)})
            response = self.client.chat.completions.create(model=self.model, messages=messages, tools=TOOLS, tool_choice="auto")
            assistant_message = response.choices[0].message
        
        response_text = assistant_message.content or ""
        
        # Check if AI asks for name
        if "как вас записать" in response_text.lower():
            ctx = self._get_booking_context(full_session_id)
            if ctx.get("staff_id") and ctx.get("service_id") and ctx.get("date"):
                time_match = re.search(r'(\d{1,2}):(\d{2})', response_text)
                if time_match:
                    date_str = ctx["date"].split("T")[0] if "T" in ctx["date"] else ctx["date"]
                    datetime_str = f"{date_str}T{time_match.group(1).zfill(2)}:{time_match.group(2)}:00"
                    self._set_booking_context(full_session_id, datetime=datetime_str, waiting_for_name=True)
                elif ctx.get("requested_hour"):
                    date_str = ctx["date"].split("T")[0] if "T" in ctx["date"] else ctx["date"]
                    datetime_str = f"{date_str}T{str(ctx['requested_hour']).zfill(2)}:00:00"
                    self._set_booking_context(full_session_id, datetime=datetime_str, waiting_for_name=True)
                else:
                    self._set_booking_context(full_session_id, waiting_for_name=True)
        
        self._save_messages(full_session_id, messages)
        logger.info(f"   Response: {response_text[:200]}")
        
        return response_text


ai_agent_service = AIAgentService()