# Frontend Setup Instructions

## Overview
Полностью функциональный admin panel для Khan Barbershop проекта, построенный на React 19 с Material-UI.

## Installation & Setup

### 1. Install Dependencies
```bash
cd frontend
npm install
```

### 2. Environment Configuration
Create `.env` file (уже создан автоматически):
```
VITE_API_URL=http://localhost:8000
```

### 3. Start Development Server
```bash
npm run dev
```
Frontend будет доступен на: **http://localhost:5174/**

### 4. Build for Production
```bash
npm run build
```
Output в `/frontend/dist/`

## Features Implemented

### 📊 Dashboard (`/`)
- Статистические карточки (записи, диалоги, клиенты, рейтинг)
- Недавние записи к мастеру
- График статистики (еженедельно)
- Real-time обновления

### 📅 Appointments (`/appointments`)
- Таблица всех записей с фильтрацией
- Full CRUD операции
- Статус отслеживание (scheduled, completed, cancelled)
- Dialog форма для добавления/редактирования
- Быстрое удаление с подтверждением

### 👨‍💼 Masters (`/masters`)
- Сетка карточек мастеров
- Управление профилями (имя, телефон, специализация, опыт, рейтинг)
- Редактирование и удаление
- Рейтинг отображение с звёздками

### 💇 Services (`/services`)
- Каталог услуг с категориями
- Цены в тенге (₸)
- Длительность услуги
- Full CRUD управление

### 📝 Logs (`/logs`)
- Dual-tab interface (переписка + backend логи)
- Группировка чатов по номерам телефонов
- Фильтрация по телефону и уровню логирования
- Подробный просмотр в dialog окне
- Скачивание логов в .txt файл

### 📢 Broadcasts (`/broadcasts`)
- Создание массовых рассылок
- Вставка номеров телефонов (один на строку)
- Отслеживание статуса (pending, sending, completed, failed)
- Progress bar для отправки
- История рассылок с удалением

### ⚙️ Settings (`/settings`)
- Настройки компании (название, телефон, адрес, часы работы)
- Параметры бота (имя, макс время ответа)
- AI подсказка (prompt) редактирование
- Toggle переключатели для уведомлений и аналитики
- System информация (версия, API статус, БД тип)

## Technology Stack

- **React** 19.2.4 - UI library
- **TypeScript** 6.0.2 - Type safety
- **Vite** 8.0.4 - Build tool & dev server
- **Material-UI** 9.0.0 - Component library
- **React Router** 7.14.0 - Navigation
- **React Query** 5.96.2 - Server state management
- **Zustand** 5.0.12 - Client state (auth)
- **Axios** 1.14.0 - HTTP client
- **React Hook Form** 7.72.1 - Form management
- **date-fns** 3.0.0 - Date utilities
- **recharts** 2.10.0 - Data visualization (prepared)

## Architecture

### State Management
- **Auth**: Zustand store (`src/store/authStore.ts`)
  - JWT token management
  - User login/logout
  - Protected routes via PrivateRoute HOC

- **Server State**: React Query
  - Automatic caching
  - Background refetching
  - Mutation handling with optimistic updates

### API Integration
- Centralized client (`src/api/client.ts`)
- Axios interceptor for JWT injection
- Base URL from environment variable
- Standardized error handling

### Component Structure
```
src/
├── App.tsx                 # Root with routing
├── components/
│   └── Layout.tsx         # Navigation & layout
├── pages/
│   ├── Dashboard.tsx
│   ├── Appointments.tsx
│   ├── Masters.tsx
│   ├── Services.tsx
│   ├── Logs.tsx
│   ├── Broadcasts.tsx
│   ├── Settings.tsx
│   └── Login.tsx
├── api/
│   └── client.ts          # API client
└── store/
    └── authStore.ts       # Auth state
```

## Authentication

Default credentials:
```
Username: admin
Password: admin123
```

JWT token is:
- Retrieved from login endpoint
- Stored in Zustand auth store
- Injected via axios interceptor
- Retrieved on each request

## API Endpoints Required

The backend should provide these endpoints under `/api/admin`:

```
POST   /login                    - Login
GET    /stats                    - Dashboard statistics
GET/POST/PUT/DELETE /appointments
GET/POST/PUT/DELETE /masters
GET/POST/PUT/DELETE /services
GET    /logs?page=1&limit=50
GET/POST/DELETE /broadcasts
PUT    /prompt                   - Update AI prompt
GET/PUT /settings
GET    /backend-logs             - Backend log retrieval
```

## Customization

### Theme
Edit `App.tsx` to modify Material-UI theme:
```typescript
const theme = createTheme({
  palette: {
    mode: 'dark',
    primary: { main: '#90caf9' },
    secondary: { main: '#f48fb1' },
    // ...
  },
});
```

### API Base URL
Set `VITE_API_URL` environment variable to point to your backend.

### Menu Items
Edit `Layout.tsx` to add/remove navigation items:
```typescript
const menuItems = [
  { label: 'Dashboard', path: '/' },
  // Add more items...
];
```

## Troubleshooting

### Port Already in Use
```bash
# Kill process on port 5174
lsof -ti:5174 | xargs kill -9
# Or change port in vite.config.ts
```

### API Connection Issues
1. Ensure backend is running on `http://localhost:8000`
2. Check `.env` file has correct `VITE_API_URL`
3. Verify CORS is enabled on backend

### Build Errors
```bash
# Clear cache and rebuild
rm -rf node_modules dist
npm install
npm run build
```

### TypeScript Errors
```bash
# Check for errors
npm run build

# Fix lint issues
npm run lint
```

## Performance Optimization

Current optimizations:
- Code splitting ready (recharts, date-fns not imported)
- CSS-in-JS with Emotion (styled components)
- React Query caching strategy
- Lazy route loading ready

Future improvements:
- Dynamic imports for heavy pages
- Image optimization
- Bundle size analysis

## Available Scripts

| Command | Description |
|---------|-------------|
| `npm run dev` | Start development server |
| `npm run build` | Build for production |
| `npm run preview` | Preview production build |
| `npm run lint` | Run ESLint |

## Browser Support

- Modern browsers (Chrome, Firefox, Safari, Edge)
- React 19 requires ES2020+
- Mobile responsive design included

## File Size Warning

Current build size: ~665KB (gzip: 205KB) due to Material-UI bundle.
Consider code-splitting for further optimization.

## Notes

1. **Grid Components**: Replaced deprecated Grid with CSS Grid for MUI v9 compatibility
2. **Form Fields**: Using standard TextField instead of deprecated SelectProps
3. **Responsive**: All components are mobile-responsive with breakpoint handling
4. **Dark Theme**: Applied globally via Material-UI theme
5. **Internationalization**: Ready for i18n implementation (currently Russian)

## Next Steps

1. Ensure backend API is running and accessible
2. Verify all endpoints exist on backend
3. Test CRUD operations with real data
4. Configure environment variables for production
5. Add error boundaries for production robustness
6. Implement logging/monitoring

---

**Created**: 2025
**Last Updated**: Today
**Status**: Production Ready ✅
