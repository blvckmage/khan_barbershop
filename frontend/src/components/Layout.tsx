import { useState } from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';

const NAV = [
  { label: 'Главная', path: '/', icon: '▦' },
  { label: 'Чаты', path: '/logs', icon: '💬' },
  { label: 'Рассылки', path: '/broadcasts', icon: '📢' },
  { label: 'Настройки бота', path: '/bot-settings', icon: '⚙️' },
];

const s: Record<string, React.CSSProperties> = {
  root: { display: 'flex', height: '100vh', overflow: 'hidden', background: '#0D0D12' },
  sidebar: {
    width: 220, flexShrink: 0, display: 'flex', flexDirection: 'column',
    background: '#16161F', borderRight: '1px solid rgba(255,255,255,0.06)',
  },
  logo: {
    padding: '28px 24px 20px', borderBottom: '1px solid rgba(255,255,255,0.06)',
  },
  logoTitle: { fontSize: 18, fontWeight: 800, color: '#C9A84C', letterSpacing: 1 },
  logoSub: { fontSize: 11, color: '#5A5A6E', marginTop: 2, letterSpacing: 2, textTransform: 'uppercase' as const },
  nav: { flex: 1, padding: '16px 12px', display: 'flex', flexDirection: 'column', gap: 4 },
  navItemBase: {
    display: 'flex', alignItems: 'center', gap: 10, padding: '10px 12px',
    borderRadius: 8, cursor: 'pointer', transition: 'all 0.15s', fontSize: 14,
  } as React.CSSProperties,
  navIcon: { fontSize: 16, width: 20, textAlign: 'center' as const },
  bottom: { padding: '16px 12px', borderTop: '1px solid rgba(255,255,255,0.06)' },
  logoutBtn: {
    width: '100%', display: 'flex', alignItems: 'center', gap: 10,
    padding: '10px 12px', borderRadius: 8, cursor: 'pointer',
    background: 'transparent', border: 'none', color: '#5A5A6E',
    fontSize: 14, transition: 'color 0.15s',
  },
  main: { flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' },
  topbar: {
    height: 56, display: 'flex', alignItems: 'center', justifyContent: 'space-between',
    padding: '0 28px', borderBottom: '1px solid rgba(255,255,255,0.06)',
    background: '#16161F', flexShrink: 0,
  },
  topbarTitle: { fontSize: 15, fontWeight: 600, color: '#F0F0F0' },
  content: { flex: 1, overflow: 'auto', padding: 28 },
};

export default function Layout() {
  const navigate = useNavigate();
  const location = useLocation();
  const logout = useAuthStore((s) => s.logout);
  const [hoveredLogout, setHoveredLogout] = useState(false);

  const currentPage = NAV.find((n) => n.path === location.pathname)?.label ?? 'KHAN Barbershop';

  return (
    <div style={s.root}>
      <aside style={s.sidebar}>
        <div style={s.logo}>
          <div style={s.logoTitle}>✂ KHAN</div>
          <div style={s.logoSub}>Admin Panel</div>
        </div>

        <nav style={s.nav}>
          {NAV.map((item) => {
            const active = location.pathname === item.path;
            return (
              <div key={item.path} onClick={() => navigate(item.path)} style={{
              ...s.navItemBase,
              background: active ? 'rgba(201,168,76,0.12)' : 'transparent',
              color: active ? '#C9A84C' : '#7A7A8C',
              fontWeight: active ? 600 : 400,
              border: active ? '1px solid rgba(201,168,76,0.2)' : '1px solid transparent',
            }}>
                <span style={s.navIcon}>{item.icon}</span>
                {item.label}
              </div>
            );
          })}
        </nav>

        <div style={s.bottom}>
          <button
            style={{ ...s.logoutBtn, color: hoveredLogout ? '#E74C3C' : '#5A5A6E' }}
            onMouseEnter={() => setHoveredLogout(true)}
            onMouseLeave={() => setHoveredLogout(false)}
            onClick={() => { logout(); navigate('/login'); }}
          >
            <span style={s.navIcon}>↩</span>
            Выйти
          </button>
        </div>
      </aside>

      <main style={s.main}>
        <div style={s.topbar}>
          <span style={s.topbarTitle}>{currentPage}</span>
          <span style={{ fontSize: 12, color: '#5A5A6E' }}>
            {new Date().toLocaleDateString('ru-RU', { day: 'numeric', month: 'long', year: 'numeric' })}
          </span>
        </div>
        <div style={s.content}>
          <Outlet />
        </div>
      </main>
    </div>
  );
}
