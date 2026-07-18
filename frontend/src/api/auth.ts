import { request } from './http'
import type { TokenResponse, User } from '../types/auth'

type Credentials = { email: string; password: string }

export type RegisterInput = Credentials & { acceptedTerms: boolean }

export function register(input: RegisterInput) {
  return request<User>('/api/auth/register', {
    method: 'POST',
    body: { email: input.email, password: input.password, accepted_terms: input.acceptedTerms },
  })
}

export function login(input: Credentials) {
  return request<TokenResponse>('/api/auth/login', { method: 'POST', body: input })
}

export function getCurrentUser(accessToken: string) {
  return request<User>('/api/auth/me', { headers: { Authorization: `Bearer ${accessToken}` } })
}

export function refreshTokens(refreshToken: string) {
  return request<TokenResponse>('/api/auth/refresh', { method: 'POST', body: { refresh_token: refreshToken } })
}

export function revokeSession(accessToken: string | null, refreshToken: string | null) {
  return request<void>('/api/auth/logout', {
    method: 'POST',
    headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : undefined,
    body: { refresh_token: refreshToken },
  })
}
