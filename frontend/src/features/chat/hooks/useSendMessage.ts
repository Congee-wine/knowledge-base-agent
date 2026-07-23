import { useMutation, useQueryClient } from '@tanstack/react-query'
import { sendMessage } from '../../../api/chat'
import type { ChatAgent, ConversationDetail } from '../../../types/chat'

type SendInput = {
  agent: ChatAgent
  agentId: string
  conversationId: string | null
  content: string
}

export function useSendMessage() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ agent: _agent, ...input }: SendInput) => sendMessage(input),
    onSuccess: (result, input) => {
      const conversationKey = ['chat', 'conversation', result.conversation.id] as const
      const existingDetail = queryClient.getQueryData<ConversationDetail>(conversationKey)
      queryClient.setQueryData<ConversationDetail>(conversationKey, {
        ...result.conversation,
        agent: existingDetail?.agent ?? input.agent,
        messages: [...(existingDetail?.messages ?? []), result.userMessage, result.assistantMessage],
      })
      void queryClient.invalidateQueries({ queryKey: ['chat', 'conversations', result.conversation.agentId] })
    },
  })
}
