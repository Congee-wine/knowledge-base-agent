import { render, screen } from '@testing-library/react'
import { forwardRef, useImperativeHandle, type ReactNode } from 'react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import type { ChatMessage } from '../../../../types/chat'
import { ChatMessageList } from '../ChatMessageList'

const bubbleListSpy = vi.fn()
const scrollToBeforeReady = vi.fn(() => {
  throw new Error('scroll box is not ready')
})

vi.mock('@ant-design/x', () => ({
  Bubble: {
    List: forwardRef((props: { autoScroll: boolean; items: Array<{ content: ReactNode }> }, ref) => {
      useImperativeHandle(ref, () => ({ scrollTo: scrollToBeforeReady }))
      bubbleListSpy(props)
      return <div data-testid="bubble-list">{props.items.map((item, index) => <div key={index}>{item.content}</div>)}</div>
    }),
  },
}))

vi.mock('@ant-design/x-markdown', () => ({ XMarkdown: ({ content }: { content: string }) => <>{content}</> }))

function message(): ChatMessage {
  return {
    id: 'message-1',
    role: 'user',
    content: '第一条消息',
    generationStatus: 'complete',
    createdAt: '2026-07-27T00:00:00Z',
  }
}

describe('ChatMessageList', () => {
  it('uses normal scroll direction so a new conversation starts from the top', () => {
    render(<ChatMessageList messages={[message()]} pendingAssistant scrollable />)

    expect(screen.getByText('第一条消息')).toBeInTheDocument()
    expect(bubbleListSpy).toHaveBeenLastCalledWith(expect.objectContaining({ autoScroll: false }))
    expect(bubbleListSpy).toHaveBeenLastCalledWith(expect.objectContaining({
      role: expect.objectContaining({ ai: expect.objectContaining({ styles: { content: expect.objectContaining({ textAlign: 'left' }) } }) }),
    }))
  })

  it('waits for the Bubble.List scroll box before requesting an initial scroll', () => {
    expect(() => render(<ChatMessageList messages={[message()]} pendingAssistant scrollable />)).not.toThrow()
    expect(scrollToBeforeReady).not.toHaveBeenCalled()
  })

  it('places the active run summary inside the generating assistant message', () => {
    render(<ChatMessageList messages={[{ ...message(), role: 'assistant', content: '', generationStatus: 'generating' }]} pendingAssistant statusText="正在生成回答" />)

    expect(screen.getByLabelText('回答运行过程')).toHaveTextContent('正在生成回答')
  })

  it('shows deduplicated document citations only after the answer completes', () => {
    const citations = [
      { documentNodeId: 'document-1', documentName: '智能应用.md', location: '第一章', snippet: '不应显示的片段' },
      { documentNodeId: 'document-1', documentName: '智能应用.md', location: '第二章', snippet: '重复文档片段' },
      { documentNodeId: 'document-2', documentName: '服务协议.md', location: '第三章', snippet: '不应显示的另一片段' },
    ]
    const assistantMessage = { ...message(), role: 'assistant' as const, content: '回答内容', citations }
    const { rerender } = render(
      <MemoryRouter>
        <ChatMessageList messages={[{ ...assistantMessage, generationStatus: 'generating' }]} pendingAssistant />
      </MemoryRouter>,
    )

    expect(screen.queryByText('引用2篇资料作为参考')).not.toBeInTheDocument()

    rerender(
      <MemoryRouter>
        <ChatMessageList messages={[{ ...assistantMessage, generationStatus: 'complete' }]} pendingAssistant={false} />
      </MemoryRouter>,
    )

    expect(screen.getByText('引用2篇资料作为参考')).toBeInTheDocument()
    expect(screen.queryByText('不应显示的片段')).not.toBeInTheDocument()
    expect(screen.getByRole('link', { name: '智能应用.md' })).toHaveAttribute('href', '/app/knowledge/files/document-1/preview')
    expect(screen.getByRole('link', { name: '服务协议.md' })).toHaveAttribute('href', '/app/knowledge/files/document-2/preview')
  })
})
