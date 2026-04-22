import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000';

const client = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Injecter le token JWT dans chaque requête si disponible
client.interceptors.request.use((config) => {
  const token = localStorage.getItem('fraudia_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Si le token expire (401), déconnecter
client.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401 && localStorage.getItem('fraudia_token')) {
      localStorage.removeItem('fraudia_token');
      localStorage.removeItem('fraudia_user');
      window.location.reload();
    }
    return Promise.reject(error);
  }
);

export const api = {
  // ── Auth ──
  login: async (email, password) => {
    const response = await client.post('/auth/login', { email, password });
    const { access_token, user } = response.data;
    localStorage.setItem('fraudia_token', access_token);
    localStorage.setItem('fraudia_user', JSON.stringify(user));
    return response.data;
  },

  logout: () => {
    localStorage.removeItem('fraudia_token');
    localStorage.removeItem('fraudia_user');
  },

  getMe: async () => {
    const response = await client.get('/auth/me');
    return response.data;
  },

  getStoredUser: () => {
    try {
      const user = localStorage.getItem('fraudia_user');
      const token = localStorage.getItem('fraudia_token');
      if (user && token) return JSON.parse(user);
      return null;
    } catch { return null; }
  },

  // ── Admin (Superadmin) ──
  getAnalysts: async () => {
    const response = await client.get('/auth/admin/users');
    return response.data;
  },

  gradeAnalyst: async (analystId, data) => {
    const response = await client.post(`/auth/admin/users/${analystId}/grade`, data);
    return response.data;
  },

  // ── HITL (Human-in-the-Loop) ──
  getHitlStatus: async () => {
    const response = await client.get('/hitl/status');
    return response.data;
  },

  triggerRetrain: async () => {
    const response = await client.post('/hitl/retrain', {}, { timeout: 120000 });
    return response.data;
  },

  getHitlHistory: async () => {
    const response = await client.get('/hitl/history');
    return response.data;
  },

  // ── Transactions history (cloisonné) ──
  getTransactions: async () => {
    const response = await client.get('/auth/transactions');
    return response.data;
  },

  getAnalytics: async () => {
    const response = await client.get('/auth/analytics');
    return response.data;
  },

  saveTransaction: async (data) => {
    const response = await client.post('/auth/transactions', data);
    return response.data;
  },

  updateTransaction: async (rowId, data) => {
    const response = await client.put(`/auth/transactions/${rowId}`, data);
    return response.data;
  },

  deleteTransaction: async (rowId) => {
    const response = await client.delete(`/auth/transactions/${rowId}`);
    return response.data;
  },

  // ── Batch upload ──
  batchUpload: async (file) => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await client.post('/batch/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 300000,
    });
    return response.data;
  },

  // ── Existing API ──
  checkHealth: async () => {
    const response = await client.get('/health');
    return response.data;
  },
  
  predict: async (data) => {
    const response = await client.post('/predict/', data);
    return response.data;
  },

  /** Phase 1 : Score + SHAP (rapide, ~2-3s) */
  explainShap: async (data) => {
    const response = await client.post('/explain/shap', data, { timeout: 30000 });
    return response.data;
  },

  /** Phase 2 : Explication LLM seule (lent, ~15-60s) */
  explainLlm: async (data) => {
    const response = await client.post('/explain/llm', data, { timeout: 180000 });
    return response.data;
  },
  
  explain: async (data) => {
    const response = await client.post('/explain/', data, { timeout: 180000 });
    return response.data;
  },
};
