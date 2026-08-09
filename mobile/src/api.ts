import AsyncStorage from '@react-native-async-storage/async-storage';

const env = (globalThis as {
  process?: { env?: Record<string, string | undefined> };
}).process?.env;

export const API_URL = (
  env?.EXPO_PUBLIC_API_URL || 'http://127.0.0.1:8000'
).replace(/\/$/, '');

const TOKEN_KEY = 'kindred_mobile_token';

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

type RequestOptions = {
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE';
  body?: unknown;
};

export async function getToken(): Promise<string | null> {
  return AsyncStorage.getItem(TOKEN_KEY);
}

export async function setToken(token: string): Promise<void> {
  await AsyncStorage.setItem(TOKEN_KEY, token);
}

export async function clearToken(): Promise<void> {
  await AsyncStorage.removeItem(TOKEN_KEY);
}

export async function apiRequest<T>(
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const token = await getToken();
  const response = await fetch(`${API_URL}${path}`, {
    method: options.method || 'GET',
    headers: {
      Accept: 'application/json',
      ...(options.body === undefined ? {} : { 'Content-Type': 'application/json' }),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const message = payload?.error || payload?.detail || 'Request failed';
    throw new ApiError(response.status, String(message));
  }
  return payload as T;
}

export async function login(email: string, password: string, totpCode = '') {
  const result = await apiRequest<{
    token?: string;
    requires_2fa?: boolean;
    profile_id?: string | null;
  }>('/api/auth/login', {
    method: 'POST',
    body: { email, password, totp_code: totpCode },
  });
  if (result.requires_2fa) {
    throw new ApiError(401, 'Two-factor code required; retry with your authenticator code');
  }
  if (!result.token) {
    throw new ApiError(401, 'Login did not return a session token');
  }
  await setToken(result.token);
  return result;
}
