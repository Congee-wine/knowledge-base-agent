import { useEffect, useState } from 'react'
import { HistoryOutlined, PlusCircleOutlined } from '@ant-design/icons'
import { Alert, Button, Result, Spin, message } from 'antd'
import { useParams } from 'react-router-dom'
import { ChatComposer } from '../features/chat/components/ChatComposer'
import { ChatHistorySkeleton } from '../features/chat/components/ChatHistorySkeleton'
import { ChatMessageList } from '../features/chat/components/ChatMessageList'
import { ChatWelcome } from '../features/chat/components/ChatWelcome'
import { ConversationHistoryDrawer } from '../features/chat/components/ConversationHistoryDrawer'
import { useAgent } from '../features/agents/hooks/useAgent'
import { useChatEntry } from '../features/chat/hooks/useChatEntry'
import { useConversationDetail } from '../features/chat/hooks/useConversationDetail'
import { useConversations } from '../features/chat/hooks/useConversations'
import { useSendMessage } from '../features/chat/hooks/useSendMessage'
import type { ChatMessage } from '../types/chat'

export function ChatPage() {
  const { agentId } = useParams()
  const [historyOpen, setHistoryOpen] = useState(false)
  const [composerValue, setComposerValue] = useState('')
  const [selectedConversationId, setSelectedConversationId] = useState<string | null>(null)
  const [optimisticMessages, setOptimisticMessages] = useState<ChatMessage[]>([])
  const entryQuery = useChatEntry(!agentId)
  const agentQuery = useAgent(agentId)
  const resolvedAgent = agentId ? agentQuery.data : entryQuery.data?.agent
  const isAgentPending = agentId ? agentQuery.isPending : entryQuery.isPending
  const isAgentError = agentId ? agentQuery.isError : entryQuery.isError
  const conversationsQuery = useConversations(resolvedAgent?.id)
  const conversationDetailQuery = useConversationDetail(selectedConversationId)
  const sendMessageMutation = useSendMessage()

  useEffect(() => {
    setSelectedConversationId(null)
    setOptimisticMessages([])
    setComposerValue('')
  }, [resolvedAgent?.id])

  if (isAgentPending) return <div className="grid h-full place-items-center"><Spin tip="正在加载智能体" /></div>
  if (isAgentError || !resolvedAgent) return <Result status="404" title="智能体不存在或无权访问" subTitle="请从智能体列表选择可用智能体。" />
  const agent = resolvedAgent
  const createNewConversation = () => { setSelectedConversationId(null); setComposerValue(''); setOptimisticMessages([]) }
  const sendMessage = (content: string) => {
    const normalizedContent = content.trim()
    const optimisticUserMessage: ChatMessage = { content: normalizedContent, createdAt: new Date().toISOString(), generationStatus: 'complete', id: `pending-user-${Date.now()}`, role: 'user' }
    setOptimisticMessages([optimisticUserMessage]); setComposerValue('')
    sendMessageMutation.mutate({ agent, agentId: agent.id, conversationId: selectedConversationId, content: normalizedContent }, {
      onError: () => { setOptimisticMessages([]); setComposerValue(content); message.error('消息发送失败，请稍后重试') },
      onSuccess: result => { setSelectedConversationId(result.conversation.id); setOptimisticMessages([]) },
    })
  }

  return <section className="flex h-full min-h-[680px] flex-col overflow-hidden bg-white" aria-label={`${agent.name} 聊天页面`}>
    <header className="flex h-[70px] shrink-0 items-center justify-end gap-5 px-8"><Button className="!px-0 !font-medium !text-slate-700" icon={<PlusCircleOutlined />} type="text" onClick={createNewConversation}>新会话</Button><Button className="!px-0 !font-medium !text-slate-700" icon={<HistoryOutlined />} type="text" onClick={() => setHistoryOpen(true)}>历史记录</Button></header>
    {conversationsQuery.isError && <Alert className="mx-8" type="warning" showIcon message="历史会话加载失败" action={<Button size="small" onClick={() => void conversationsQuery.refetch()}>重试</Button>} />}
    {conversationDetailQuery.isError && <Alert className="mx-8" type="warning" showIcon message="会话详情加载失败" action={<Button size="small" onClick={() => void conversationDetailQuery.refetch()}>重试</Button>} />}
    <div className="flex min-h-0 flex-1 flex-col overflow-y-auto">{selectedConversationId === null && optimisticMessages.length === 0 ? <ChatWelcome agent={agent} onPromptClick={setComposerValue} /> : conversationDetailQuery.isPending && optimisticMessages.length === 0 ? <ChatHistorySkeleton /> : <ChatMessageList messages={[...(conversationDetailQuery.data?.messages ?? []), ...optimisticMessages]} pendingAssistant={sendMessageMutation.isPending} />}<ChatComposer agent={agent} sending={sendMessageMutation.isPending} value={composerValue} onChange={setComposerValue} onSubmit={sendMessage} /></div>
    <ConversationHistoryDrawer conversations={conversationsQuery.data?.items ?? []} creating={false} loading={conversationsQuery.isPending} open={historyOpen} selectedConversationId={selectedConversationId} onClose={() => setHistoryOpen(false)} onNewConversation={createNewConversation} onSelectConversation={conversationId => { setSelectedConversationId(conversationId); setOptimisticMessages([]) }} />
  </section>
}
