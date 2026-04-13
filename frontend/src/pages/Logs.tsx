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
  TextField,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  Select,
  MenuItem,
} from '@mui/material';
import {
  Refresh as RefreshIcon,
  Download as DownloadIcon,
  Close as CloseIcon,
} from '@mui/icons-material';
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
  const [backendTotal, setBackendTotal] = useState(0);
  const [backendPage, setBackendPage] = useState(1);
  const backendLimit = 100;
  const [loading, setLoading] = useState(false);
  const [selectedPhone, setSelectedPhone] = useState<string | null>(null);
  const [selectedLog, setSelectedLog] = useState<ChatLog | null>(null);
  const [openDialog, setOpenDialog] = useState(false);
  const [filterLevel, setFilterLevel] = useState<string>('');
  const [filterPhone, setFilterPhone] = useState<string>('');

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

  const fetchBackendLogs = async (page = 1) => {
    try {
      const data = await api.getBackendLogs(page, backendLimit);
      const logs = Array.isArray(data.logs) ? data.logs : [];
      setBackendLogs(logs);
      setBackendTotal(data.total || 0);
      setBackendPage(data.page || 1);
    } catch (error) {
      console.error('Failed to fetch backend logs:', error);
    }
  };

  useEffect(() => {
    if (tab === 0) {
      fetchChatLogs();
    } else {
      fetchBackendLogs(backendPage);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab, backendPage]);

  const handleViewLog = (log: ChatLog) => {
    setSelectedLog(log);
    setOpenDialog(true);
  };

  const handleDownloadLogs = () => {
    const content = tab === 0
      ? JSON.stringify(chatLogs, null, 2)
      : backendLogs.map((l) => `[${l.time}] ${l.level}: ${l.message}`).join('\n');

    const element = document.createElement('a');
    element.setAttribute('href', 'data:text/plain;charset=utf-8,' + encodeURIComponent(content));
    element.setAttribute('download', `logs-${new Date().toISOString().slice(0, 10)}.txt`);
    element.style.display = 'none';
    document.body.appendChild(element);
    element.click();
    document.body.removeChild(element);
  };

  const filteredBackendLogs = backendLogs.filter((log) => {
    if (filterLevel && log.level.toUpperCase() !== filterLevel.toUpperCase()) return false;
    return true;
  });

  const filteredChatLogs = chatLogs.filter((log) => {
    if (filterPhone && !log.phone.includes(filterPhone)) return false;
    return true;
  });

  const groupedChats = filteredChatLogs.reduce((acc, log) => {
    if (!acc[log.phone]) {
      acc[log.phone] = [];
    }
    acc[log.phone].push(log);
    return acc;
  }, {} as Record<string, ChatLog[]>);

  const sortedPhones = Object.keys(groupedChats).sort((phoneA, phoneB) => {
    const logsA = groupedChats[phoneA];
    const logsB = groupedChats[phoneB];
    const lastTimeA = logsA.length ? new Date(logsA[logsA.length - 1].timestamp).getTime() : 0;
    const lastTimeB = logsB.length ? new Date(logsB[logsB.length - 1].timestamp).getTime() : 0;
    return lastTimeB - lastTimeA;
  });

  const sortedGroupedChats = sortedPhones.reduce((acc, phone) => {
    acc[phone] = groupedChats[phone]
      .slice()
      .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
      .reverse();
    return acc;
  }, {} as Record<string, ChatLog[]>);

  const getLevelColor = (level: string): any => {
    switch (level.toUpperCase()) {
      case 'ERROR':
        return 'error';
      case 'WARNING':
        return 'warning';
      case 'INFO':
        return 'info';
      case 'DEBUG':
        return 'default';
      default:
        return 'default';
    }
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" sx={{ fontWeight: 'bold' }}>
          {tab === 0 ? 'Логи переписки' : 'Логи бэкенда'}
        </Typography>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Button
            variant="outlined"
            startIcon={<RefreshIcon />}
            onClick={() => (tab === 0 ? fetchChatLogs() : fetchBackendLogs(backendPage))}
            disabled={loading}
          >
            Обновить
          </Button>
          <Button variant="contained" startIcon={<DownloadIcon />} onClick={handleDownloadLogs}>
            Скачать
          </Button>
        </Box>
      </Box>

      <Paper sx={{ mb: 2 }}>
        <Tabs value={tab} onChange={(_, v) => setTab(v)}>
          <Tab label="Переписка" />
          <Tab label="Логи бэкенда" />
        </Tabs>
      </Paper>

      {tab === 0 && (
        <Box>
          <Paper sx={{ p: 2, mb: 2 }}>
            <TextField
              placeholder="Поиск по номеру телефона..."
              value={filterPhone}
              onChange={(e) => setFilterPhone(e.target.value)}
              fullWidth
              size="small"
            />
          </Paper>

          <Paper sx={{ display: 'flex', height: '600px' }}>
            <Box sx={{ width: '35%', borderRight: 1, borderColor: 'divider', overflowY: 'auto' }}>
              <List sx={{ p: 0 }}>
                {sortedPhones.map((phone) => {
                  const logs = sortedGroupedChats[phone] || [];
                  return (
                    <Box key={phone}>
                      <ListItemButton selected={selectedPhone === phone} onClick={() => setSelectedPhone(phone)}>
                        <ListItemText primary={phone} secondary={`${logs.length} сообщений`} />
                      </ListItemButton>
                      <Divider />
                    </Box>
                  );
                })}
              </List>
            </Box>

            <Box sx={{ width: '65%', p: 2, overflowY: 'auto' }}>
              {selectedPhone ? (
                <Box>
                  <Typography variant="h6" sx={{ mb: 2, fontWeight: 'bold' }}>
                    {selectedPhone}
                  </Typography>
                  <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                    {sortedGroupedChats[selectedPhone]?.map((log, i) => (
                      <Box key={i}>
                        <Chip
                          size="small"
                          label={new Date(log.timestamp).toLocaleTimeString('ru-RU')}
                          variant="outlined"
                          sx={{ mb: 1 }}
                        />
                        <Paper sx={{ p: 2, mb: 1, bgcolor: 'action.hover' }}>
                          <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 1 }}>
                            Сообщение клиента:
                          </Typography>
                          <Typography variant="body2" sx={{ mb: 2 }}>
                            {log.message}
                          </Typography>
                          <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 1 }}>
                            Ответ:
                          </Typography>
                          <Typography variant="body2" sx={{ mb: 2, fontStyle: 'italic' }}>
                            {log.response}
                          </Typography>
                          <Box sx={{ display: 'flex', gap: 1 }}>
                            <Button size="small" onClick={() => handleViewLog(log)}>
                              Подробнее
                            </Button>
                          </Box>
                        </Paper>
                      </Box>
                    ))}
                  </Box>
                </Box>
              ) : (
                <Typography color="text.secondary" sx={{ textAlign: 'center', mt: 3 }}>
                  Выберите чат для просмотра сообщений
                </Typography>
              )}
            </Box>
          </Paper>
        </Box>
      )}

      {tab === 1 && (
        <Box>
          <Paper sx={{ p: 2, mb: 2 }}>
            <Box sx={{ display: 'flex', gap: 2 }}>
              <Select
                value={filterLevel}
                onChange={(e) => setFilterLevel(e.target.value as string)}
                size="small"
                displayEmpty
                sx={{ minWidth: 200 }}
              >
                <MenuItem value="">Все уровни</MenuItem>
                <MenuItem value="ERROR">ERROR</MenuItem>
                <MenuItem value="WARNING">WARNING</MenuItem>
                <MenuItem value="INFO">INFO</MenuItem>
                <MenuItem value="DEBUG">DEBUG</MenuItem>
              </Select>
            </Box>
          </Paper>

          <Paper>
            <List sx={{ maxHeight: '600px', overflowY: 'auto' }}>
              {filteredBackendLogs.map((log, i) => (
                <Box key={i}>
                  <ListItemButton>
                    <ListItemText
                      primary={log.message}
                      secondary={
                        <Box sx={{ display: 'flex', gap: 1, alignItems: 'center', mt: 1 }}>
                          <Typography variant="caption" color="text.secondary">
                            {log.time}
                          </Typography>
                          <Chip size="small" label={log.level} color={getLevelColor(log.level)} variant="outlined" />
                        </Box>
                      }
                    />
                  </ListItemButton>
                  <Divider />
                </Box>
              ))}
            </List>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', p: 2 }}>
              <Button
                variant="outlined"
                disabled={backendPage <= 1}
                onClick={() => setBackendPage((p) => Math.max(1, p - 1))}
              >
                Предыдущая
              </Button>
              <Typography variant="body2">
                Страница {backendPage} из {Math.max(1, Math.ceil(backendTotal / backendLimit))}
              </Typography>
              <Button
                variant="outlined"
                disabled={backendPage >= Math.ceil(backendTotal / backendLimit)}
                onClick={() => setBackendPage((p) => p + 1)}
              >
                Следующая
              </Button>
            </Box>
          </Paper>
        </Box>
      )}

      <Dialog open={openDialog} onClose={() => setOpenDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          Детали логирования
          <IconButton onClick={() => setOpenDialog(false)}>
            <CloseIcon />
          </IconButton>
        </DialogTitle>
        <DialogContent sx={{ pt: 2 }}>
          {selectedLog && (
            <Box>
              <Typography variant="subtitle2" sx={{ fontWeight: 'bold', mb: 1 }}>
                Номер клиента:
              </Typography>
              <Typography variant="body2" sx={{ mb: 2 }}>
                {selectedLog.phone}
              </Typography>

              <Typography variant="subtitle2" sx={{ fontWeight: 'bold', mb: 1 }}>
                Время:
              </Typography>
              <Typography variant="body2" sx={{ mb: 2 }}>
                {new Date(selectedLog.timestamp).toLocaleString('ru-RU')}
              </Typography>

              <Typography variant="subtitle2" sx={{ fontWeight: 'bold', mb: 1 }}>
                Сообщение клиента:
              </Typography>
              <Typography variant="body2" sx={{ mb: 2, p: 1, bgcolor: 'action.hover', borderRadius: 1 }}>
                {selectedLog.message}
              </Typography>

              <Typography variant="subtitle2" sx={{ fontWeight: 'bold', mb: 1 }}>
                Ответ бота:
              </Typography>
              <Typography variant="body2" sx={{ mb: 2, p: 1, bgcolor: 'action.hover', borderRadius: 1 }}>
                {selectedLog.response}
              </Typography>

              <Typography variant="subtitle2" sx={{ fontWeight: 'bold', mb: 1 }}>
                Распознанное намерение (Intent):
              </Typography>
              <Chip label={selectedLog.intent} color="primary" />
            </Box>
          )}
        </DialogContent>
      </Dialog>
    </Box>
  );
}