export type KnowledgeItemKind = 'folder' | 'pdf' | 'markdown' | 'word'

export type KnowledgeItem = {
  id: string
  kind: KnowledgeItemKind
  name: string
  size?: string
}
