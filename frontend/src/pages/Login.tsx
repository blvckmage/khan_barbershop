import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import { api } from '../api/client';

export default function Login() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const login = useAuthStore((s) => s.login);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const data = await api.login(username, password);
      if (data.token) { login(data.token); navigate('/'); }
      else setError('Неверный логин или пароль');
    } catch {
      setError('Ошибка подключения к серверу');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center',
      background: '#0D0D12', fontFamily: 'Inter, system-ui, sans-serif',
    }}>
      {/* Background glow */}
      <div style={{
        position: 'fixed', inset: 0, pointerEvents: 'none',
        background: 'radial-gradient(ellipse 60% 50% at 50% 0%, rgba(201,168,76,0.07) 0%, transparent 70%)',
      }} />

      <div style={{
        width: 380, padding: '44px 40px', borderRadius: 16,
        background: '#16161F', border: '1px solid rgba(255,255,255,0.07)',
        boxShadow: '0 40px 80px rgba(0,0,0,0.5)',
        position: 'relative',
      }}>
        {/* Logo */}
        <div style={{ textAlign: 'center', marginBottom: 36 }}>
          <div style={{ fontSize: 40, marginBottom: 8 }}>✂</div>
          <div style={{ fontSize: 22, fontWeight: 800, color: '#C9A84C', letterSpacing: 2 }}>KHAN</div>
          <div style={{ fontSize: 11, color: '#5A5A6E', letterSpacing: 3, marginTop: 4, textTransform: 'uppercase' }}>
            Barbershop Admin
          </div>
        </div>

        {error && (
          <div style={{
            marginBottom: 20, padding: '10px 14px', borderRadius: 8,
            background: 'rgba(231,76,60,0.1)', border: '1px solid rgba(231,76,60,0.3)',
            color: '#E74C3C', fontSize: 13,
          }}>{error}</div>
        )}

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          {[
            { label: 'Логин', value: username, set: setUsername, type: 'text' },
            { label: 'Пароль', value: password, set: setPassword, type: 'password' },
          ].map(({ label, value, set, type }) => (
            <div key={label}>
              <label style={{ display: 'block', fontSize: 12, color: '#7A7A8C', marginBottom: 6, fontWeight: 500 }}>
                {label}
              </label>
              <input
                type={type}
                value={value}
                onChange={(e) => set(e.target.value)}
                required
                style={{
                  width: '100%', padding: '11px 14px', borderRadius: 8, fontSize: 14,
                  background: '#0D0D12', border: '1px solid rgba(255,255,255,0.1)',
                  color: '#F0F0F0', outline: 'none', transition: 'border-color 0.15s',
                }}
                onFocus={(e) => e.target.style.borderColor = '#C9A84C'}
                onBlur={(e) => e.target.style.borderColor = 'rgba(255,255,255,0.1)'}
              />
            </div>
          ))}

          <button
            type="submit"
            disabled={loading}
            style={{
              marginTop: 8, padding: '13px', borderRadius: 8, border: 'none',
              background: loading ? 'rgba(201,168,76,0.4)' : '#C9A84C',
              color: '#0D0D12', fontWeight: 700, fontSize: 15, cursor: loading ? 'not-allowed' : 'pointer',
              transition: 'all 0.15s', letterSpacing: 0.5,
            }}
          >
            {loading ? 'Вход...' : 'Войти'}
          </button>
        </form>
      </div>
    </div>
  );
}
