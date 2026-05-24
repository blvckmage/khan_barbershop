import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
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

function Input({ value, onChange, placeholder = '', type = 'text', rows }: {
  value: string; onChange: (v: string) => void; placeholder?: string; type?: string; rows?: number;
}) {
  const base: React.CSSProperties = {
    width: '100%', padding: '10px 14px', borderRadius: 8, fontSize: 13,
    background: SURFACE2, border: `1px solid ${BORDER}`, color: '#F0F0F0',
    outline: 'none', transition: 'border-color 0.15s', resize: 'vertical' as const,
  };
  if (rows) {
    return (
      <textarea
        rows={rows} value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        style={base}
        onFocus={(e) => (e.target.style.borderColor = GOLD)}
        onBlur={(e) => (e.target.style.borderColor = 'rgba(255,255,255,0.07)')}
      />
    );
  }
  return (
    <input
      type={type} value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      style={base}
      onFocus={(e) => (e.target.style.borderColor = GOLD)}
      onBlur={(e) => (e.target.style.borderColor = 'rgba(255,255,255,0.07)')}
    />
  );
}

function Btn({ children, onClick, disabled = false, variant = 'primary', style = {} }: {
  children: React.ReactNode; onClick?: () => void; disabled?: boolean;
  variant?: 'primary' | 'secondary' | 'danger'; style?: React.CSSProperties;
}) {
  const colors = {
    primary: { bg: GOLD, color: '#0D0D12' },
    secondary: { bg: SURFACE2, color: '#F0F0F0' },
    danger: { bg: 'rgba(231,76,60,0.15)', color: '#E74C3C' },
  };
  const c = colors[variant];
  return (
    <button
      onClick={onClick} disabled={disabled}
      style={{
        padding: '9px 20px', borderRadius: 8, border: `1px solid ${variant === 'primary' ? GOLD : BORDER}`,
        background: disabled ? 'rgba(201,168,76,0.2)' : c.bg, color: disabled ? MUTED : c.color,
        fontSize: 13, fontWeight: 600, cursor: disabled ? 'not-allowed' : 'pointer',
        transition: 'all 0.15s', ...style,
      }}
    >{children}</button>
  );
}

