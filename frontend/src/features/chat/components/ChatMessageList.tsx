import { Bubble } from '@ant-design/x'
import { CopyOutlined } from '@ant-design/icons'
import { Button, message, Tooltip } from 'antd'
import { XMarkdown } from '@ant-design/x-markdown'
import type { ChatMessage } from '../../../types/chat'

type Props = { className?: string; messages: ChatMessage[]; pendingAssistant: boolean; statusText?: string | null }

export function ChatMessageList({ className = 'w-full max-w-[810px] px-8 pt-3 lg:ml-[18%] lg:px-0', messages, pendingAssistant, statusText }: Props) {
  const copyMessage = async (content: string) => {
    try {
      await navigator.clipboard.writeText(content)
      message.success('已复制')
    } catch {
      message.error('复制失败，请手动复制内容')
    }
  }

  const items = [
    ...messages.map(message => ({
      content: message.role === 'assistant'
        ? <XMarkdown content={message.content} streaming={{ hasNextChunk: message.generationStatus === 'generating', tail: true }} />
        : message.content,
      key: message.id,
      loading: message.role === 'assistant' && message.generationStatus === 'generating' && !message.content,
      role: message.role === 'user' ? 'user' : 'ai',
      footer: message.role === 'assistant' && message.content
        ? <Tooltip title="复制">
            <Button aria-label="复制" icon={<CopyOutlined />} size="small" type="text" onClick={() => void copyMessage(message.content)} />
          </Tooltip>
        : undefined,
      footerPlacement: 'outer-start' as const,
    })),
    ...(pendingAssistant ? [{ content: '', key: 'pending-assistant', loading: true, role: 'ai' }] : []),
  ]

  return (
    <div className={className}>
      {statusText && <p className="mb-2 text-sm text-slate-400">{statusText}</p>}
      <Bubble.List
        autoScroll
        items={items}
        role={{
          ai: {
            placement: 'start',
            styles: { content: { background: 'transparent', padding: 0 } },
            variant: 'borderless',
          },
          user: { placement: 'end', variant: 'filled' },
        }}
      />
    </div>
  )
}
