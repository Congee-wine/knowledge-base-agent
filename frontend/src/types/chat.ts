export type AgentKind = 'builtin' | 'personal'

export type ChatAgent = {
  id: string
  kind: AgentKind
  name: string
  description: string | null
  avatarKey: string | null
  welcomeMessage: string | null
  presetQuestions: string[]
  allowConversationUpload: boolean
}

export type Conversation = {
  id: string
  agentId: string
  title: string | null
  createdAt: string
  updatedAt: string
}
