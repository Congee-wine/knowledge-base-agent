import { useState } from 'react'
import {
  AppstoreOutlined,
  DatabaseOutlined,
  LogoutOutlined,
  RobotOutlined,
} from '@ant-design/icons'
import { Avatar, Button } from 'antd'
import { useAgents } from '../features/agents/hooks/useAgents'
import { AgentAvatar } from '../features/agents/components/AgentAvatar'
import { useChatEntry } from '../features/chat/hooks/useChatEntry'
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { logout } from '../lib/auth'
import { routes } from '../routes/paths'
import type { User } from '../types/auth'

type Props = { user: User; onLogout: () => void }

const navigationItems = [
  { label: 'AI管家', to: routes.app.chat, icon: <RobotOutlined /> },
  { label: '智能体', to: routes.app.agents, icon: <AppstoreOutlined /> },
  {
    label: '知识库',
    to: routes.app.knowledgeBases,
    icon: <DatabaseOutlined />,
  },
]

export function AppLayout({ user, onLogout }: Props) {
  const navigate = useNavigate()
  const location = useLocation()
  const [collapsed, setCollapsed] = useState(false)
  const agentsQuery = useAgents()
  const entryQuery = useChatEntry()
  const isAgentWorkbench = /^\/app\/agents\/[^/]+\/edit$/.test(
    location.pathname,
  )

  const handleLogout = async () => {
    await logout()
    onLogout()
    navigate(routes.login)
  }
  const defaultAgentId = entryQuery.data?.agent.id
  const sidebarAgents = [...(agentsQuery.data?.items ?? [])].sort(
    (left, right) => {
      if (left.id === defaultAgentId) return -1
      if (right.id === defaultAgentId) return 1
      if (left.kind === 'builtin') return -1
      if (right.kind === 'builtin') return 1
      return Date.parse(right.updatedAt) - Date.parse(left.updatedAt)
    },
  )

  if (isAgentWorkbench) {
    return (
      <main className="agent-workbench-shell">
        <Outlet />
      </main>
    )
  }

  return (
    <main className="app-shell">
      <aside
        className={`app-sidebar ${collapsed ? 'app-sidebar--collapsed' : ''}`}
      >
        <div
          className={`app-sidebar__brand ${collapsed ? 'justify-center' : 'justify-between'}`}
        >
          {!collapsed && (
            <div className="flex items-center gap-2 text-xl font-bold tracking-tight text-slate-800">
              <span className="app-sidebar__logo">
                知
              </span>
              知问
            </div>
          )}
          <Button
            aria-label={collapsed ? '展开导航栏' : '收起导航栏'}
            className="!text-slate-600"
            icon={
              <span className="relative block h-5 w-6 rounded-md border-2 border-current before:absolute before:inset-y-0 before:left-1/2 before:border-l-2 before:border-current" />
            }
            type="text"
            onClick={() => setCollapsed((value) => !value)}
          />
        </div>

        {!collapsed && (
          <>
            <nav className="app-sidebar__nav">
              {navigationItems.map((item) => (
                <NavLink
                  key={item.to}
                  className={({ isActive }) => {
                    const isChat =
                      item.to === routes.app.chat &&
                      location.pathname.startsWith(routes.app.chat)
                    return `app-sidebar__nav-item ${isActive || isChat ? 'is-active' : ''}`
                  }}
                  to={item.to}
                >
                  <span className="text-xl">{item.icon}</span>
                  {item.label}
                </NavLink>
              ))}
            </nav>

            <div className="app-sidebar__agents">
              <p>我的智能体</p>
              {sidebarAgents.map((agent) => (
                <NavLink
                  end
                  key={agent.id}
                  className={({ isActive }) =>
                    `app-sidebar__agent ${isActive ? 'is-active' : ''}`
                  }
                  to={
                    agent.kind === 'builtin'
                      ? routes.app.chat
                      : routes.app.chatAgent(agent.id)
                  }
                >
                  <AgentAvatar
                    agent={agent}
                    className="app-sidebar__agent-avatar"
                    imageClassName="h-full w-full object-cover"
                  />
                  <span className="truncate">{agent.name}</span>
                </NavLink>
              ))}
            </div>

            <div className="app-sidebar__account">
              <Avatar className="bg-slate-200 text-slate-500" size={32}>
                {user.email.slice(0, 1).toUpperCase()}
              </Avatar>
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm text-slate-700">{user.email}</p>
                <p className="truncate text-xs text-slate-400">当前登录账号</p>
              </div>
              <Button
                aria-label="退出登录"
                icon={<LogoutOutlined />}
                type="text"
                onClick={() => void handleLogout()}
              />
            </div>
          </>
        )}
      </aside>
      <section className="min-w-0 flex-1 overflow-hidden">
        <Outlet />
      </section>
    </main>
  )
}
