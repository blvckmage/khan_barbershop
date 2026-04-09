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
  Stack,
} from '@mui/material';
import { api } from '../api/client';

export default function Dashboard() {
  const { data: stats, isLoading } = useQuery({
    queryKey: ['stats'],
    queryFn: api.getStats,
  });

  if (isLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  const statCards = [
    { title: 'Записей сегодня', value: stats?.todayAppointments || 0, color: '#4caf50' },
    { title: 'Диалогов сегодня', value: stats?.todayChats || 0, color: '#2196f3' },
    { title: 'Всего клиентов', value: stats?.totalClients || 0, color: '#ff9800' },
    { title: 'Рейтинг бота', value: stats?.rating || '4.9', color: '#9c27b0' },
  ];

  return (
    <Box>
      <Typography variant="h4" gutterBottom sx={{ fontWeight: 'bold' }}>
        Панель управления
      </Typography>

      <Stack direction={{ xs: 'column', sm: 'row' }} spacing={3} sx={{ mb: 4, flexWrap: 'wrap' }}>
        {statCards.map((stat) => (
          <Card key={stat.title} sx={{ bgcolor: 'background.paper', minWidth: 200, flex: 1 }}>
            <CardContent>
              <Typography color="text.secondary" variant="body2">
                {stat.title}
              </Typography>
              <Typography variant="h3" sx={{ color: stat.color, fontWeight: 'bold' }}>
                {stat.value}
              </Typography>
            </CardContent>
          </Card>
        ))}
      </Stack>

      <Stack direction={{ xs: 'column', md: 'row' }} spacing={3}>
        <Paper sx={{ p: 2, flex: 1 }}>
          <Typography variant="h6" gutterBottom>
            Последние записи
          </Typography>
          <List>
            {stats?.recentAppointments?.map((apt: any, i: number) => (
              <ListItem key={i} divider>
                <ListItemText
                  primary={`${apt.time} - ${apt.master}`}
                  secondary={apt.client}
                />
                <Chip label={apt.service} size="small" />
              </ListItem>
            )) || (
              <ListItem>
                <ListItemText primary="Нет записей за сегодня" />
              </ListItem>
            )}
          </List>
        </Paper>

        <Paper sx={{ p: 2, flex: 1 }}>
          <Typography variant="h6" gutterBottom>
            Последние диалоги
          </Typography>
          <List>
            {stats?.recentChats?.map((chat: any, i: number) => (
              <ListItem key={i} divider>
                <ListItemText
                  primary={chat.phone}
                  secondary={chat.lastMessage}
                />
                <Typography variant="caption" color="text.secondary">
                  {chat.time}
                </Typography>
              </ListItem>
            )) || (
              <ListItem>
                <ListItemText primary="Нет диалогов за сегодня" />
              </ListItem>
            )}
          </List>
        </Paper>
      </Stack>
    </Box>
  );
}