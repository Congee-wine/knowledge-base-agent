import { useCallback, useRef, useState, type Dispatch, type MutableRefObject, type SetStateAction } from 'react'
import { streamChat, type ChatStreamEvent } from '../../../api/chat'
import type { ChatAgent, ChatMessage, Conversation } from '../../../types/chat'

type SendStreamInput = {
  agent: ChatAgent
  content: string
  conversationId: string | null
  preview?: boolean
}

type StreamState = {
  conversation: Conversation | null
  error: string | null
  messages: ChatMessage[]
  sending: boolean
  statusText: string | null
}

const initialState: StreamState = { conversation: null, error: null, messages: [], sending: false, statusText: null }

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

  const send = useCallback(async ({ agent, content, conversationId, preview = false }: SendStreamInput) => {
    const requestId = createRequestId()
    const createdAt = new Date().toISOString()
    const userMessage: ChatMessage = { content, createdAt, generationStatus: 'complete', id: `local-user-${requestId}`, role: 'user' }
    const assistantMessage: ChatMessage = { content: '', createdAt, generationStatus: 'generating', id: `local-assistant-${requestId}`, role: 'assistant' }
    lastSequence.current = 0
    setState(current => ({ ...current, error: null, messages: [...current.messages, userMessage, assistantMessage], sending: true, statusText: '正在生成回答' }))
    const path = preview
      ? `/api/agents/${encodeURIComponent(agent.id)}/preview/messages:stream`
      : `/api/conversations/messages:stream?agentId=${encodeURIComponent(agent.id)}${conversationId ? `&conversationId=${encodeURIComponent(conversationId)}` : ''}`
    const body = preview
      ? { content, draftAgent: agent, history: state.messages.map(message => ({ content: message.content, role: message.role })), requestId }
      : { content, requestId }

    try {
      await streamChat({ body, path, onEvent: event => applyEvent(event, requestId, setState, lastSequence) })
    } catch (error) {
      const text = error instanceof Error ? error.message : '发送失败，请稍后重试'
      setState(current => ({ ...current, error: text, messages: updateAssistant(current.messages, requestId, message => ({ ...message, generationStatus: 'failed' })), sending: false }))
    }
  }, [state.messages])

  return { ...state, reset, send }
}

function applyEvent(event: ChatStreamEvent, requestId: string, setState: Dispatch<SetStateAction<StreamState>>, lastSequence: MutableRefObject<number>) {
  if (event.requestId !== requestId || event.sequence <= lastSequence.current) return
  lastSequence.current = event.sequence
  setState(current => {
    if (event.type === 'status') return { ...current, statusText: event.text ?? '正在生成回答' }
    if (event.type === 'answer_delta') return { ...current, messages: updateAssistant(current.messages, requestId, message => ({ ...message, content: message.content + (event.content ?? '') })) }
    if (event.type === 'message_start' && event.conversationId) return { ...current, conversation: { agentId: '', createdAt: '', id: event.conversationId, title: null, updatedAt: '' } }
    if (event.type === 'message_end') return { ...current, messages: updateAssistant(current.messages, requestId, message => ({ ...message, generationStatus: 'complete', id: event.messageId ?? message.id })), sending: false, statusText: null }
    if (event.type === 'error') return { ...current, error: event.message ?? '模型服务不可用', messages: updateAssistant(current.messages, requestId, message => ({ ...message, generationStatus: 'failed' })), sending: false, statusText: null }
    return current
  })
}

function updateAssistant(messages: ChatMessage[], requestId: string, update: (message: ChatMessage) => ChatMessage) {
  const messageId = `local-assistant-${requestId}`
  return messages.map(message => message.id === messageId ? update(message) : message)
}
