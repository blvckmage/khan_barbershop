import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';
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

  const { data: nps, isLoading: npsLoading, error: npsError } = useQuery({
    queryKey: ['nps-stats'],
    queryFn: () => api.getNpsStats(30),
    refetchInterval: 60_000,
    retry: 1,
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

      {/* NPS Statistics */}
      <NpsSection nps={nps} isLoading={npsLoading} error={npsError} />

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

// ─── NPS Section ──────────────────────────────────────────────────────────────

type NpsData = {
  total_responses: number;
  avg_rating: number;
  distribution: Record<string, number>;
  by_master: { master: string; avg: number; count: number }[];
  trend: { day: string; avg: number; count: number }[];
  recent: { rating: number; master_name: string | null; client_name: string | null; comment: string | null; created_at: string }[];
  period_days: number;
};

function ratingColor(r: number): string {
  if (r >= 5) return '#27AE60';
  if (r >= 4) return '#7DC383';
  if (r >= 3) return GOLD;
  if (r >= 2) return '#F39C12';
  return '#E74C3C';
}

function NpsSection({ nps, isLoading, error }: { nps: NpsData | undefined; isLoading: boolean; error: unknown }) {
  // 1) Loading
  if (isLoading) {
    return (
      <div style={{ background: SURFACE, border: `1px solid ${BORDER}`, borderRadius: 14, padding: 24 }}>
        <SectionHeader title="⭐ NPS — Оценки клиентов" />
        <div style={{ color: MUTED, fontSize: 13 }}>⏳ Загрузка...</div>
      </div>
    );
  }

  // 2) Error — usually means backend isn't restarted after schema change
  if (error || !nps) {
    const errMsg = (error as any)?.response?.status === 404
      ? 'Эндпоинт /api/admin/nps-stats не найден. Перезапустите backend для применения новой схемы БД.'
      : (error as any)?.message ?? 'Не удалось загрузить статистику NPS';
    return (
      <div style={{ background: SURFACE, border: `1px solid ${BORDER}`, borderRadius: 14, padding: 24 }}>
        <SectionHeader title="⭐ NPS — Оценки клиентов" />
        <div style={{
          color: '#E74C3C', fontSize: 13, padding: '14px 16px',
          background: 'rgba(231,76,60,0.08)', borderRadius: 10,
          border: '1px solid rgba(231,76,60,0.2)',
        }}>
          ⚠️ {errMsg}
        </div>
      </div>
    );
  }

  // 3) Empty state
  if (nps.total_responses === 0) {
    return (
      <div style={{ background: SURFACE, border: `1px solid ${BORDER}`, borderRadius: 14, padding: 24 }}>
        <SectionHeader title={`⭐ NPS — Оценки клиентов (${nps.period_days} дн.)`} />
        <div style={{ color: MUTED, fontSize: 13, padding: '20px 0', textAlign: 'center' }}>
          Пока нет ни одной оценки. Они появятся, когда клиенты начнут отвечать на NPS-запросы после визитов.
        </div>
      </div>
    );
  }

  // Chart data
  const chartData = ['1', '2', '3', '4', '5'].map(r => ({
    rating: `${r} ⭐`,
    count: nps.distribution[r] || 0,
    color: ratingColor(Number(r)),
  }));

  const accent = ratingColor(nps.avg_rating);

  return (
    <div style={{ background: SURFACE, border: `1px solid ${BORDER}`, borderRadius: 14, padding: 24 }}>
      <SectionHeader title={`⭐ NPS — Оценки клиентов (за ${nps.period_days} дн.)`} />

      <div style={{ display: 'grid', gridTemplateColumns: '220px 1fr', gap: 24, marginBottom: 24 }}>
        {/* Big average rating card */}
        <div style={{
          background: SURFACE2, borderRadius: 12, padding: '24px 16px',
          display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
          border: `1px solid ${accent}30`,
        }}>
          <div style={{ fontSize: 11, color: MUTED, marginBottom: 8, fontWeight: 500, letterSpacing: 1 }}>
            СРЕДНИЙ БАЛЛ
          </div>
          <div style={{ fontSize: 56, fontWeight: 800, color: accent, lineHeight: 1 }}>
            {nps.avg_rating.toFixed(1)}
          </div>
          <div style={{ fontSize: 13, color: MUTED, marginTop: 8 }}>из 5</div>
          <div style={{ fontSize: 12, color: MUTED, marginTop: 12, paddingTop: 12, borderTop: `1px solid ${BORDER}`, width: '100%', textAlign: 'center' }}>
            {nps.total_responses} {nps.total_responses === 1 ? 'оценка' : nps.total_responses < 5 ? 'оценки' : 'оценок'}
          </div>
        </div>

        {/* Distribution bar chart */}
        <div style={{ background: SURFACE2, borderRadius: 12, padding: '16px 12px' }}>
          <div style={{ fontSize: 12, color: MUTED, marginBottom: 8, paddingLeft: 8 }}>
            Распределение оценок
          </div>
          <ResponsiveContainer width="100%" height={180}>
            <BarChart data={chartData} margin={{ top: 5, right: 8, left: -20, bottom: 0 }}>
              <XAxis dataKey="rating" tick={{ fill: MUTED, fontSize: 12 }} axisLine={{ stroke: BORDER }} tickLine={false} />
              <YAxis tick={{ fill: MUTED, fontSize: 11 }} axisLine={false} tickLine={false} allowDecimals={false} />
              <Tooltip
                contentStyle={{ background: SURFACE, border: `1px solid ${BORDER}`, borderRadius: 8, fontSize: 12 }}
                labelStyle={{ color: '#F0F0F0' }}
                cursor={{ fill: 'rgba(255,255,255,0.04)' }}
              />
              <Bar dataKey="count" radius={[6, 6, 0, 0]}>
                {chartData.map((d, i) => <Cell key={i} fill={d.color} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* By master + recent */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
        {/* By master */}
        <div>
          <div style={{ fontSize: 13, fontWeight: 600, color: '#D0D0D0', marginBottom: 10 }}>
            По мастерам
          </div>
          {nps.by_master.length === 0 ? (
            <div style={{ fontSize: 12, color: MUTED }}>Нет данных по мастерам</div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {nps.by_master.map(m => (
                <div key={m.master} style={{
                  display: 'flex', alignItems: 'center', gap: 12,
                  padding: '8px 12px', borderRadius: 8, background: SURFACE2,
                }}>
                  <div style={{ flex: 1, fontSize: 13, color: '#F0F0F0', fontWeight: 500 }}>{m.master}</div>
                  <div style={{
                    fontSize: 13, fontWeight: 700, color: ratingColor(m.avg),
                    minWidth: 36, textAlign: 'right',
                  }}>
                    {m.avg.toFixed(1)}
                  </div>
                  <div style={{ fontSize: 11, color: MUTED, minWidth: 40, textAlign: 'right' }}>
                    {m.count} {m.count === 1 ? 'отз.' : 'отз.'}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Recent ratings */}
        <div>
          <div style={{ fontSize: 13, fontWeight: 600, color: '#D0D0D0', marginBottom: 10 }}>
            Последние оценки
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6, maxHeight: 240, overflowY: 'auto' }}>
            {nps.recent.map((r, i) => (
              <div key={i} style={{
                display: 'flex', alignItems: 'center', gap: 10,
                padding: '8px 12px', borderRadius: 8, background: SURFACE2,
              }}>
                <div style={{
                  width: 30, height: 30, borderRadius: 6, flexShrink: 0,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: 13, fontWeight: 800,
                  background: `${ratingColor(r.rating)}20`, color: ratingColor(r.rating),
                }}>{r.rating}</div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 12, color: '#F0F0F0', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    {r.client_name || 'Клиент'} → {r.master_name || '—'}
                  </div>
                  <div style={{ fontSize: 10, color: MUTED, marginTop: 2 }}>{r.created_at}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
