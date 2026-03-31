import axios from 'axios';
import type { AxiosError } from 'axios';

import type { ApiErrorResponse } from '../api/contracts';

const defaultApiBaseUrl = (() => {
  if (typeof window === 'undefined') {
    return 'http://127.0.0.1:8000';
  }
  return `http://${window.location.hostname}:8000`;
})();

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? defaultApiBaseUrl;
export const API_TIMEOUT_MS = 10_000;

export const http = axios.create({
  baseURL: API_BASE_URL,
  timeout: API_TIMEOUT_MS,
  headers: {
    'Content-Type': 'application/json',
  },
});

export function parseApiError(error: unknown): string {
  const fallback = 'Unknown error';
  if (!error) {
    return fallback;
  }

  const axiosError = error as AxiosError<ApiErrorResponse>;
  const apiMessage = axiosError.response?.data?.error?.message;
  const apiCode = axiosError.response?.data?.error?.code;
  if (apiMessage) {
    return apiCode ? `${apiMessage} (${apiCode})` : apiMessage;
  }

  if (error instanceof Error) {
    return error.message;
  }
  return fallback;
}
