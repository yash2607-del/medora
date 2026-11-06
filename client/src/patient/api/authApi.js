
import axios from 'axios';

const API_BASE =
  import.meta.env.VITE_API_URL ||
  'http://localhost:8000';

const authClient = axios.create({
  baseURL: `${API_BASE}/api/auth`,
  timeout: 30000,
  withCredentials: true,
});

export const authApi = {
  signup: async (data) => {
    const response = await authClient.post('/signup', data);
    return response.data;
  },

  login: async (username, password) => {
    const response = await authClient.post('/login', {
      username,
      password,
    });
    return response.data;
  },

  me: async () => {
    const response = await authClient.get('/me');
    return response.data;
  },

  logout: async () => {
    const response = await authClient.post('/logout');
    return response.data;
  },
};

export default authApi;
