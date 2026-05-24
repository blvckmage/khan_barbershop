import { useState, useEffect } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '../api/client';

const SURFACE = '#16161F';
const SURFACE2 = '#1E1E2A';
const BORDER = 'rgba(255,255,255,0.07)';
const MUTED = '#7A7A8C';
const GOLD = '#C9A84C';

function Card({ children, style = {} }: { children: React.ReactNode; style?: React.CSSProperties }) {
  return (
    <div style={{ background: SURFACE, border: `1px solid ${BORDER}`, borderRadius: 14, padding: 24, ...style }}>
      {children}
    </div>
  );
}

function Label({ children }: { children: React.ReactNode }) {
  return <div style={{ fontSize: 12, color: MUTED, fontWeight: 500, marginBottom: 6 }}>{children}</div>;
}

export default function BotSettings() {
  const qc = useQueryClient();
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  const { data: botSettings, isLoading: botLoading } = useQuery({
    queryKey: ['bot-settings'],
    queryFn: api.getBotSettings,
  });

  // Stats (includes masters data)
  const { isLoading: staffLoading } = useQuery({
    queryKey: ['alteegio-staff'],
    queryFn: api.getStats,
    staleTime: 60_000,
  });

  // Also try to get masters from /masters endpoint
  const { data: mastersData } = useQuery({
    queryKey: ['masters'],
    queryFn: api.getMasters,
  });

  const [excludedIds, setExcludedIds] = useState<Set<number>>(new Set());
  const [botEnabled, setBotEnabled] = useState(true);

  useEffect(() => {
    if (botSettings) {
      setBotEnabled(botSettings.chatbot_enabled ?? true);
      setExcludedIds(new Set(botSettings.excluded_master_ids ?? []));
    }
  }, [botSettings]);

  // Build masters list from all available sources
  const mastersList: { id: number; name: string; specialization?: string; position?: string }[] =
    (mastersData ?? []).map((m: any) => ({
      id: m.alteegio_id ?? m.id,
      name: m.name,
      position: m.position,
    }));

  const toggleMaster = (id: number) => {
    setExcludedIds(prev => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  const save = async () => {
    setSaving(true);
    setSaved(false);
    try {
      await api.updateBotSettings({
        chatbot_enabled: botEnabled,
        excluded_master_ids: [...excludedIds],
      });
      qc.invalidateQueries({ queryKey: ['bot-settings'] });
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24, maxWidth: 800 }}>

      {/* Bot toggle */}
      <Card>
        <div style={{ fontSize: 14, fontWeight: 600, color: '#D0D0D0', marginBottom: 20 }}>
          🤖 Статус чатбота
        </div>

        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '16px 20px', borderRadius: 10, background: SURFACE2 }}>
          <div>
            <div style={{ fontSize: 14, fontWeight: 600, color: '#F0F0F0', marginBottom: 4 }}>
              Чатбот WhatsApp
            </div>
            <div style={{ fontSize: 12, color: MUTED }}>
              Когда выключен — бот не отвечает клиентам и возвращает сообщение о недоступности
            </div>
          </div>
          <button
            onClick={() => setBotEnabled(v => !v)}
            style={{
              width: 52, height: 28, borderRadius: 14, border: 'none', cursor: 'pointer',
              background: botEnabled ? '#27AE60' : '#444',
              position: 'relative', transition: 'background 0.2s', flexShrink: 0,
            }}
          >
            <div style={{
              position: 'absolute', top: 3, left: botEnabled ? 27 : 3,
              width: 22, height: 22, borderRadius: '50%', background: '#fff',
              transition: 'left 0.2s', boxShadow: '0 1px 3px rgba(0,0,0,0.4)',
            }} />
          </button>
        </div>

        {!botEnabled && (
          <div style={{
            marginTop: 12, padding: '10px 14px', borderRadius: 8, fontSize: 13,
            background: 'rgba(231,76,60,0.08)', border: '1px solid rgba(231,76,60,0.2)', color: '#E98080',
          }}>
            ⚠️ Бот будет отключён. Клиенты, написавшие в WhatsApp, получат сообщение: «Бот временно недоступен. Позвоните нам или напишите позже 🙏»
          </div>
        )}
      </Card>

      {/* Excluded masters */}
      <Card>
        <div style={{ fontSize: 14, fontWeight: 600, color: '#D0D0D0', marginBottom: 6 }}>
          🚫 Скрыть мастеров из чатбота
        </div>
        <div style={{ fontSize: 12, color: MUTED, marginBottom: 20 }}>
          Выбранные мастера не будут предлагаться ботом при подборе. Клиент всё равно может попросить запись к конкретному мастеру по имени.
        </div>

        {(botLoading || staffLoading) ? (
          <div style={{ color: MUTED, fontSize: 13 }}>Загрузка мастеров...</div>
        ) : mastersList.length === 0 ? (
          <div style={{ color: MUTED, fontSize: 13 }}>
            Список мастеров недоступен. Введите Alteegio ID мастера вручную ниже.
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {mastersList.map(m => {
              const excluded = excludedIds.has(m.id);
              return (
                <div
                  key={m.id}
                  onClick={() => toggleMaster(m.id)}
                  style={{
                    display: 'flex', alignItems: 'center', gap: 12, padding: '12px 16px',
                    borderRadius: 10, cursor: 'pointer', transition: 'background 0.1s',
                    background: excluded ? 'rgba(231,76,60,0.08)' : SURFACE2,
                    border: `1px solid ${excluded ? 'rgba(231,76,60,0.25)' : 'transparent'}`,
                  }}
                >
                  <div style={{
                    width: 18, height: 18, borderRadius: 5, flexShrink: 0,
                    background: excluded ? '#E74C3C' : SURFACE,
                    border: `1.5px solid ${excluded ? '#E74C3C' : 'rgba(255,255,255,0.15)'}`,
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontSize: 11, color: '#fff', fontWeight: 800,
                  }}>{excluded ? '✕' : ''}</div>
                  <div style={{ flex: 1 }}>
                    <span style={{ fontSize: 14, fontWeight: 600, color: excluded ? '#E98080' : '#F0F0F0' }}>
                      {m.name}
                    </span>
                    {m.position && (
                      <span style={{ fontSize: 12, color: MUTED, marginLeft: 8 }}>{m.position}</span>
                    )}
                  </div>
                  <span style={{ fontSize: 11, color: MUTED }}>ID: {m.id}</span>
                  {excluded && (
                    <span style={{
                      fontSize: 11, fontWeight: 600, padding: '2px 8px', borderRadius: 10,
                      background: 'rgba(231,76,60,0.15)', color: '#E74C3C',
                    }}>Скрыт</span>
                  )}
                </div>
              );
            })}
          </div>
        )}

        {/* Manual ID input */}
        <div style={{ marginTop: 16, paddingTop: 16, borderTop: `1px solid ${BORDER}` }}>
          <Label>Добавить мастера по Alteegio ID (если не отображается выше)</Label>
          <ManualIdInput excludedIds={excludedIds} setExcludedIds={setExcludedIds} />
        </div>
      </Card>

      {/* Save button */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
        <button
          onClick={save}
          disabled={saving}
          style={{
            padding: '11px 28px', borderRadius: 10, border: `1px solid ${GOLD}`,
            background: saving ? `${GOLD}30` : GOLD, color: saving ? MUTED : '#0D0D12',
            fontWeight: 700, fontSize: 14, cursor: saving ? 'wait' : 'pointer',
            transition: 'all 0.15s',
          }}
        >
          {saving ? '⏳ Сохранение...' : '💾 Сохранить настройки'}
        </button>
        {saved && (
          <span style={{ fontSize: 13, color: '#27AE60' }}>✅ Настройки сохранены</span>
        )}
      </div>
    </div>
  );
}

