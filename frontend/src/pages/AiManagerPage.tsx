import { useState } from 'react'
import { Alert, Button, Result, Spin, message } from 'antd'
import { HistoryOutlined, PlusCircleOutlined } from '@ant-design/icons'
import { ChatComposer } from '../features/chat/components/ChatComposer'
import { ChatWelcome } from '../features/chat/components/ChatWelcome'
import { ConversationHistoryDrawer } from '../features/chat/components/ConversationHistoryDrawer'
import { useChatEntry } from '../features/chat/hooks/useChatEntry'
import { useConversations } from '../features/chat/hooks/useConversations'

export function AiManagerPage() {
  const [historyOpen, setHistoryOpen] = useState(false)
  const [composerValue, setComposerValue] = useState('')
  const entryQuery = useChatEntry()
  const conversationsQuery = useConversations(entryQuery.data?.agent.id)

  if (entryQuery.isPending) return <div className="grid h-full place-items-center"><Spin tip="正在加载 AI 管家…" /></div>
  if (entryQuery.isError || !entryQuery.data) return <Result status="error" title="无法加载 AI 管家" subTitle="请检查网络后重试" extra={<Button type="primary" onClick={() => void entryQuery.refetch()}>重试</Button>} />

  const agent = entryQuery.data.agent
  const showNewConversationTip = () => message.info('新建会话将在消息发送接口联调时接入')

  return (
    <section className="flex h-full min-h-[680px] flex-col overflow-hidden bg-white" aria-label="AI管家页面">
      <header className="flex h-[70px] shrink-0 items-center justify-end gap-5 px-8">
        <Button className="!px-0 !font-medium !text-slate-700" icon={<PlusCircleOutlined />} type="text" onClick={showNewConversationTip}>新会话</Button>
        <Button className="!px-0 !font-medium !text-slate-700" icon={<HistoryOutlined />} type="text" onClick={() => setHistoryOpen(true)}>历史记录</Button>
      </header>
      {conversationsQuery.isError && <Alert className="mx-8" type="warning" showIcon message="历史会话加载失败" action={<Button size="small" onClick={() => void conversationsQuery.refetch()}>重试</Button>} />}
      <div className="flex min-h-0 flex-1 flex-col overflow-y-auto">
        <ChatWelcome agent={agent} onPromptClick={prompt => setComposerValue(prompt)} />
        <ChatComposer agent={agent} initialValue={composerValue} />
      </div>
      <ConversationHistoryDrawer conversations={conversationsQuery.data?.items ?? []} loading={conversationsQuery.isPending} open={historyOpen} onClose={() => setHistoryOpen(false)} onNewConversation={showNewConversationTip} />
    </section>
  )
}
