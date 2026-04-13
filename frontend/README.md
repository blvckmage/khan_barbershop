# Khan Barbershop - Frontend Admin Panel

Современная и удобная панель управления для барбершопа "KHAN" с поддержкой управления записями, мастерами, услугами и рассылками.

## ✨ Особенности

- 📊 **Интерактивная панель управления** с статистикой и аналитикой
- 📅 **Управление записями** - создание, редактирование и удаление записей
- 👥 **Управление мастерами** - профили мастеров с рейтингом и опытом
- 🎯 **Управление услугами** - каталог услуг с ценами и описаниями
- 💬 **Просмотр логов** - чаты клиентов и логи бэкенда
- 📢 **Рассылки сообщений** - массовые СМС/WhatsApp рассылки
- ⚙️ **Настройки** - полная конфигурация приложения
- 🌙 **Темная тема** - удобный интерфейс Material Design
- 📱 **Адаптивный дизайн** - работает на всех устройствах

## 🚀 Быстрый старт

### Установка зависимостей

```bash
cd frontend
npm install
```

### Запуск в режиме разработки

```bash
npm run dev
```

Приложение будет доступно по адресу `http://localhost:5173`

### Сборка для продакшена

```bash
npm run build
npm run preview
```

## 📋 Структура проекта

```
src/
├── pages/
│   ├── Dashboard.tsx          # Главная панель управления
│   ├── Appointments.tsx       # Управление записями
│   ├── Masters.tsx            # Управление мастерами
│   ├── Services.tsx           # Управление услугами
│   ├── Logs.tsx               # Просмотр логов
│   ├── Broadcasts.tsx         # Рассылки сообщений
│   ├── Settings.tsx           # Настройки
│   └── Login.tsx              # Страница входа
├── components/
│   └── Layout.tsx             # Макет приложения (навигация, шапка)
├── api/
│   └── client.ts              # API клиент и эндпоинты
├── store/
│   └── authStore.ts           # Zustand хранилище для аутентификации
├── App.tsx                    # Основной компонент приложения
└── main.tsx                   # Точка входа
```

## 🔑 Ключевые компоненты

### Dashboard
Главная страница с:
- Карточками статистики (записи, чаты, клиенты, рейтинг)
- Списком последних записей
- Списком последних диалогов
- Недельной статистикой

### Управление записями (Appointments)
- Таблица со всеми записями
- Создание новой записи через форму
- Редактирование и удаление записей
- Фильтрация по статусу

### Управление мастерами (Masters)
- Карточки мастеров с информацией
- Фото, специализация, опыт и рейтинг
- Быстрое добавление и редактирование

### Управление услугами (Services)
- Каталог услуг с фото и описанием
- Категоризация услуг
- Цены и длительность

### Логи (Logs)
- Просмотр чатов клиентов в разрезе по номерам
- Просмотр логов бэкенда с фильтрацией по уровню
- Скачивание логов в текстовый файл
- Поиск по номерам телефонов

### Рассылки (Broadcasts)
- Создание массовых сообщений
- Ввод списка номеров телефонов
- История рассылок с статусом отправки
- Отслеживание статуса (отправлено/ошибка)

### Настройки (Settings)
- Информация о компании (название, телефон, адрес)
- Настройки бота (имя, время ответа)
- Системный prompt для AI
- Включение/отключение функций

## 🛠 Использованные технологии

- **React 19** - фреймворк для построения UI
- **TypeScript** - статическая типизация
- **Vite** - быстрая сборка
- **Material-UI (MUI)** - компоненты и стили
- **React Router** - маршрутизация
- **Zustand** - управление состоянием
- **React Query** - управление данными и синхронизация
- **Axios** - HTTP клиент
- **React Hook Form** - управление формами

## 🔐 Аутентификация

Приложение использует JWT токены для аутентификации:

1. На странице Login вводятся учетные данные
2. API возвращает токен
3. Токен сохраняется в Zustand хранилище
4. Токен автоматически добавляется во все запросы
5. PrivateRoute компонент защищает приватные маршруты

Учетные данные по умолчанию:
- **Логин**: admin
- **Пароль**: admin123

## 📡 API интеграция

Все запросы идут на бэкенд API по адресу `http://localhost:8000/api/admin`

Основные эндпоинты:
- `POST /login` - вход
- `GET /stats` - статистика
- `GET/POST/PUT/DELETE /appointments` - управление записями
- `GET/POST/PUT/DELETE /masters` - управление мастерами
- `GET/POST/PUT/DELETE /services` - управление услугами
- `GET /logs` - логи
- `GET/POST /broadcasts` - рассылки
- `GET/PUT /settings` - настройки
- `GET/PUT /prompt` - AI prompt

## 🎨 Кастомизация

### Изменение цветов

Отредактируйте `src/App.tsx`:

```tsx
const darkTheme = createTheme({
  palette: {
    primary: { main: '#90caf9' },  // Основной цвет
    secondary: { main: '#f48fb1' }, // Вторичный цвет
  },
});
```

### Добавление новой страницы

1. Создайте файл `src/pages/NewPage.tsx`
2. Добавьте маршрут в `src/App.tsx`
3. Добавьте пункт в меню в `src/components/Layout.tsx`

## 🚨 Решение проблем

### Ошибка: "Cannot find module"
- Убедитесь, что все зависимости установлены: `npm install`
- Очистите кеш: `rm -rf node_modules package-lock.json && npm install`

### API не доступен
- Проверьте, что бэкенд запущен на `http://localhost:8000`
- Проверьте CORS настройки в бэкенде

### Логирование не работает
- Убедитесь, что бэкенд эндпоинт `/api/admin/logs` существует
- Проверьте права доступа

## 📚 Документация

Для подробной информации о бэкенде см. `/backend/README.md`

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) uses [Oxc](https://oxc.rs)
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) uses [SWC](https://swc.rs/)

## React Compiler

The React Compiler is not enabled on this template because of its impact on dev & build performances. To add it, see [this documentation](https://react.dev/learn/react-compiler/installation).

## Expanding the ESLint configuration

If you are developing a production application, we recommend updating the configuration to enable type-aware lint rules:

```js
export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      // Other configs...

      // Remove tseslint.configs.recommended and replace with this
      tseslint.configs.recommendedTypeChecked,
      // Alternatively, use this for stricter rules
      tseslint.configs.strictTypeChecked,
      // Optionally, add this for stylistic rules
      tseslint.configs.stylisticTypeChecked,

      // Other configs...
    ],
    languageOptions: {
      parserOptions: {
        project: ['./tsconfig.node.json', './tsconfig.app.json'],
        tsconfigRootDir: import.meta.dirname,
      },
      // other options...
    },
  },
])
```

You can also install [eslint-plugin-react-x](https://github.com/Rel1cx/eslint-react/tree/main/packages/plugins/eslint-plugin-react-x) and [eslint-plugin-react-dom](https://github.com/Rel1cx/eslint-react/tree/main/packages/plugins/eslint-plugin-react-dom) for React-specific lint rules:

```js
// eslint.config.js
import reactX from 'eslint-plugin-react-x'
import reactDom from 'eslint-plugin-react-dom'

export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      // Other configs...
      // Enable lint rules for React
      reactX.configs['recommended-typescript'],
      // Enable lint rules for React DOM
      reactDom.configs.recommended,
    ],
    languageOptions: {
      parserOptions: {
        project: ['./tsconfig.node.json', './tsconfig.app.json'],
        tsconfigRootDir: import.meta.dirname,
      },
      // other options...
    },
  },
])
```
