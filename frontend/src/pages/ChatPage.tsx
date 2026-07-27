import { useEffect, useMemo, useState } from 'react'
import { HistoryOutlined, PlusCircleOutlined } from '@ant-design/icons'
import { Alert, Button, Result, Spin } from 'antd'
import { useQueryClient } from '@tanstack/react-query'
import { useParams } from 'react-router-dom'
import { ChatComposer } from '../features/chat/components/ChatComposer'
import { ChatHistorySkeleton } from '../features/chat/components/ChatHistorySkeleton'
import { ChatMessageList } from '../features/chat/components/ChatMessageList'
import { ChatWelcome } from '../features/chat/components/ChatWelcome'
import { ConversationHistoryDrawer } from '../features/chat/components/ConversationHistoryDrawer'
import { useAgent } from '../features/agents/hooks/useAgent'
import type { Conversation } from '../types/chat'
import { useChatEntry } from '../features/chat/hooks/useChatEntry'
import { useConversationDetail } from '../features/chat/hooks/useConversationDetail'
import { useConversations } from '../features/chat/hooks/useConversations'
import { useStreamingChat } from '../features/chat/hooks/useStreamingChat'
import { mergeMessages } from '../features/chat/utils/mergeMessages'

export function ChatPage() {
  const { agentId } = useParams()
  const [historyOpen, setHistoryOpen] = useState(false)
  const [composerValue, setComposerValue] = useState('')
  const [selectedConversationId, setSelectedConversationId] = useState<string | null>(null)
  const entryQuery = useChatEntry(!agentId)
  const agentQuery = useAgent(agentId)
  const resolvedAgent = agentId ? agentQuery.data : entryQuery.data?.agent
  const isAgentPending = agentId ? agentQuery.isPending : entryQuery.isPending
  const isAgentError = agentId ? agentQuery.isError : entryQuery.isError
  const conversationsQuery = useConversations(resolvedAgent?.id)
  const conversationDetailQuery = useConversationDetail(selectedConversationId)
  const streaming = useStreamingChat()
  const stream = streaming.getStream(selectedConversationId)
  const queryClient = useQueryClient()
  const { acknowledgePersistedPair, pendingPersistedPairs } = streaming

  useEffect(() => {
    void streaming.stop()
    setSelectedConversationId(null)
    setComposerValue('')
    streaming.reset()
  }, [resolvedAgent?.id, streaming.reset, streaming.stop])

  useEffect(() => {
    if (!resolvedAgent?.id) return
    for (const pair of pendingPersistedPairs) {
      void queryClient.invalidateQueries({ queryKey: ['chat', 'conversation', pair.conversationId] })
      void queryClient.invalidateQueries({ queryKey: ['chat', 'conversations', resolvedAgent.id] })
    }
  }, [pendingPersistedPairs, queryClient, resolvedAgent?.id])

  useEffect(() => {
    const serverMessages = conversationDetailQuery.data?.messages ?? []
    for (const pair of pendingPersistedPairs) {
      if (pair.conversationId !== selectedConversationId) continue
      const hasCompletedUser = serverMessages.some(message => message.id === pair.userMessageId)
      const hasCompletedAssistant = serverMessages.some(
        message => message.id === pair.assistantMessageId && message.generationStatus === 'complete',
      )
      if (hasCompletedUser && hasCompletedAssistant) {
        acknowledgePersistedPair(pair.requestId)
      }
    }
  }, [acknowledgePersistedPair, conversationDetailQuery.data?.messages, pendingPersistedPairs, selectedConversationId])

  const localAssistantPriorityIds = useMemo(() => {
    const ids = new Set<string>()
    for (const message of stream.messages) {
      if (message.role === 'assistant' && (stream.sending || pendingPersistedPairs.some(pair => pair.assistantMessageId === message.id))) {
        ids.add(message.id)
      }
    }
    return ids
  }, [pendingPersistedPairs, stream.messages, stream.sending])

  const displayedMessages = mergeMessages(
    conversationDetailQuery.data?.messages ?? [],
    stream.messages,
    localAssistantPriorityIds,
  )

  if (isAgentPending) return <div className="grid h-full place-items-center"><Spin tip="正在加载智能体" /></div>
  if (isAgentError || !resolvedAgent) return <Result status="404" title="智能体不存在或无权访问" subTitle="请从智能体列表选择可用智能体。" />
  const agent = resolvedAgent

  const createNewConversation = () => {
    setSelectedConversationId(null)
    setComposerValue('')
  }
  const sendMessage = (content: string) => {
    const normalizedContent = content.trim()
    if (!normalizedContent || stream.sending) return
    setComposerValue('')
    void streaming.send({
      agent,
      content: normalizedContent,
      conversationId: selectedConversationId,
      onConversationCreated: conversationId => {
        const now = new Date().toISOString()
        const createdConversation: Conversation = {
          agentId: agent.id,
          createdAt: now,
          id: conversationId,
          title: normalizedContent.slice(0, 50),
          updatedAt: now,
        }
        queryClient.setQueryData<{ items: Conversation[] }>(['chat', 'conversations', agent.id], current => ({
          items: [createdConversation, ...(current?.items ?? []).filter(item => item.id !== conversationId)],
        }))
        setSelectedConversationId(current => current ?? conversationId)
      },
    })
  }

  return (
    <section className="flex h-full min-h-[680px] flex-col overflow-hidden bg-white" aria-label={`${agent.name} 聊天页面`}>
      <header className="flex h-[70px] shrink-0 items-center justify-end gap-5 px-8">
        <Button className="!px-0 !font-medium !text-slate-700" icon={<PlusCircleOutlined />} type="text" onClick={createNewConversation}>新会话</Button>
        <Button className="!px-0 !font-medium !text-slate-700" icon={<HistoryOutlined />} type="text" onClick={() => setHistoryOpen(true)}>历史记录</Button>
      </header>
      {conversationsQuery.isError && <Alert className="mx-8" type="warning" showIcon message="历史会话加载失败" action={<Button size="small" onClick={() => void conversationsQuery.refetch()}>重试</Button>} />}
      {conversationDetailQuery.isError && <Alert className="mx-8" type="warning" showIcon message="会话详情加载失败" action={<Button size="small" onClick={() => void conversationDetailQuery.refetch()}>重试</Button>} />}
      <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
        {selectedConversationId === null && stream.messages.length === 0
          ? <ChatWelcome agent={agent} onPromptClick={setComposerValue} />
          : conversationDetailQuery.isPending && stream.messages.length === 0
            ? <ChatHistorySkeleton />
            : <ChatMessageList messages={displayedMessages} pendingAssistant={false} scrollable statusText={stream.statusText} />}
        {stream.error && <Alert className="mx-auto mt-3 w-full max-w-[810px]" message={stream.error} showIcon type="error" />}
      </div>
      <ChatComposer agent={agent} sending={stream.sending} value={composerValue} onChange={setComposerValue} onStop={() => void streaming.stop(selectedConversationId)} onSubmit={sendMessage} />
      <ConversationHistoryDrawer
        conversations={conversationsQuery.data?.items ?? []}
        creating={false}
        loading={conversationsQuery.isPending}
        open={historyOpen}
        selectedConversationId={selectedConversationId}
        onClose={() => setHistoryOpen(false)}
        onNewConversation={createNewConversation}
        onSelectConversation={conversationId => setSelectedConversationId(conversationId)}
      />
    </section>
  )
}
