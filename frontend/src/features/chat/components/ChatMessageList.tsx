import { Bubble } from '@ant-design/x'
import { ArrowDownOutlined, CopyOutlined } from '@ant-design/icons'
import { Button, message, Tooltip } from 'antd'
import { XMarkdown } from '@ant-design/x-markdown'
import { useLayoutEffect, useRef, useState } from 'react'
import type { BubbleListRef } from '@ant-design/x/es/bubble'
import type { ChatMessage } from '../../../types/chat'

type Props = {
  className?: string
  messages: ChatMessage[]
  pendingAssistant: boolean
  scrollable?: boolean
  statusText?: string | null
}

export function ChatMessageList({
  className = 'w-full max-w-[810px] px-8 pt-3 lg:ml-[18%] lg:px-0',
  messages,
  pendingAssistant,
  scrollable = false,
  statusText,
}: Props) {
  const listRef = useRef<BubbleListRef>(null)
  const shouldFollowLatestRef = useRef(true)
  const [showScrollToBottom, setShowScrollToBottom] = useState(false)

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

  useLayoutEffect(() => {
    if (!scrollable || !shouldFollowLatestRef.current) return
    const list = listRef.current
    if (!list?.scrollBoxNativeElement) return
    list.scrollTo({ top: 'bottom', behavior: 'auto' })
  }, [messages, pendingAssistant, scrollable])

  const handleScroll = (event: React.UIEvent<HTMLElement>) => {
    const { clientHeight, scrollHeight, scrollTop } = event.currentTarget
    const isNearBottom = scrollHeight - scrollTop - clientHeight <= 24
    shouldFollowLatestRef.current = isNearBottom
    setShowScrollToBottom(current => current === !isNearBottom ? current : !isNearBottom)
  }

  return (
    <div className={`${className} ${scrollable ? 'relative flex min-h-0 flex-1 flex-col' : ''}`}>
      {statusText && <p className="mb-2 text-sm text-slate-400">{statusText}</p>}
      <Bubble.List
        ref={listRef}
        autoScroll={false}
        items={items}
        onScroll={handleScroll}
        role={{
          ai: {
            placement: 'start',
            styles: { content: { background: 'transparent', padding: 0 } },
            variant: 'borderless',
          },
          user: { placement: 'end', variant: 'filled' },
        }}
        styles={scrollable ? { root: { display: 'flex', flex: 1, minHeight: 0 }, scroll: { flex: 1, minHeight: 0 } } : undefined}
      />
      {scrollable && showScrollToBottom && (
        <Tooltip title="回到底部">
          <Button
            aria-label="回到底部"
            className="!absolute !bottom-4 !right-4"
            icon={<ArrowDownOutlined />}
            shape="circle"
            type="primary"
            onClick={() => listRef.current?.scrollTo({ top: 'bottom', behavior: 'smooth' })}
          />
        </Tooltip>
      )}
    </div>
  )
}
