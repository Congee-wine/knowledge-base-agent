import { useCallback, useRef, useState, type Dispatch, type MutableRefObject, type SetStateAction } from 'react'
import { streamChat, type ChatStreamEvent } from '../../../api/chat'
import type { ChatAgent, ChatMessage, Conversation } from '../../../types/chat'

type SendStreamInput = {
  agent: ChatAgent
  content: string
  conversationId: string | null
  preview?: boolean
}

type PendingPersistedPair = {
  requestId: string
  conversationId: string
  userMessageId: string
  assistantMessageId: string
}

type StreamState = {
  conversation: Conversation | null
  error: string | null
  messages: ChatMessage[]
  sending: boolean
  statusText: string | null
  userMessageId: string | null
  assistantMessageId: string | null
  pendingPersistedPairs: PendingPersistedPair[]
}

const initialState: StreamState = {
  conversation: null,
  error: null,
  messages: [],
  sending: false,
  statusText: null,
  userMessageId: null,
  assistantMessageId: null,
  pendingPersistedPairs: [],
}

function createRequestId() {
  return crypto.randomUUID()
}

export function useStreamingChat() {
  const [state, setState] = useState<StreamState>(initialState)
  const lastSequence = useRef(0)

  const reset = useCallback(() => {
    lastSequence.current = 0
    setState(initialState)
  }, [])

  const acknowledgePersistedPair = useCallback((requestId: string) => {
    setState(current => {
      const pair = current.pendingPersistedPairs.find(item => item.requestId === requestId)
      if (!pair) return current

      return {
        ...current,
        messages: current.messages.filter(
          message => message.id !== pair.userMessageId && message.id !== pair.assistantMessageId,
        ),
        pendingPersistedPairs: current.pendingPersistedPairs.filter(
          item => item.requestId !== requestId,
        ),
      }
    })
  }, [])

  const send = useCallback(async ({ agent, content, conversationId, preview = false }: SendStreamInput) => {
    const requestId = createRequestId()
    const createdAt = new Date().toISOString()
    const userMessage: ChatMessage = { content, createdAt, generationStatus: 'complete', id: `local-user-${requestId}`, role: 'user' }
    const assistantMessage: ChatMessage = { content: '', createdAt, generationStatus: 'generating', id: `local-assistant-${requestId}`, role: 'assistant' }
    lastSequence.current = 0
    setState(current => ({
      ...current,
      error: null,
      messages: [...current.messages, userMessage, assistantMessage],
      sending: true,
      statusText: '正在生成回答',
      userMessageId: null,
      assistantMessageId: null,
    }))
    const path = preview
      ? `/api/agents/${encodeURIComponent(agent.id)}/preview/messages:stream`
      : `/api/conversations/messages:stream?agentId=${encodeURIComponent(agent.id)}${conversationId ? `&conversationId=${encodeURIComponent(conversationId)}` : ''}`
    const body = preview
      ? { content, draftAgent: agent, history: state.messages.map(message => ({ content: message.content, role: message.role })), requestId }
      : { content, requestId }

    try {
      await streamChat({ body, path, onEvent: event => applyEvent(event, requestId, preview ? 'preview' : 'conversation', setState, lastSequence) })
    } catch (error) {
      const text = error instanceof Error ? error.message : '发送失败，请稍后重试'
      setState(current => ({ ...current, error: text, messages: updateAssistant(current.messages, current.assistantMessageId, requestId, message => ({ ...message, generationStatus: 'failed' })), sending: false }))
    }
  }, [state.messages])

  return { ...state, acknowledgePersistedPair, reset, send }
}

function applyEvent(event: ChatStreamEvent, requestId: string, mode: ChatStreamEvent['mode'], setState: Dispatch<SetStateAction<StreamState>>, lastSequence: MutableRefObject<number>) {
  if (event.requestId !== requestId || event.mode !== mode || event.sequence <= lastSequence.current) return
  lastSequence.current = event.sequence
  setState(current => {
    if (event.type === 'status') return { ...current, statusText: event.text }

    if (event.type === 'answer_delta') return { ...current, messages: updateAssistant(current.messages, current.assistantMessageId, requestId, message => ({ ...message, content: message.content + event.content })) }

    if (event.type === 'message_start') {
      if (event.mode === 'preview') return current
      return {
        ...current,
        conversation: { agentId: '', createdAt: '', id: event.conversationId, title: null, updatedAt: '' },
        userMessageId: event.userMessageId,
        assistantMessageId: event.assistantMessageId,
        messages: current.messages.map(message => {
          if (message.id === `local-user-${requestId}`) return { ...message, id: event.userMessageId }
          if (message.id === `local-assistant-${requestId}`) return { ...message, id: event.assistantMessageId }
          return message
        }),
      }
    }

    if (event.type === 'message_end') {
      if (event.mode === 'preview') {
        return {
          ...current,
          messages: updateAssistant(current.messages, null, requestId, message => ({ ...message, generationStatus: event.generationStatus })),
          sending: false,
          statusText: null,
        }
      }
      const userMessageId = current.userMessageId
      const assistantMessageId = current.assistantMessageId
      const conversationId = current.conversation?.id

      const messages = updateAssistant(current.messages, assistantMessageId, requestId, message => ({
        ...message,
        id: event.messageId,
        generationStatus: event.generationStatus,
      }))

      const pendingPair: PendingPersistedPair | null =
        conversationId && userMessageId && assistantMessageId
          ? { requestId, conversationId, userMessageId, assistantMessageId }
          : null

      return {
        ...current,
        messages,
        sending: false,
        statusText: null,
        userMessageId: null,
        assistantMessageId: null,
        pendingPersistedPairs: pendingPair
          ? [...current.pendingPersistedPairs, pendingPair]
          : current.pendingPersistedPairs,
      }
    }

    if (event.type === 'error') return { ...current, error: event.message, messages: updateAssistant(current.messages, current.assistantMessageId, requestId, message => ({ ...message, generationStatus: 'failed' })), sending: false, statusText: null }

    return current
  })
}

function updateAssistant(
  messages: ChatMessage[],
  assistantMessageId: string | null,
  requestId: string,
  update: (message: ChatMessage) => ChatMessage,
) {
  const targetId = assistantMessageId ?? `local-assistant-${requestId}`
  return messages.map(message => (message.id === targetId ? update(message) : message))
}
