import { useQuery } from '@tanstack/react-query';
import {
  Box,
  Card,
  CardContent,
  Typography,
  CircularProgress,
  Paper,
  List,
  ListItem,
  ListItemText,
  Chip,
  LinearProgress,
} from '@mui/material';
import {
  CheckCircle as CheckCircleIcon,
} from '@mui/icons-material';
import { api } from '../api/client';

export default function Dashboard() {
  const { data: stats, isLoading } = useQuery({
    queryKey: ['stats'],
    queryFn: api.getStats,
  });

  if (isLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '400px' }}>
        <CircularProgress />
      </Box>
    );
  }

  const statCards = [
    {
      title: 'Записей сегодня',
      value: stats?.appointments_today || 0,
      icon: <CheckCircleIcon sx={{ fontSize: 32 }} />,
      color: '#4caf50',
      bgcolor: 'rgba(76, 175, 80, 0.1)',
    },
  ];

  return (
    <Box>
      <Typography variant="h4" sx={{ fontWeight: 'bold', mb: 3 }}>
        Панель управления
      </Typography>

      <Box
        sx={{
          display: 'grid',
          gridTemplateColumns: { xs: '1fr', sm: '1fr' },
          gap: 2,
          mb: 4,
        }}
      >
        {statCards.map((card, index) => (
          <Card key={index} sx={{ bgcolor: card.bgcolor, border: `2px solid ${card.color}` }}>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
                <Box>
                  <Typography color="text.secondary" variant="body2" sx={{ mb: 1 }}>
                    {card.title}
                  </Typography>
                  <Typography variant="h4" sx={{ fontWeight: 'bold', color: card.color }}>
                    {card.value}
                  </Typography>
                </Box>
                <Box sx={{ color: card.color, opacity: 0.7 }}>
                  {card.icon}
                </Box>
              </Box>
            </CardContent>
          </Card>
        ))}
      </Box>

      <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' }, gap: 3 }}>
        {/* Недавние записи */}
        <Paper sx={{ p: 3 }}>
          <Typography variant="h6" sx={{ fontWeight: 'bold', mb: 2 }}>
            Недавние записи
          </Typography>
          {stats?.recent_appointments && stats.recent_appointments.length > 0 ? (
            <List sx={{ p: 0 }}>
              {stats.recent_appointments.slice(0, 5).map((apt: any, index: number) => (
                <ListItem key={index} sx={{ py: 1, px: 0 }}>
                  <ListItemText
                    primary={apt.client_name || 'Неизвестный клиент'}
                    secondary={
                      <Box sx={{ display: 'flex', gap: 1, alignItems: 'center', mt: 0.5 }}>
                        <Chip label={apt.time || 'Время не указано'} size="small" variant="outlined" />
                        <Typography variant="caption" color="text.secondary">
                          {apt.service || 'Услуга не указана'}
                        </Typography>
                      </Box>
                    }
                  />
                </ListItem>
              ))}
            </List>
          ) : (
            <Typography color="text.secondary" variant="body2">
              Записей нет
            </Typography>
          )}
        </Paper>

        {/* Статистика чатов */}
        <Paper sx={{ p: 3 }}>
          <Typography variant="h6" sx={{ fontWeight: 'bold', mb: 2 }}>
            Активность чатов
          </Typography>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <Box>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                <Typography variant="body2">Обработано сообщений</Typography>
                <Typography variant="body2" sx={{ fontWeight: 'bold' }}>
                  {stats?.messages_processed || 0}
                </Typography>
              </Box>
              <LinearProgress
                variant="determinate"
                value={Math.min((stats?.messages_processed || 0) / (stats?.chats_today || 1), 100)}
              />
            </Box>

            <Box>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                <Typography variant="body2">Среднее время ответа</Typography>
                <Typography variant="body2" sx={{ fontWeight: 'bold' }}>
                  {stats?.avg_response_time ? `${stats.avg_response_time.toFixed(1)}s` : 'N/A'}
                </Typography>
              </Box>
            </Box>

            <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mt: 1 }}>
              <Chip
                label={`Успешных: ${stats?.successful_chats || 0}`}
                color="success"
                variant="outlined"
                size="small"
              />
              <Chip
                label={`Активных: ${stats?.active_chats || 0}`}
                color="info"
                variant="outlined"
                size="small"
              />
            </Box>
          </Box>
        </Paper>
      </Box>
    </Box>
  );
}
