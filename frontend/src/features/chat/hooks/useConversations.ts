import { useQuery } from '@tanstack/react-query'
import { getConversations } from '../../../api/chat'

export function useConversations(agentId: string | undefined) {
  return useQuery({
    queryKey: ['chat', 'conversations', agentId],
    queryFn: () => getConversations(agentId!),
    enabled: Boolean(agentId),
  })
}
