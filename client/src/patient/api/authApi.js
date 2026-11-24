
import axios from 'axios';

const rawApi = import.meta.env.VITE_API_URL || 'http://localhost:8080';
const API_BASE = rawApi.replace(/\/+$/, '');

const authClient = axios.create({
  baseURL: `${API_BASE}/api/auth`,
  timeout: 30000,
  withCredentials: true,
});

authClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('medora_auth_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export const authApi = {
  signup: async (data) => {
    const response = await authClient.post('/signup', data);
    if (response?.data?.token) {
      localStorage.setItem('medora_auth_token', response.data.token);
    }
    return response.data;
  },

  login: async (username, password) => {
    const response = await authClient.post('/login', {
      username,
      password,
    });
    if (response?.data?.token) {
      localStorage.setItem('medora_auth_token', response.data.token);
    }
    return response.data;
  },

  me: async () => {
    const response = await authClient.get('/me');
    return response.data;
  },

  logout: async () => {
    try {
      const response = await authClient.post('/logout');
      return response.data;
    } finally {
      localStorage.removeItem('medora_auth_token');
    }
  },
};

export default authApi;
