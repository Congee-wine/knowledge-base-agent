export const agentKeys = {
  all: ['agents'] as const,
  detail: (agentId: string) => ['agents', agentId] as const,
  entry: ['chat', 'entry'] as const,
}
