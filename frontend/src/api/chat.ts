import { request } from './http'
import { getStoredAccessToken } from '../lib/auth'
import type { ChatAgent, Conversation } from '../types/chat'

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