function ManualIdInput({ excludedIds, setExcludedIds }: {
  excludedIds: Set<number>;
  setExcludedIds: React.Dispatch<React.SetStateAction<Set<number>>>;
}) {
  const [input, setInput] = useState('');

  const add = () => {
    const id = parseInt(input.trim());
    if (!isNaN(id) && id > 0) {
      setExcludedIds(prev => new Set([...prev, id]));
      setInput('');
    }
  };

  const remove = (id: number) => {
    setExcludedIds(prev => {
      const next = new Set(prev);
      next.delete(id);
      return next;
    });
  };

  return (
    <div>
      <div style={{ display: 'flex', gap: 8, marginBottom: 10 }}>
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && add()}
          placeholder="Alteegio Staff ID (число)"
          style={{
            flex: 1, padding: '8px 12px', borderRadius: 8, fontSize: 13,
            background: '#1E1E2A', border: '1px solid rgba(255,255,255,0.07)',
            color: '#F0F0F0', outline: 'none',
          }}
        />
        <button onClick={add} style={{
          padding: '8px 16px', borderRadius: 8, border: '1px solid rgba(255,255,255,0.1)',
          background: '#2A2A3A', color: '#F0F0F0', cursor: 'pointer', fontSize: 13,
        }}>Добавить</button>
      </div>
      {excludedIds.size > 0 && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
          {[...excludedIds].map(id => (
            <span key={id} style={{
              display: 'inline-flex', alignItems: 'center', gap: 6,
              padding: '4px 10px', borderRadius: 8, fontSize: 12, fontWeight: 600,
              background: 'rgba(231,76,60,0.12)', color: '#E98080',
              border: '1px solid rgba(231,76,60,0.25)',
            }}>
              ID {id}
              <button onClick={() => remove(id)} style={{
                background: 'none', border: 'none', color: '#E74C3C',
                cursor: 'pointer', padding: 0, fontSize: 12, lineHeight: 1,
              }}>✕</button>
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
