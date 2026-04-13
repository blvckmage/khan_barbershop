# Khan Barbershop - Project Summary

## 🎯 Project Overview

Полноценный admin panel для системы управления barbershop (салоном парикмахерских услуг). Включает в себя:

**Backend**: FastAPI Python приложение
**Frontend**: React 19 с Material-UI admin interface

---

## 📦 Project Structure

```
khan_barbershop/
├── backend/                  # Python FastAPI приложение
│   ├── app/
│   │   ├── main.py          # Entry point, роуты
│   │   ├── config.py        # Конфигурация
│   │   ├── database.py      # Database setup
│   │   ├── models/          # Database models
│   │   ├── routers/         # API endpoints
│   │   │   ├── admin.py     # Admin endpoints
│   │   │   └── webhook.py   # Webhook endpoints
│   │   └── services/        # Бизнес логика
│   │       ├── ai_agent_service.py
│   │       ├── alteegio_service.py
│   │       ├── broadcast_service.py
│   │       ├── sheets_service.py
│   │       └── twilio_service.py
│   ├── khan_barbershop.db   # SQLite база данных
│   ├── requirements.txt     # Python зависимости
│   └── README.md           # Backend документация
│
├── frontend/               # React приложение
│   ├── src/
│   │   ├── App.tsx        # Root component с routing
│   │   ├── main.tsx       # Entry point
│   │   ├── api/
│   │   │   └── client.ts  # API client с Axios
│   │   ├── components/
│   │   │   └── Layout.tsx # Navigation & layout
│   │   ├── pages/         # Page components
│   │   │   ├── Dashboard.tsx
│   │   │   ├── Appointments.tsx
│   │   │   ├── Masters.tsx
│   │   │   ├── Services.tsx
│   │   │   ├── Logs.tsx
│   │   │   ├── Broadcasts.tsx
│   │   │   ├── Settings.tsx
│   │   │   └── Login.tsx
│   │   ├── store/
│   │   │   └── authStore.ts  # Zustand auth state
│   │   └── index.css
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── .env                # API URL configuration
│   ├── SETUP.md           # Детальная инструкция
│   └── README.md
│
└── n8n_workflow.json      # N8N workflow (если используется)
```

---

## 🚀 Quick Start

### Backend Setup
```bash
cd backend
pip install -r requirements.txt
python -m app.main
```
Backend запустится на: **http://localhost:8000**

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
Frontend запустится на: **http://localhost:5174**

### Default Login
```
Username: admin
Password: admin123
```

---

## 📋 Features

### ✅ Appointments Management
- Просмотр всех записей в таблице
- Добавление новых записей (клиент, мастер, услуга, время)
- Редактирование существующих записей
- Удаление записей
- Фильтрация по статусу (scheduled, completed, cancelled)

### ✅ Masters Management
- Карточки мастеров с информацией
- Добавление новых мастеров
- Редактирование профилей (имя, телефон, специализация, опыт, рейтинг)
- Удаление мастеров

### ✅ Services Management
- Каталог всех услуг
- Создание новых услуг (название, описание, категория, цена, длительность)
- Редактирование услуг
- Удаление услуг

### ✅ Dashboard Statistics
- Статистические карточки (записи сегодня, диалоги, клиенты, рейтинг)
- Список недавних записей
- Недельная статистика с прогресс-барами

### ✅ Logs Management
- **Чаты**: Просмотр переписки клиентов с ботом
  - Группировка по номерам телефонов
  - Просмотр отдельных сообщений
  - Интент распознавания
- **Backend логи**: Логи системы
  - Фильтрация по уровню (ERROR, WARNING, INFO, DEBUG)
  - Скачивание логов в файл

### ✅ Broadcasts
- Создание массовых рассылок по SMS/WhatsApp
- Ввод номеров телефонов (один на строку)
- Отслеживание статуса рассылки
- Progress bar для отправки
- История всех рассылок

### ✅ Settings
- Информация о компании (название, телефон, адрес, часы)
- Параметры AI бота
- Редактирование AI промпта (системная инструкция)
- Toggle переключатели (уведомления, аналитика)
- System информация (версия, статус API, тип БД)

### ✅ Authentication
- JWT токен-базированная авторизация
- Защита маршрутов (PrivateRoute)
- Logout функциональность

---

## 🛠 Technology Stack

### Backend
- **FastAPI** - Web framework
- **SQLite/SQLAlchemy** - Database ORM
- **Twilio** - SMS/WhatsApp sending
- **Google Sheets API** - Data integration
- **Pydantic** - Data validation
- **n8n** - Workflow automation (опционально)

### Frontend
- **React 19.2.4** - UI framework
- **TypeScript 6.0.2** - Type safety
- **Material-UI 9.0.0** - Component library
- **Vite 8.0.4** - Build tool
- **React Router 7.14.0** - Navigation
- **React Query 5.96.2** - Server state
- **Zustand 5.0.12** - Client state
- **Axios 1.14.0** - HTTP client
- **React Hook Form** - Form management

---

