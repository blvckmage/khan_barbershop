# Khan Barbershop Backend

Backend API для чат-бота барбершопа «KHAN» с интеграцией Alteegio и OpenAI.

## Функциональность

- 🤖 AI-ассистент для консультаций и записи клиентов
- 📅 Интеграция с Alteegio API для управления записями
- 📊 Google Sheets для хранения данных о мастерах и услугах
- 💬 Webhook для интеграции с ManyChat (WhatsApp)
- 📱 Twilio WhatsApp/SMS для уведомлений клиентов

## Структура проекта

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI приложение
│   ├── config.py            # Конфигурация (env переменные)
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py       # Pydantic модели
│   ├── routers/
│   │   ├── __init__.py
│   │   └── webhook.py       # Webhook endpoints
│   └── services/
│       ├── __init__.py
│       ├── alteegio_service.py   # Alteegio API клиент
│       ├── sheets_service.py     # Google Sheets клиент
│       ├── ai_agent_service.py   # OpenAI AI Agent
│       └── twilio_service.py     # Twilio WhatsApp/SMS
├── requirements.txt
├── .env.example
└── README.md
```

## Установка

### 1. Клонирование и настройка

```bash
cd backend

# Создать виртуальное окружение
python -m venv venv

# Активировать
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate     # Windows

# Установить зависимости
pip install -r requirements.txt
```

### 2. Настройка переменных окружения

```bash
# Скопировать пример и заполнить
cp .env.example .env
```

Отредактируйте `.env`:

```env
# Alteegio API
ALTEEGIO_BEARER_TOKEN=your_bearer_token
ALTEEGIO_USER_TOKEN=your_user_token
ALTEEGIO_COMPANY_ID=1097365

# OpenAI
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4.1-mini

# Google Sheets
GOOGLE_CREDENTIALS_PATH=./credentials.json
STAFF_SPREADSHEET_ID=your_staff_spreadsheet_id
SERVICES_SPREADSHEET_ID=your_services_spreadsheet_id
```

### 3. Google Credentials

1. Создайте проект в [Google Cloud Console](https://console.cloud.google.com/)
2. Включите Google Sheets API
3. Создайте Service Account и скачайте `credentials.json`
4. Положите файл в папку `backend/`
5. Предоставьте доступ к таблицам для email из Service Account

### 4. Запуск

```bash
# Разработка
python -m app.main

# Или через uvicorn
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## API Endpoints

### Webhook для ManyChat

```
POST /webhook/wa_khan_main_chatbot
```

Request body:
```json
{
  "user_input": "Хочу записаться на стрижку",
  "user_phone": "77071234567"
}
```

Response:
```json
{
  "output": "Привет! Я чат-бот барбершопа KHAN. К кому вы хотите записаться?"
}
```

### Тестовый чат

```
POST /webhook/chat
```

Request body:
```json
{
  "message": "Какие услуги у вас есть?",
  "session_id": "test_session",
  "user_phone": "77071234567"
}
```

### Health Check

```
GET /health
GET /
```

## Интеграция с ManyChat

1. В ManyChat создайте External Request
2. URL: `https://your-domain.com/webhook/wa_khan_main_chatbot`
3. Method: POST
4. Body:
```json
{
  "user_input": "{{input_text}}",
  "user_phone": "{{wa_id}}"
}
```

## Интеграция с Twilio WhatsApp

### Настройка Twilio

1. Создайте аккаунт на [Twilio](https://www.twilio.com/)
2. В консоли Twilio перейдите в Messaging > Try it out > Send a WhatsApp message
3. Следуйте инструкциям для активации WhatsApp Sandbox (или настройте WhatsApp Business API)
4. Скопируйте Account SID и Auth Token из Dashboard
5. Добавьте переменные в `.env`:

```env
# Twilio
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_PHONE_NUMBER=whatsapp:+14155238886
```

### Webhook для входящих сообщений

В Twilio Console настройте webhook:
1. Перейдите в Phone Numbers > Manage > Active numbers
2. Выберите номер или Sandbox
3. В поле "A message comes in" укажите:
   - URL: `https://your-domain.com/webhook/twilio/whatsapp`
   - Method: POST

### Отправка уведомлений

```
POST /webhook/send-notification
```

Request body (подтверждение записи):
```json
{
  "phone": "+77071234567",
  "type": "confirmation",
  "client_name": "Аслан",
  "master_name": "Ерлан",
  "service_name": "Мужская стрижка",
  "datetime": "2025-03-01 15:00",
  "price": "5000"
}
```

Request body (напоминание):
```json
{
  "phone": "+77071234567",
  "type": "reminder",
  "client_name": "Аслан",
  "master_name": "Ерлан",
  "datetime": "2025-03-01 15:00"
}
```

### Twilio API Endpoints

| Endpoint | Описание |
|----------|----------|
| `POST /webhook/twilio/whatsapp` | Webhook для входящих WhatsApp сообщений |
| `POST /webhook/twilio/sms` | Webhook для входящих SMS |
| `POST /webhook/send-notification` | Отправка уведомления клиенту |

## Деплой

### Render.com

1. Создайте аккаунт на [render.com](https://render.com)
2. Подключите GitHub репозиторий
3. Создайте Web Service:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. Добавьте Environment Variables

### Railway.app

1. `npm install -g railway`
2. `railway login`
3. `railway init`
4. `railway up`

## Инструменты AI Agent

AI Agent имеет доступ к следующим инструментам:

| Инструмент | Описание |
|------------|----------|
| `get_all_staff` | Получить список всех мастеров |
| `get_all_services` | Получить все услуги с ценами |
| `get_services_by_staff_name` | Услуги конкретного мастера |
| `get_available_dates` | Доступные даты для записи |
| `get_available_times` | Свободные окошки на день |
| `get_available_masters` | Доступные мастера на время |
| `create_appointment` | Создать запись |

## Лицензия

MIT