export default function BroadcastSettings() {
  const qc = useQueryClient();

  // Tabs
  const [tab, setTab] = useState<'send' | 'templates'>('send');

  // Broadcast history
  const { data: bData } = useQuery({ queryKey: ['broadcasts'], queryFn: () => api.getBroadcasts(1, 20) });
  const broadcasts: any[] = bData?.items ?? [];

  // Client list
  const { data: cData, isLoading: cLoading } = useQuery({ queryKey: ['broadcast-clients'], queryFn: () => api.getBroadcastClients(30) });
  const clients: any[] = cData?.items ?? [];

  // New broadcast form
  const [message, setMessage] = useState('');
  const [selectedPhones, setSelectedPhones] = useState<Set<string>>(new Set());
  const [sending, setSending] = useState(false);
  const [result, setResult] = useState<{ success?: boolean; error?: string; sent?: number; failed?: number } | null>(null);

  // WABA Templates
  const { data: tmplData, isLoading: tmplLoading, refetch: refetchTemplates } = useQuery({
    queryKey: ['waba-templates'],
    queryFn: () => api.getWabaTemplates(false),
    enabled: tab === 'templates',
  });
  const templates: any[] = tmplData?.templates ?? [];
  const [tmplText, setTmplText] = useState('');
  const [tmplCategory, setTmplCategory] = useState('MARKETING');
  const [submittingTmpl, setSubmittingTmpl] = useState(false);
  const [tmplResult, setTmplResult] = useState<{ warning?: string; error?: string; name?: string; status?: string } | null>(null);

  // Quick Reply buttons for new template
  const [btnInput, setBtnInput] = useState('');
  const [tmplButtons, setTmplButtons] = useState<{ text: string }[]>([]);

  const addButton = () => {
    const text = btnInput.trim();
    if (!text || text.length > 25) return;
    if (tmplButtons.length >= 10) return;
    setTmplButtons([...tmplButtons, { text }]);
    setBtnInput('');
  };

  const removeButton = (i: number) => {
    setTmplButtons(tmplButtons.filter((_, idx) => idx !== i));
  };

  // Reminder enable/disable
  const { data: reminderSettings } = useQuery({
    queryKey: ['reminder-settings'],
    queryFn: api.getReminderSettings,
    enabled: tab === 'templates',
  });
  const [savingReminders, setSavingReminders] = useState(false);

  const toggleReminder = async (key: 'enable_one_hour_reminder' | 'enable_revisit_reminder' | 'enable_nps_request') => {
    if (!reminderSettings) return;
    setSavingReminders(true);
    try {
      const next = { ...reminderSettings, [key]: !reminderSettings[key] };
      await api.updateReminderSettings(next);
      qc.invalidateQueries({ queryKey: ['reminder-settings'] });
    } finally {
      setSavingReminders(false);
    }
  };

  const submitTemplate = async () => {
    if (!tmplText.trim()) return;
    setSubmittingTmpl(true);
    setTmplResult(null);
    try {
      const payload: any = { body_text: tmplText, category: tmplCategory };
      if (tmplButtons.length > 0) {
        payload.buttons = tmplButtons.map(b => ({ type: 'QUICK_REPLY', text: b.text }));
      }
      const res = await api.createWabaTemplate(payload);
      if (res.meta_error || res.warning) {
        setTmplResult({ warning: res.warning, name: res.template?.name });
      } else {
        setTmplResult({ name: res.template?.name, status: res.template?.meta_status });
        setTmplText('');
        setTmplButtons([]);
      }
      qc.invalidateQueries({ queryKey: ['waba-templates'] });
    } catch (e: any) {
      setTmplResult({ error: e.message ?? 'Ошибка' });
    } finally {
      setSubmittingTmpl(false);
    }
  };

  const syncTemplates = async () => {
    await api.getWabaTemplates(true);
    refetchTemplates();
  };

  const deleteTmplMutation = useMutation({
    mutationFn: (id: number) => api.deleteWabaTemplate(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['waba-templates'] }),
  });

  const toggleClient = (phone: string) => {
    setSelectedPhones((prev) => {
      const next = new Set(prev);
      next.has(phone) ? next.delete(phone) : next.add(phone);
      return next;
    });
  };

  const toggleAll = () => {
    if (selectedPhones.size === clients.length) {
      setSelectedPhones(new Set());
    } else {
      setSelectedPhones(new Set(clients.map((c) => c.phone)));
    }
  };

  const sendBroadcast = async () => {
    if (!message.trim() || selectedPhones.size === 0) return;
    setSending(true);
    setResult(null);
    try {
      const res = await api.createBroadcast({ message, recipients: [...selectedPhones] });
      setResult({ success: true, sent: res.sentCount, failed: res.failedCount });
      setMessage('');
      setSelectedPhones(new Set());
      qc.invalidateQueries({ queryKey: ['broadcasts'] });
    } catch (e: any) {
      setResult({ error: e.message ?? 'Ошибка отправки' });
    } finally {
      setSending(false);
    }
  };

  const delMutation = useMutation({
    mutationFn: (id: number) => api.deleteBroadcast(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['broadcasts'] }),
  });

  function statusColor(s: string) {
    if (s === 'completed') return '#27AE60';
    if (s === 'failed') return '#E74C3C';
    if (s === 'sending') return GOLD;
    return MUTED;
  }

  function tmplStatusColor(s: string) {
    if (s === 'APPROVED') return '#27AE60';
    if (s === 'REJECTED') return '#E74C3C';
    if (s === 'PENDING' || s === 'IN_APPEAL') return GOLD;
    if (s === 'ERROR') return '#E74C3C';
    return MUTED;
  }

  const tabStyle = (active: boolean): React.CSSProperties => ({
    padding: '8px 20px', borderRadius: 8, cursor: 'pointer', fontSize: 13, fontWeight: 600,
    background: active ? `${GOLD}18` : 'transparent',
    color: active ? GOLD : MUTED,
    border: active ? `1px solid ${GOLD}30` : '1px solid transparent',
    transition: 'all 0.15s',
  });

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24, maxWidth: 1100 }}>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: 8 }}>
        <button style={tabStyle(tab === 'send')} onClick={() => setTab('send')}>📤 Рассылки</button>
        <button style={tabStyle(tab === 'templates')} onClick={() => setTab('templates')}>📋 Шаблоны Meta</button>
      </div>

      {tab === 'templates' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
          {/* Reminder toggles */}
          <Card>
            <div style={{ fontSize: 14, fontWeight: 600, color: '#D0D0D0', marginBottom: 6 }}>
              🔔 Автоматические напоминания
            </div>
            <div style={{ fontSize: 12, color: MUTED, marginBottom: 16 }}>
              Каждое напоминание можно отдельно включать и выключать. Выключенные напоминания пропускаются APScheduler-ом сразу же при следующем запуске задачи.
            </div>
            {!reminderSettings ? (
              <div style={{ color: MUTED, fontSize: 13 }}>Загрузка настроек...</div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                {[
                  { key: 'enable_one_hour_reminder' as const, title: '⏳ За час до приёма', sub: 'Отправляется за 60 минут до записи (каждые 5 мин)' },
                  { key: 'enable_revisit_reminder' as const, title: '💈 Пора подстричься', sub: 'Через 20 дней после последнего визита (ежедневно в 12:00)' },
                  { key: 'enable_nps_request' as const, title: '⭐ NPS оценка визита', sub: 'Через ~2 часа после стрижки (каждые 30 мин)' },
                ].map(item => {
                  const enabled = reminderSettings[item.key];
                  return (
                    <div key={item.key} style={{
                      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                      padding: '14px 18px', borderRadius: 10, background: SURFACE2,
                      border: `1px solid ${enabled ? 'rgba(39,174,96,0.2)' : 'transparent'}`,
                    }}>
                      <div>
                        <div style={{ fontSize: 14, fontWeight: 600, color: '#F0F0F0' }}>{item.title}</div>
                        <div style={{ fontSize: 12, color: MUTED, marginTop: 2 }}>{item.sub}</div>
                      </div>
                      <button
                        onClick={() => toggleReminder(item.key)}
                        disabled={savingReminders}
                        style={{
                          width: 52, height: 28, borderRadius: 14, border: 'none',
                          cursor: savingReminders ? 'wait' : 'pointer',
                          background: enabled ? '#27AE60' : '#444',
                          position: 'relative', transition: 'background 0.2s', flexShrink: 0,
                        }}
                      >
                        <div style={{
                          position: 'absolute', top: 3, left: enabled ? 27 : 3,
                          width: 22, height: 22, borderRadius: '50%', background: '#fff',
                          transition: 'left 0.2s', boxShadow: '0 1px 3px rgba(0,0,0,0.4)',
                        }} />
                      </button>
                    </div>
                  );
                })}
              </div>
            )}
          </Card>

          {/* Info banner */}
          <div style={{
            padding: '14px 18px', borderRadius: 10,
            background: 'rgba(41,128,185,0.08)', border: '1px solid rgba(41,128,185,0.2)',
            fontSize: 13, color: '#7EC8E3', lineHeight: 1.6,
          }}>
            <strong style={{ color: '#B0D8F0' }}>📌 Зачем нужны шаблоны?</strong><br />
            WhatsApp запрещает отправлять свободный текст клиентам, которые не писали вам последние 24 часа.
            Для рассылок по «холодной» базе нужны <strong>одобренные шаблоны Meta</strong>.
            После создания шаблон проходит проверку Meta (~24 часа). Статус «APPROVED» — можно использовать.
            <br /><strong style={{ color: '#B0D8F0' }}>Требуется:</strong> добавить <code>WHATSAPP_WABA_ID</code> в <code>backend/.env</code>
          </div>

          {/* Create template */}
          <Card>
            <div style={{ fontSize: 14, fontWeight: 600, color: '#D0D0D0', marginBottom: 16 }}>
              ✍️ Создать новый шаблон
            </div>
            <div style={{ marginBottom: 12 }}>
              <Label>Категория</Label>
              <div style={{ display: 'flex', gap: 8 }}>
                {['MARKETING', 'UTILITY', 'AUTHENTICATION'].map(cat => (
                  <button key={cat} onClick={() => setTmplCategory(cat)} style={{
                    padding: '6px 14px', borderRadius: 6, fontSize: 12, fontWeight: 600, cursor: 'pointer',
                    background: tmplCategory === cat ? `${GOLD}20` : SURFACE2,
                    color: tmplCategory === cat ? GOLD : MUTED,
                    border: `1px solid ${tmplCategory === cat ? GOLD + '50' : 'transparent'}`,
                  }}>{cat}</button>
                ))}
              </div>
            </div>
            <div style={{ marginBottom: 12 }}>
              <Label>Текст сообщения</Label>
              <Input
                value={tmplText}
                onChange={setTmplText}
                rows={4}
                placeholder={'Привет! Это KHAN Barbershop. Записаться можно прямо здесь — просто напишите нам!'}
              />
              <div style={{ fontSize: 11, color: MUTED, marginTop: 6 }}>
                💡 Используйте {'{{1}}'}, {'{{2}}'} и т.д. для переменных (имя клиента, дата и т.п.)
              </div>
            </div>

            {/* Quick Reply buttons (optional) */}
            <div style={{ marginBottom: 12 }}>
              <Label>Кнопки быстрого ответа (опционально, до 10)</Label>
              <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
                <input
                  value={btnInput}
                  onChange={e => setBtnInput(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && (e.preventDefault(), addButton())}
                  maxLength={25}
                  placeholder='Текст кнопки (например "Записаться" или "5")'
                  style={{
                    flex: 1, padding: '8px 12px', borderRadius: 8, fontSize: 13,
                    background: SURFACE2, border: `1px solid ${BORDER}`, color: '#F0F0F0', outline: 'none',
                  }}
                />
                <button
                  onClick={addButton}
                  disabled={!btnInput.trim() || tmplButtons.length >= 10}
                  style={{
                    padding: '8px 16px', borderRadius: 8, border: `1px solid ${BORDER}`,
                    background: SURFACE2, color: '#F0F0F0',
                    cursor: !btnInput.trim() || tmplButtons.length >= 10 ? 'not-allowed' : 'pointer',
                    fontSize: 13,
                  }}
                >+ Добавить</button>
              </div>
              {tmplButtons.length > 0 && (
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                  {tmplButtons.map((b, i) => (
                    <span key={i} style={{
                      display: 'inline-flex', alignItems: 'center', gap: 6,
                      padding: '4px 10px', borderRadius: 8, fontSize: 12, fontWeight: 600,
                      background: 'rgba(201,168,76,0.12)', color: GOLD,
                      border: `1px solid ${GOLD}30`,
                    }}>
                      {b.text}
                      <button onClick={() => removeButton(i)} style={{
                        background: 'none', border: 'none', color: '#E74C3C',
                        cursor: 'pointer', padding: 0, fontSize: 12, lineHeight: 1,
                      }}>✕</button>
                    </span>
                  ))}
                </div>
              )}
              <div style={{ fontSize: 11, color: MUTED, marginTop: 6 }}>
                💡 Для NPS: добавьте «1», «2», «3», «4», «5» — статистика по кнопкам автоматически попадёт в дашборд.
                Каждая кнопка ≤ 25 символов.
              </div>
            </div>

            {tmplResult && (
              <div style={{
                marginBottom: 12, padding: '10px 14px', borderRadius: 8, fontSize: 13,
                background: tmplResult.error ? 'rgba(231,76,60,0.1)' : tmplResult.warning ? 'rgba(241,196,15,0.1)' : 'rgba(39,174,96,0.1)',
                border: `1px solid ${tmplResult.error ? 'rgba(231,76,60,0.3)' : tmplResult.warning ? 'rgba(241,196,15,0.3)' : 'rgba(39,174,96,0.3)'}`,
                color: tmplResult.error ? '#E74C3C' : tmplResult.warning ? '#F1C40F' : '#27AE60',
              }}>
                {tmplResult.error && `❌ ${tmplResult.error}`}
                {tmplResult.warning && `⚠️ ${tmplResult.warning}`}
                {!tmplResult.error && !tmplResult.warning && tmplResult.name && (
                  <>✅ Шаблон <strong>{tmplResult.name}</strong> отправлен на проверку Meta. Статус: {tmplResult.status}</>
                )}
              </div>
            )}

            <Btn onClick={submitTemplate} disabled={submittingTmpl || !tmplText.trim()}>
              {submittingTmpl ? '⏳ Отправляю в Meta...' : '🚀 Отправить на подтверждение'}
            </Btn>
          </Card>

          {/* Templates list */}
          <Card>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
              <div style={{ fontSize: 14, fontWeight: 600, color: '#D0D0D0' }}>📋 Мои шаблоны</div>
              <button onClick={syncTemplates} style={{
                fontSize: 12, color: GOLD, background: 'none', border: 'none', cursor: 'pointer',
              }}>🔄 Синхронизировать статусы</button>
            </div>
            {tmplLoading ? (
              <div style={{ color: MUTED, fontSize: 13 }}>Загрузка...</div>
            ) : templates.length === 0 ? (
              <div style={{ color: MUTED, fontSize: 13 }}>Шаблонов нет. Создайте первый выше.</div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                {templates.map((t: any) => (
                  <div key={t.id} style={{
                    display: 'flex', alignItems: 'flex-start', gap: 14, padding: '12px 16px',
                    borderRadius: 10, background: SURFACE2,
                  }}>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                        <code style={{ fontSize: 12, color: GOLD }}>{t.name}</code>
                        <span style={{
                          fontSize: 11, fontWeight: 600, padding: '2px 8px', borderRadius: 12,
                          background: `${tmplStatusColor(t.meta_status)}18`,
                          color: tmplStatusColor(t.meta_status),
                          border: `1px solid ${tmplStatusColor(t.meta_status)}30`,
                        }}>{t.meta_status}</span>
                        <span style={{ fontSize: 11, color: MUTED }}>{t.category} · {t.language}</span>
                      </div>
                      <div style={{ fontSize: 13, color: '#C0C0D0', lineHeight: 1.5 }}>{t.body_text}</div>
                      {Array.isArray(t.buttons) && t.buttons.length > 0 && (
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 8 }}>
                          {t.buttons.map((b: any, bi: number) => (
                            <span key={bi} style={{
                              padding: '3px 10px', borderRadius: 14, fontSize: 11, fontWeight: 600,
                              background: 'rgba(39,174,96,0.12)', color: '#27AE60',
                              border: '1px solid rgba(39,174,96,0.25)',
                            }}>
                              ⚡ {b.text}
                            </span>
                          ))}
                        </div>
                      )}
                      <div style={{ fontSize: 11, color: MUTED, marginTop: 6 }}>{t.created_at}</div>
                    </div>
                    <button
                      onClick={() => deleteTmplMutation.mutate(t.id)}
                      style={{ background: 'none', border: 'none', color: '#E74C3C', cursor: 'pointer', fontSize: 16, padding: 4 }}
                      title="Удалить"
                    >🗑</button>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </div>
      )}

      {tab === 'send' && <>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>

        {/* Compose */}
        <Card>
          <div style={{ fontSize: 14, fontWeight: 600, color: '#D0D0D0', marginBottom: 20 }}>📢 Новая рассылка</div>

          <div style={{ marginBottom: 16 }}>
            <Label>Сообщение</Label>
            <Input value={message} onChange={setMessage} rows={5} placeholder="Введите текст рассылки..." />
          </div>

          {result && (
            <div style={{
              marginBottom: 16, padding: '10px 14px', borderRadius: 8, fontSize: 13,
              background: result.error ? 'rgba(231,76,60,0.1)' : 'rgba(39,174,96,0.1)',
              border: `1px solid ${result.error ? 'rgba(231,76,60,0.3)' : 'rgba(39,174,96,0.3)'}`,
              color: result.error ? '#E74C3C' : '#27AE60',
            }}>
              {result.error
                ? `❌ ${result.error}`
                : `✅ Отправлено: ${result.sent}, ошибок: ${result.failed}`}
            </div>
          )}

          <Btn
            onClick={sendBroadcast}
            disabled={sending || !message.trim() || selectedPhones.size === 0}
          >
            {sending ? '⏳ Отправка...' : `📤 Отправить (${selectedPhones.size} чел.)`}
          </Btn>
        </Card>

        {/* Client picker */}
        <Card>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
            <div style={{ fontSize: 14, fontWeight: 600, color: '#D0D0D0' }}>
              👥 Клиенты ({clients.length})
            </div>
            <button
              onClick={toggleAll}
              style={{ fontSize: 12, color: GOLD, background: 'none', border: 'none', cursor: 'pointer' }}
            >
              {selectedPhones.size === clients.length ? 'Снять всё' : 'Выбрать всех'}
            </button>
          </div>
          {cLoading ? (
            <div style={{ color: MUTED, fontSize: 13 }}>Загрузка клиентов...</div>
          ) : (
            <div style={{ maxHeight: 280, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 6 }}>
              {clients.map((c: any) => {
                const sel = selectedPhones.has(c.phone);
                return (
                  <div
                    key={c.phone}
                    onClick={() => toggleClient(c.phone)}
                    style={{
                      display: 'flex', alignItems: 'center', gap: 10, padding: '8px 12px',
                      borderRadius: 8, cursor: 'pointer', transition: 'background 0.1s',
                      background: sel ? `${GOLD}10` : SURFACE2,
                      border: `1px solid ${sel ? GOLD + '40' : 'transparent'}`,
                    }}
                  >
                    <div style={{
                      width: 16, height: 16, borderRadius: 4, flexShrink: 0,
                      background: sel ? GOLD : SURFACE, border: `1.5px solid ${sel ? GOLD : BORDER}`,
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      fontSize: 10, color: '#0D0D12', fontWeight: 800,
                    }}>{sel ? '✓' : ''}</div>
                    <span style={{ fontSize: 13, color: '#F0F0F0' }}>{c.name}</span>
                    <span style={{ fontSize: 12, color: MUTED, marginLeft: 'auto' }}>{c.phone}</span>
                  </div>
                );
              })}
            </div>
          )}
        </Card>
      </div>

      {/* History */}
      <Card>
        <div style={{ fontSize: 14, fontWeight: 600, color: '#D0D0D0', marginBottom: 16 }}>📋 История рассылок</div>
        {broadcasts.length === 0 ? (
          <div style={{ color: MUTED, fontSize: 13 }}>Рассылок нет</div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {broadcasts.map((b: any) => (
              <div key={b.id} style={{
                display: 'flex', alignItems: 'center', gap: 16, padding: '12px 16px',
                borderRadius: 10, background: SURFACE2,
              }}>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{
                    fontSize: 13, color: '#F0F0F0', marginBottom: 4,
                    whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
                  }}>{b.message}</div>
                  <div style={{ fontSize: 11, color: MUTED }}>
                    {b.createdAt?.split('T')[0]} · Получателей: {b.recipientCount} · Отправлено: {b.sentCount} · Ошибок: {b.failedCount}
                  </div>
                </div>
                <span style={{
                  fontSize: 11, fontWeight: 600, padding: '3px 10px', borderRadius: 20,
                  background: `${statusColor(b.status)}18`, color: statusColor(b.status),
                  border: `1px solid ${statusColor(b.status)}30`, flexShrink: 0,
                }}>{b.status}</span>
                <button
                  onClick={() => delMutation.mutate(b.id)}
                  style={{ background: 'none', border: 'none', color: '#E74C3C', cursor: 'pointer', fontSize: 16, padding: 4 }}
                  title="Удалить"
                >🗑</button>
              </div>
            ))}
          </div>
        )}
      </Card>
      </>}
    </div>
  );
}
