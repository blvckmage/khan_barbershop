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

  // Masters
  getMasters: async () => {
    const response = await apiClient.get('/masters');
    return response.data;
  },
  updateMaster: async (id: number, data: object) => {
    const response = await apiClient.put(`/masters/${id}`, data);
    return response.data;
  },

  // Services
  getServices: async () => {
    const response = await apiClient.get('/services');
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

  // Broadcasts
  getBroadcasts: async () => {
    const response = await apiClient.get('/broadcasts');
    return response.data;
  },
  createBroadcast: async (data: { message: string; recipients: string[] }) => {
    const response = await apiClient.post('/broadcasts', data);
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
};