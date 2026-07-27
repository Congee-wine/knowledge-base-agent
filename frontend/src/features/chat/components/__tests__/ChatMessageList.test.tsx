import { render, screen } from '@testing-library/react'
import { forwardRef, useImperativeHandle, type ReactNode } from 'react'
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
})
