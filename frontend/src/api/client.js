import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000';

const client = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const api = {
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
