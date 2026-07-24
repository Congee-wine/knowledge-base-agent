import type { ChatAgent } from './chat'

export type AgentFormValues = {
  name: string
  description: string | null
  avatarKey: string | null
  systemPrompt: string | null
  welcomeMessage: string | null
  presetQuestions: string[]
  allowConversationUpload: boolean
  allowNetworkAccess: boolean
}

export type AgentListResponse = { items: ChatAgent[] }
