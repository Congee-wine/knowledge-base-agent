import { getApiBaseUrl, request } from './http'
import { getStoredAccessToken } from '../lib/auth'
import type { ChatAgent, Conversation, ConversationDetail, SendMessageResult } from '../types/chat'

export type ChatStreamEvent = {
  type: 'message_start' | 'status' | 'answer_delta' | 'message_end' | 'error'
  requestId: string
  sequence: number
  content?: string
  conversationId?: string
  userMessageId?: string
  assistantMessageId?: string
  messageId?: string
  generationStatus?: 'complete' | 'interrupted'
  message?: string
  text?: string
}

type StreamOptions = {
  path: string
  body: unknown
  signal?: AbortSignal
  onEvent: (event: ChatStreamEvent) => void
}

function authorizationHeader() {
  const accessToken = getStoredAccessToken()
  if (!accessToken) throw new Error('登录已过期，请重新登录')
  return { Authorization: `Bearer ${accessToken}` }
}

export function getChatEntry() {
  return request<{ agent: ChatAgent }>('/api/chat/entry', { headers: authorizationHeader() })
}

export function getConversations(agentId: string) {
  return request<{ items: Conversation[] }>('/api/conversations?agentId=' + encodeURIComponent(agentId), {
    headers: authorizationHeader(),
  })
}

export function createConversation(agentId: string) {
  return request<Conversation>('/api/conversations', {
    body: { agentId },
    headers: authorizationHeader(),
    method: 'POST',
  })
}

export function getConversation(conversationId: string) {
  return request<ConversationDetail>(`/api/conversations/${encodeURIComponent(conversationId)}`, {
    headers: authorizationHeader(),
  })
}

export function sendMessage(input: { agentId: string; conversationId: string | null; content: string }) {
  return request<SendMessageResult>('/api/conversations/messages', {
    body: input.conversationId === null
      ? { agentId: input.agentId, content: input.content }
      : { agentId: input.agentId, conversationId: input.conversationId, content: input.content },
    headers: authorizationHeader(),
    method: 'POST',
  })
}

export async function streamChat(options: StreamOptions): Promise<void> {
  const response = await fetch(`${getApiBaseUrl()}${options.path}`, {
    body: JSON.stringify(options.body),
    headers: { ...authorizationHeader(), 'Content-Type': 'application/json' },
    method: 'POST',
    signal: options.signal,
  })
  if (!response.ok || response.body === null) {
    const data: unknown = await response.json().catch(() => undefined)
    const detail = typeof data === 'object' && data !== null && 'detail' in data ? data.detail : undefined
    throw new Error(typeof detail === 'string' ? detail : '流式请求未能建立')
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let pending = ''
  while (true) {
    const { done, value } = await reader.read()
    pending += decoder.decode(value, { stream: !done })
    const frames = pending.split('\n\n')
    pending = frames.pop() ?? ''
    for (const frame of frames) {
      const dataLine = frame.split('\n').find(line => line.startsWith('data: '))
      if (!dataLine) continue
      options.onEvent(JSON.parse(dataLine.slice(6)) as ChatStreamEvent)
    }
    if (done) return
  }
}
