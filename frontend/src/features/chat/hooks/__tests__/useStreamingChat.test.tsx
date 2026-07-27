import { act, renderHook, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { ChatStreamEvent } from '../../../../api/chat'
import type { ChatAgent } from '../../../../types/chat'
import { useStreamingChat } from '../useStreamingChat'

let capturedOnEvent: ((event: ChatStreamEvent) => void) | null = null
let resolveStream: (() => void) | null = null
let rejectStream: ((reason?: unknown) => void) | null = null

vi.mock('../../../../api/chat', () => ({
  interruptStreamMessage: vi.fn(),
  streamChat: vi.fn(async (options: { onEvent: (event: ChatStreamEvent) => void }) => {
    capturedOnEvent = options.onEvent
    return new Promise<void>((resolve, reject) => {
      resolveStream = resolve
      rejectStream = reject
    })
  }),
}))

const mockAgent: ChatAgent = {
  id: 'agent-1',
  kind: 'builtin',
  name: 'Test Agent',
  description: null,
  avatarKey: null,
  systemPrompt: null,
  welcomeMessage: null,
  presetQuestions: [],
  allowConversationUpload: false,
  allowNetworkAccess: false,
  interactionType: 'text',
  createdAt: '2026-01-01T00:00:00Z',
  updatedAt: '2026-01-01T00:00:00Z',
}

function emit(event: ChatStreamEvent) {
  act(() => {
    capturedOnEvent?.(event)
  })
}

function getRequestId(result: { current: ReturnType<typeof useStreamingChat> }) {
  const userMsg = result.current.messages.find(m => m.role === 'user')
  return userMsg!.id.replace('local-user-', '')
}

describe('useStreamingChat', () => {
  beforeEach(() => {
    capturedOnEvent = null
    resolveStream = null
    rejectStream = null
    vi.clearAllMocks()
  })

  it('replaces temp IDs with real IDs on message_start', async () => {
    const { result } = renderHook(() => useStreamingChat())

    act(() => {
      void result.current.send({ agent: mockAgent, content: 'hello', conversationId: null })
    })

    await waitFor(() => {
      expect(result.current.messages).toHaveLength(2)
    })

    const requestId = getRequestId(result)
    expect(result.current.messages.find(m => m.role === 'user')?.id).toBe(`local-user-${requestId}`)
    expect(result.current.messages.find(m => m.role === 'assistant')?.id).toBe(`local-assistant-${requestId}`)

    emit({
      type: 'message_start',
      mode: 'conversation',
      requestId,
      sequence: 1,
      conversationId: 'conv-1',
      userMessageId: 'real-user-1',
      assistantMessageId: 'real-assistant-1',
    })

    await waitFor(() => {
      expect(result.current.messages.find(m => m.role === 'user')?.id).toBe('real-user-1')
      expect(result.current.messages.find(m => m.role === 'assistant')?.id).toBe('real-assistant-1')
    })

    act(() => { resolveStream?.() })
  })

  it('appends answer_delta to the real assistant ID', async () => {
    const { result } = renderHook(() => useStreamingChat())

    act(() => {
      void result.current.send({ agent: mockAgent, content: 'hi', conversationId: null })
    })

    await waitFor(() => {
      expect(result.current.messages).toHaveLength(2)
    })

    const requestId = getRequestId(result)

    emit({ type: 'message_start', mode: 'conversation', requestId, sequence: 1, conversationId: 'conv-1', userMessageId: 'u-1', assistantMessageId: 'a-1' })
    emit({ type: 'answer_delta', mode: 'conversation', requestId, sequence: 2, content: 'Hello' })
    emit({ type: 'answer_delta', mode: 'conversation', requestId, sequence: 3, content: ' world' })

    await waitFor(() => {
      const assistant = result.current.messages.find(m => m.role === 'assistant')
      expect(assistant?.id).toBe('a-1')
      expect(assistant?.content).toBe('Hello world')
    })

    act(() => { resolveStream?.() })
  })

  it('keeps preview messages local when preview events omit persisted IDs', async () => {
    const { result } = renderHook(() => useStreamingChat())

    act(() => {
      void result.current.send({ agent: mockAgent, content: 'preview', conversationId: null, preview: true })
    })

    await waitFor(() => {
      expect(result.current.messages).toHaveLength(2)
    })

    const requestId = getRequestId(result)
    emit({ type: 'message_start', mode: 'preview', requestId, sequence: 1 })
    emit({ type: 'answer_delta', mode: 'preview', requestId, sequence: 2, content: 'preview answer' })
    emit({ type: 'message_end', mode: 'preview', requestId, sequence: 3, generationStatus: 'complete' })

    await waitFor(() => {
      expect(result.current.conversation).toBeNull()
      expect(result.current.pendingPersistedPairs).toHaveLength(0)
      expect(result.current.messages.find(message => message.role === 'assistant')).toMatchObject({
        content: 'preview answer',
        generationStatus: 'complete',
      })
      expect(result.current.sending).toBe(false)
    })

    act(() => { resolveStream?.() })
  })

  it('stops a conversation and persists the partial assistant answer', async () => {
    const { interruptStreamMessage } = await import('../../../../api/chat')
    const { result } = renderHook(() => useStreamingChat())
    act(() => { void result.current.send({ agent: mockAgent, content: 'stop me', conversationId: null }) })
    await waitFor(() => expect(result.current.messages).toHaveLength(2))
    const requestId = getRequestId(result)
    emit({ type: 'message_start', mode: 'conversation', requestId, sequence: 1, conversationId: 'conv-1', userMessageId: 'u-1', assistantMessageId: 'a-1' })
    emit({ type: 'answer_delta', mode: 'conversation', requestId, sequence: 2, content: 'partial' })

    await act(async () => { await result.current.stop() })

    expect(interruptStreamMessage).toHaveBeenCalledWith('a-1', 'partial')
    expect(result.current.sending).toBe(false)
    expect(result.current.messages.find(message => message.id === 'a-1')?.generationStatus).toBe('interrupted')
  })

  it('keeps messages and records pending pair on message_end', async () => {
    const { result } = renderHook(() => useStreamingChat())

    act(() => {
      void result.current.send({ agent: mockAgent, content: 'test', conversationId: null })
    })

    await waitFor(() => {
      expect(result.current.messages).toHaveLength(2)
    })

    const requestId = getRequestId(result)

    emit({ type: 'message_start', mode: 'conversation', requestId, sequence: 1, conversationId: 'conv-1', userMessageId: 'u-1', assistantMessageId: 'a-1' })
    emit({ type: 'answer_delta', mode: 'conversation', requestId, sequence: 2, content: 'answer' })
    emit({ type: 'message_end', mode: 'conversation', requestId, sequence: 3, messageId: 'a-1', generationStatus: 'complete' })

    await waitFor(() => {
      expect(result.current.sending).toBe(false)
      expect(result.current.messages).toHaveLength(2)
      expect(result.current.pendingPersistedPairs).toHaveLength(1)
      expect(result.current.pendingPersistedPairs[0]).toEqual({
        requestId,
        conversationId: 'conv-1',
        userMessageId: 'u-1',
        assistantMessageId: 'a-1',
      })
    })

    act(() => { resolveStream?.() })
  })

  it('acknowledgePersistedPair removes only that pair messages', async () => {
    const { result } = renderHook(() => useStreamingChat())

    act(() => {
      void result.current.send({ agent: mockAgent, content: 'first', conversationId: null })
    })

    await waitFor(() => {
      expect(result.current.messages).toHaveLength(2)
    })

    const requestId = getRequestId(result)

    emit({ type: 'message_start', mode: 'conversation', requestId, sequence: 1, conversationId: 'conv-1', userMessageId: 'u-1', assistantMessageId: 'a-1' })
    emit({ type: 'answer_delta', mode: 'conversation', requestId, sequence: 2, content: 'done' })
    emit({ type: 'message_end', mode: 'conversation', requestId, sequence: 3, messageId: 'a-1', generationStatus: 'complete' })

    await waitFor(() => {
      expect(result.current.pendingPersistedPairs).toHaveLength(1)
    })

    act(() => {
      result.current.acknowledgePersistedPair(requestId)
    })

    await waitFor(() => {
      expect(result.current.messages).toHaveLength(0)
      expect(result.current.pendingPersistedPairs).toHaveLength(0)
    })

    act(() => { resolveStream?.() })
  })

  it('acknowledgePersistedPair is a no-op for unknown requestId', async () => {
    const { result } = renderHook(() => useStreamingChat())

    act(() => {
      void result.current.send({ agent: mockAgent, content: 'test', conversationId: null })
    })

    await waitFor(() => {
      expect(result.current.messages).toHaveLength(2)
    })

    const requestId = getRequestId(result)

    emit({ type: 'message_start', mode: 'conversation', requestId, sequence: 1, conversationId: 'conv-1', userMessageId: 'u-1', assistantMessageId: 'a-1' })
    emit({ type: 'message_end', mode: 'conversation', requestId, sequence: 2, messageId: 'a-1', generationStatus: 'complete' })

    await waitFor(() => {
      expect(result.current.pendingPersistedPairs).toHaveLength(1)
    })

    act(() => {
      result.current.acknowledgePersistedPair('non-existent')
    })

    expect(result.current.pendingPersistedPairs).toHaveLength(1)
    expect(result.current.messages).toHaveLength(2)

    act(() => { resolveStream?.() })
  })

  it('reset clears all state including pending pairs', async () => {
    const { result } = renderHook(() => useStreamingChat())

    act(() => {
      void result.current.send({ agent: mockAgent, content: 'test', conversationId: null })
    })

    await waitFor(() => {
      expect(result.current.messages).toHaveLength(2)
    })

    const requestId = getRequestId(result)

    emit({ type: 'message_start', mode: 'conversation', requestId, sequence: 1, conversationId: 'conv-1', userMessageId: 'u-1', assistantMessageId: 'a-1' })
    emit({ type: 'message_end', mode: 'conversation', requestId, sequence: 2, messageId: 'a-1', generationStatus: 'complete' })

    await waitFor(() => {
      expect(result.current.pendingPersistedPairs).toHaveLength(1)
    })

    act(() => {
      result.current.reset()
    })

    expect(result.current.messages).toHaveLength(0)
    expect(result.current.pendingPersistedPairs).toHaveLength(0)
    expect(result.current.conversation).toBeNull()
    expect(result.current.sending).toBe(false)

    act(() => { resolveStream?.() })
  })

  it('does not mark the previous real assistant as failed when a new request fails before message_start', async () => {
    const { result } = renderHook(() => useStreamingChat())

    act(() => {
      void result.current.send({ agent: mockAgent, content: 'first', conversationId: null })
    })

    await waitFor(() => {
      expect(result.current.messages).toHaveLength(2)
    })

    const firstRequestId = getRequestId(result)
    emit({ type: 'message_start', mode: 'conversation', requestId: firstRequestId, sequence: 1, conversationId: 'conv-1', userMessageId: 'u-1', assistantMessageId: 'a-1' })
    emit({ type: 'message_end', mode: 'conversation', requestId: firstRequestId, sequence: 2, messageId: 'a-1', generationStatus: 'complete' })

    await waitFor(() => {
      expect(result.current.sending).toBe(false)
      expect(result.current.messages.find(message => message.id === 'a-1')?.generationStatus).toBe('complete')
    })

    act(() => {
      void result.current.send({ agent: mockAgent, content: 'second', conversationId: 'conv-1' })
    })

    await waitFor(() => {
      expect(result.current.messages).toHaveLength(4)
    })

    const secondAssistant = result.current.messages.find(message => message.id.startsWith('local-assistant-'))
    expect(secondAssistant).toBeDefined()

    act(() => {
      rejectStream?.(new Error('network failed'))
    })

    await waitFor(() => {
      expect(result.current.messages.find(message => message.id === 'a-1')?.generationStatus).toBe('complete')
      expect(result.current.messages.find(message => message.id === secondAssistant?.id)?.generationStatus).toBe('failed')
    })
  })
})
