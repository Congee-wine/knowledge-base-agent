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
  interactionType: 'text' | 'voice' | 'digital_human'
}

export type AgentListResponse = { items: ChatAgent[] }
