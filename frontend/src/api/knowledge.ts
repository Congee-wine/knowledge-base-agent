import { getStoredAccessToken } from '../lib/auth'
import { getApiBaseUrl, ApiError, request, requestForm } from './http'

export type KnowledgeNode = {
  id: string
  parentId: string | null
  nodeType: 'folder' | 'file'
  name: string
  status: 'uploaded' | 'processing' | 'ready' | 'failed' | null
  mimeType: string | null
  byteSize: number | null
  createdAt: string
  updatedAt: string
  children: KnowledgeNode[]
}

type KnowledgeTreeResponse = { items: KnowledgeNode[] }

export type DocumentPreview =
  | { kind: 'pdf'; name: string; blob: Blob }
  | { kind: 'text'; name: string; content: string; isMarkdown: boolean }
  | { kind: 'html'; name: string; html: string }

function authorizationHeader() {
  const accessToken = getStoredAccessToken()
  if (!accessToken) throw new Error('登录已过期，请重新登录')
  return { Authorization: `Bearer ${accessToken}` }
}

export function getKnowledgeTree() {
  return request<KnowledgeTreeResponse>('/api/knowledge/nodes', { headers: authorizationHeader() })
}

export function createKnowledgeFolder(parentId: string | null, name: string) {
  return request<KnowledgeNode>('/api/knowledge/nodes', { body: { parentId, name }, headers: authorizationHeader(), method: 'POST' })
}

export function renameKnowledgeNode(nodeId: string, name: string) {
  return request<KnowledgeNode>(`/api/knowledge/nodes/${encodeURIComponent(nodeId)}`, { body: { name }, headers: authorizationHeader(), method: 'PATCH' })
}

export function moveKnowledgeNode(nodeId: string, parentId: string | null) {
  return request<KnowledgeNode>(`/api/knowledge/nodes/${encodeURIComponent(nodeId)}`, { body: { parentId }, headers: authorizationHeader(), method: 'PATCH' })
}

export function deleteKnowledgeNode(nodeId: string) {
  return request<void>(`/api/knowledge/nodes/${encodeURIComponent(nodeId)}`, { headers: authorizationHeader(), method: 'DELETE' })
}

export function uploadKnowledgeFile(parentId: string | null, file: File) {
  const formData = new FormData()
  if (parentId) formData.set('parentId', parentId)
  formData.set('file', file)
  return requestForm<KnowledgeNode>('/api/knowledge/files', formData, { headers: authorizationHeader(), method: 'POST' })
}

export async function getDocumentPreview(nodeId: string): Promise<DocumentPreview> {
  const response = await fetch(`${getApiBaseUrl()}/api/knowledge/files/${encodeURIComponent(nodeId)}/preview`, { headers: authorizationHeader() })
  if (!response.ok) {
    const data: unknown = await response.json().catch(() => undefined)
    throw new ApiError(response.status, data, '文件预览失败，请稍后重试')
  }
  if (response.headers.get('content-type')?.includes('application/pdf')) {
    return { kind: 'pdf', name: decodePreviewName(response.headers.get('x-document-name')), blob: await response.blob() }
  }
  return await response.json() as Exclude<DocumentPreview, { kind: 'pdf' }>
}

function decodePreviewName(encodedName: string | null) {
  if (!encodedName) return 'document.pdf'
  try {
    return decodeURIComponent(encodedName)
  } catch {
    return 'document.pdf'
  }
}
