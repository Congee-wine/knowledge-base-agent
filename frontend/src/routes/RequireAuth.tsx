import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { routes } from './paths'
import type { User } from '../types/auth'

type Props = { user: User | null }

export function RequireAuth({ user }: Props) {
  const location = useLocation()

  if (user) return <Outlet />

  return <Navigate to={routes.login} replace state={{ from: location }} />
}
