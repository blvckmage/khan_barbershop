import { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Tabs,
  Tab,
  List,
  ListItemButton,
  ListItemText,
  Chip,
  IconButton,
  Divider,
} from '@mui/material';
import { Refresh as RefreshIcon, Send as SendIcon } from '@mui/icons-material';
import { api } from '../api/client';

interface ChatLog {
  id: number;
  phone: string;
  message: string;
  response: string;
  intent: string;
  timestamp: string;
}

interface BackendLog {
  time: string;
  level: string;
  message: string;
}

export default function Logs() {
  const [tab, setTab] = useState(0);
  const [chatLogs, setChatLogs] = useState<ChatLog[]>([]);
  const [backendLogs, setBackendLogs] = useState<BackendLog[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedPhone, setSelectedPhone] = useState<string | null>(null);

  const fetchChatLogs = async () => {
    setLoading(true);
    try {
      const data = await api.getLogs(1, 100);
      setChatLogs(data.items || []);
    } catch (error) {
      console.error('Failed to fetch chat logs:', error);
    }
    setLoading(false);
  };

  const fetchBackendLogs = async () => {
    // Читаем логи из файла через API
    try {
      const response = await fetch('/api/admin/backend-logs', {
        headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
      });
      const data = await response.json();
      setBackendLogs(data.logs || []);
    } catch (error) {
      console.error('Failed to fetch backend logs:', error);
    }
  };

  useEffect(() => {
    if (tab === 0) {
      fetchChatLogs();
    } else {
      fetchBackendLogs();
    }
  }, [tab]);

  // Группируем чаты по телефону
  const groupedChats = chatLogs.reduce((acc, log) => {
    if (!acc[log.phone]) {
      acc[log.phone] = [];
    }
    acc[log.phone].push(log);
    return acc;
  }, {} as Record<string, ChatLog[]>);

  const getLevelColor = (level: string) => {
    switch (level.toUpperCase()) {
      case 'ERROR': return 'error';
      case 'WARNING': return 'warning';
      case 'INFO': return 'info';
      case 'DEBUG': return 'default';
      default: return 'default';
    }
  };

  return (
    <Box>
      <Paper sx={{ mb: 2 }}>
        <Tabs value={tab} onChange={(_, v) => setTab(v)}>
          <Tab label="Переписка" />
          <Tab label="Логи бэкенда" />
        </Tabs>
      </Paper>

      {tab === 0 && (
        <Box sx={{ display: 'flex', gap: 2, height: 'calc(100vh - 200px)' }}>
          {/* Список чатов */}
          <Paper sx={{ width: 300, overflow: 'auto' }}>
            <Box sx={{ p: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Typography variant="h6">Чаты</Typography>
              <IconButton onClick={fetchChatLogs} disabled={loading}>
                <RefreshIcon />
              </IconButton>
            </Box>
            <Divider />
            <List dense>
              {Object.entries(groupedChats).map(([phone, logs]) => (
                <ListItemButton
                  key={phone}
                  selected={selectedPhone === phone}
                  onClick={() => setSelectedPhone(phone)}
                >
                  <ListItemText
                    primary={phone}
                    secondary={`${logs.length} сообщений`}
                  />
                  <Chip
                    size="small"
                    label={logs[logs.length - 1].intent || 'chat'}
                  />
                </ListItemButton>
              ))}
            </List>
          </Paper>

          {/* Диалог */}
          <Paper sx={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
            {selectedPhone ? (
              <>
                <Box sx={{ p: 2, borderBottom: '1px solid #333' }}>
                  <Typography variant="h6">{selectedPhone}</Typography>
                </Box>
                <Box sx={{ flex: 1, overflow: 'auto', p: 2 }}>
                  {(groupedChats[selectedPhone] || []).map((log) => (
                    <Box key={log.id} sx={{ mb: 2 }}>
                      {/* Сообщение клиента */}
                      <Paper
                        sx={{
                          p: 2,
                          maxWidth: '70%',
                          bgcolor: 'primary.main',
                          borderRadius: '16px 16px 0 16px',
                          mb: 1,
                        }}
                      >
                        <Typography variant="body2" color="text.secondary">
                          {log.timestamp}
                        </Typography>
                        <Typography>{log.message}</Typography>
                      </Paper>
                      
                      {/* Ответ бота */}
                      <Paper
                        sx={{
                          p: 2,
                          maxWidth: '70%',
                          bgcolor: 'background.paper',
                          borderRadius: '16px 16px 16px 0',
                          ml: 'auto',
                        }}
                      >
                        <Typography variant="body2" color="text.secondary">
                          Bot • {log.intent}
                        </Typography>
                        <Typography>{log.response}</Typography>
                      </Paper>
                    </Box>
                  ))}
                </Box>
              </>
            ) : (
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%' }}>
                <Typography color="text.secondary">Выберите чат</Typography>
              </Box>
            )}
          </Paper>
        </Box>
      )}

      {tab === 1 && (
        <Paper sx={{ height: 'calc(100vh - 200px)', overflow: 'auto', bgcolor: '#0d1117' }}>
          <Box sx={{ p: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Typography variant="h6">Логи бэкенда</Typography>
            <IconButton onClick={fetchBackendLogs}>
              <RefreshIcon />
            </IconButton>
          </Box>
          <Divider />
          <Box sx={{ p: 2, fontFamily: 'monospace', fontSize: 12 }}>
            {backendLogs.map((log, i) => (
              <Box key={i} sx={{ mb: 0.5 }}>
                <Chip
                  size="small"
                  label={log.level}
                  color={getLevelColor(log.level) as 'error' | 'warning' | 'info' | 'default'}
                  sx={{ mr: 1, minWidth: 60 }}
                />
                <Typography component="span" color="text.secondary" sx={{ mr: 1 }}>
                  {log.time}
                </Typography>
                <Typography component="span" sx={{ color: log.level === 'ERROR' ? '#f44336' : '#e0e0e0' }}>
                  {log.message}
                </Typography>
              </Box>
            ))}
          </Box>
        </Paper>
      )}
    </Box>
  );
}