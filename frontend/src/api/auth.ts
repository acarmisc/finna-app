import { apiPost } from './client';
import type { TokenResponse } from './types';

const TOKEN_KEY = 'finna_token';

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export async function login(username: string, password: string): Promise<TokenResponse> {
  const res = await apiPost<TokenResponse>('/auth/token', { username, password });
  localStorage.setItem(TOKEN_KEY, res.access_token);
  return res;
}

export function logout(): void {
  localStorage.removeItem(TOKEN_KEY);
  window.location.href = '/login';
}
