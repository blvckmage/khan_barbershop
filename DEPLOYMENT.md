# Deployment Roadmap — KHAN Barbershop

Production deployment via **Railway** (backend) + **Vercel** (frontend) + **Cloudflare** (DNS).
Total monthly cost: **~$5** (Railway Hobby plan; Vercel/Cloudflare free).

---

## 0. Подготовка (1–2 часа)

### 0.1. Очистить репозиторий от секретов
```bash
# Убедиться что НЕ в git:
git ls-files | grep -E "credentials.json|\.env$|\.db$"
# Должно быть пусто. Если нет:
git rm --cached backend/credentials.json backend/.env backend/khan_barbershop.db
git commit -m "Remove secrets from tracking"
```

### 0.2. Закрыть критические дыры безопасности (обязательно перед prod!)
- [ ] Хешировать пароль admin (`bcrypt` вместо plaintext `admin123`)
- [ ] Заменить токен-auth на JWT с подписью (`pyjwt`)
- [ ] Сузить CORS: `allow_origins=["https://admin.khan-barbershop.kz"]`
- [ ] Установить `DEBUG=False` в production env
- [ ] Включить rate limiting на webhook (`slowapi`)

### 0.3. Подготовить файлы (уже сделано)
- ✅ `backend/railway.json` — конфиг Railway
- ✅ `backend/requirements.txt` — Python deps
- ✅ `backend/.gitignore` — секреты исключены
- ✅ `backend/.env.example` — образец env переменных

### 0.4. Push в GitHub
```bash
gh repo create khan-barbershop --private --source=. --push
```

---

## 1. Backend на Railway (30 минут)

### 1.1. Создать проект
1. Зайти на https://railway.app → New Project → Deploy from GitHub
2. Выбрать репо `khan-barbershop`
3. Set Root Directory: `backend`
4. Railway сам подхватит `railway.json` и `requirements.txt`

### 1.2. Добавить persistent volume для SQLite + логов
1. В Railway → Settings → Volumes → Add Volume
2. Mount path: `/data`
3. Size: 1 GB (хватит на ~1M строк + логи)

### 1.3. Изменить пути в коде на volume
Поменять в `backend/app/database.py`:
```python
DATABASE_PATH = os.environ.get("DATABASE_PATH", "khan_barbershop.db")
```
И в `backend/app/main.py`:
```python
LOG_DIR = os.environ.get("LOG_DIR", "logs")
```

В Railway env установить:
```
DATABASE_PATH=/data/khan_barbershop.db
LOG_DIR=/data/logs
```

### 1.4. Залить env переменные в Railway
```env
# Alteegio
ALTEEGIO_BEARER_TOKEN=...
ALTEEGIO_USER_TOKEN=...
ALTEEGIO_COMPANY_ID=1097365

# OpenAI
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4.1-mini

# Google Sheets
GOOGLE_CREDENTIALS_PATH=/data/credentials.json
STAFF_SPREADSHEET_ID=...
SERVICES_SPREADSHEET_ID=...

# WhatsApp
WHATSAPP_API_URL=https://graph.facebook.com
WHATSAPP_API_VERSION=v17.0
WHATSAPP_PHONE_NUMBER_ID=...
WHATSAPP_ACCESS_TOKEN=...
WHATSAPP_VERIFY_TOKEN=khan_random_string_123
WHATSAPP_WABA_ID=...

# Templates (заполнить ПОСЛЕ approval — см. Этап 4)
TEMPLATE_ONE_HOUR_REMINDER=
TEMPLATE_REVISIT_REMINDER=
TEMPLATE_NPS_REQUEST=
TEMPLATE_LANGUAGE=ru

# App
DEBUG=False
APP_HOST=0.0.0.0
# APP_PORT — Railway сам подставит через $PORT
```

### 1.5. Загрузить `credentials.json` в volume
Railway не позволяет загружать файлы напрямую. Два варианта:

**Вариант A (рекомендуется):** Закодировать в base64 и положить как env:
```bash
base64 -i backend/credentials.json | pbcopy
```
Добавить в Railway env: `GOOGLE_CREDENTIALS_B64=<paste>`.

