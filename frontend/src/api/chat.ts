import { getApiBaseUrl, request } from './http'
import { getStoredAccessToken } from '../lib/auth'
import { parseSseChunk } from '../features/chat/streaming/sseParser'
import type { ChatAgent, ChatCitation, Conversation, ConversationDetail, SendMessageResult } from '../types/chat'

type StreamEventBase = {
  mode: 'conversation' | 'preview'
  requestId: string
  sequence: number
}

export type ChatStreamEvent =
  | ({
      type: 'message_start'
      mode: 'conversation'
      conversationId: string
      userMessageId: string
      assistantMessageId: string
    } & Omit<StreamEventBase, 'mode'>)
  | ({ type: 'message_start'; mode: 'preview' } & Omit<StreamEventBase, 'mode'>)
  | (StreamEventBase & { type: 'status'; stage: 'retrieving' | 'no_match' | 'retrieval_failed' | 'context' | 'generating'; text: string })
  | (StreamEventBase & { type: 'sources'; items: ChatCitation[] })
  | (StreamEventBase & { type: 'answer_delta'; content: string })
  | ({ type: 'message_end'; mode: 'conversation'; messageId: string; generationStatus: 'complete' | 'interrupted' } & Omit<StreamEventBase, 'mode'>)
  | ({ type: 'message_end'; mode: 'preview'; generationStatus: 'complete' | 'interrupted' } & Omit<StreamEventBase, 'mode'>)
  | (StreamEventBase & { type: 'error'; code: string; message: string; retryable: boolean })

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

function readRequiredString(value: Record<string, unknown>, field: string): string {
  const result = value[field]
  if (typeof result !== 'string' || result.length === 0) {
    throw new Error(`流式事件缺少有效字段：${field}`)
  }
  return result
}

function readString(value: Record<string, unknown>, field: string): string {
  const result = value[field]
  if (typeof result !== 'string') {
    throw new Error(`流式事件缺少字符串字段：${field}`)
  }
  return result
}

function readEvent(payload: unknown): ChatStreamEvent {
  if (typeof payload !== 'object' || payload === null || Array.isArray(payload)) {
    throw new Error('流式事件格式无效')
  }

  const event = payload as Record<string, unknown>
  const requestId = readRequiredString(event, 'requestId')
  const sequence = event.sequence
  const type = readRequiredString(event, 'type')
  const mode = readRequiredString(event, 'mode')
  if (typeof sequence !== 'number' || !Number.isInteger(sequence) || sequence < 1) {
    throw new Error('流式事件 sequence 无效')
  }
  if (mode !== 'conversation' && mode !== 'preview') {
    throw new Error('流式事件 mode 无效')
  }

  if (type === 'message_start') {
    if (mode === 'preview') return { type, mode, requestId, sequence }
    return {
      type,
      mode,
      requestId,
      sequence,
      conversationId: readRequiredString(event, 'conversationId'),
      userMessageId: readRequiredString(event, 'userMessageId'),
      assistantMessageId: readRequiredString(event, 'assistantMessageId'),
    }
  }
  if (type === 'status') {
    if (!['retrieving', 'no_match', 'retrieval_failed', 'context', 'generating'].includes(String(event.stage))) throw new Error('流式状态阶段无效')
    return { type, mode, requestId, sequence, stage: event.stage, text: readRequiredString(event, 'text') }
  }
  if (type === 'sources') {
    if (!Array.isArray(event.items)) throw new Error('引用事件格式无效')
    return { type, mode, requestId, sequence, items: event.items as ChatCitation[] }
  }
  if (type === 'answer_delta') return { type, mode, requestId, sequence, content: readString(event, 'content') }
  if (type === 'message_end') {
    if (event.generationStatus !== 'complete' && event.generationStatus !== 'interrupted') throw new Error('流式结束状态无效')
    if (mode === 'preview') return { type, mode, requestId, sequence, generationStatus: event.generationStatus }
    return { type, mode, requestId, sequence, messageId: readRequiredString(event, 'messageId'), generationStatus: event.generationStatus }
  }
  if (type === 'error') {
    if (typeof event.retryable !== 'boolean') throw new Error('流式错误事件 retryable 无效')
    return {
      type,
      mode,
      requestId,
      sequence,
      message: readRequiredString(event, 'message'),
      code: readRequiredString(event, 'code'),
      retryable: event.retryable,
    }
  }
  throw new Error(`不支持的流式事件类型：${type}`)
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

export function interruptStreamMessage(assistantMessageId: string, content: string) {
  return request<{ id: string; generationStatus: 'interrupted' }>(
    `/api/conversations/messages/${encodeURIComponent(assistantMessageId)}:interrupt`,
    { body: { content }, headers: authorizationHeader(), method: 'POST' },
  )
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
    const parsed = parseSseChunk(pending, decoder.decode(value, { stream: !done }), done)
    pending = parsed.pending
    for (const payload of parsed.frames) options.onEvent(readEvent(payload))
    if (done) return
  }
}
