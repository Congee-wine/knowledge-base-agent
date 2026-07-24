export const routes = {
  home: '/',
  login: '/login',
  register: '/register',
  app: {
    root: '/app',
    chat: '/app/chat',
    chatAgent: (agentId: string) => `/app/chat/agents/${agentId}`,
    agents: '/app/agents',
    agentNew: '/app/agents/new',
    agentEdit: (agentId: string) => `/app/agents/${agentId}/edit`,
    knowledgeBases: '/app/knowledge-bases',
  },
} as const
