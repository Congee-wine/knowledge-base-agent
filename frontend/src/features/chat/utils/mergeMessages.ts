import type { ChatMessage } from '../../../types/chat'

export function mergeMessages(
  serverMessages: ChatMessage[],
  localMessages: ChatMessage[],
  localAssistantPriorityIds: ReadonlySet<string>,
): ChatMessage[] {
  const messages = new Map<string, ChatMessage>()

  for (const message of serverMessages) {
    messages.set(message.id, message)
  }

  for (const message of localMessages) {
    const shouldOverrideServer =
      message.role === 'assistant' && localAssistantPriorityIds.has(message.id)

    if (!messages.has(message.id) || shouldOverrideServer) {
      messages.set(message.id, message)
    }
  }

  return [...messages.values()]
}
