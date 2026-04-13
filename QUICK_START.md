# 🚀 Khan Barbershop - Quick Start Guide

## ⚡ 30 Seconds to Running Application

### Terminal 1: Start Backend
```bash
cd backend
python -m app.main
# Backend runs on http://localhost:8000
```

### Terminal 2: Start Frontend  
```bash
cd frontend
npm run dev
# Frontend runs on http://localhost:5174
```

### Browser
```
URL: http://localhost:5174
Username: admin
Password: admin123
```

✅ **Done!** Admin panel is now running.

---

## 📖 Quick Navigation

### Pages Available
| Page | URL | Purpose |
|------|-----|---------|
| 📊 Dashboard | `/` | Statistics & overview |
| 📅 Appointments | `/appointments` | Booking management |
| 👨‍💼 Masters | `/masters` | Staff profiles |
| 💇 Services | `/services` | Service catalog |
| 📝 Logs | `/logs` | System logs |
| 📢 Broadcasts | `/broadcasts` | Mass messaging |
| ⚙️ Settings | `/settings` | Configuration |
| 🔑 Login | `/login` | Authentication |

---

## 🔧 Configuration

### Frontend Environment
File: `.env`
```
VITE_API_URL=http://localhost:8000
```

### Backend Database
File: `backend/khan_barbershop.db`

---

## 📚 Documentation

**Complete Setup**: Read `/frontend/SETUP.md`
**Project Overview**: Read `/README_PROJECT.md`
**Completion Summary**: Read `FRONTEND_COMPLETION_SUMMARY.md`

---

## ✅ What's Included

- ✅ 7 fully functional pages
- ✅ Complete CRUD operations
- ✅ JWT authentication
- ✅ Material-UI dark theme
- ✅ Responsive design
- ✅ API integration
- ✅ Production build
- ✅ TypeScript types

---

## 🐛 Troubleshooting

### Port Already in Use
```bash
# Kill process on port 5174
lsof -ti:5174 | xargs kill -9
```

### API Connection Error
- Ensure backend is running: `http://localhost:8000`
- Check `.env` has correct `VITE_API_URL`

### Dependencies Issue
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
```

---

## 🎯 Common Tasks

### Add New Page
1. Create `src/pages/YourPage.tsx`
2. Add route in `App.tsx`
3. Add menu item in `Layout.tsx`

### Connect New Endpoint
1. Add method to `src/api/client.ts`
2. Use in component via `api.yourMethod()`

### Change Theme
1. Edit color palette in `App.tsx`
2. Modify `createTheme()` call

---

## 📊 Build Information

- **Size**: 665 KB (gzip: 205 KB)
- **Build Time**: ~1.35 seconds
- **Dev Start**: ~542 ms
- **Modules**: 11,771 bundled

---

## 🔐 Default Credentials

```
Username: admin
Password: admin123
```

⚠️ Change in production!

---

## 📞 Contact

For detailed information, see:
- Frontend setup: `/frontend/SETUP.md`
- Project overview: `/README_PROJECT.md`
- Completion details: `/FRONTEND_COMPLETION_SUMMARY.md`

---

**Status**: ✅ Ready to Use
**Last Updated**: Today
