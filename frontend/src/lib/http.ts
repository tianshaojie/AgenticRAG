import axios from 'axios';

const defaultApiBaseUrl = (() => {
  if (typeof window === 'undefined') {
    return 'http://127.0.0.1:8000';
  }
  return `http://${window.location.hostname}:8000`;
})();

export const http = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? defaultApiBaseUrl,
  timeout: 10_000,
  headers: {
    'Content-Type': 'application/json',
  },
});
