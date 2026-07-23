import { request } from './http'
import { getStoredAccessToken } from '../lib/auth'
import type { ChatAgent, Conversation, ConversationDetail, SendMessageResult } from '../types/chat'

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
