import { useState } from 'react'
import {
  AppstoreOutlined,
  BellOutlined,
  DatabaseOutlined,
  FundProjectionScreenOutlined,
  LogoutOutlined,
  RobotOutlined,
  SearchOutlined,
} from '@ant-design/icons'
import { Avatar, Button, Input } from 'antd'
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
  { label: '知识库', to: routes.app.knowledgeBases, icon: <DatabaseOutlined /> },
]

export function AppLayout({ user, onLogout }: Props) {
  const navigate = useNavigate()
  const location = useLocation()
  const [collapsed, setCollapsed] = useState(false)
  const agentsQuery = useAgents()
  const entryQuery = useChatEntry()
  const isAgentWorkbench = /^\/app\/agents\/[^/]+\/edit$/.test(location.pathname)

  const handleLogout = async () => {
    await logout()
    onLogout()
    navigate(routes.login)
  }
  const defaultAgentId = entryQuery.data?.agent.id
  const sidebarAgents = [...(agentsQuery.data?.items ?? [])].sort((left, right) => {
    if (left.id === defaultAgentId) return -1
    if (right.id === defaultAgentId) return 1
    if (left.kind === 'builtin') return -1
    if (right.kind === 'builtin') return 1
    return Date.parse(right.updatedAt) - Date.parse(left.updatedAt)
  })

  if (isAgentWorkbench) {
    return <main className="h-screen overflow-hidden bg-white text-slate-700"><Outlet /></main>
  }

  return (
    <main className="flex h-screen overflow-hidden bg-white text-slate-700">
      <aside className={`flex shrink-0 flex-col border-r border-slate-200 bg-[#fbfcff] transition-[width] duration-200 ${collapsed ? 'w-[64px]' : 'w-[240px]'}`}>
        <div className={`flex h-[70px] items-center ${collapsed ? 'justify-center' : 'justify-between px-4'}`}>
          {!collapsed && (
            <div className="flex items-center gap-2 text-xl font-bold tracking-tight text-slate-800">
              <span className="grid h-8 w-8 place-items-center rounded-md bg-gradient-to-br from-cyan-300 via-blue-400 to-indigo-500 text-sm text-white">R</span>
              软小筑
            </div>
          )}
          <Button
            aria-label={collapsed ? '展开导航栏' : '收起导航栏'}
            className="!text-slate-600"
            icon={<span className="relative block h-5 w-6 rounded-md border-2 border-current before:absolute before:inset-y-0 before:left-1/2 before:border-l-2 before:border-current" />}
            type="text"
            onClick={() => setCollapsed(value => !value)}
          />
        </div>

        {!collapsed && (
          <>
            <div className="px-4">
              <Input className="!h-10 !rounded-xl !border-0 !bg-slate-100" prefix={<SearchOutlined />} placeholder="搜索" suffix={<span className="text-xs text-slate-500">Ctrl K</span>} />
            </div>
            <nav className="mt-4 px-4">
              {navigationItems.map(item => (
                <NavLink
                  key={item.to}
                  className={({ isActive }) => {
                    const isChat = item.to === routes.app.chat && location.pathname.startsWith(routes.app.chat)
                    return `mb-1 flex h-12 items-center gap-3 rounded-xl px-3 text-[15px] transition ${isActive || isChat ? 'bg-indigo-50 text-[#3665e6]' : 'text-slate-600 hover:bg-slate-100'}`
                  }}
                  to={item.to}
                >
                  <span className="text-xl">{item.icon}</span>
                  {item.label}
                </NavLink>
              ))}
              <div className="mb-1 flex h-12 cursor-default items-center gap-3 rounded-xl px-3 text-[15px] text-slate-600"><span className="text-xl"><FundProjectionScreenOutlined /></span>自动化任务</div>
            </nav>

            <div className="mt-3 border-t border-slate-200 px-4 pt-4">
              <p className="mb-3 text-sm text-slate-500">我的智能体</p>
              {sidebarAgents.map(agent => <NavLink key={agent.id} className={({ isActive }) => `mb-1 flex h-12 items-center gap-3 rounded-xl px-2 text-[15px] ${isActive || (agent.kind === 'builtin' && location.pathname === routes.app.chat) ? 'bg-indigo-50 text-[#3665e6]' : 'text-slate-600 hover:bg-slate-100'}`} to={agent.kind === 'builtin' ? routes.app.chat : routes.app.chatAgent(agent.id)}>
                <AgentAvatar agent={agent} className="grid h-8 w-8 place-items-center overflow-hidden rounded-lg bg-gradient-to-br from-cyan-300 to-indigo-500 text-base text-white" imageClassName="h-full w-full object-cover" />
                <span className="truncate">{agent.name}</span>
              </NavLink>)}
            </div>

            <div className="mt-auto flex items-center gap-2 border-t border-slate-200 px-4 py-4">
              <Avatar className="bg-slate-200 text-slate-500" size={32}>{user.email.slice(0, 1).toUpperCase()}</Avatar>
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm text-slate-700">{user.email}</p>
                <p className="truncate text-xs text-slate-400">当前登录账号</p>
              </div>
              <Button aria-label="通知" icon={<BellOutlined />} type="text" />
              <Button aria-label="退出登录" icon={<LogoutOutlined />} type="text" onClick={() => void handleLogout()} />
            </div>
          </>
        )}
      </aside>
      <section className="min-w-0 flex-1 overflow-hidden"><Outlet /></section>
    </main>
  )
}
