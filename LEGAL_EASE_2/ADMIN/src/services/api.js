import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({ baseURL: API_URL, headers: { 'Content-Type': 'application/json' } });

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('admin_access_token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

let _isRefreshing = false;
let _failedQueue = [];

function processQueue(error, token = null) {
  _failedQueue.forEach(({ resolve, reject }) => (error ? reject(error) : resolve(token)));
  _failedQueue = [];
}

api.interceptors.response.use(
  (res) => res,
  async (err) => {
    const originalRequest = err.config;
    if (err.response?.status === 401 && !originalRequest._retry) {
      const refreshToken = localStorage.getItem('admin_refresh_token');
      if (!refreshToken) {
        localStorage.removeItem('admin_access_token');
        localStorage.removeItem('admin_refresh_token');
        window.location.href = '/login';
        return Promise.reject(err);
      }

      if (_isRefreshing) {
        return new Promise((resolve, reject) => {
          _failedQueue.push({ resolve, reject });
        }).then((token) => {
          originalRequest.headers.Authorization = `Bearer ${token}`;
          return api(originalRequest);
        });
      }

      originalRequest._retry = true;
      _isRefreshing = true;

      try {
        const { data } = await api.post('/api/auth/refresh', { refresh_token: refreshToken });
        localStorage.setItem('admin_access_token', data.access_token);
        localStorage.setItem('admin_refresh_token', data.refresh_token);
        processQueue(null, data.access_token);
        originalRequest.headers.Authorization = `Bearer ${data.access_token}`;
        return api(originalRequest);
      } catch (refreshErr) {
        processQueue(refreshErr);
        localStorage.removeItem('admin_access_token');
        localStorage.removeItem('admin_refresh_token');
        window.location.href = '/login';
        return Promise.reject(refreshErr);
      } finally {
        _isRefreshing = false;
      }
    }
    return Promise.reject(err);
  }
);

export default api;

// ─── Auth ───
export async function adminLogin(email, password) {
  const res = await api.post('/api/auth/login', { email, password });
  localStorage.setItem('admin_access_token', res.data.access_token);
  localStorage.setItem('admin_refresh_token', res.data.refresh_token);
  return res.data;
}

export async function getMe() {
  const res = await api.get('/api/auth/me');
  return res.data;
}

// ─── Admin Endpoints ───
export async function getStats() {
  const res = await api.get('/api/admin/stats');
  return res.data;
}

export async function getUsers(skip = 0, limit = 20) {
  const res = await api.get('/api/admin/users', { params: { skip, limit } });
  return res.data;
}

export async function updateUser(userId, data) {
  const res = await api.patch(`/api/admin/users/${userId}`, data);
  return res.data;
}

export async function getDocuments(skip = 0, limit = 20, status = null) {
  const params = { skip, limit };
  if (status) params.status = status;
  const res = await api.get('/api/admin/documents', { params });
  return res.data;
}

export async function deleteDocument(documentId) {
  const res = await api.delete(`/api/admin/documents/${documentId}`);
  return res.data;
}

export function logout() {
  localStorage.removeItem('admin_access_token');
  localStorage.removeItem('admin_refresh_token');
}

// Bundled admin API object used by pages
export const adminApi = {
  login: adminLogin,
  getMe,
  logout,
  getStats,
  getUsers,
  updateUser,
  getDocuments,
  deleteDocument,
};
