# Developer Quick Reference

## 🚀 Start Here

```bash
# Terminal 1: Backend
cd backend && python -m app.main

# Terminal 2: Frontend
cd frontend && npm run dev

# Browser
http://localhost:5174
```

---

## 📍 File Locations

### Pages
- **Dashboard**: `src/pages/Dashboard.tsx`
- **Appointments**: `src/pages/Appointments.tsx`
- **Masters**: `src/pages/Masters.tsx`
- **Services**: `src/pages/Services.tsx`
- **Logs**: `src/pages/Logs.tsx`
- **Broadcasts**: `src/pages/Broadcasts.tsx`
- **Settings**: `src/pages/Settings.tsx`
- **Login**: `src/pages/Login.tsx`

### Core Files
- **Routing**: `src/App.tsx`
- **Layout**: `src/components/Layout.tsx`
- **API Client**: `src/api/client.ts`
- **Auth Store**: `src/store/authStore.ts`

---

## 🔗 API Methods

### Get Data
```typescript
const appointments = await api.getAppointments();
const masters = await api.getMasters();
const services = await api.getServices();
const stats = await api.getStats();
const logs = await api.getLogs(1, 50);
const broadcasts = await api.getBroadcasts(1, 50);
const settings = await api.getSettings();
const prompt = await api.getPrompt();
```

### Create Data
```typescript
await api.createAppointment({ clientName, clientPhone, ... });
await api.createMaster({ name, phone, ... });
await api.createService({ name, description, ... });
await api.createBroadcast({ message, recipients: [...] });
```

### Update Data
```typescript
await api.updateAppointment(id, { status, ... });
await api.updateMaster(id, { name, ... });
await api.updateService(id, { price, ... });
await api.updateSettings({ companyName, ... });
await api.updatePrompt(prompt);
```

### Delete Data
```typescript
await api.deleteAppointment(id);
await api.deleteMaster(id);
await api.deleteService(id);
await api.deleteBroadcast(id);
```

---

## 💾 State Management

### Auth Store (Zustand)
```typescript
import { useAuthStore } from '../store/authStore';

// Get token
const token = useAuthStore.getState().token;

// Login
useAuthStore.getState().login(token);

// Logout
useAuthStore.getState().logout();

// In component
const { token, isAuthenticated } = useAuthStore();
```

### Server State (React Query)
```typescript
import { useQuery } from '@tanstack/react-query';

const { data, isLoading, error } = useQuery({
  queryKey: ['appointments'],
  queryFn: () => api.getAppointments(),
});
```

---

## 🎨 Component Patterns

### Dialog Form
```typescript
const [openDialog, setOpenDialog] = useState(false);
const [editingId, setEditingId] = useState<number | null>(null);

const handleEdit = (id: number) => {
  setEditingId(id);
  setOpenDialog(true);
};

// In JSX
<Dialog open={openDialog} onClose={() => setOpenDialog(false)}>
  {/* Form content */}
</Dialog>
```

### Table
```typescript
<TableContainer component={Paper}>
  <Table>
    <TableHead>
      <TableRow>
        <TableCell>Column</TableCell>
      </TableRow>
    </TableHead>
    <TableBody>
      {data.map(item => (
        <TableRow key={item.id}>
          <TableCell>{item.name}</TableCell>
        </TableRow>
      ))}
    </TableBody>
  </Table>
</TableContainer>
```

### Card Grid
```typescript
<Box sx={{
  display: 'grid',
  gridTemplateColumns: {
    xs: '1fr',
    sm: 'repeat(2, 1fr)',
    md: 'repeat(3, 1fr)',
  },
  gap: 2,
}}>
  {items.map(item => (
    <Card key={item.id}>
      {/* Content */}
    </Card>
  ))}
</Box>
```

---

## 🎯 Adding New Features

### Add New API Endpoint
1. Add method to `src/api/client.ts`:
```typescript
const myNewMethod = async (param: string) => {
  const response = await apiClient.get(`/my-endpoint/${param}`);
  return response.data;
};
```

2. Use in component:
```typescript
const data = await api.myNewMethod('value');
```

### Add New Page
1. Create `src/pages/MyPage.tsx`
2. Add to `App.tsx`:
```typescript
import MyPage from './pages/MyPage';

const router = createBrowserRouter([
  { path: '/my-page', element: <MyPage /> },
]);
```

