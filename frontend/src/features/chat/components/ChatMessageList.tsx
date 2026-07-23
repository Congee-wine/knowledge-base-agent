import { Bubble } from '@ant-design/x'
import type { ChatMessage } from '../../../types/chat'

type Props = { messages: ChatMessage[]; pendingAssistant: boolean }

export function ChatMessageList({ messages, pendingAssistant }: Props) {
  const items = [
    ...messages.map(message => ({
      content: message.content,
      key: message.id,
      role: message.role === 'user' ? 'user' : 'ai',
    })),
    ...(pendingAssistant ? [{ content: '', key: 'pending-assistant', loading: true, role: 'ai' }] : []),
  ]

  return (
    <div className="w-full max-w-[810px] px-8 pt-3 lg:ml-[18%] lg:px-0">
      <Bubble.List
        autoScroll
        items={items}
        role={{
          ai: { placement: 'start', variant: 'filled' },
          user: { placement: 'end', variant: 'filled' },
        }}
      />
    </div>
  )
}
