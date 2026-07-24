import { refreshTokens, revokeSession } from '../api/auth'
import { ApiError } from '../api/http'
import type { TokenResponse, User } from '../types/auth'
const ACCESS_TOKEN_KEY = 'access_token'
const REFRESH_TOKEN_KEY = 'refresh_token'
const CURRENT_USER_KEY = 'current_user'
let refreshRequest: Promise<User> | null = null

export class MissingRefreshTokenError extends Error {
  constructor() {
    super('登录已过期')
    this.name = 'MissingRefreshTokenError'
  }
}

export function isAuthenticationRejected(error: unknown) {
  return error instanceof MissingRefreshTokenError || (error instanceof ApiError && (error.status === 401 || error.status === 403))
}

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
  if (!refreshToken) throw new MissingRefreshTokenError()
  if (refreshRequest) return refreshRequest

  refreshRequest = refreshWithToken(refreshToken).finally(() => {
    refreshRequest = null
  })
  return refreshRequest
}

async function refreshWithToken(refreshToken: string): Promise<User> {
  try {
    const data = await refreshTokens(refreshToken)
    saveTokens(data)
    return data.user
  } catch (error) {
    const latestRefreshToken = localStorage.getItem(REFRESH_TOKEN_KEY)
    const storedUser = getStoredUser()
    if (latestRefreshToken && latestRefreshToken !== refreshToken && storedUser) return storedUser
    throw error
  }
}

export function getStoredUser(): User | null {
  const rawUser = localStorage.getItem(CURRENT_USER_KEY)
  if (!rawUser) return null
  try {
    const user: unknown = JSON.parse(rawUser)
    if (typeof user === 'object' && user !== null && 'id' in user && 'email' in user && typeof user.id === 'string' && typeof user.email === 'string') return user as User
  } catch {
    return null
  }
  return null
}

export async function logout() {
  const accessToken = getStoredAccessToken()
  const refreshToken = localStorage.getItem(REFRESH_TOKEN_KEY)
  await revokeSession(accessToken, refreshToken).catch(() => undefined)
  clearStoredSession()
}
