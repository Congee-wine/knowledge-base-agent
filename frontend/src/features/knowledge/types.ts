export type KnowledgeItemKind = 'folder' | 'pdf' | 'markdown' | 'word'
export type KnowledgeActionId = 'open' | 'preview' | 'edit' | 'rename' | 'move' | 'download' | 'delete' | 'retry-embedding'
export type KnowledgeProcessingStatus = 'uploaded' | 'processing' | 'ready' | 'failed'

export type KnowledgeItem = {
  id: string
  kind: KnowledgeItemKind
  name: string
  size?: string
  processingStatus?: KnowledgeProcessingStatus
  indexStatus?: 'pending' | 'processing' | 'ready' | 'failed'
  parentId?: string
  actions?: KnowledgeActionId[]
  shortcuts?: Partial<Record<KnowledgeActionId, string>>
  ownerName?: string
  isBuiltin?: boolean
}
