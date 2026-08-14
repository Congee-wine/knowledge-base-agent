import { FormOutlined } from '@ant-design/icons'
import { Button, Empty, Modal, Result, Spin, message } from 'antd'
import { useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { useState } from 'react'
import { clearDefaultAgent, deleteAgent, setDefaultAgent } from '../api/agents'
import { AgentCard } from '../features/agents/components/AgentCard'
import { CreateAgentModal } from '../features/agents/components/CreateAgentModal'
import { agentKeys } from '../features/agents/agentKeys'
import { useAgents } from '../features/agents/hooks/useAgents'
import { useChatEntry } from '../features/chat/hooks/useChatEntry'
import { routes } from '../routes/paths'
import type { ChatAgent } from '../types/chat'

type AgentCategory = 'all' | 'official' | 'text'

const categoryTabs: Array<{ id: AgentCategory; label: string }> = [
  { id: 'all', label: '全部' },
  { id: 'official', label: '官方智能体' },
  { id: 'text', label: '文本会话' },
]

function matchesCategory(agent: ChatAgent, category: AgentCategory) {
  if (category === 'all') return true
  if (category === 'official') return agent.kind === 'builtin'
  if (category === 'text') return true
  return false
}

export function AgentListPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const agentsQuery = useAgents()
  const entryQuery = useChatEntry()
  const [selectedCategory, setSelectedCategory] = useState<AgentCategory>('all')
  const [createModalOpen, setCreateModalOpen] = useState(false)
  const invalidateAgentState = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: agentKeys.all }),
      queryClient.invalidateQueries({ queryKey: agentKeys.entry }),
    ])
  }

  if (agentsQuery.isPending || entryQuery.isPending) return <div className="grid h-full place-items-center"><Spin tip="正在加载智能体" /></div>
  if (agentsQuery.isError || entryQuery.isError || !agentsQuery.data || !entryQuery.data) {
    return <Result status="error" title="无法加载智能体" extra={<Button type="primary" onClick={() => void invalidateAgentState()}>重试</Button>} />
  }

  const defaultAgentId = entryQuery.data.agent.id
  const agents = [...agentsQuery.data.items].sort((left, right) => {
    if (left.id === defaultAgentId) return -1
    if (right.id === defaultAgentId) return 1
    if (left.kind === 'builtin') return -1
    if (right.kind === 'builtin') return 1
    return Date.parse(right.updatedAt) - Date.parse(left.updatedAt)
  })
  const filteredAgents = agents.filter(agent => matchesCategory(agent, selectedCategory))
  const openAgent = (agent: ChatAgent) => navigate(agent.kind === 'builtin' ? routes.app.chat : routes.app.chatAgent(agent.id))
  const makeDefault = async (agent: ChatAgent) => {
    try {
      if (agent.kind === 'builtin') await clearDefaultAgent()
      else await setDefaultAgent(agent.id)
      await invalidateAgentState()
      message.success(`${agent.name} 已设为默认打开`)
    } catch {
      message.error('设置默认智能体失败，请重试')
    }
  }
  const removeAgent = (agent: ChatAgent) => {
    Modal.confirm({
      title: `删除“${agent.name}”？`,
      content: '删除后将无法从列表、侧栏或聊天页访问该智能体及其会话。',
      okButtonProps: { danger: true },
      okText: '删除',
      onOk: async () => {
        try {
          await deleteAgent(agent.id)
          await invalidateAgentState()
          message.success('智能体已删除')
        } catch {
          message.error('删除失败；默认智能体请先切换默认打开对象')
        }
      },
    })
  }

  return <section className="agent-list-page">
    <header className="agent-list-page__banner">
      <div><h1>智能体</h1><p>管理您的智能体，控制您的智能体分发策略。</p></div>
      <Button className="agent-list-page__create" icon={<FormOutlined />} onClick={() => setCreateModalOpen(true)}>新建智能体</Button>
    </header>
    <nav className="agent-list-page__tabs" aria-label="智能体类型">
      {categoryTabs.map(tab => <button key={tab.id} aria-pressed={selectedCategory === tab.id} className={selectedCategory === tab.id ? 'is-active' : ''} type="button" onClick={() => setSelectedCategory(tab.id)}>{tab.label}</button>)}
    </nav>
    {filteredAgents.length ? <div className="agent-list-page__grid">
      {filteredAgents.map(agent => <AgentCard key={agent.id} agent={agent} isDefault={agent.id === defaultAgentId} onDelete={removeAgent} onEdit={item => navigate(routes.app.agentEdit(item.id))} onOpen={openAgent} onSetDefault={item => void makeDefault(item)} />)}
    </div> : <Empty description={`暂无${categoryTabs.find(tab => tab.id === selectedCategory)?.label ?? '智能体'}`} />}
    <CreateAgentModal open={createModalOpen} onOpenChange={setCreateModalOpen} onCreated={agentId => {
      void invalidateAgentState()
      navigate(routes.app.agentEdit(agentId))
    }} />
  </section>
}
