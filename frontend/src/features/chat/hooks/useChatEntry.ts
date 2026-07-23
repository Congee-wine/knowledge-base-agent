import { useQuery } from '@tanstack/react-query'
import { getChatEntry } from '../../../api/chat'

export function useChatEntry() {
  return useQuery({ queryKey: ['chat', 'entry'], queryFn: getChatEntry })
}
