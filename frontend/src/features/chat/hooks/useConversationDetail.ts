import { useQuery } from '@tanstack/react-query'
import { getConversation } from '../../../api/chat'

const CONVERSATION_DETAIL_STALE_TIME_MS = 30_000

export function useConversationDetail(conversationId: string | null) {
  return useQuery({
    queryKey: ['chat', 'conversation', conversationId],
    queryFn: () => getConversation(conversationId!),
    enabled: Boolean(conversationId),
    staleTime: CONVERSATION_DETAIL_STALE_TIME_MS,
  })
}
