import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { routes } from './paths'
import type { User } from '../types/auth'

type LocationState = { from?: { pathname: string; search?: string; hash?: string } }
type Props = { user: User | null }

function getReturnPath(state: unknown) {
  const from = (state as LocationState | null)?.from
  return from ? `${from.pathname}${from.search ?? ''}${from.hash ?? ''}` : routes.app.chat
}

export function GuestOnly({ user }: Props) {
  const location = useLocation()

  if (!user) return <Outlet />

  return <Navigate to={getReturnPath(location.state)} replace />
}
