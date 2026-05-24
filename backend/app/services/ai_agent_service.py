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

    return f"""Ты — виртуальный ассистент барбершопа «KHAN» (Момышулы 55).
Записываешь клиентов на стрижки. Отвечай кратко и по делу. Цены — в тенге.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
АБСОЛЮТНЫЕ ПРАВИЛА (нельзя нарушать):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. НИКОГДА не придумывай staff_id, service_id, seance_length — только из ответов инструментов.
2. НИКОГДА не показывай клиенту технические ID.
3. НИКОГДА не представляйся повторно — только один раз в начале разговора.
4. НИКОГДА не вызывай create_appointment без явно названного клиентом имени.
5. НИКОГДА не называй свободное время без вызова инструмента — только реальные данные из API.
6. НИКОГДА не вызывай get_available_times без staff_id из инструмента.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
МАСТЕРА И СПЕЦИАЛИЗАЦИЯ:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• Наргиза — ТОЛЬКО: химическая завивка, маникюр, педикюр.
  При вопросе о СТРИЖКЕ (мужской, женской, детской) — НЕ включать Наргизу!
• Сухрабхан, Миша, Нурперзент, Эльбрус, Сундет, Нурдаулет — все виды стрижек.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
АЛГОРИТМ ЗАПИСИ — СТРОГО ПО ШАГАМ:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ШАГ 1: Клиент назвал мастера
  → вызови get_services_by_staff_name(staff_name)
  → из ответа запомни staff_id и service_id (НЕ придумывай!)

ШАГ 2: Есть staff_id + клиент назвал дату
  → вызови get_available_times(staff_id, date, service_ids)
  → покажи клиенту время в виде: «Свободные окошки: 10:00, 11:30, 14:00»

ШАГ 3: Клиент выбрал время
  → напиши: «Как вас записать?»
  → жди имя клиента

ШАГ 4: Клиент назвал имя
  → вызови create_appointment со всеми параметрами из шагов 1–3
  → подтверди запись: «Записал! [Мастер] ждёт вас [дата]. До встречи!»

ВАЖНО: нельзя перескакивать шаги! Нет staff_id — нельзя get_available_times. Нет имени — нельзя create_appointment.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ВОПРОС «КТО СВОБОДЕН?»:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• Указаны И дата И время → вызови get_available_masters(datetime)
  → покажи список (для стрижки — без Наргизы)
• Указана только дата без времени → вызови get_services_by_staff_name, затем get_available_times
  → покажи слоты, спроси на какое время

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ЗАПИСЬ НЕСКОЛЬКИХ ЧЕЛОВЕК:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
«Двое детей», «на двоих», «екі бала» = нужно ДВА мастера на одно время:
1. get_available_masters → выбери двух свободных мастеров
2. Спроси имя
3. Создай ДВЕ записи: каждому мастеру своя, одно время, одно имя

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ФОРМАТ ОТВЕТОВ:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• Дата: «7 марта в 14:00» — НЕ «2026-03-07 14:00:00»
• Слоты: «Свободные окошки: 10:00, 11:30, 14:00, 16:00»
• Если нет свободных окошек: «На эту дату нет свободных окошек. Выберите другую дату?»

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ТЕКУЩЕЕ ВРЕМЯ:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Сейчас: {now.strftime('%Y-%m-%d %H:%M')} (Алматы, UTC+5)
Сегодня: {now.strftime('%Y-%m-%d')} ({today_name})
Завтра: {tomorrow.strftime('%Y-%m-%d')} ({tomorrow_name})"""


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_all_staff",
            "description": (
                "Список всех мастеров с именами. "
                "Вызывай ТОЛЬКО когда клиент спрашивает «кто работает?», «какие мастера?», «кым бар?». "
                "НЕ показывай клиенту staff_id из результата — только имена."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_services_by_staff_name",
            "description": (
                "Услуги и ID мастера по имени. "
                "ОБЯЗАТЕЛЬНО вызывать первым после того, как клиент назвал мастера — ШАГ 1 алгоритма. "
                "Из ответа бери staff_id и service_id — НИКОГДА не придумывай их сам. "
                "Для стрижки используй service с «стрижка» в названии."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "staff_name": {"type": "string", "description": "Имя мастера (например 'Миша', 'Нурдаулет')"}
                },
                "required": ["staff_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_services_by_name",
            "description": (
                "Поиск услуги по названию (например «стрижка», «борода», «маникюр»). "
                "Используй когда клиент называет услугу ДО выбора мастера. "
                "Возвращает service_id и seance_length для записи."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "service_name": {"type": "string", "description": "Название услуги"},
                    "staff_name": {"type": "string", "description": "Имя мастера (опционально)"}
                },
                "required": ["service_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_available_dates",
            "description": (
                "Доступные даты для записи к мастеру. "
                "Требует staff_id и service_ids из get_services_by_staff_name. "
                "Используй только когда клиент не указал конкретную дату."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "staff_id": {"type": "string", "description": "ID мастера из get_services_by_staff_name (не придумывать!)"},
                    "service_ids": {"type": "array", "items": {"type": "string"}, "description": "ID услуг из get_services_by_staff_name"}
                },
                "required": ["staff_id", "service_ids"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_available_times",
            "description": (
                "Свободные окошки мастера на конкретную дату — ШАГ 2 алгоритма. "
                "ТРЕБУЕТ staff_id из get_services_by_staff_name (не придумывать!). "
                "Дата — только в формате YYYY-MM-DD (например '2026-03-07'). "
                "НЕ вызывай без staff_id из инструмента. "
                "Результат: список доступных времён для показа клиенту."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "staff_id": {"type": "string", "description": "ID мастера из get_services_by_staff_name (не придумывать!)"},
                    "date": {"type": "string", "description": "Дата в формате YYYY-MM-DD"},
                    "service_ids": {"type": "array", "items": {"type": "string"}, "description": "ID услуг из get_services_by_staff_name"}
                },
                "required": ["staff_id", "date", "service_ids"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_available_masters",
            "description": (
                "Свободные мастера на конкретное дату И время. "
                "Вызывай ТОЛЬКО когда клиент указал И дату И время одновременно. "
                "Если только дата без времени — НЕ вызывай этот инструмент! "
                "datetime в ISO формате: '2026-04-05T15:00:00'. "
                "Для стрижки — в ответе исключи Наргизу из предложений."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "datetime": {"type": "string", "description": "Дата И время ISO: '2026-04-05T15:00:00'"}
                },
                "required": ["datetime"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_appointment",
            "description": (
                "Создаёт запись в системе — ШАГ 4 алгоритма. "
                "ОБЯЗАТЕЛЬНЫЕ условия ПЕРЕД вызовом:\n"
                "  1. staff_id получен из get_services_by_staff_name или get_available_masters\n"
                "  2. service_id получен из get_services_by_staff_name\n"
                "  3. Клиент ЯВНО назвал своё имя (не «да», не «хорошо»)\n"
                "  4. Дата и время подтверждены\n"
                "НЕ вызывай если хоть одно условие не выполнено!"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "staff_id": {"type": "string", "description": "ID мастера из инструмента (НЕ придумывать!)"},
                    "service_id": {"type": "string", "description": "ID услуги из инструмента (НЕ придумывать!)"},
                    "client_phone": {"type": "string", "description": "Номер телефона клиента"},
                    "client_name": {"type": "string", "description": "Имя клиента — явно сказанное, не придуманное"},
                    "datetime": {"type": "string", "description": "Дата и время в ISO формате"},
                    "seance_length": {"type": "string", "description": "Длина сеанса в секундах из get_services_by_staff_name"}
                },
                "required": ["staff_id", "service_id", "client_phone", "client_name", "datetime", "seance_length"]
            }
        }
    }
]


# Слова-не-имена: ответы-подтверждения которые клиент пишет вместо имени
_NON_NAME_WORDS = {
    "да", "нет", "не", "ок", "окей", "хорошо", "ладно", "конечно", "понятно",
    "давай", "ага", "угу", "идёт", "идет", "продолжай", "записывай",
    "жақсы", "жаксы", "иа", "йа", "yes", "no", "ok", "okay", "sure", "yep",
    "ясно", "отлично", "супер", "класс", "хор", "хор.", "понял", "поняла",
    "спасибо", "пожалуйста", "благодарю", "спс", "thx", "thanks",
    "сегодня", "завтра", "послезавтра", "утром", "вечером",
    "записывайте", "запишите", "запиши", "давайте", "пишите",
    "подтверждаю", "подходит", "устраивает", "согласен", "согласна",
}


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
                "multi_booking_staff_ids": []
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
        """Save conversation history, properly handling tool calls."""
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

            if role == "system":
                continue

            if role == "tool":
                if last_assistant_had_tool_calls:
                    history.append(msg_dict)
                continue

            if role == "assistant":
                last_assistant_had_tool_calls = bool(msg_dict.get("tool_calls"))
            else:
                last_assistant_had_tool_calls = False

            history.append(msg_dict)

        # Truncate, then ensure history starts with a user message.
        # Cutting in the middle of a tool_call block causes OpenAI 400:
        # "messages with role 'tool' must be a response to a preceding message with 'tool_calls'"
        history = history[-20:]
        while history and history[0].get("role") != "user":
            history.pop(0)

        self.conversations[session_id] = history
    
    async def _execute_tool(self, name: str, args: Dict, session_id: str = None) -> Any:
        logger.info(f"Tool called: {name}, args: {json.dumps(args, ensure_ascii=False)}")
        
        try:
            if name == "get_all_staff":
                result = sheets_service.get_all_staff()
            elif name == "get_all_services":
                result = sheets_service.get_all_services()
            elif name == "get_services_by_staff_name":
                result = sheets_service.get_services_by_staff_name(args["staff_name"])
                if not result:
                    return {
                        "error": f"Мастер '{args['staff_name']}' не найден. Вызови get_all_staff чтобы увидеть актуальный список мастеров."
                    }
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
                # Убедимся что дата в формате YYYY-MM-DD (AI иногда передаёт с временем)
                date_clean = args["date"].split("T")[0] if "T" in args.get("date", "") else args.get("date", "")
                raw_result = await alteegio_service.get_available_times(args["staff_id"], date_clean, service_ids)
                if session_id and date_clean:
                    # Always save the queried date — even if no slots found.
                    # Without this, follow-up messages like "давайте на пять" have no date in context.
                    ctx_update: Dict[str, Any] = {"date": date_clean}
                    if raw_result and "data" in raw_result and len(raw_result["data"]) > 0:
                        first_slot = raw_result["data"][0]
                        ctx_update["service_id"] = service_ids[0] if service_ids else None
                        ctx_update["seance_length"] = str(first_slot.get("seance_length", "3600"))
                    self._set_booking_context(session_id, **ctx_update)
                result = self._format_times_for_ai(raw_result)
            elif name == "get_available_masters":
                # Python-level guard: if master already selected, block this call entirely.
                # The AI sometimes calls this even when staff_id is already in context.
                if session_id:
                    guard_ctx = self._get_booking_context(session_id)
                    if guard_ctx.get("staff_id") and guard_ctx.get("service_id"):
                        logger.warning(f"   ⚠️ BLOCKED get_available_masters — master already in context (staff_id={guard_ctx['staff_id']})")
                        return {
                            "blocked": True,
                            "instruction": "Мастер уже выбран! НЕ предлагай других мастеров. Спроси у клиента ДАТУ и ВРЕМЯ для записи к выбранному мастеру."
                        }
                raw_masters = await alteegio_service.get_available_masters(args["datetime"])
                # Load excluded master IDs from bot settings (set via admin dashboard)
                excluded_ids: set = set()
                try:
                    from app.database import get_bot_settings as _gbs
                    _bot_cfg = _gbs()
                    excluded_ids = {str(eid) for eid in _bot_cfg.get("excluded_master_ids", [])}
                except Exception:
                    pass
                # Also always hide Наргиза from the general list (specialises in manicure only)
                masters_to_use = [
                    m for m in raw_masters
                    if "наргиз" not in m.get("name", "").lower()
                    and str(m.get("id", "")) not in excluded_ids
                ]
                if not masters_to_use:
                    masters_to_use = raw_masters  # fallback: show all if everything filtered
                note_parts = ["Мастера доступны для стрижки."]
                if excluded_ids:
                    note_parts.append(f"Скрытые мастера (id): {', '.join(excluded_ids)} — не предлагай их.")
                result = {
                    "available_masters": masters_to_use,
                    "note": " ".join(note_parts)
                }
                masters_list = masters_to_use
                if session_id and masters_list and len(masters_list) > 0:
                    ctx = self._get_booking_context(session_id)
                    multi_count = ctx.get("multi_booking_count", 1)
                    if multi_count > 1:
                        # Сохраняем ID первых мастеров
                        staff_ids = [str(m["id"]) for m in masters_list[:multi_count]]
                        datetime_str = args.get("datetime", "")
                        # Получаем service_id для первой услуги (по умолчанию стрижка)
                        first_master_name = masters_list[0].get("name", "") if masters_list else ""
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
    
    def _format_times_for_ai(self, times_result: Dict) -> Dict:
        """Convert raw get_available_times API response to AI-friendly format."""
        if not times_result or "data" not in times_result:
            return {"available_times": [], "message": "Нет свободных окошек на эту дату"}

        slots = times_result["data"]
        if not slots:
            return {"available_times": [], "message": "Нет свободных окошек на эту дату"}

        formatted = []
        for slot in slots:
            time_str = slot.get("time", "")
            if not time_str:
                continue
            # time can be "09:00:00" or "2026-03-07T09:00:00"
            if "T" in time_str:
                time_part = time_str.split("T")[1][:5]
            else:
                time_part = time_str[:5]
            formatted.append(time_part)

        seance_length = slots[0].get("seance_length", 3600) if slots else 3600
        return {
            "available_times": formatted,
            "seance_length": seance_length,
            "count": len(formatted),
            "instruction": "Покажи клиенту список: «Свободные окошки: " + ", ".join(formatted) + "» и спроси на какое время записать."
        }

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
        
        # Check for "HH:MM" pattern (explicit colon format)
        time_match = re.search(r'(\d{1,2}):(\d{2})', text)
        if time_match:
            return int(time_match.group(1))

        # NOTE: no bare-number fallback — "2 бала", "3 человека" etc. must NOT be treated as times
        return None
    
    async def chat(self, user_input: str, session_id: str, user_phone: str = None) -> str:
        import re
        full_session_id = f"{SESSION_PREFIX}_{session_id}"

        # ── Проверяем, включён ли чатбот ────────────────────────────────────
        try:
            from app.database import get_bot_settings
            bot_cfg = get_bot_settings()
            if not bot_cfg.get("chatbot_enabled", True):
                logger.info(f"   🔕 Chatbot is DISABLED — dropping message from {session_id}")
                return "Бот временно недоступен. Позвоните нам или напишите позже 🙏"
        except Exception as _e:
            logger.warning(f"   ⚠️ Could not read bot settings: {_e}")

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
            # Проверяем - может клиент уточнил ВРЕМЯ а не сказал имя?
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
            # Критическая проверка: без datetime запись невозможна
            if not ctx.get("datetime"):
                logger.warning(f"   waiting_for_name=True but datetime is None — asking for time")
                name_candidate = user_input.strip()
                if name_candidate.lower() not in _NON_NAME_WORDS and len(name_candidate) >= 2:
                    return f"Хорошо, {name_candidate}! На какую дату и время вас записать?"
                return "На какую дату и время записываем?"

            name_patterns = [
                r'меня зовут\s+([А-ЯЁа-яёA-Za-z][А-ЯЁа-яёA-Za-z\s\-]{1,30})',
                r'я\s+([А-ЯЁа-яёA-Za-z][А-ЯЁа-яёA-Za-z\s\-]{1,30})',
                r'(?:как|на имя|зовут)\s+([А-ЯЁа-яёA-Za-z][А-ЯЁа-яёA-Za-z\s\-]{1,30})',
                r'имя[:\s]+([А-ЯЁа-яёA-Za-z][А-ЯЁа-яёA-Za-z\s\-]{1,30})',
            ]

            raw_name = user_input.strip()
            name = raw_name
            for pattern in name_patterns:
                m = re.search(pattern, user_input, re.IGNORECASE)
                if m:
                    name = m.group(1).strip()
                    break

            if name.lower() in _NON_NAME_WORDS or len(name) < 2:
                return "Пожалуйста, напишите ваше имя для записи:"

            multi_count = ctx.get("multi_booking_count", 1)
            multi_staff_ids = ctx.get("multi_booking_staff_ids", [])
            logger.info(f"   Auto-creating {multi_count} appointment(s) for: {name}")

            results = []
            master_names = []

            for i in range(multi_count):
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

            def _reset_ctx():
                self._set_booking_context(full_session_id,
                    staff_id=None, service_id=None, seance_length=None,
                    datetime=None, waiting_for_name=False, preferred_time=None,
                    requested_hour=None, requested_minute=None, date=None,
                    multi_booking_count=1, bookings_created=0, multi_booking_staff_ids=[])

            if success_count == multi_count:
                _reset_ctx()
                master_name = results[0].get("data", {}).get("staff", {}).get("name", "мастер")
                time_raw = results[0].get("data", {}).get("date", "")
                time_formatted = format_datetime_human(time_raw) if time_raw else ""
                if multi_count > 1:
                    return f"Записал {multi_count} человека! {master_name} ждёт вас {time_formatted}. До встречи!"
                return f"Записал вас! {master_name} ждёт вас {time_formatted}. До встречи!"
            elif success_count > 0:
                _reset_ctx()
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
        # Сначала проверяем точный формат HH:MM (всегда надёжен)
        requested_time = self._detect_requested_time(user_input)
        requested_hour = None
        requested_minute = None
        if requested_time is not None:
            requested_hour, requested_minute = requested_time
            self._set_booking_context(full_session_id, requested_hour=requested_hour, requested_minute=requested_minute)
            logger.info(f"   Detected exact time: {requested_hour:02d}:{requested_minute:02d}")
        elif not detected_multi:
            # Слово-based детекция времени пропускаем если мульти-запись обнаружена в этом же сообщении.
            # Причина: "на два ребёнка" → "на два" ложно трактуется как 14:00.
            requested_hour = self._detect_requested_hour(user_input)
            if requested_hour is not None:
                self._set_booking_context(full_session_id, requested_hour=requested_hour, requested_minute=None)
                logger.info(f"   Detected hour: {requested_hour}")

        # АВТО-ЗАПИСЬ: мастер выбран + клиент указал время + дата известна → сразу спрашиваем имя
        if ctx.get("staff_id") and ctx.get("service_id") and ctx.get("date") and requested_hour is not None:
            date_str = ctx["date"].split("T")[0] if "T" in ctx["date"] else ctx["date"]
            minute = requested_minute if requested_minute is not None else 0
            datetime_str = f"{date_str}T{str(requested_hour).zfill(2)}:{str(minute).zfill(2)}:00"
            self._set_booking_context(full_session_id, datetime=datetime_str, waiting_for_name=True)
            logger.info(f"   ✅ Auto-set datetime={datetime_str}, asking for name")
            hour_str = f"{requested_hour:02d}:{minute:02d}"
            return f"Отлично, записываем на {hour_str}! Как вас записать?"

        # Мастер выбран + время указано, но ДАТА неизвестна → спросить дату (без AI)
        if ctx.get("staff_id") and ctx.get("service_id") and requested_hour is not None and not ctx.get("date"):
            hour_str = f"{requested_hour:02d}:{requested_minute:02d}" if requested_minute is not None else f"{requested_hour}:00"
            logger.info(f"   Client specified time {hour_str}, but no date in context — asking for date")
            return f"На какую дату записываем в {hour_str}? Сегодня или на другой день?"

        # Build user message with context
        user_message = f"User Input: {user_input}"
        if user_phone:
            user_message += f"\nUser Phone: {user_phone}"
        
        ctx = self._get_booking_context(full_session_id)
        context_hints = []
        
        # Если в контексте есть staff_id, service_id и date — клиент уже выбрал мастера!
        # Добавляем подсказку чтобы AI НЕ предлагал других мастеров
        if ctx.get("staff_id") and ctx.get("service_id") and ctx.get("date"):
            context_hints.append(
                f"Мастер и дата уже выбраны (date={ctx['date']}). "
                "Покажи свободные окошки если ещё не показал, затем запроси имя. "
                "НЕ вызывай get_available_masters. "
                "Если клиент хочет ДРУГОГО мастера — вызови get_services_by_staff_name для нового мастера."
            )
        elif ctx.get("staff_id") and ctx.get("service_id"):
            # Мастер выбран, но дата ещё не известна
            context_hints.append(
                "Мастер уже выбран (staff_id сохранён). "
                "ЗАПРЕЩЕНО вызывать get_available_masters — мастер уже есть! "
                "Спроси у клиента ДАТУ записи, затем вызови get_available_times для этого мастера."
            )
        elif ctx.get("waiting_for_name") and ctx.get("datetime"):
            context_hints.append(f"Клиент ждет подтверждения записи на {format_datetime_human(ctx['datetime'])}. Спросите, как его записать.")
        
        if ctx.get("preferred_time"):
            hints = {"lunch": "Клиент хочет на обед (12:00-14:00)!", "morning": "Клиент хочет утром (09:00-12:00)!", "evening": "Клиент хочет вечером (17:00-20:00)!"}
            context_hints.append(hints.get(ctx['preferred_time'], ''))
        
        # Хинт о времени только если время было указано В ЭТОМ же сообщении (не стейл из контекста)
        if requested_hour is not None:
            min_part = f":{requested_minute:02d}" if requested_minute is not None else ":00"
            time_str = f"{requested_hour:02d}{min_part}"
            if ctx.get("staff_id") and ctx.get("service_id"):
                context_hints.append(
                    f"Клиент указал время {time_str}, мастер УЖЕ выбран. "
                    "Спроси на КАКУЮ ДАТУ записать. НЕ вызывай get_available_masters! "
                    "Когда клиент скажет дату — вызови get_available_times."
                )
            else:
                context_hints.append(
                    f"Клиент указал время {time_str}. "
                    "Если дата тоже известна — вызови get_available_masters(datetime). "
                    "Если дата не известна — уточни дату у клиента."
                )
        
        if context_hints:
            user_message += f"\n\nПРИМЕЧАНИЕ: {' '.join(context_hints)}"
        
        messages.append({"role": "user", "content": user_message})
        
        # Call OpenAI
        response = self.client.chat.completions.create(
            model=self.model, messages=messages, tools=TOOLS, tool_choice="auto", max_tokens=600
        )
        assistant_message = response.choices[0].message

        # Handle tool calls (loop until no more tool calls)
        while assistant_message.tool_calls:
            messages.append(assistant_message)
            for tool_call in assistant_message.tool_calls:
                args = json.loads(tool_call.function.arguments)
                result = await self._execute_tool(tool_call.function.name, args, full_session_id)
                messages.append({"role": "tool", "tool_call_id": tool_call.id, "content": json.dumps(result, ensure_ascii=False, default=str)})
            response = self.client.chat.completions.create(
                model=self.model, messages=messages, tools=TOOLS, tool_choice="auto", max_tokens=600
            )
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