3. Add to `Layout.tsx` menu:
```typescript
{ label: 'My Page', path: '/my-page', icon: <MyIcon /> }
```

### Add New Stat Card
In `Dashboard.tsx`:
```typescript
<Card>
  <CardContent>
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
      <Icon sx={{ color: 'primary.main' }} />
      <Box>
        <Typography variant="body2" color="text.secondary">
          Label
        </Typography>
        <Typography variant="h5">
          {value}
        </Typography>
      </Box>
    </Box>
  </CardContent>
</Card>
```

---

## 🐛 Common Patterns

### Error Handling
```typescript
try {
  const data = await api.method();
  // handle success
} catch (error) {
  console.error('Error:', error);
  alert('Failed to fetch data');
}
```

### Loading State
```typescript
const [loading, setLoading] = useState(false);

const handleSubmit = async (formData) => {
  setLoading(true);
  try {
    await api.createAppointment(formData);
    // refresh data
  } finally {
    setLoading(false);
  }
};

// In JSX
<Button disabled={loading}>
  {loading ? 'Loading...' : 'Submit'}
</Button>
```

### Confirmation Dialog
```typescript
const handleDelete = (id: number) => {
  if (window.confirm('Are you sure?')) {
    api.deleteAppointment(id);
  }
};
```

---

## 🔑 Environment Variables

### Frontend (.env)
```
VITE_API_URL=http://localhost:8000
```

### Backend (must have)
```
DATABASE_URL=sqlite:///./khan_barbershop.db
```

---

## 📦 npm Commands

```bash
npm run dev       # Start dev server
npm run build     # Production build
npm run preview   # Preview build
npm run lint      # Check for issues
npm install       # Install deps
```

---

## 🌐 Useful Links

- **MUI Docs**: https://mui.com/
- **React Router**: https://reactrouter.com/
- **React Query**: https://tanstack.com/query/latest/
- **Zustand**: https://github.com/pmndrs/zustand
- **Vite**: https://vitejs.dev/

---

## 🎨 Theme Customization

In `App.tsx`:
```typescript
const theme = createTheme({
  palette: {
    mode: 'dark',
    primary: {
      main: '#90caf9',
    },
    secondary: {
      main: '#f48fb1',
    },
  },
});
```

---

## 🔐 Login & Auth

### Test Credentials
```
Username: admin
Password: admin123
```

### How It Works
1. User logs in at `/login`
2. Backend returns JWT token
3. Token stored in Zustand
4. Axios interceptor adds token to all requests
5. Protected routes via PrivateRoute HOC

---

## 📊 Data Flow

```
User Input
    ↓
React Component (form, button)
    ↓
API Client (axios)
    ↓
Backend (FastAPI)
    ↓
Database (SQLite)
    ↓
Response (JSON)
    ↓
React Query (cache)
    ↓
Component (UI update)
```

---

## ⚡ Performance Tips

- Use React Query for server state (handles caching)
- Memoize heavy components with `React.memo()`
- Use lazy loading with `React.lazy()`
- Avoid unnecessary re-renders
- Use `key` prop in lists properly

---

## 🧪 Testing API Locally

```bash
# Test endpoint with curl
curl http://localhost:8000/api/admin/stats \
  -H "Authorization: Bearer YOUR_TOKEN"

# Or use Postman/Insomnia
# Set Authorization header with JWT token
```

---

## 🆘 Troubleshooting

### Build Error
```bash
rm -rf dist node_modules
npm install
npm run build
```

### Port Conflict
```bash
lsof -ti:5174 | xargs kill -9
npm run dev
```

### API Connection Failed
- Check backend is running: http://localhost:8000
- Check .env has correct VITE_API_URL
- Check network tab in DevTools

### TypeScript Error
```bash
npm run build 2>&1
# Check exact error
```

---

## 📚 Documentation

- **Setup**: `/frontend/SETUP.md`
- **Project**: `/README_PROJECT.md`
- **Quick Start**: `/QUICK_START.md`
- **Completion**: `/COMPLETION_REPORT.md`

---

**Last Updated**: Today
**Status**: ✅ Ready to Code
