import { useState, useEffect, useMemo } from 'react';
import {
  Box,
  Paper,
  Typography,
  TextField,
  Button,
  Card,
  Switch,
  Divider,
  Autocomplete,
  Chip,
  Tabs,
  Tab,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  IconButton,
} from '@mui/material';
import {
  Save as SaveIcon,
  Settings as SettingsIcon,
  Delete as DeleteIcon,
} from '@mui/icons-material';
import { api } from '../api/client';

interface BroadcastConfig {
  enabled: boolean;
  phoneNumbers: string;
  messageTemplate: string;
  schedule: string;
  sendTime: string;
}

interface BroadcastClient {
  phone: string;
  name: string;
}

export default function BroadcastSettings() {
  const [tab, setTab] = useState(0);
  const [config, setConfig] = useState<BroadcastConfig>({
    enabled: false,
    phoneNumbers: '',
    messageTemplate: '',
    schedule: 'manual',
    sendTime: '10:00',
  });
  const [clients, setClients] = useState<BroadcastClient[]>([]);
  const [selectedClients, setSelectedClients] = useState<BroadcastClient[]>([]);
  const [clientsLoading, setClientsLoading] = useState(false);
  const [clientsError, setClientsError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const [loading, setLoading] = useState(false);
  const [sending, setSending] = useState(false);
  const [sendResult, setSendResult] = useState<string | null>(null);
  
  // New State for Scheduling and History
  const [scheduledAt, setScheduledAt] = useState('');
  const [broadcasts, setBroadcasts] = useState<any[]>([]);

  const recipientPhones = useMemo(() => {
    const manualPhones = config.phoneNumbers
      .split('\n')
      .map((p) => p.trim())
      .filter(Boolean);
    const clientPhones = selectedClients.map((client) => client.phone);
    return Array.from(new Set([...clientPhones, ...manualPhones]));
  }, [config.phoneNumbers, selectedClients]);

  useEffect(() => {
    const loadConfig = async () => {
      try {
        const data = await api.getBroadcastSettings();
        setConfig({
          enabled: data.enabled,
          phoneNumbers: data.phoneNumbers,
          messageTemplate: data.messageTemplate,
          schedule: data.schedule,
          sendTime: data.sendTime,
        });
      } catch (error) {
        console.error('Failed to load broadcast settings:', error);
      }
    };

    loadConfig();
  }, []);

  const loadClients = async () => {
    setClientsLoading(true);
    setClientsError(null);
    try {
      const data = await api.getBroadcastClients(30);
      setClients(data.items || []);
    } catch (error) {
      console.error('Failed to load broadcast clients:', error);
      setClientsError('Не удалось загрузить клиентов из Alteegio');
    } finally {
      setClientsLoading(false);
    }
  };

  const loadBroadcasts = async () => {
    try {
      const data = await api.getBroadcasts(1, 50);
      setBroadcasts(data.items || []);
    } catch (error) {
      console.error('Failed to load broadcasts:', error);
    }
  };

  useEffect(() => {
    if (tab === 1) {
      loadBroadcasts();
    }
  }, [tab]);

  const handleChange = (field: keyof BroadcastConfig, value: any) => {
    setConfig((prev) => ({
      ...prev,
      [field]: value,
    }));
    setSaved(false);
  };

  const handleSave = async () => {
    setLoading(true);
    try {
      await api.updateBroadcastSettings(config);
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (error) {
      console.error('Failed to save broadcast settings:', error);
      alert('Не удалось сохранить настройки рассылки');
    } finally {
      setLoading(false);
    }
  };

  const handleSendNow = async () => {
    const recipients = recipientPhones;

    if (!recipients.length) {
      alert('Добавьте хотя бы один телефон для рассылки.');
      return;
    }

    if (!config.messageTemplate.trim()) {
      alert('Введите текст сообщения для отправки.');
      return;
    }

    setSending(true);
    setSendResult(null);
    try {
      const payload: any = {
        message: config.messageTemplate,
        recipients,
      };
      
      if (scheduledAt) {
        payload.scheduled_at = new Date(scheduledAt).toISOString();
      }

      const result = await api.createBroadcast(payload);
      
      if (scheduledAt) {
        setSendResult(`Рассылка запланирована на ${new Date(scheduledAt).toLocaleString()}`);
        setScheduledAt('');
      } else {
        setSendResult(`Рассылка отправлена: ${result.sentCount} из ${result.recipientCount} сообщений.`);
      }
    } catch (error) {
      console.error('Failed to send broadcast:', error);
      setSendResult('Ошибка при отправке рассылки. Проверьте конфигурацию WhatsApp Cloud API и журнал.');
      alert('Не удалось отправить рассылку.');
    } finally {
      setSending(false);
    }
  };

  const handleDeleteBroadcast = async (id: number) => {
    if (!window.confirm('Отменить эту запланированную рассылку?')) return;
    try {
      await api.deleteBroadcast(id);
      loadBroadcasts();
    } catch (e) {
      alert('Ошибка при удалении рассылки');
    }
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 3 }}>
        <SettingsIcon sx={{ fontSize: 32 }} />
        <Typography variant="h4" sx={{ fontWeight: 'bold' }}>
          Настройки рассылки
        </Typography>
      </Box>

      <Paper sx={{ mb: 3 }}>
        <Tabs value={tab} onChange={(_, v) => setTab(v)} variant="fullWidth">
          <Tab label="Новая рассылка" />
          <Tab label="История и Запланированные" />
        </Tabs>
      </Paper>

      {tab === 0 && (
        <>
          <Paper sx={{ mb: 3, p: 2, bgcolor: 'info.light' }}>
            <Typography variant="body2" color="info.main">
              Здесь вы можете загрузить клиентов из базы Alteegio, выбрать получателей и отправить или запланировать рассылку.
            </Typography>
          </Paper>

          {saved && (
            <Paper sx={{ mb: 3, p: 2, bgcolor: 'success.light' }}>
              <Typography variant="body2" color="success.main">
                ✓ Настройки успешно сохранены
              </Typography>
            </Paper>
          )}

          <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '2fr 1fr' }, gap: 3 }}>
            <Paper sx={{ p: 3 }}>
              <Typography variant="h6" sx={{ fontWeight: 'bold', mb: 2 }}>
                Основные параметры
              </Typography>

              <Card sx={{ mb: 2, p: 2, bgcolor: 'rgba(2, 136, 209, 0.05)' }}>
                <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 1 }}>
                  <Switch
                    checked={config.enabled}
                    slotProps={{
                      input: {
                        onChange: (e) => handleChange('enabled', (e.target as HTMLInputElement).checked),
                      },
                    }}
                  />
                  <Box>
                    <Typography variant="subtitle2" sx={{ fontWeight: 'bold' }}>
                      Включить рассылку
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      Активирует автоматическую отправку
                    </Typography>
                  </Box>
                </Box>
              </Card>

              <Divider sx={{ my: 2 }} />

              <Typography variant="subtitle2" sx={{ fontWeight: 'bold', mb: 1 }}>
                Клиенты из Alteegio
              </Typography>
              <Box sx={{ mb: 2, display: 'flex', gap: 2, flexWrap: 'wrap' }}>
                <Button
                  variant="outlined"
                  onClick={loadClients}
                  disabled={clientsLoading}
                >
                  {clientsLoading ? 'Загрузка...' : 'Загрузить клиентов'}
                </Button>
                <Button
                  variant="outlined"
                  onClick={() => setSelectedClients(clients)}
                  disabled={!clients.length}
                >
                  Выбрать всех
                </Button>
              </Box>
              {clientsError && (
                <Typography color="error" variant="body2" sx={{ mb: 2 }}>
                  {clientsError}
                </Typography>
              )}
              <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 1 }}>
                Выбрано получателей: {recipientPhones.length}. Дубли автоматически удалены.
              </Typography>
              <Autocomplete
                multiple
                options={clients}
                getOptionLabel={(option) => `${option.name} ${option.phone}`}
                value={selectedClients}
                onChange={(_, value) => setSelectedClients(value)}
                disableCloseOnSelect
                renderInput={(params) => (
                  <TextField
                    {...params}
                    label="Выберите получателей"
                    placeholder="Найти клиента"
                    sx={{ mb: 2 }}
                  />
                )}
                renderOption={(props, option, { selected }) => (
                  <li {...props}>
                    <Chip
                      label={`${option.name} ${option.phone}`}
                      variant={selected ? 'filled' : 'outlined'}
                      color={selected ? 'primary' : 'default'}
                      sx={{ mr: 1 }}
                    />
                  </li>
                )}
              />

              <Divider sx={{ my: 2 }} />

              <Typography variant="subtitle2" sx={{ fontWeight: 'bold', mb: 1 }}>
                Номера телефонов для рассылки
              </Typography>
              <TextField
                fullWidth
                multiline
                rows={4}
                value={config.phoneNumbers}
                onChange={(e) => handleChange('phoneNumbers', e.target.value)}
                placeholder="Один номер на строку\nПример:\n+77001234567\n+77009876543"
                sx={{ mb: 2 }}
              />

              <Divider sx={{ my: 2 }} />

              <Typography variant="subtitle2" sx={{ fontWeight: 'bold', mb: 1 }}>
                Шаблон сообщения
              </Typography>
              <TextField
                fullWidth
                multiline
                rows={4}
                value={config.messageTemplate}
                onChange={(e) => handleChange('messageTemplate', e.target.value)}
                placeholder="Введите текст сообщения\n\nДоступные переменные:\n{name} - имя клиента"
                sx={{ mb: 2 }}
              />

              <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
                <Button
                  variant="contained"
                  color="primary"
                  startIcon={<SaveIcon />}
                  onClick={handleSave}
                  size="large"
                  disabled={loading}
                >
                  {loading ? 'Сохраняем...' : 'Сохранить настройки'}
                </Button>
                <Button
                  variant="outlined"
                  color="secondary"
                  onClick={handleSendNow}
                  size="large"
                  disabled={sending}
                >
                  {sending ? 'Отправляем...' : (scheduledAt ? 'Запланировать' : 'Отправить сейчас')}
                </Button>
              </Box>

              {sendResult && (
                <Paper sx={{ mt: 2, p: 2, bgcolor: 'info.light' }}>
                  <Typography variant="body2" color="text.secondary">
                    {sendResult}
                  </Typography>
                </Paper>
              )}
            </Paper>

            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              <Card sx={{ p: 2 }}>
                <Typography variant="subtitle2" sx={{ fontWeight: 'bold', mb: 2 }}>
                  Запланировать отправку
                </Typography>
                <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 2 }}>
                  Оставьте пустым, чтобы отправить мгновенно. Иначе рассылка уйдет в выбранное время.
                </Typography>
                <TextField
                  type="datetime-local"
                  fullWidth
                  value={scheduledAt}
                  onChange={(e) => setScheduledAt(e.target.value)}
                  size="small"
                  slotProps={{ inputLabel: { shrink: true } }}
                />
              </Card>

              <Card sx={{ p: 2, bgcolor: config.enabled ? 'success.light' : 'rgba(2, 136, 209, 0.05)' }}>
                <Typography variant="subtitle2" sx={{ fontWeight: 'bold', mb: 1 }}>
                  Статус системы (Авто-напоминания)
                </Typography>
                <Typography variant="body2" color={config.enabled ? 'success.main' : 'text.secondary'}>
                  {config.enabled ? '✓ Автоматические уведомления активны' : '○ Автоматические уведомления отключены'}
                </Typography>
              </Card>
            </Box>
          </Box>
        </>
      )}

      {tab === 1 && (
        <Paper sx={{ p: 3 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
            <Typography variant="h6" sx={{ fontWeight: 'bold' }}>
              История рассылок
            </Typography>
            <Button variant="outlined" onClick={loadBroadcasts}>
              Обновить
            </Button>
          </Box>
          <TableContainer>
            <Table size="small">
              <TableHead>
                <TableRow sx={{ bgcolor: 'rgba(0,0,0,0.02)' }}>
                  <TableCell>ID</TableCell>
                  <TableCell>Создано / Запланировано</TableCell>
                  <TableCell>Текст (начало)</TableCell>
                  <TableCell>Аудитория</TableCell>
                  <TableCell>Статус</TableCell>
                  <TableCell align="right">Действия</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {broadcasts.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={6} align="center" sx={{ py: 3, color: 'text.secondary' }}>
                      Нет данных о рассылках
                    </TableCell>
                  </TableRow>
                ) : (
                  broadcasts.map((row) => (
                    <TableRow key={row.id}>
                      <TableCell>{row.id}</TableCell>
                      <TableCell>
                        <Typography variant="body2">Создано: {new Date(row.created_at).toLocaleString()}</Typography>
                        {row.scheduled_at && (
                          <Typography variant="body2" color="primary">
                            План: {new Date(row.scheduled_at).toLocaleString()}
                          </Typography>
                        )}
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2" noWrap sx={{ maxWidth: 200 }}>
                          {row.message}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2">{row.recipients_count} получателей</Typography>
                        {(row.sent_count > 0 || row.failed_count > 0) && (
                          <Typography variant="caption" color="text.secondary">
                            Успешно: {row.sent_count}, Ошибок: {row.failed_count}
                          </Typography>
                        )}
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={row.status === 'scheduled' ? 'Запланировано' : row.status === 'sending' ? 'Отправляется' : row.status === 'completed' ? 'Завершено' : 'Ошибка'}
                          color={row.status === 'scheduled' ? 'warning' : row.status === 'sending' ? 'info' : row.status === 'completed' ? 'success' : 'error'}
                          size="small"
                        />
                      </TableCell>
                      <TableCell align="right">
                        {row.status === 'scheduled' && (
                          <IconButton onClick={() => handleDeleteBroadcast(row.id)} color="error" title="Отменить">
                            <DeleteIcon />
                          </IconButton>
                        )}
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </TableContainer>
        </Paper>
      )}
    </Box>
  );
}
