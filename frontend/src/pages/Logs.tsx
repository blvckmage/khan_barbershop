import { useState, useEffect, useRef } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../api/client';

const SURFACE  = '#16161F';
const SURFACE2 = '#1E1E2A';
const SURFACE3 = '#22222E';
const BORDER   = 'rgba(255,255,255,0.07)';
const MUTED    = '#7A7A8C';
const GOLD     = '#C9A84C';

// ─── helpers ────────────────────────────────────────────────────────────────

function levelColor(level: string) {
  if (level.includes('ERROR') || level.includes('ERR')) return '#E74C3C';
  if (level.includes('WARN')) return '#F39C12';
  if (level.includes('DEBUG')) return '#7A7A8C';
  return '#27AE60';
}

function fmtPhone(p: string) {
  const d = p?.replace(/\D/g, '') ?? '';
  if (d.length === 11) return `+${d[0]} (${d.slice(1,4)}) ${d.slice(4,7)}-${d.slice(7,9)}-${d.slice(9)}`;
  return `+${d}`;
}

function fmtTime(ts: string) {
  if (!ts) return '';
  const d = new Date(ts.includes('T') ? ts : ts.replace(' ', 'T'));
  if (isNaN(d.getTime())) return ts;
  const now = new Date();
  const diffMs = now.getTime() - d.getTime();
  const diffDays = Math.floor(diffMs / 86400000);
  if (diffDays === 0) return d.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' });
  if (diffDays === 1) return 'вчера';
  if (diffDays < 7) return d.toLocaleDateString('ru-RU', { weekday: 'short' });
  return d.toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' });
}

function truncate(s: string, n = 52) {
  if (!s) return '';
  return s.length > n ? s.slice(0, n) + '…' : s;
}

// ─── types ──────────────────────────────────────────────────────────────────

interface LogEntry {
  phone: string;
  message: string;
  response: string;
  timestamp: string;
}

interface Conversation {
  phone: string;
  lastMessage: string;
  lastTime: string;
  count: number;
  messages: LogEntry[];
}

// ─── sub-components ──────────────────────────────────────────────────────────

function ContactRow({ conv, active, onClick }: {
  conv: Conversation; active: boolean; onClick: () => void;
}) {
  return (
    <div
      onClick={onClick}
      style={{
        padding: '12px 16px', cursor: 'pointer', transition: 'background 0.12s',
        background: active ? `${GOLD}12` : 'transparent',
        borderBottom: `1px solid ${BORDER}`,
        borderLeft: active ? `3px solid ${GOLD}` : '3px solid transparent',
      }}
      onMouseEnter={e => { if (!active) e.currentTarget.style.background = SURFACE2; }}
      onMouseLeave={e => { if (!active) e.currentTarget.style.background = 'transparent'; }}
    >
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10 }}>
        {/* Avatar */}
        <div style={{
          width: 38, height: 38, borderRadius: '50%', flexShrink: 0,
          background: active ? `${GOLD}22` : 'rgba(41,128,185,0.14)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 15, border: `1.5px solid ${active ? GOLD + '50' : 'transparent'}`,
        }}>👤</div>

        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 3 }}>
            <span style={{ fontSize: 13, fontWeight: 600, color: active ? GOLD : '#E8E8E8' }}>
              {fmtPhone(conv.phone)}
            </span>
            <span style={{ fontSize: 10, color: MUTED, flexShrink: 0 }}>{fmtTime(conv.lastTime)}</span>
          </div>
          <div style={{ fontSize: 12, color: MUTED, lineHeight: 1.4, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
            {truncate(conv.lastMessage, 40)}
          </div>
          <div style={{ marginTop: 4 }}>
            <span style={{
              fontSize: 10, fontWeight: 600, padding: '1px 6px', borderRadius: 8,
              background: `${MUTED}18`, color: MUTED,
            }}>{conv.count} сообщ.</span>
          </div>
        </div>
      </div>
    </div>
  );
}

function ChatBubble({ side, text, time }: { side: 'client' | 'bot'; text: string; time: string }) {
  const isBot = side === 'bot';
  return (
    <div style={{
      display: 'flex', flexDirection: 'column',
      alignItems: isBot ? 'flex-end' : 'flex-start',
      marginBottom: 10,
    }}>
      <div style={{ display: 'flex', alignItems: 'flex-end', gap: 6, flexDirection: isBot ? 'row-reverse' : 'row' }}>
        <div style={{
          width: 28, height: 28, borderRadius: '50%', flexShrink: 0,
          background: isBot ? `${GOLD}20` : 'rgba(41,128,185,0.15)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 12, marginBottom: 2,
        }}>{isBot ? '🤖' : '👤'}</div>
        <div style={{
          maxWidth: '72%', padding: '10px 14px', borderRadius: isBot ? '14px 4px 14px 14px' : '4px 14px 14px 14px',
          background: isBot ? `${GOLD}14` : 'rgba(41,128,185,0.12)',
          border: `1px solid ${isBot ? GOLD + '28' : 'rgba(41,128,185,0.25)'}`,
          fontSize: 13, color: '#E0E0E8', lineHeight: 1.55, wordBreak: 'break-word',
        }}>
          {text}
        </div>
      </div>
      <span style={{ fontSize: 10, color: MUTED, marginTop: 3, paddingLeft: isBot ? 0 : 34, paddingRight: isBot ? 34 : 0 }}>
        {fmtTime(time)}
      </span>
    </div>
  );
}

