import { CloseOutlined, HistoryOutlined, MessageOutlined, PlusOutlined } from '@ant-design/icons'
import { Button, Drawer, Skeleton, Typography } from 'antd'
import type { Conversation } from '../../../types/chat'

type Props = {
  conversations: Conversation[]
  loading: boolean
  creating: boolean
  open: boolean
  selectedConversationId: string | null
  onClose: () => void
  onNewConversation: () => void
  onSelectConversation: (conversationId: string) => void
}

export function ConversationHistoryDrawer({ conversations, loading, creating, open, selectedConversationId, onClose, onNewConversation, onSelectConversation }: Props) {
  const hasConversations = conversations.length > 0

  return (
    <Drawer
      className="conversation-history-drawer"
      closable={false}
      extra={<Button aria-label="关闭历史记录" icon={<CloseOutlined />} type="text" onClick={onClose} />}
      mask={false}
      open={open}
      placement="right"
      styles={{
        section: { boxShadow: 'none' },
        wrapper: { borderLeft: '1px solid #d9d9d9', boxShadow: 'none' },
      }}
      title={<span className="flex items-center gap-2 text-base font-semibold text-slate-700"><HistoryOutlined />历史记录</span>}
      width={260}
      onClose={onClose}
    >
      <Button className="!mb-8 !h-10 !border-0 !bg-slate-100 !text-[15px] !font-medium !text-slate-700 hover:!bg-slate-200" block icon={<PlusOutlined />} loading={creating} onClick={onNewConversation}>
        新建会话
      </Button>
      {loading ? <Skeleton active paragraph={{ rows: 4 }} /> : (
        <div>
          {hasConversations && <p className="mb-5 text-sm text-slate-400">最近一周</p>}
          {conversations.map(conversation => (
            <button key={conversation.id} className={`mb-2 flex w-full items-center gap-2 rounded-lg px-2 py-2 text-left text-[15px] ${selectedConversationId === conversation.id ? 'bg-indigo-50 text-indigo-600' : 'text-slate-700 hover:bg-slate-100'}`} type="button" onClick={() => onSelectConversation(conversation.id)}>
              <MessageOutlined className="shrink-0 text-slate-400" />
              <Typography.Text className="!text-[15px]" ellipsis>{conversation.title ?? '新会话'}</Typography.Text>
            </button>
          ))}
          <p className="pt-2 text-center text-sm text-slate-400">没有更多了</p>
        </div>
      )}
    </Drawer>
  )
}
