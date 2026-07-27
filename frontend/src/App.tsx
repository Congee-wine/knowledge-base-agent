import { lazy, Suspense, useEffect } from 'react'
import { ConfigProvider } from 'antd'
import { useQuery } from '@tanstack/react-query'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AppLayout } from './layouts/AppLayout'
import { getCurrentUser } from './api/auth'
import { ApiError } from './api/http'
import { clearStoredSession, getStoredUser, getTokenExpiresAt, getStoredAccessToken, isAuthenticationRejected, refreshSession } from './lib/auth'
import { AuthPage } from './pages/AuthPage'
import { AiManagerPage } from './pages/AiManagerPage'
import { EmptyPage } from './pages/EmptyPage'
import { NotFoundPage } from './pages/NotFoundPage'
import { GuestOnly } from './routes/GuestOnly'
import { RequireAuth } from './routes/RequireAuth'
import { routes } from './routes/paths'
import { useAuthStore } from './stores/auth'

const REFRESH_BEFORE_EXPIRY_MS = 3 * 60 * 1000
const AgentEditorPage = lazy(async () =>
  import('./pages/AgentEditorPage').then(module => ({
    default: module.AgentEditorPage,
  })),
)
const AgentListPage = lazy(async () =>
  import('./pages/AgentListPage').then(module => ({
    default: module.AgentListPage,
  })),
)
const ChatPage = lazy(async () =>
  import('./pages/ChatPage').then(module => ({ default: module.ChatPage })),
)

function RouteLoadingFallback() {
  return (
    <div className="grid h-full min-h-screen place-items-center bg-slate-50 text-sm text-slate-500">
      正在加载页面…
    </div>
  )
}

function App() {
  const user = useAuthStore(state => state.user)
  const setUser = useAuthStore(state => state.setUser)
  const clearUser = useAuthStore(state => state.clearUser)
  const accessToken = getStoredAccessToken()
  const cachedUser = accessToken ? getStoredUser() : null
  const authenticatedUser = user ?? cachedUser
  const sessionQuery = useQuery({
    queryKey: ['auth', 'current-user', accessToken],
    queryFn: async () => {
      try {
        return await getCurrentUser(accessToken!)
      } catch (error) {
        if (error instanceof ApiError && error.status === 401) return refreshSession()
        throw error
      }
    },
    enabled: Boolean(accessToken),
    retry: false,
  })

  useEffect(() => {
    if (sessionQuery.data) setUser(sessionQuery.data)
  }, [sessionQuery.data, setUser])

  useEffect(() => {
    if (!sessionQuery.isError || !isAuthenticationRejected(sessionQuery.error)) return
    clearStoredSession()
    clearUser()
  }, [sessionQuery.isError, sessionQuery.error, clearUser])

  useEffect(() => {
    if (!user) return
    const accessToken = getStoredAccessToken()
    if (!accessToken) return
    const delay = Math.max(0, getTokenExpiresAt(accessToken) - Date.now() - REFRESH_BEFORE_EXPIRY_MS)
    const timer = window.setTimeout(() => {
      void refreshSession().then(setUser).catch(error => {
        if (!isAuthenticationRejected(error)) return
        clearStoredSession()
        clearUser()
      })
    }, delay)
    return () => window.clearTimeout(timer)
  }, [user])

  if (accessToken && sessionQuery.isPending) return <div className="grid h-screen place-items-center bg-slate-50 text-sm text-slate-500">正在检查登录状态…</div>

  return <ConfigProvider theme={{ token: { colorPrimary: '#4f6cff', borderRadius: 10, fontFamily: 'Microsoft YaHei, PingFang SC, Arial, sans-serif' } }}>
    <BrowserRouter>
      <Suspense fallback={<RouteLoadingFallback />}>
          <Routes>
        <Route path={routes.home} element={<Navigate to={routes.app.chat} replace />} />
        <Route element={<GuestOnly user={authenticatedUser} />}>
          <Route path={routes.login} element={<AuthPage mode="login" onAuthenticated={setUser} />} />
          <Route path={routes.register} element={<AuthPage mode="register" onAuthenticated={setUser} />} />
        </Route>
        <Route element={<RequireAuth user={authenticatedUser} />}>
          <Route element={authenticatedUser ? <AppLayout user={authenticatedUser} onLogout={clearUser} /> : null}>
            <Route path={routes.app.root} element={<Navigate to={routes.app.chat} replace />} />
            <Route path={routes.app.chat} element={<AiManagerPage />} />
            <Route path="/app/chat/agents/:agentId" element={<ChatPage />} />
            <Route path={routes.app.agents} element={<AgentListPage />} />
            <Route path={routes.app.agentNew} element={<Navigate to={routes.app.agents} replace />} />
            <Route path="/app/agents/:agentId/edit" element={<AgentEditorPage />} />
            <Route path={routes.app.knowledgeBases} element={<EmptyPage />} />
          </Route>
        </Route>
        <Route path="*" element={<NotFoundPage />} />
          </Routes>
      </Suspense>
    </BrowserRouter>
  </ConfigProvider>
}

export default App
