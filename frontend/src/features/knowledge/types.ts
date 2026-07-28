export type KnowledgeItemKind = 'folder' | 'pdf' | 'markdown' | 'word'
export type KnowledgeActionId = 'open' | 'preview' | 'edit' | 'rename' | 'move' | 'download' | 'delete'

export type KnowledgeItem = {
  id: string
  kind: KnowledgeItemKind
  name: string
  size?: string
  parentId?: string
  actions?: KnowledgeActionId[]
  shortcuts?: Partial<Record<KnowledgeActionId, string>>
  ownerName?: string
  isBuiltin?: boolean
}
