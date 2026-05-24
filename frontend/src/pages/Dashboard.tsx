import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '../api/client';

const GOLD = '#C9A84C';
const SURFACE = '#16161F';
const SURFACE2 = '#1E1E2A';
const BORDER = 'rgba(255,255,255,0.07)';
const MUTED = '#7A7A8C';

function StatCard({ icon, label, value, sub, accent = GOLD }: {
  icon: string; label: string; value: string | number; sub?: string; accent?: string;
}) {
  return (
    <div style={{
      background: SURFACE, border: `1px solid ${BORDER}`, borderRadius: 14,
      padding: '22px 24px', display: 'flex', alignItems: 'center', gap: 18,
    }}>
      <div style={{
        width: 48, height: 48, borderRadius: 12, display: 'flex', alignItems: 'center',
        justifyContent: 'center', fontSize: 22, flexShrink: 0,
        background: `${accent}18`, border: `1px solid ${accent}30`,
      }}>{icon}</div>
      <div>
        <div style={{ fontSize: 12, color: MUTED, fontWeight: 500, marginBottom: 4 }}>{label}</div>
        <div style={{ fontSize: 26, fontWeight: 800, color: '#F0F0F0', lineHeight: 1 }}>{value}</div>
        {sub && <div style={{ fontSize: 11, color: MUTED, marginTop: 4 }}>{sub}</div>}
      </div>
    </div>
  );
}

function SectionHeader({ title, extra }: { title: string; extra?: React.ReactNode }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
      <div style={{ fontSize: 14, fontWeight: 600, color: '#D0D0D0' }}>{title}</div>
      {extra}
    </div>
  );
}

function Badge({ text, color }: { text: string; color: string }) {
  return (
    <span style={{
      fontSize: 11, fontWeight: 600, padding: '2px 8px', borderRadius: 20,
      background: `${color}18`, color, border: `1px solid ${color}30`,
    }}>{text}</span>
  );
}

