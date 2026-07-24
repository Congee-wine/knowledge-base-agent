import { getStoredAccessToken } from '../lib/auth'
import type { AgentFormValues, AgentListResponse } from '../types/agents'
import type { ChatAgent } from '../types/chat'
import { request, requestBlob, requestForm } from './http'

function authorizationHeader() {
  const accessToken = getStoredAccessToken()
  if (!accessToken) throw new Error('登录已过期，请重新登录')
  return { Authorization: `Bearer ${accessToken}` }
}

export function getAgents() {
  return request<AgentListResponse>('/api/agents', { headers: authorizationHeader() })
}

export function getAgent(agentId: string) {
  return request<ChatAgent>(`/api/agents/${encodeURIComponent(agentId)}`, { headers: authorizationHeader() })
}

export function createAgent(values: AgentFormValues) {
  return request<ChatAgent>('/api/agents', { body: values, headers: authorizationHeader(), method: 'POST' })
}

export type AgentBootstrapValues = {
  name: string
  description: string
  avatar: File | null
}

export function bootstrapAgent(values: AgentBootstrapValues) {
  const formData = new FormData()
  formData.set('name', values.name)
  if (values.description) formData.set('description', values.description)
  if (values.avatar) formData.set('avatar', values.avatar)
  return requestForm<ChatAgent>('/api/agents/bootstrap', formData, { headers: authorizationHeader(), method: 'POST' })
}

export function getAgentAvatar(agentId: string) {
  return requestBlob(`/api/agents/${encodeURIComponent(agentId)}/avatar`, { headers: authorizationHeader() })
}

export function updateAgent(agentId: string, values: AgentFormValues) {
  return request<ChatAgent>(`/api/agents/${encodeURIComponent(agentId)}`, { body: values, headers: authorizationHeader(), method: 'PATCH' })
}

export function deleteAgent(agentId: string) {
  return request<void>(`/api/agents/${encodeURIComponent(agentId)}`, { headers: authorizationHeader(), method: 'DELETE' })
}

export function setDefaultAgent(agentId: string) {
  return request<{ defaultAgentId: string }>(`/api/agents/${encodeURIComponent(agentId)}/default`, { headers: authorizationHeader(), method: 'PUT' })
}

export function clearDefaultAgent() {
  return request<void>('/api/agents/default', { headers: authorizationHeader(), method: 'DELETE' })
}
