import { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  TextField,
  Button,
  Card,
  CardContent,
  Chip,
  LinearProgress,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Autocomplete,
} from '@mui/material';
import {
  Send as SendIcon,
  Delete as DeleteIcon,
  Schedule as ScheduleIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  Pending as PendingIcon,
} from '@mui/icons-material';
import { api } from '../api/client';

interface ClientItem {
  phone: string;
  name: string;
}

interface Broadcast {
  id: number;
  message: string;
  recipientCount: number;
  sentCount: number;
  failedCount: number;
  status: 'pending' | 'sending' | 'completed' | 'failed';
  createdAt: string;
  completedAt?: string;
}

export default function Broadcasts() {
  const [message, setMessage] = useState('');
  const [phones, setPhones] = useState('');
  const [availableClients, setAvailableClients] = useState<ClientItem[]>([]);
  const [selectedClients, setSelectedClients] = useState<ClientItem[]>([]);
  const [clientLoading, setClientLoading] = useState(false);
  const [broadcasts, setBroadcasts] = useState<Broadcast[]>([]);
  const [selectedBroadcast, setSelectedBroadcast] = useState<Broadcast | null>(null);
  const [loading, setLoading] = useState(false);
  const [openDialog, setOpenDialog] = useState(false);

  const fetchBroadcastClients = async (days = 30) => {
    setClientLoading(true);
    try {
      const data = await api.getBroadcastClients(days);
      setAvailableClients(Array.isArray(data.items) ? data.items : []);
    } catch (error) {
      console.error('Failed to fetch broadcast clients:', error);
      alert('Не удалось загрузить клиентов из Alteegio. Проверьте настройки API.');
    } finally {
      setClientLoading(false);
    }
  };

  const normalizePhone = (phone: string) => {
    const cleaned = phone.trim().replace(/[^0-9+]/g, '');
    if (!cleaned) {
      return '';
    }
    if (cleaned.startsWith('whatsapp:')) {
      return cleaned.replace('whatsapp:', '');
    }
    if (cleaned.startsWith('+')) {
      return cleaned;
    }
    if (cleaned.length === 11 && cleaned.startsWith('8')) {
      return `+7${cleaned.slice(1)}`;
    }
    if (cleaned.length === 10) {
      return `+7${cleaned}`;
    }
    return cleaned;
  };

  const fetchBroadcasts = async () => {
    try {
      const data = await api.getBroadcasts(1, 50);
      setBroadcasts(Array.isArray(data) ? data : data.items || []);
    } catch (error) {
      console.error('Failed to fetch broadcasts:', error);
    }
  };

  useEffect(() => {
    fetchBroadcasts();
  }, []);

  const handleSendBroadcast = async () => {
    if (!message.trim()) {
      alert('Заполните текст сообщения.');
      return;
    }

    const manualPhones = phones
      .split('\n')
      .map((p) => normalizePhone(p))
      .filter(Boolean);

    const selectedPhones = selectedClients.map((client) => normalizePhone(client.phone));
    const recipients = Array.from(new Set([...selectedPhones, ...manualPhones]));

    if (!recipients.length) {
      alert('Добавьте хотя бы один номер телефона через выбор клиентов или вручную.');
      return;
    }

    setLoading(true);
    try {
      await api.createBroadcast({
        message,
        recipients,
      });

      setMessage('');
      setPhones('');
      setSelectedClients([]);
      await fetchBroadcasts();
    } catch (error) {
      console.error('Failed to send broadcast:', error);
      alert('Ошибка при отправке рассылки');
    }
    setLoading(false);
  };

  const handleClearForm = () => {
    setMessage('');
    setPhones('');
    setSelectedClients([]);
  };

  const handleDeleteBroadcast = async (id: number) => {
    if (window.confirm('Удалить эту рассылку?')) {
      try {
        await api.deleteBroadcast(id);
        await fetchBroadcasts();
      } catch (error) {
        console.error('Failed to delete broadcast:', error);
      }
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircleIcon sx={{ color: 'success.main' }} />;
      case 'failed':
        return <ErrorIcon sx={{ color: 'error.main' }} />;
      case 'sending':
        return <PendingIcon sx={{ color: 'warning.main' }} />;
      default:
        return <ScheduleIcon sx={{ color: 'info.main' }} />;
    }
  };

  const getStatusColor = (status: string): any => {
    switch (status) {
      case 'completed':
        return 'success';
      case 'failed':
        return 'error';
      case 'sending':
        return 'warning';
      default:
        return 'info';
    }
  };

  const getStatusLabel = (status: string) => {
    const labels: Record<string, string> = {
      pending: 'Ожидание',
      sending: 'Отправляется',
      completed: 'Завершено',
      failed: 'Ошибка',
    };
    return labels[status] || status;
  };

  const handleOpenDialog = (broadcast: Broadcast) => {
    setSelectedBroadcast(broadcast);
    setOpenDialog(true);
  };

  return (
    <Box>
      <Typography variant="h4" sx={{ fontWeight: 'bold', mb: 3 }}>
        Рассылка сообщений
      </Typography>

      <Paper sx={{ p: 3, mb: 4 }}>
        <Typography variant="h6" sx={{ fontWeight: 'bold', mb: 2 }}>
          Создать новую рассылку
        </Typography>

        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          <TextField
            label="Текст сообщения"
            multiline
            rows={4}
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder="Введите текст сообщения..."
            fullWidth
          />

          <Autocomplete
            multiple
            options={availableClients}
            getOptionLabel={(option) => `${option.name} (${option.phone})`}
            value={selectedClients}
            onChange={(event, newValue) => {
              setSelectedClients(newValue);
            }}
            loading={clientLoading}
            renderInput={(params) => (
              <TextField
                {...params}
                label="Выбор клиентов"
                placeholder="Начните вводить имя или номер телефона"
                fullWidth
              />
            )}
            renderOption={(props, option) => (
              <li {...props}>
                <Typography variant="body2">{option.name}</Typography>
                <Typography variant="caption" color="text.secondary">
                  {option.phone}
                </Typography>
              </li>
            )}
            sx={{ mb: 2 }}
          />

          <TextField
            label="Номера телефонов (вручную)"
            multiline
            rows={5}
            value={phones}
            onChange={(e) => setPhones(e.target.value)}
            placeholder="Один номер на строку&#10;Пример:&#10;+77001234567&#10;+77009876543"
            fullWidth
          />

          <Box sx={{ display: 'flex', gap: 2, justifyContent: 'flex-end' }}>
            <Button
              variant="outlined"
              color="inherit"
              onClick={handleClearForm}
              disabled={loading}
            >
              Очистить
            </Button>
            <Button
              variant="contained"
              color="primary"
              startIcon={<SendIcon />}
              onClick={handleSendBroadcast}
              disabled={loading}
            >
              {loading ? 'Отправка...' : 'Отправить'}
            </Button>
          </Box>
        </Box>
      </Paper>

      <Typography variant="h6" sx={{ fontWeight: 'bold', mb: 2 }}>
        История рассылок
      </Typography>

      {broadcasts.length === 0 ? (
        <Paper sx={{ p: 3, textAlign: 'center' }}>
          <Typography color="text.secondary">
            Рассылок еще нет. Создайте новую рассылку выше.
          </Typography>
        </Paper>
      ) : (
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          {broadcasts.map((broadcast) => (
            <Card key={broadcast.id}>
              <CardContent>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', mb: 2 }}>
                  <Box sx={{ flex: 1 }}>
                    <Box sx={{ display: 'flex', gap: 1, alignItems: 'center', mb: 1 }}>
                      {getStatusIcon(broadcast.status)}
                      <Chip
                        label={getStatusLabel(broadcast.status)}
                        color={getStatusColor(broadcast.status)}
                        size="small"
                      />
                      <Typography variant="caption" color="text.secondary">
                        {new Date(broadcast.createdAt).toLocaleString('ru-RU')}
                      </Typography>
                    </Box>
                    <Typography variant="body2" sx={{ mb: 2, whiteSpace: 'pre-wrap' }}>
                      {broadcast.message}
                    </Typography>
                  </Box>
                  <Button
                    size="small"
                    color="error"
                    startIcon={<DeleteIcon />}
                    onClick={() => handleDeleteBroadcast(broadcast.id)}
                  >
                    Удалить
                  </Button>
                </Box>
                <Button size="small" onClick={() => handleOpenDialog(broadcast)}>
                  Подробнее
                </Button>

                {broadcast.status === 'sending' && (
                  <Box sx={{ mb: 2 }}>
                    <LinearProgress
                      variant="determinate"
                      value={(broadcast.sentCount / broadcast.recipientCount) * 100}
                      sx={{ mb: 1 }}
                    />
                    <Typography variant="caption" color="text.secondary">
                      Отправлено: {broadcast.sentCount} из {broadcast.recipientCount}
                    </Typography>
                  </Box>
                )}

                <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
                  <Chip
                    label={`Получателей: ${broadcast.recipientCount}`}
                    size="small"
                    variant="outlined"
                  />
                  <Chip
                    label={`Отправлено: ${broadcast.sentCount}`}
                    size="small"
                    variant="outlined"
                    color="success"
                  />
                  {broadcast.failedCount > 0 && (
                    <Chip
                      label={`Ошибок: ${broadcast.failedCount}`}
                      size="small"
                      variant="outlined"
                      color="error"
                    />
                  )}
                  {broadcast.completedAt && (
                    <Typography variant="caption" color="text.secondary">
                      Завершено: {new Date(broadcast.completedAt).toLocaleString('ru-RU')}
                    </Typography>
                  )}
                </Box>
              </CardContent>
            </Card>
          ))}
        </Box>
      )}

      <Dialog open={openDialog} onClose={() => setOpenDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Детали рассылки</DialogTitle>
        <DialogContent sx={{ pt: 2 }}>
          {selectedBroadcast ? (
            <Box sx={{ display: 'grid', gap: 1 }}>
              <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap', mb: 2 }}>
                {selectedBroadcast.message}
              </Typography>
              <Typography variant="body2">Статус: {getStatusLabel(selectedBroadcast.status)}</Typography>
              <Typography variant="body2">Получателей: {selectedBroadcast.recipientCount}</Typography>
              <Typography variant="body2">Отправлено: {selectedBroadcast.sentCount}</Typography>
              <Typography variant="body2">Ошибок: {selectedBroadcast.failedCount}</Typography>
              {selectedBroadcast.completedAt && (
                <Typography variant="body2">Завершено: {new Date(selectedBroadcast.completedAt).toLocaleString('ru-RU')}</Typography>
              )}
            </Box>
          ) : (
            <Typography variant="body2" color="text.secondary">
              Выберите рассылку для просмотра подробностей
            </Typography>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenDialog(false)}>Закрыть</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