// ─── main component ──────────────────────────────────────────────────────────

export default function Logs() {
  const [tab, setTab] = useState<'chats' | 'backend'>('chats');
  const [search, setSearch] = useState('');
  const [selectedPhone, setSelectedPhone] = useState<string | null>(null);
  const [backendPage, setBackendPage] = useState(1);
  const [levelFilter, setLevelFilter] = useState<string>('ALL');
  const chatEndRef = useRef<HTMLDivElement>(null);

  // Load lots of chat logs (200) so we can group them client-side
  const { data: chatLogs, isLoading: chatLoading, dataUpdatedAt } = useQuery({
    queryKey: ['logs-all'],
    queryFn: () => api.getLogs(1, 200),
    refetchInterval: 30_000,
    enabled: tab === 'chats',
  });

  const { data: backendLogs, isLoading: backendLoading } = useQuery({
    queryKey: ['backend-logs', backendPage],
    queryFn: () => api.getBackendLogs(backendPage, 150),
    enabled: tab === 'backend',
    refetchInterval: 15_000,
  });

  // Group chat logs by phone
  const allItems: LogEntry[] = chatLogs?.items ?? [];

  const conversations: Conversation[] = (() => {
    const map = new Map<string, LogEntry[]>();
    for (const log of allItems) {
      const key = log.phone ?? 'unknown';
      if (!map.has(key)) map.set(key, []);
      map.get(key)!.push(log);
    }
    return Array.from(map.entries())
      .map(([phone, msgs]) => ({
        phone,
        messages: msgs,
        lastMessage: msgs[msgs.length - 1]?.message ?? '',
        lastTime: msgs[msgs.length - 1]?.timestamp ?? '',
        count: msgs.length,
      }))
      .sort((a, b) => (b.lastTime > a.lastTime ? 1 : -1));
  })();

  const filteredConversations = search
    ? conversations.filter(c =>
        c.phone.includes(search) ||
        c.messages.some(m =>
          m.message?.toLowerCase().includes(search.toLowerCase()) ||
          m.response?.toLowerCase().includes(search.toLowerCase())
        )
      )
    : conversations;

  const activeConv = selectedPhone
    ? conversations.find(c => c.phone === selectedPhone) ?? null
    : null;

  // Auto-select first conversation on load
  useEffect(() => {
    if (!selectedPhone && filteredConversations.length > 0) {
      setSelectedPhone(filteredConversations[0].phone);
    }
  }, [conversations.length]);

  // Scroll to bottom of chat when conversation changes
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [selectedPhone, dataUpdatedAt]);

  // Backend logs
  const backendItems: any[] = backendLogs?.logs ?? [];
  const filteredBackend = backendItems.filter(l => {
    const matchSearch = !search ||
      l.message?.toLowerCase().includes(search.toLowerCase()) ||
      l.level?.toLowerCase().includes(search.toLowerCase());
    const matchLevel = levelFilter === 'ALL' || (l.level ?? '').includes(levelFilter);
    return matchSearch && matchLevel;
  });

  const tabStyle = (active: boolean): React.CSSProperties => ({
    padding: '7px 18px', borderRadius: 8, cursor: 'pointer', fontSize: 13, fontWeight: 600,
    background: active ? `${GOLD}18` : 'transparent',
    color: active ? GOLD : MUTED,
    border: active ? `1px solid ${GOLD}30` : '1px solid transparent',
    transition: 'all 0.15s',
  });

  // ── Layout ──────────────────────────────────────────────────────────────────

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16, height: 'calc(100vh - 112px)' }}>

      {/* Top bar */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexShrink: 0, flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', gap: 6 }}>
          <button style={tabStyle(tab === 'chats')} onClick={() => setTab('chats')}>💬 Чаты WhatsApp</button>
          <button style={tabStyle(tab === 'backend')} onClick={() => setTab('backend')}>🖥 Логи сервера</button>
        </div>
        <div style={{ position: 'relative', flex: 1, minWidth: 180 }}>
          <span style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', fontSize: 13, color: MUTED }}>🔍</span>
          <input
            value={search}
            onChange={e => { setSearch(e.target.value); setSelectedPhone(null); }}
            placeholder={tab === 'chats' ? 'Поиск по номеру или тексту...' : 'Поиск в логах...'}
            style={{
              width: '100%', padding: '8px 12px 8px 34px', borderRadius: 8, fontSize: 13,
              background: SURFACE, border: `1px solid ${BORDER}`, color: '#F0F0F0', outline: 'none',
              boxSizing: 'border-box',
            }}
          />
        </div>
        {tab === 'chats' && (
          <span style={{ fontSize: 12, color: MUTED, flexShrink: 0 }}>
            {filteredConversations.length} диалог{filteredConversations.length !== 1 ? 'ов' : ''}
          </span>
        )}
        {tab === 'backend' && (
          <div style={{ display: 'flex', gap: 5 }}>
            {['ALL', 'INFO', 'WARN', 'ERROR', 'DEBUG'].map(lvl => (
              <button key={lvl} onClick={() => setLevelFilter(lvl)} style={{
                padding: '5px 10px', borderRadius: 6, fontSize: 11, fontWeight: 600, cursor: 'pointer',
                border: `1px solid ${levelFilter === lvl ? levelColor(lvl) + '60' : BORDER}`,
                background: levelFilter === lvl ? levelColor(lvl) + '18' : 'transparent',
                color: levelFilter === lvl ? levelColor(lvl) : MUTED,
              }}>{lvl}</button>
            ))}
          </div>
        )}
      </div>

      {/* ── CHATS TAB ─────────────────────────────────────────────────────── */}
      {tab === 'chats' && (
        <div style={{
          flex: 1, display: 'flex', borderRadius: 14, overflow: 'hidden',
          border: `1px solid ${BORDER}`, background: SURFACE, minHeight: 0,
        }}>

          {/* Left: contact list */}
          <div style={{
            width: 300, flexShrink: 0, borderRight: `1px solid ${BORDER}`,
            overflowY: 'auto', display: 'flex', flexDirection: 'column',
          }}>
            {/* Header */}
            <div style={{
              padding: '14px 16px', borderBottom: `1px solid ${BORDER}`, flexShrink: 0,
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            }}>
              <span style={{ fontSize: 13, fontWeight: 700, color: '#E0E0E8' }}>Диалоги</span>
              <span style={{ fontSize: 11, color: MUTED }}>
                {chatLoading ? '⏳' : `${filteredConversations.length}`}
              </span>
            </div>

            {chatLoading ? (
              <div style={{ padding: 32, textAlign: 'center', color: MUTED, fontSize: 13 }}>
                <div style={{ fontSize: 24, marginBottom: 8 }}>⏳</div>
                Загрузка диалогов...
              </div>
            ) : filteredConversations.length === 0 ? (
              <div style={{ padding: 32, textAlign: 'center', color: MUTED, fontSize: 13 }}>
                <div style={{ fontSize: 24, marginBottom: 8 }}>💬</div>
                Нет диалогов
              </div>
            ) : (
              filteredConversations.map(conv => (
                <ContactRow
                  key={conv.phone}
                  conv={conv}
                  active={selectedPhone === conv.phone}
                  onClick={() => setSelectedPhone(conv.phone)}
                />
              ))
            )}
          </div>

          {/* Right: chat view */}
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
            {!activeConv ? (
              <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: MUTED }}>
                <div style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: 40, marginBottom: 12 }}>💬</div>
                  <div style={{ fontSize: 14 }}>Выберите диалог</div>
                </div>
              </div>
            ) : (
              <>
                {/* Chat header */}
                <div style={{
                  padding: '14px 20px', borderBottom: `1px solid ${BORDER}`, flexShrink: 0,
                  display: 'flex', alignItems: 'center', gap: 12, background: SURFACE,
                }}>
                  <div style={{
                    width: 38, height: 38, borderRadius: '50%',
                    background: 'rgba(41,128,185,0.15)', display: 'flex',
                    alignItems: 'center', justifyContent: 'center', fontSize: 16,
                  }}>👤</div>
                  <div>
                    <div style={{ fontSize: 14, fontWeight: 700, color: '#F0F0F0' }}>
                      {fmtPhone(activeConv.phone)}
                    </div>
                    <div style={{ fontSize: 11, color: MUTED, marginTop: 1 }}>
                      {activeConv.count} сообщений · последнее {fmtTime(activeConv.lastTime)}
                    </div>
                  </div>
                </div>

                {/* Messages */}
                <div style={{
                  flex: 1, overflowY: 'auto', padding: '20px 24px',
                  display: 'flex', flexDirection: 'column',
                  background: SURFACE3,
                }}>
                  {/* Date separator for oldest message */}
                  {activeConv.messages.length > 0 && (
                    <div style={{ textAlign: 'center', marginBottom: 16 }}>
                      <span style={{
                        fontSize: 11, color: MUTED, background: SURFACE2,
                        padding: '3px 10px', borderRadius: 10,
                      }}>
                        {new Date(activeConv.messages[0].timestamp?.includes('T')
                          ? activeConv.messages[0].timestamp
                          : activeConv.messages[0].timestamp?.replace(' ', 'T') ?? '')
                          .toLocaleDateString('ru-RU', { day: 'numeric', month: 'long' })}
                      </span>
                    </div>
                  )}

                  {activeConv.messages.map((msg, i) => (
                    <div key={i}>
                      {/* Show date separator between days */}
                      {i > 0 && (() => {
                        const prev = activeConv.messages[i - 1].timestamp ?? '';
                        const curr = msg.timestamp ?? '';
                        const prevDay = prev.slice(0, 10);
                        const currDay = curr.slice(0, 10);
                        if (prevDay !== currDay) {
                          return (
                            <div style={{ textAlign: 'center', margin: '16px 0' }}>
                              <span style={{
                                fontSize: 11, color: MUTED, background: SURFACE2,
                                padding: '3px 10px', borderRadius: 10,
                              }}>
                                {new Date(currDay).toLocaleDateString('ru-RU', { day: 'numeric', month: 'long' })}
                              </span>
                            </div>
                          );
                        }
                        return null;
                      })()}

                      {msg.message && (
                        <ChatBubble side="client" text={msg.message} time={msg.timestamp} />
                      )}
                      {msg.response && (
                        <ChatBubble side="bot" text={msg.response} time={msg.timestamp} />
                      )}
                    </div>
                  ))}
                  <div ref={chatEndRef} />
                </div>
              </>
            )}
          </div>
        </div>
      )}

      {/* ── BACKEND LOGS TAB ─────────────────────────────────────────────── */}
      {tab === 'backend' && (
        <div style={{
          flex: 1, borderRadius: 14, overflow: 'hidden',
          border: `1px solid ${BORDER}`, background: SURFACE,
          display: 'flex', flexDirection: 'column', minHeight: 0,
        }}>
          <div style={{ flex: 1, overflowY: 'auto', fontFamily: 'ui-monospace, Consolas, monospace' }}>
            {backendLoading ? (
              <div style={{ padding: 40, textAlign: 'center', color: MUTED }}>Загрузка...</div>
            ) : filteredBackend.length === 0 ? (
              <div style={{ padding: 40, textAlign: 'center', color: MUTED }}>Логов нет</div>
            ) : (
              filteredBackend.map((log: any, i: number) => (
                <div key={i} style={{
                  padding: '4px 16px', display: 'flex', gap: 12, fontSize: 12, alignItems: 'flex-start',
                  borderBottom: `1px solid rgba(255,255,255,0.03)`,
                }}
                  onMouseEnter={e => (e.currentTarget.style.background = SURFACE2)}
                  onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
                >
                  <span style={{ color: MUTED, flexShrink: 0, width: 128, fontSize: 11 }}>{log.time}</span>
                  <span style={{
                    flexShrink: 0, width: 46, fontWeight: 700, fontSize: 11,
                    color: levelColor(log.level ?? ''),
                  }}>
                    {(log.level ?? 'INFO').replace('WARNING', 'WARN').replace('CRITICAL', 'CRIT').slice(0, 5)}
                  </span>
                  <span style={{ color: '#C0C0D0', wordBreak: 'break-all', lineHeight: 1.5 }}>{log.message}</span>
                </div>
              ))
            )}
          </div>

          {/* Pagination */}
          <div style={{
            padding: '10px 20px', borderTop: `1px solid ${BORDER}`,
            display: 'flex', gap: 10, alignItems: 'center', flexShrink: 0, background: SURFACE,
          }}>
            <button
              disabled={backendPage <= 1}
              onClick={() => setBackendPage(p => p - 1)}
              style={{
                padding: '5px 14px', borderRadius: 6, border: `1px solid ${BORDER}`,
                background: SURFACE2, color: backendPage <= 1 ? MUTED : '#F0F0F0',
                cursor: backendPage <= 1 ? 'not-allowed' : 'pointer', fontSize: 12,
              }}
            >← Назад</button>
            <span style={{ fontSize: 12, color: MUTED }}>Стр. {backendPage}</span>
            <button
              disabled={filteredBackend.length < 150}
              onClick={() => setBackendPage(p => p + 1)}
              style={{
                padding: '5px 14px', borderRadius: 6, border: `1px solid ${BORDER}`,
                background: SURFACE2, color: filteredBackend.length < 150 ? MUTED : '#F0F0F0',
                cursor: filteredBackend.length < 150 ? 'not-allowed' : 'pointer', fontSize: 12,
              }}
            >Вперёд →</button>
            <span style={{ fontSize: 11, color: MUTED, marginLeft: 'auto' }}>
              {filteredBackend.length} строк · авто-обновление 15с
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