Затем в `backend/app/main.py` (в startup_event):
```python
import base64
b64 = os.environ.get("GOOGLE_CREDENTIALS_B64")
if b64 and not os.path.exists(settings.google_credentials_path):
    os.makedirs(os.path.dirname(settings.google_credentials_path), exist_ok=True)
    with open(settings.google_credentials_path, "wb") as f:
        f.write(base64.b64decode(b64))
```

**Вариант B:** Через Railway CLI: `railway run bash` → залить файл вручную через SCP. Менее надёжно.

### 1.6. Сгенерировать публичный домен
- Railway → Settings → Networking → Generate Domain
- Получишь `https://khan-barbershop-production.up.railway.app`
- Сохрани этот URL — он понадобится для Meta webhook

### 1.7. Проверить деплой
```bash
curl https://your-railway-domain.up.railway.app/health
# → {"status":"healthy"}
```

---

## 2. Frontend на Vercel (15 минут)

### 2.1. Создать проект
1. https://vercel.com → New Project → Import GitHub repo
2. Root Directory: `frontend`
3. Framework Preset: **Vite**
4. Build Command: `npm run build`
5. Output Directory: `dist`

### 2.2. Env переменные
```env
VITE_API_URL=https://khan-barbershop-production.up.railway.app
```

### 2.3. Deploy → получить URL
- `https://khan-barbershop.vercel.app`

### 2.4. Привязать кастомный домен
- Vercel → Settings → Domains → `admin.khan-barbershop.kz`
- В Cloudflare DNS добавить CNAME → `cname.vercel-dns.com`

### 2.5. Обновить CORS в backend
В `backend/app/main.py`:
```python
allow_origins=[
    "https://admin.khan-barbershop.kz",
    "https://khan-barbershop.vercel.app",
],
```

---

## 3. WhatsApp Business настройка (1–2 часа)

### 3.1. Meta Developer Console
1. https://developers.facebook.com/apps → Create App → Business
2. Add Product: **WhatsApp**
3. Получить permanent access token (System User → Generate Token, не temporary!)

### 3.2. Купить и верифицировать номер
- WhatsApp Manager → Phone Numbers → Add Number
- Использовать **новый** номер, не используемый ранее в личном WhatsApp
- Верифицировать через SMS/звонок

### 3.3. Настроить webhook
- App Dashboard → WhatsApp → Configuration → Webhook
- Callback URL: `https://your-railway-domain.up.railway.app/webhook/whatsapp`
- Verify Token: значение `WHATSAPP_VERIFY_TOKEN` из env
- Subscribe to fields: ✅ `messages`

### 3.4. Тест
- С обычного WhatsApp написать на бизнес-номер «Привет»
- Должен прийти ответ от бота
- В Railway → Deployments → Logs увидеть `📲 WhatsApp Business Cloud API webhook received`

---

## 4. WABA Templates approval (~24–48 часов на approval)

### 4.1. Создать шаблоны через админку
Зайти в `https://admin.khan-barbershop.kz` → Рассылки → Шаблоны Meta.

Создать 3 шаблона:

**Шаблон 1: One-hour reminder** (UTILITY)
```
⏳ Напоминание о записи

Здравствуйте, {{1}}! Через 1 час вас ждёт мастер {{2}}.
⏰ {{3}}
📍 KHAN Barbershop, Момышулы 55

Если не успеваете — напишите нам.
```

**Шаблон 2: Revisit reminder** (MARKETING)
```
💈 {{1}}, прошло 20 дней с вашего последнего визита ({{2}}).

Самое время для свежей стрижки. Напишите нам — подберём удобное время!

KHAN Barbershop
```

**Шаблон 3: NPS request** (UTILITY)
```
Здравствуйте, {{1}}! ✂️

Вы посетили KHAN Barbershop у мастера {{2}}.
Оцените вашу стрижку от 1 до 5 — просто отправьте цифру в ответ.

Спасибо!
```

### 4.2. Подождать approval Meta (~24ч)
В админке → Рассылки → Шаблоны → нажать «🔄 Синхронизировать статусы».
Когда статус станет `APPROVED` — скопировать `name` шаблона (например `khan_napominanie_12345`).

