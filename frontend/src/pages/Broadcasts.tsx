import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import {
  Box,
  Typography,
  Paper,
  TextField,
  Button,
  Alert,
  CircularProgress,
  List,
  ListItem,
  ListItemText,
  Divider,
} from '@mui/material';
import { api } from '../api/client';

export default function Broadcasts() {
  const [message, setMessage] = useState('');
  const [recipients, setRecipients] = useState('');
  const [success, setSuccess] = useState(false);

  const { data: broadcasts, isLoading } = useQuery({
    queryKey: ['broadcasts'],
    queryFn: api.getBroadcasts,
  });

  const mutation = useMutation({
    mutationFn: () => api.createBroadcast({
      message,
      recipients: recipients.split('\n').filter(Boolean),
    }),
    onSuccess: () => {
      setSuccess(true);
      setMessage('');
      setRecipients('');
      setTimeout(() => setSuccess(false), 3000);
    },
  });

  if (isLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom sx={{ fontWeight: 'bold' }}>
        Рассылки
      </Typography>

      {success && <Alert severity="success" sx={{ mb: 2 }}>Рассылка запущена!</Alert>}

      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          Новая рассылка
        </Typography>
        
        <TextField
          fullWidth
          multiline
          rows={4}
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          placeholder="Текст сообщения для рассылки..."
          sx={{ mb: 2 }}
        />

        <TextField
          fullWidth
          multiline
          rows={4}
          value={recipients}
          onChange={(e) => setRecipients(e.target.value)}
          placeholder="Номера телефонов (по одному на строку)&#10;+77771234567&#10;+77771234568"
          sx={{ mb: 2 }}
        />

        <Button
          variant="contained"
          onClick={() => mutation.mutate()}
          disabled={mutation.isPending || !message || !recipients}
        >
          {mutation.isPending ? 'Отправка...' : 'Отправить рассылку'}
        </Button>
      </Paper>

      <Paper sx={{ p: 2 }}>
        <Typography variant="h6" gutterBottom>
          История рассылок
        </Typography>
        
        <List>
          {broadcasts?.map((broadcast: any) => (
            <Box key={broadcast.id}>
              <ListItem>
                <ListItemText
                  primary={broadcast.message}
                  secondary={`${broadcast.recipients_count} получателей • ${broadcast.created_at}`}
                />
              </ListItem>
              <Divider />
            </Box>
          )) || (
            <ListItem>
              <ListItemText primary="Нет рассылок" />
            </ListItem>
          )}
        </List>
      </Paper>
    </Box>
  );
}