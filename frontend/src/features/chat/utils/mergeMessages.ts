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
    const existingMessage = messages.get(message.id)
    const shouldOverrideServer =
      message.role === 'assistant' && localAssistantPriorityIds.has(message.id)

    if (!existingMessage || shouldOverrideServer) {
      messages.set(message.id, message)
    } else if (message.role === 'assistant' && message.runSteps?.length) {
      messages.set(message.id, { ...existingMessage, runSteps: message.runSteps })
    }
  }

  return [...messages.values()]
}