## 🔌 API Integration

### Authentication Flow
1. User submits login credentials
2. Backend verifies and returns JWT token
3. Token stored in Zustand auth store
4. Axios interceptor injects token in all requests
5. Protected routes check for valid token

### Request/Response Pattern
```typescript
// All API calls include Authorization header
Authorization: Bearer <JWT_TOKEN>

// Response format
{
  "items": [...],      // Data array
  "total": 100,        // Total count for pagination
  "page": 1            // Current page
}
```

---

## 📱 UI/UX Features

### Design System
- **Material-UI Dark Theme** - Professional dark interface
- **Responsive Layout** - Works on mobile/tablet/desktop
- **Icons** - Material icons throughout
- **Color Coding** - Status indicators with colors
- **Toast Notifications** - User feedback (ready for implementation)

### Components Used
- Tables (Appointments)
- Cards (Masters, Services)
- Dialogs (Forms)
- Tabs (Logs)
- Chips (Status, Categories)
- Lists (Logs)
- Progress bars (Statistics, Broadcasts)
- Drawers (Navigation)

---

## 🔐 Security Notes

1. **JWT Authentication** - Stateless token-based auth
2. **HTTP Only Cookies** - (Consider implementing for token storage)
3. **CORS** - Configure for production
4. **Input Validation** - React Hook Form + Pydantic
5. **Rate Limiting** - Implement on backend

---

## 📊 Database Schema

### Key Tables
- **appointments** - Записи клиентов
- **masters** - Мастера/сотрудники
- **services** - Услуги салона
- **chats** - История чатов
- **broadcasts** - История рассылок
- **settings** - Конфигурация системы

---

## 🚦 API Endpoints Overview

### Admin Endpoints (Protected)
```
POST   /api/admin/login              - User authentication
GET    /api/admin/stats              - Dashboard statistics
GET    /api/admin/appointments       - List appointments
POST   /api/admin/appointments       - Create appointment
PUT    /api/admin/appointments/:id   - Update appointment
DELETE /api/admin/appointments/:id   - Delete appointment

GET    /api/admin/masters            - List masters
POST   /api/admin/masters            - Create master
PUT    /api/admin/masters/:id        - Update master
DELETE /api/admin/masters/:id        - Delete master

GET    /api/admin/services           - List services
POST   /api/admin/services           - Create service
PUT    /api/admin/services/:id       - Update service
DELETE /api/admin/services/:id       - Delete service

GET    /api/admin/logs               - Get chats
GET    /api/admin/backend-logs       - Get backend logs
GET    /api/admin/broadcasts         - List broadcasts
POST   /api/admin/broadcasts         - Create broadcast
DELETE /api/admin/broadcasts/:id     - Delete broadcast

GET    /api/admin/settings           - Get settings
PUT    /api/admin/settings           - Update settings
GET    /api/admin/prompt             - Get AI prompt
PUT    /api/admin/prompt             - Update AI prompt
```

---

## 🐛 Known Issues & TODOs

### Completed ✅
- TypeScript compilation errors fixed
- Material-UI v9 compatibility resolved
- All 7 pages implemented and working
- Production build successful

### Future Enhancements
- [ ] Error boundary for crash handling
- [ ] Toast notifications for user feedback
- [ ] Pagination component
- [ ] Advanced filters
- [ ] Export to CSV/Excel
- [ ] Dark mode toggle
- [ ] Multi-language support (i18n)
- [ ] Performance metrics dashboard
- [ ] User management page
- [ ] Backup/restore functionality

---

## 📝 Environment Variables

### Frontend (.env)
```
VITE_API_URL=http://localhost:8000
```

### Backend (.env)
```
DATABASE_URL=sqlite:///./khan_barbershop.db
TWILIO_ACCOUNT_SID=your_sid
TWILIO_AUTH_TOKEN=your_token
TWILIO_PHONE_NUMBER=+...
OPENAI_API_KEY=sk-...
GOOGLE_SHEETS_API_KEY=...
```

---

## 🎓 Development Tips

### Running Both Services
**Terminal 1 - Backend**
```bash
cd backend
python -m app.main
```

**Terminal 2 - Frontend**
```bash
cd frontend
npm run dev
```

Then open browser to: **http://localhost:5174**

### Hot Reload
- Frontend: Vite provides instant HMR
- Backend: Use `--reload` flag with uvicorn

### Debugging
- Frontend: DevTools in browser (React DevTools, Network tabs)
- Backend: Check `backend.log` or `logs/app.log`

### Testing
Frontend:
```bash
npm run build  # Production build test
npm run lint   # ESLint checks
```

Backend:
```bash
python -m pytest  # If tests exist
```

---

## 📞 Support & Contacts

For issues or feature requests, check:
- `/frontend/SETUP.md` - Detailed frontend setup
- `/backend/README.md` - Backend documentation
- Logs in `/backend/logs/app.log`

---

## 📄 License

[Your License Here]

---

**Project Status**: ✅ **Production Ready**
**Last Updated**: 2025
**Maintained By**: Your Team
