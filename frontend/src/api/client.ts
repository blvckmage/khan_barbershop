import axios from 'axios';
import { useAuthStore } from '../store/authStore';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const apiClient = axios.create({
  baseURL: `${API_BASE_URL}/api/admin`,
  headers: {
    'Content-Type': 'application/json',
  },
});

apiClient.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export const api = {
  // Auth
  login: async (username: string, password: string) => {
    const response = await apiClient.post('/login', { username, password });
    return response.data;
  },

  // Dashboard stats
  getStats: async () => {
    const response = await apiClient.get('/stats');
    return response.data;
  },

  // Appointments
  getAppointments: async () => {
    const response = await apiClient.get('/appointments');
    return response.data;
  },
  createAppointment: async (data: object) => {
    const response = await apiClient.post('/appointments', data);
    return response.data;
  },
  updateAppointment: async (id: number, data: object) => {
    const response = await apiClient.put(`/appointments/${id}`, data);
    return response.data;
  },
  deleteAppointment: async (id: number) => {
    const response = await apiClient.delete(`/appointments/${id}`);
    return response.data;
  },

  // Masters
  getMasters: async () => {
    const response = await apiClient.get('/masters');
    return response.data;
  },
  createMaster: async (data: object) => {
    const response = await apiClient.post('/masters', data);
    return response.data;
  },
  updateMaster: async (id: number, data: object) => {
    const response = await apiClient.put(`/masters/${id}`, data);
    return response.data;
  },
  deleteMaster: async (id: number) => {
    const response = await apiClient.delete(`/masters/${id}`);
    return response.data;
  },

  // Services
  getServices: async () => {
    const response = await apiClient.get('/services');
    return response.data;
  },
  createService: async (data: object) => {
    const response = await apiClient.post('/services', data);
    return response.data;
  },
  updateService: async (id: number, data: object) => {
    const response = await apiClient.put(`/services/${id}`, data);
    return response.data;
  },
  deleteService: async (id: number) => {
    const response = await apiClient.delete(`/services/${id}`);
    return response.data;
  },

  // Prompt
  getPrompt: async () => {
    const response = await apiClient.get('/prompt');
    return response.data;
  },
  updatePrompt: async (prompt: string) => {
    const response = await apiClient.put('/prompt', { prompt });
    return response.data;
  },

  // Logs
  getLogs: async (page = 1, limit = 50) => {
    const response = await apiClient.get(`/logs?page=${page}&limit=${limit}`);
    return response.data;
  },

  getBackendLogs: async (page = 1, limit = 100) => {
    try {
      const response = await apiClient.get(`/backend-logs?page=${page}&limit=${limit}`);
      return response.data;
    } catch (error) {
      return { logs: [], total: 0, page, limit };
    }
  },

  // Broadcasts
  getBroadcastClients: async (days = 30) => {
    const response = await apiClient.get(`/broadcast-clients?days=${days}`);
    return response.data;
  },
  getBroadcasts: async (page = 1, limit = 50) => {
    const response = await apiClient.get(`/broadcasts?page=${page}&limit=${limit}`);
    return response.data;
  },
  createBroadcast: async (data: { message: string; recipients: string[]; scheduled_at?: string }) => {
    const response = await apiClient.post('/broadcasts', data);
    return response.data;
  },
  deleteBroadcast: async (id: number) => {
    const response = await apiClient.delete(`/broadcasts/${id}`);
    return response.data;
  },
  getBroadcastSettings: async () => {
    const response = await apiClient.get('/broadcast-settings');
    return response.data;
  },
  updateBroadcastSettings: async (data: object) => {
    const response = await apiClient.put('/broadcast-settings', data);
    return response.data;
  },

  // Settings
  getSettings: async () => {
    const response = await apiClient.get('/settings');
    return response.data;
  },
  updateSettings: async (settings: object) => {
    const response = await apiClient.put('/settings', settings);
    return response.data;
  },

  // Bot settings (chatbot on/off + excluded masters)
  getBotSettings: async () => {
    const response = await apiClient.get('/bot-settings');
    return response.data;
  },
  updateBotSettings: async (data: { chatbot_enabled: boolean; excluded_master_ids: number[] }) => {
    const response = await apiClient.put('/bot-settings', data);
    return response.data;
  },

  // WABA Templates
  getWabaTemplates: async (sync = false) => {
    const response = await apiClient.get(`/waba-templates?sync=${sync}`);
    return response.data;
  },
  createWabaTemplate: async (data: { body_text: string; category?: string; language?: string }) => {
    const response = await apiClient.post('/waba-templates', data);
    return response.data;
  },
  deleteWabaTemplate: async (id: number) => {
    const response = await apiClient.delete(`/waba-templates/${id}`);
    return response.data;
  },
};
