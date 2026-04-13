import { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  TextField,
  Button,
  Card,
  Switch,
  Divider,
} from '@mui/material';
import {
  Save as SaveIcon,
  Settings as SettingsIcon,
} from '@mui/icons-material';
import { api } from '../api/client';

interface BroadcastConfig {
  enabled: boolean;
  phoneNumbers: string;
  messageTemplate: string;
  schedule: string;
  sendTime: string;
}

export default function BroadcastSettings() {
  const [config, setConfig] = useState<BroadcastConfig>({
    enabled: false,
    phoneNumbers: '',
    messageTemplate: '',
    schedule: 'manual',
    sendTime: '10:00',
  });

  const [saved, setSaved] = useState(false);
  const [loading, setLoading] = useState(false);
  const [sending, setSending] = useState(false);
  const [sendResult, setSendResult] = useState<string | null>(null);

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

  const handleChange = (field: keyof BroadcastConfig, value: any) => {
    setConfig(prev => ({
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
    const recipients = config.phoneNumbers
      .split('\n')
      .map((p) => p.trim())
      .filter(Boolean);

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
      const result = await api.createBroadcast({
        message: config.messageTemplate,
        recipients,
      });
      setSendResult(`Рассылка отправлена: ${result.sentCount} из ${result.recipientCount} сообщений.`);
    } catch (error) {
      console.error('Failed to send broadcast:', error);
      setSendResult('Ошибка при отправке рассылки.');
      alert('Не удалось отправить рассылку. Проверьте конфигурацию Twilio и журналы.');
    } finally {
      setSending(false);
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

      <Paper sx={{ mb: 3, p: 2, bgcolor: 'info.dark' }}>
        <Typography variant="body2" color="info.main">
          Здесь вы можете настроить параметры автоматической рассылки сообщений клиентам (функция в разработке)
        </Typography>
      </Paper>

      {saved && (
        <Paper sx={{ mb: 3, p: 2, bgcolor: 'success.dark' }}>
          <Typography variant="body2" color="success.main">
            ✓ Настройки успешно сохранены
          </Typography>
        </Paper>
      )}

      <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '2fr 1fr' }, gap: 3 }}>
        {/* Основные настройки */}
        <Paper sx={{ p: 3 }}>
          <Typography variant="h6" sx={{ fontWeight: 'bold', mb: 2 }}>
            Основные параметры
          </Typography>

          {/* Включение/отключение */}
          <Card sx={{ mb: 2, p: 2, bgcolor: 'action.hover' }}>
            <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 1 }}>
              <Switch 
                checked={config.enabled}
                slotProps={{
                  input: { 
                    onChange: (e) => handleChange('enabled', (e.target as HTMLInputElement).checked)
                  }
                }}
              />
              <Box>
                <Typography variant="subtitle2" sx={{ fontWeight: 'bold' }}>
                  Включить рассылку
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  Активирует автоматическую отправку сообщений
                </Typography>
              </Box>
            </Box>
          </Card>

          <Divider sx={{ my: 2 }} />

          {/* Номера для рассылки */}
          <Typography variant="subtitle2" sx={{ fontWeight: 'bold', mb: 1 }}>
            Номера телефонов для рассылки
          </Typography>
          <TextField
            fullWidth
            multiline
            rows={4}
            value={config.phoneNumbers}
            onChange={(e) => handleChange('phoneNumbers', e.target.value)}
            placeholder="Один номер на строку&#10;Пример:&#10;+77001234567&#10;+77009876543"
            sx={{ mb: 2 }}
          />

          <Divider sx={{ my: 2 }} />

          {/* Шаблон сообщения */}
          <Typography variant="subtitle2" sx={{ fontWeight: 'bold', mb: 1 }}>
            Шаблон сообщения
          </Typography>
          <TextField
            fullWidth
            multiline
            rows={4}
            value={config.messageTemplate}
            onChange={(e) => handleChange('messageTemplate', e.target.value)}
            placeholder="Введите текст сообщения&#10;&#10;Доступные переменные:&#10;{name} - имя клиента&#10;{date} - дата рассылки&#10;{time} - время рассылки"
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
              disabled={sending || !config.enabled || config.schedule !== 'manual'}
            >
              {sending ? 'Отправляем...' : 'Отправить сейчас'}
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

        {/* Дополнительные опции */}
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          {/* Расписание */}
          <Card sx={{ p: 2 }}>
            <Typography variant="subtitle2" sx={{ fontWeight: 'bold', mb: 2 }}>
              Расписание
            </Typography>

            <TextField
              select
              fullWidth
              value={config.schedule}
              onChange={(e) => handleChange('schedule', e.target.value)}
              size="small"
              slotProps={{ select: { native: true } }}
              sx={{ mb: 2 }}
            >
              <option value="manual">Ручная отправка</option>
              <option value="daily">Ежедневно</option>
              <option value="weekly">Еженедельно</option>
              <option value="monthly">Ежемесячно</option>
            </TextField>

            {config.schedule !== 'manual' && (
              <TextField
                type="time"
                value={config.sendTime}
                onChange={(e) => handleChange('sendTime', e.target.value)}
                size="small"
                fullWidth
                label="Время отправки"
              />
            )}
          </Card>

          {/* Статус */}
          <Card sx={{ p: 2, bgcolor: config.enabled ? 'success.dark' : 'action.hover' }}>
            <Typography variant="subtitle2" sx={{ fontWeight: 'bold', mb: 1 }}>
              Статус системы
            </Typography>
            <Typography variant="body2" color={config.enabled ? 'success.main' : 'text.secondary'}>
              {config.enabled ? '✓ Рассылка активирована' : '○ Рассылка отключена'}
            </Typography>
          </Card>

          {/* История */}
          <Card sx={{ p: 2 }}>
            <Typography variant="subtitle2" sx={{ fontWeight: 'bold', mb: 2 }}>
              История рассылок
            </Typography>
            <Typography variant="caption" color="text.secondary">
              Здесь будут отображаться все отправленные рассылки (в разработке)
            </Typography>
          </Card>
        </Box>
      </Box>

      {/* Предупреждение */}
      <Paper sx={{ p: 2, mt: 3, bgcolor: 'warning.dark' }}>
        <Typography variant="subtitle2" sx={{ fontWeight: 'bold', mb: 1 }}>
          ⚠️ Внимание
        </Typography>
        <Typography variant="caption" color="text.secondary">
          Убедитесь, что у вас есть согласие клиентов на получение рассылок. Отправка сообщений без согласия может привести к нарушению закона о защите персональных данных.
        </Typography>
      </Paper>
    </Box>
  );
}