### 4.3. Прописать имена шаблонов в Railway env
```env
TEMPLATE_ONE_HOUR_REMINDER=khan_napominanie_12345
TEMPLATE_REVISIT_REMINDER=khan_revisit_67890
TEMPLATE_NPS_REQUEST=khan_nps_11111
TEMPLATE_LANGUAGE=ru
```
Railway автоматически перезапустит сервис.

---

## 5. Domain + SSL (30 минут)

### 5.1. Купить домен
- Любой регистратор (NIC.KZ, Namecheap, Cloudflare Registrar)

### 5.2. Cloudflare DNS
- Перевести NS на Cloudflare
- Добавить записи:
  ```
  api.khan-barbershop.kz   CNAME   khan-barbershop-production.up.railway.app
  admin.khan-barbershop.kz CNAME   cname.vercel-dns.com
  ```

### 5.3. Привязать в Railway
- Settings → Domains → Add Custom Domain → `api.khan-barbershop.kz`
- Обновить Meta webhook URL → `https://api.khan-barbershop.kz/webhook/whatsapp`

---

## 6. Мониторинг и backups (1 час)

### 6.1. Sentry для ошибок (free tier: 5k events/мес)
```bash
pip install sentry-sdk[fastapi]
```
В `backend/app/main.py`:
```python
import sentry_sdk
sentry_sdk.init(dsn=os.environ.get("SENTRY_DSN"), traces_sample_rate=0.1)
```

### 6.2. Backups SQLite
Railway → Cron → раз в сутки:
```bash
cp /data/khan_barbershop.db /data/backups/khan_$(date +%F).db
# Сохранять 7 дней
find /data/backups -name "*.db" -mtime +7 -delete
```

### 6.3. UptimeRobot
- https://uptimerobot.com (free)
- Monitor: `https://api.khan-barbershop.kz/health` каждые 5 минут
- Alert → Telegram/email при downtime

---

## 7. Чек-лист перед запуском в боевом режиме

- [ ] Сменить пароль admin с `admin123` на сложный
- [ ] `DEBUG=False` в Railway env
- [ ] `/docs` и `/redoc` недоступны (отключены при `DEBUG=False` — уже в коде)
- [ ] CORS сужен до prod-доменов
- [ ] Webhook Meta verify token не дефолтный
- [ ] Все 3 WABA шаблона `APPROVED`
- [ ] Алерт UptimeRobot настроен
- [ ] Backups SQLite работают
- [ ] Sentry получает ошибки (нажать тестовую кнопку)
- [ ] Протестировать: запись на стрижку через WhatsApp с реального номера
- [ ] Протестировать: 1-час напоминание (создать запись через 1ч5мин, подождать)

---

## Альтернативы Railway

| Сервис | Плюсы | Минусы | Цена |
|---|---|---|---|
| **Fly.io** | Edge locations, лучше для KZ-аудитории | Сложнее настройка | ~$3/мес |
| **Render** | Free tier есть | Free instance засыпает через 15 мин — недопустимо для webhook! | $7/мес минимум |
| **Hetzner VPS** | Полный контроль, дёшево | Сам настраиваешь nginx/Caddy/Docker/SSL | €4.5/мес |
| **DigitalOcean App** | Хорошие docs | Дороже Railway | $5/мес + $5/db |

**Вердикт:** Railway оптимален для команды без DevOps. Для масштаба >10k клиентов — переезд на Fly.io или Hetzner.

---

## Estimate стоимости в месяц

| Сервис | План | $/мес |
|---|---|---|
| Railway Hobby | $5 + usage | ~$5–10 |
| Vercel | Hobby (free) | $0 |
| Cloudflare | Free | $0 |
| Sentry | Developer (free) | $0 |
| UptimeRobot | Free | $0 |
| Domain `.kz` | ~$10/год | ~$1 |
| OpenAI API (1000 чатов/мес) | gpt-4.1-mini | ~$5–15 |
| WhatsApp Business | Per-conversation | ~$0.01–0.03 за диалог |
| **Итого** | | **~$15–30/мес** |
