import { Bubble } from '@ant-design/x'
import { ArrowDownOutlined, CopyOutlined, DownOutlined, UpOutlined } from '@ant-design/icons'
import { Button, message, Tooltip } from 'antd'
import { XMarkdown } from '@ant-design/x-markdown'
import { useLayoutEffect, useRef, useState } from 'react'
import type { BubbleListRef } from '@ant-design/x/es/bubble'
import type { ChatMessage } from '../../../types/chat'
import { ChatRunSummary, type ChatRunStep } from './ChatRunSummary'

type Props = {
  className?: string
  messages: ChatMessage[]
  pendingAssistant: boolean
  scrollable?: boolean
  statusText?: string | null
}

function getRunSteps(message: ChatMessage, statusText: string | null | undefined): ChatRunStep[] {
  if (message.role !== 'assistant') return []
  if (message.runSteps?.length) return message.runSteps.map(step => {
    const completed = message.generationStatus !== 'generating' && step.status === 'loading'
    return {
      ...step,
      status: completed ? 'success' : step.status,
      title: completed && step.id.startsWith('generating-') ? '已生成回答' : step.title,
    }
  })
  if (message.generationStatus !== 'generating') return []

  return [{
    id: 'answer-generation',
    status: 'loading',
    title: statusText || '正在生成回答',
  }]
}

function CitationList({ message }: { message: ChatMessage }) {
  if (message.role !== 'assistant' || message.generationStatus !== 'complete' || !message.citations?.length) return null

  const citations = message.citations.filter((citation, index, all) =>
    all.findIndex(item => item.documentNodeId === citation.documentNodeId) === index,
  )

  return (
    <details className="chat-citations" open>
      <summary>
        <span>{`引用${citations.length}篇资料作为参考`}</span>
        <span className="chat-citations__toggle" aria-hidden="true">
          <UpOutlined className="is-expanded" />
          <DownOutlined className="is-collapsed" />
        </span>
      </summary>
      <div className="chat-citations__list">
        {citations.map((citation, index) => (
          <div className="chat-citations__item" key={citation.documentNodeId}>
            <span className="chat-citations__index">{index + 1}</span>
            <span className="chat-citations__name">{citation.documentName}</span>
          </div>
        ))}
      </div>
    </details>
  )
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
    ...messages.map(item => ({
      content: item.role === 'assistant'
        ? <>
            <ChatRunSummary steps={getRunSteps(item, statusText)} />
            {item.content && <XMarkdown content={item.content} streaming={{ hasNextChunk: item.generationStatus === 'generating', tail: true }} />}
            <CitationList message={item} />
          </>
        : item.content,
      key: item.id,
      role: item.role === 'user' ? 'user' : 'ai',
      footer: item.role === 'assistant' && item.content
        ? <Tooltip title="复制">
            <Button aria-label="复制" icon={<CopyOutlined />} size="small" type="text" onClick={() => void copyMessage(item.content)} />
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
      <Bubble.List
        ref={listRef}
        autoScroll={false}
        items={items}
        onScroll={handleScroll}
        role={{
          ai: {
            placement: 'start',
            styles: { content: { background: 'transparent', padding: 0, textAlign: 'left' } },
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
