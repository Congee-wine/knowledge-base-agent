export type AgentKind = 'builtin' | 'personal'

export type ChatAgent = {
  id: string
  kind: AgentKind
  name: string
  description: string | null
  avatarKey: string | null
  systemPrompt: string | null
  welcomeMessage: string | null
  presetQuestions: string[]
  allowConversationUpload: boolean
  allowNetworkAccess: boolean
  interactionType: 'text' | 'voice' | 'digital_human'
  createdAt: string
  updatedAt: string
}

export type Conversation = {
  id: string
  agentId: string
  title: string | null
  createdAt: string
  updatedAt: string
}

export type ChatMessage = {
  id: string
  role: 'user' | 'assistant'
  content: string
  generationStatus: 'generating' | 'complete' | 'interrupted' | 'failed'
  createdAt: string
}

export type ConversationDetail = Conversation & {
  agent: ChatAgent
  messages: ChatMessage[]
}

export type SendMessageResult = {
  conversation: Conversation
  userMessage: ChatMessage
  assistantMessage: ChatMessage
}
