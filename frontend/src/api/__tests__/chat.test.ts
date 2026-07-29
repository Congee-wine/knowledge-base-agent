import { afterEach, describe, expect, it, vi } from 'vitest'
import { streamChat, type ChatStreamEvent } from '../chat'

function sseFrame(event: unknown) {
  return `data: ${JSON.stringify(event)}\n\n`
}

describe('streamChat', () => {
  afterEach(() => {
    localStorage.clear()
    vi.unstubAllGlobals()
  })

  it('parses a valid message_start event before dispatching it', async () => {
    localStorage.setItem('access_token', 'test-token')
    const event: ChatStreamEvent = {
      type: 'message_start',
      mode: 'conversation',
      requestId: 'request-1',
      sequence: 1,
      conversationId: 'conversation-1',
      userMessageId: 'user-1',
      assistantMessageId: 'assistant-1',
    }
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(sseFrame(event), { status: 200 })))
    const received: ChatStreamEvent[] = []

    await streamChat({ body: { content: 'hello' }, onEvent: item => received.push(item), path: '/stream' })

    expect(received).toEqual([event])
  })

  it('rejects malformed SSE events instead of dispatching unsafe data', async () => {
    localStorage.setItem('access_token', 'test-token')
    const malformedEvent = {
      type: 'message_start',
      mode: 'conversation',
      requestId: 'request-1',
      sequence: 1,
      conversationId: 'conversation-1',
      userMessageId: 'user-1',
    }
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(sseFrame(malformedEvent), { status: 200 })))

    await expect(streamChat({ body: { content: 'hello' }, onEvent: vi.fn(), path: '/stream' }))
      .rejects.toThrow('流式事件缺少有效字段：assistantMessageId')
  })

  it('parses preview events without persisted message IDs', async () => {
    localStorage.setItem('access_token', 'test-token')
    const events: ChatStreamEvent[] = [
      { type: 'message_start', mode: 'preview', requestId: 'request-1', sequence: 1 },
      { type: 'status', mode: 'preview', requestId: 'request-1', sequence: 2, stage: 'generating', text: '正在生成回答' },
      { type: 'answer_delta', mode: 'preview', requestId: 'request-1', sequence: 3, content: '预览回答' },
      { type: 'message_end', mode: 'preview', requestId: 'request-1', sequence: 4, generationStatus: 'complete' },
    ]
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(events.map(sseFrame).join(''), { status: 200 })))
    const received: ChatStreamEvent[] = []

    await streamChat({ body: { content: 'hello' }, onEvent: item => received.push(item), path: '/stream' })

    expect(received).toEqual(events)
  })

  it('accepts LangGraph analysis and clarification stages', async () => {
    localStorage.setItem('access_token', 'test-token')
    const events: ChatStreamEvent[] = [
      { type: 'status', mode: 'conversation', requestId: 'request-1', sequence: 1, stage: 'analyzing', text: '正在分析问题' },
      { type: 'status', mode: 'conversation', requestId: 'request-1', sequence: 2, stage: 'clarifying', text: '正在确认关键条件' },
    ]
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(events.map(sseFrame).join(''), { status: 200 })))
    const received: ChatStreamEvent[] = []

    await streamChat({ body: { content: 'hello' }, onEvent: item => received.push(item), path: '/stream' })

    expect(received).toEqual(events)
  })
})
