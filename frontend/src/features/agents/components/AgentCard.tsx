import { EllipsisOutlined, StarFilled, UserOutlined } from '@ant-design/icons'
import { Button, Dropdown, Tag } from 'antd'
import type { MenuProps } from 'antd'
import type { ChatAgent } from '../../../types/chat'

type Props = {
  agent: ChatAgent
  isDefault: boolean
  onDelete: (agent: ChatAgent) => void
  onEdit: (agent: ChatAgent) => void
  onOpen: (agent: ChatAgent) => void
  onSetDefault: (agent: ChatAgent) => void
}

function agentAvatar(agent: ChatAgent) {
  return agent.avatarKey?.slice(0, 1).toUpperCase() ?? agent.name.slice(0, 1).toUpperCase()
}

function formatUpdatedAt(updatedAt: string) {
  return new Intl.DateTimeFormat('zh-CN', {
    day: '2-digit', hour: '2-digit', minute: '2-digit', month: '2-digit', year: 'numeric',
  }).format(new Date(updatedAt)).replaceAll('/', '-')
}

export function AgentCard({ agent, isDefault, onDelete, onEdit, onOpen, onSetDefault }: Props) {
  const isBuiltin = agent.kind === 'builtin'
  const menuItems: MenuProps['items'] = isBuiltin
    ? [{ key: 'default', disabled: isDefault, label: isDefault ? '当前默认打开' : '设为默认打开', icon: <StarFilled /> }]
    : [
        { key: 'default', disabled: isDefault, label: isDefault ? '当前默认打开' : '设为默认打开', icon: <StarFilled /> },
        { key: 'edit', label: '编辑' },
        { key: 'delete', danger: true, label: '删除' },
      ]

  return (
    <article className="agent-card" onClick={() => onOpen(agent)} onKeyDown={event => {
        if (event.key === 'Enter' || event.key === ' ') onOpen(agent)
      }} role="button" tabIndex={0}>
      <div className="agent-card__content">
        <h2 className="agent-card__title">{agent.name}</h2>
        <p className="agent-card__description">{agent.description || '暂无描述'}</p>
        <span className="agent-card__avatar" aria-hidden="true">{agentAvatar(agent)}</span>
        <div className="agent-card__labels">
          <Tag bordered={false}>会话智能体</Tag>
          {isBuiltin ? <><Tag bordered={false} color="green">官方应用</Tag><Tag bordered={false} color="blue">已开通</Tag></> : <Tag bordered={false} color="blue">我的</Tag>}
          {isDefault && <Tag bordered={false} color="orange">默认</Tag>}
        </div>
        <div className="agent-card__footer">
          <span><UserOutlined /> 我</span>
          <span>最近编辑&nbsp; {formatUpdatedAt(agent.updatedAt)}</span>
        </div>
        <Dropdown menu={{ items: menuItems, onClick: info => {
          info.domEvent.stopPropagation()
          if (info.key === 'default') onSetDefault(agent)
          if (info.key === 'edit') onEdit(agent)
          if (info.key === 'delete') onDelete(agent)
        } }} trigger={['click']}>
          <Button aria-label={`${agent.name} 操作`} className="agent-card__more" icon={<EllipsisOutlined />} type="text" onClick={event => event.stopPropagation()} />
        </Dropdown>
      </div>
    </article>
  )
}
