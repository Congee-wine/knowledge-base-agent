import { refreshTokens, revokeSession } from '../api/auth'
import type { TokenResponse, User } from '../types/auth'
const ACCESS_TOKEN_KEY = 'access_token'
const REFRESH_TOKEN_KEY = 'refresh_token'
const CURRENT_USER_KEY = 'current_user'

export function getTokenExpiresAt(token: string) {
  try {
    const payload = JSON.parse(atob(token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/')))
    return typeof payload.exp === 'number' ? payload.exp * 1000 : 0
  } catch {
    return 0
  }
}

export function getStoredAccessToken() {
  return localStorage.getItem(ACCESS_TOKEN_KEY)
}

export function saveTokens(data: TokenResponse) {
  localStorage.setItem(ACCESS_TOKEN_KEY, data.access_token)
  localStorage.setItem(REFRESH_TOKEN_KEY, data.refresh_token)
  localStorage.setItem(CURRENT_USER_KEY, JSON.stringify(data.user))
}

export function clearStoredSession() {
  localStorage.removeItem(ACCESS_TOKEN_KEY)
  localStorage.removeItem(REFRESH_TOKEN_KEY)
  localStorage.removeItem(CURRENT_USER_KEY)
}

export async function refreshSession(): Promise<User> {
  const refreshToken = localStorage.getItem(REFRESH_TOKEN_KEY)
  if (!refreshToken) throw new Error('登录已过期')
  const data = await refreshTokens(refreshToken)
  saveTokens(data)
  return data.user
}

export async function logout() {
  const accessToken = getStoredAccessToken()
  const refreshToken = localStorage.getItem(REFRESH_TOKEN_KEY)
  await revokeSession(accessToken, refreshToken).catch(() => undefined)
  clearStoredSession()
}
