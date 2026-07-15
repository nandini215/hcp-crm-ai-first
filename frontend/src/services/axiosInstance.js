import axios from 'axios';

// The FastAPI backend mounts every route at the root (POST /chat,
// GET/POST/PUT /interaction, GET /hcp/{name}) — there is no /api/v1 prefix.
const baseURL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

const axiosInstance = axios.create({
  baseURL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor — placeholder for auth token injection, request logging, etc.
axiosInstance.interceptors.request.use(
  (config) => config,
  (error) => Promise.reject(error)
);

// Response interceptor — normalizes error shape for the UI layer.
axiosInstance.interceptors.response.use(
  (response) => response,
  (error) => {
    const message =
      error?.response?.data?.detail ||
      error?.response?.data?.message ||
      error?.message ||
      'Something went wrong while talking to the AI Assistant.';
    return Promise.reject(new Error(message));
  }
);

export default axiosInstance;