export default function Dashboard() {
  const qc = useQueryClient();
  const [toggling, setToggling] = useState(false);

  const { data: stats, isLoading, error } = useQuery({
    queryKey: ['stats'],
    queryFn: api.getStats,
    refetchInterval: 30_000,
  });

  const { data: masters, isLoading: mastersLoading } = useQuery({
    queryKey: ['masters'],
    queryFn: api.getMasters,
    refetchInterval: 60_000,
  });

  const { data: botSettings } = useQuery({
    queryKey: ['bot-settings'],
    queryFn: api.getBotSettings,
    refetchInterval: 15_000,
  });

  const botEnabled: boolean = botSettings?.chatbot_enabled ?? true;

  const toggleBot = async () => {
    setToggling(true);
    try {
      await api.updateBotSettings({
        chatbot_enabled: !botEnabled,
        excluded_master_ids: botSettings?.excluded_master_ids ?? [],
      });
      qc.invalidateQueries({ queryKey: ['bot-settings'] });
    } finally {
      setToggling(false);
    }
  };

  if (isLoading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 400, color: MUTED }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: 32, marginBottom: 12 }}>⏳</div>
          <div style={{ fontSize: 14 }}>Загрузка...</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 400 }}>
        <div style={{
          padding: '24px 32px', borderRadius: 12,
          background: 'rgba(231,76,60,0.08)', border: '1px solid rgba(231,76,60,0.2)',
          color: '#E74C3C', fontSize: 14, textAlign: 'center',
        }}>
          <div style={{ fontSize: 28, marginBottom: 8 }}>⚠️</div>
          Ошибка загрузки данных
        </div>
      </div>
    );
  }

  const appointments = stats?.appointments_today ?? 0;
  const messages = stats?.messages_processed ?? 0;
  const activeChats = stats?.active_chats ?? 0;
  const totalClients = stats?.total_clients ?? 0;

  const recentAppointments: any[] = stats?.recentAppointments ?? [];
  const recentChats: any[] = stats?.recentChats ?? [];
  const mastersList: any[] = masters ?? [];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24, maxWidth: 1200 }}>

      {/* Bot Toggle Banner */}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '16px 24px', borderRadius: 14,
        background: botEnabled ? 'rgba(39,174,96,0.08)' : 'rgba(231,76,60,0.08)',
        border: `1px solid ${botEnabled ? 'rgba(39,174,96,0.25)' : 'rgba(231,76,60,0.25)'}`,
        transition: 'all 0.3s',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
          <div style={{
            width: 44, height: 44, borderRadius: 11, display: 'flex', alignItems: 'center',
            justifyContent: 'center', fontSize: 22,
            background: botEnabled ? 'rgba(39,174,96,0.15)' : 'rgba(231,76,60,0.15)',
          }}>
            {botEnabled ? '🤖' : '🔕'}
          </div>
          <div>
            <div style={{ fontSize: 14, fontWeight: 700, color: '#F0F0F0' }}>
              Чатбот WhatsApp
            </div>
            <div style={{ fontSize: 12, color: botEnabled ? '#27AE60' : '#E74C3C', marginTop: 2 }}>
              {botEnabled ? '● Активен — отвечает на сообщения клиентов' : '● Отключён — входящие сообщения игнорируются'}
            </div>
          </div>
        </div>
        <button
          onClick={toggleBot}
          disabled={toggling}
          style={{
            display: 'flex', alignItems: 'center', gap: 10, padding: '10px 22px',
            borderRadius: 10, border: 'none', cursor: toggling ? 'wait' : 'pointer',
            fontWeight: 700, fontSize: 13, transition: 'all 0.2s',
            background: botEnabled ? 'rgba(231,76,60,0.15)' : 'rgba(39,174,96,0.15)',
            color: botEnabled ? '#E74C3C' : '#27AE60',
          }}
        >
          {toggling ? '⏳' : botEnabled ? '⏸ Отключить бота' : '▶ Включить бота'}
        </button>
      </div>

      {/* Stat Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16 }}>
        <StatCard icon="📅" label="Записей через бота сегодня" value={appointments} accent={GOLD} />
        <StatCard icon="💬" label="Активных чатов (24ч)" value={activeChats} accent="#27AE60" />
        <StatCard icon="📨" label="Обработано сообщений" value={messages} accent="#2980B9" />
        <StatCard icon="👤" label="Уникальных клиентов" value={totalClients} accent="#8E44AD" />
      </div>

      {/* Main grid */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>

        {/* Recent appointments */}
        <div style={{ background: SURFACE, border: `1px solid ${BORDER}`, borderRadius: 14, padding: 24 }}>
          <SectionHeader title="Последние записи (бот)" />
          {recentAppointments.length === 0 ? (
            <div style={{ color: MUTED, fontSize: 13, paddingTop: 8 }}>Записей нет</div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {recentAppointments.map((apt: any, i: number) => (
                <div key={i} style={{
                  display: 'flex', alignItems: 'center', gap: 14,
                  padding: '10px 14px', borderRadius: 10, background: SURFACE2,
                }}>
                  <div style={{
                    width: 36, height: 36, borderRadius: 8, background: `${GOLD}18`,
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontSize: 13, fontWeight: 700, color: GOLD, flexShrink: 0,
                  }}>{apt.time || '—'}</div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: 13, fontWeight: 600, color: '#F0F0F0' }}>
                      {apt.master || apt.client || 'Клиент'}
                    </div>
                    <div style={{ fontSize: 11, color: MUTED, marginTop: 2 }}>
                      {apt.service || 'Стрижка'}
                    </div>
                  </div>
                  <Badge text="✓ Запись" color="#27AE60" />
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Recent chats */}
        <div style={{ background: SURFACE, border: `1px solid ${BORDER}`, borderRadius: 14, padding: 24 }}>
          <SectionHeader
            title="Последние чаты"
            extra={<a href="/logs" style={{ fontSize: 12, color: GOLD, textDecoration: 'none' }}>Все →</a>}
          />
          {recentChats.length === 0 ? (
            <div style={{ color: MUTED, fontSize: 13, paddingTop: 8 }}>Чатов нет</div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {recentChats.map((chat: any, i: number) => (
                <div key={i} style={{
                  display: 'flex', alignItems: 'center', gap: 12,
                  padding: '10px 14px', borderRadius: 10, background: SURFACE2,
                }}>
                  <div style={{
                    width: 36, height: 36, borderRadius: '50%',
                    background: 'rgba(41,128,185,0.15)', display: 'flex', alignItems: 'center',
                    justifyContent: 'center', fontSize: 16, flexShrink: 0,
                  }}>👤</div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: 12, fontWeight: 600, color: '#F0F0F0' }}>
                      +{chat.phone}
                    </div>
                    <div style={{
                      fontSize: 11, color: MUTED, marginTop: 2,
                      whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
                    }}>
                      {chat.lastMessage}
                    </div>
                  </div>
                  <div style={{ fontSize: 11, color: MUTED, flexShrink: 0 }}>{chat.time}</div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Masters */}
      <div style={{ background: SURFACE, border: `1px solid ${BORDER}`, borderRadius: 14, padding: 24 }}>
        <SectionHeader title="Мастера" />
        {mastersLoading ? (
          <div style={{ color: MUTED, fontSize: 13 }}>Загрузка...</div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: 12 }}>
            {mastersList.map((m: any) => (
              <div key={m.id} style={{
                padding: '16px', borderRadius: 10, background: SURFACE2,
                border: `1px solid ${m.is_active ? 'rgba(39,174,96,0.2)' : BORDER}`,
                display: 'flex', flexDirection: 'column', gap: 8,
              }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <div style={{ fontSize: 22 }}>✂</div>
                  <div style={{
                    width: 8, height: 8, borderRadius: '50%',
                    background: m.is_active ? '#27AE60' : '#555',
                  }} />
                </div>
                <div>
                  <div style={{ fontSize: 13, fontWeight: 600, color: '#F0F0F0' }}>{m.name}</div>
                  <div style={{ fontSize: 11, color: MUTED, marginTop: 2 }}>{m.position}</div>
                </div>
                {m.rating > 0 && (
                  <div style={{ fontSize: 11, color: GOLD }}>{'★'.repeat(Math.round(m.rating))} {m.rating}</div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
