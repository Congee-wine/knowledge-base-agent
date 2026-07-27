import { useCallback, useEffect, useRef, useState } from 'react'
import { interruptStreamMessage, streamChat, type ChatStreamEvent } from '../../../api/chat'
import type { ChatAgent, ChatMessage, Conversation } from '../../../types/chat'

type SendStreamInput = {
  agent: ChatAgent
  content: string
  conversationId: string | null
  onConversationCreated?: (conversationId: string) => void
  preview?: boolean
}

type PendingPersistedPair = {
  requestId: string
  conversationId: string
  userMessageId: string
  assistantMessageId: string
}

type ConversationStream = {
  conversation: Conversation | null
  error: string | null
  messages: ChatMessage[]
  sending: boolean
  statusText: string | null
  userMessageId: string | null
  assistantMessageId: string | null
  pendingPersistedPairs: PendingPersistedPair[]
}

type StreamStore = {
  streams: Record<string, ConversationStream>
  lastKey: string
}

type ActiveStream = {
  assistantMessageId: string | null
  controller: AbortController
  key: string
  mode: 'conversation' | 'preview'
  requestId: string
  sequence: number
}

const DRAFT_KEY = '__draft__'
const PREVIEW_KEY = '__preview__'
const initialStream: ConversationStream = {
  assistantMessageId: null,
  conversation: null,
  error: null,
  messages: [],
  pendingPersistedPairs: [],
  sending: false,
  statusText: null,
  userMessageId: null,
}

const initialStore: StreamStore = { streams: {}, lastKey: DRAFT_KEY }

function conversationKey(conversationId: string | null, preview: boolean) {
  if (preview) return PREVIEW_KEY
  return conversationId ?? DRAFT_KEY
}

function createRequestId() {
  return crypto.randomUUID()
}

function updateAssistant(
  messages: ChatMessage[], assistantMessageId: string | null, requestId: string,
  update: (message: ChatMessage) => ChatMessage,
) {
  const targetId = assistantMessageId ?? `local-assistant-${requestId}`
  return messages.map(message => (message.id === targetId ? update(message) : message))
}

export function useStreamingChat() {
  const [store, setStore] = useState<StreamStore>(initialStore)
  const storeRef = useRef(store)
  const activeStreams = useRef(new Map<string, ActiveStream>())
  storeRef.current = store

  const updateStream = useCallback((key: string, update: (stream: ConversationStream) => ConversationStream) => {
    setStore(current => ({
      ...current,
      lastKey: key,
      streams: { ...current.streams, [key]: update(current.streams[key] ?? initialStream) },
    }))
  }, [])

  const stopKey = useCallback(async (key: string) => {
    const active = activeStreams.current.get(key)
    if (!active) return
    active.controller.abort()
    activeStreams.current.delete(key)
    const stream = storeRef.current.streams[key] ?? initialStream
    const assistant = stream.messages.find(message => message.id === (active.assistantMessageId ?? `local-assistant-${active.requestId}`))
    updateStream(key, current => ({
      ...current,
      messages: updateAssistant(current.messages, active.assistantMessageId, active.requestId, message => ({ ...message, generationStatus: 'interrupted' })),
      sending: false,
      statusText: null,
    }))
    if (active.mode === 'conversation' && active.assistantMessageId) {
      try {
        await interruptStreamMessage(active.assistantMessageId, assistant?.content ?? '')
      } catch {
        updateStream(key, current => ({ ...current, error: '停止生成失败，请刷新会话确认最终状态。' }))
      }
    }
  }, [updateStream])

  const stop = useCallback(async (conversationId?: string | null) => {
    if (conversationId !== undefined) {
      await stopKey(conversationKey(conversationId, false))
      return
    }
    await Promise.all([...activeStreams.current.keys()].map(stopKey))
  }, [stopKey])

  const reset = useCallback(() => setStore(initialStore), [])

  useEffect(() => () => { void stop() }, [stop])

  const acknowledgePersistedPair = useCallback((requestId: string) => {
    setStore(current => {
      const entry = Object.entries(current.streams).find(([, stream]) => stream.pendingPersistedPairs.some(pair => pair.requestId === requestId))
      if (!entry) return current
      const [key, stream] = entry
      const pair = stream.pendingPersistedPairs.find(item => item.requestId === requestId)!
      return {
        ...current,
        streams: {
          ...current.streams,
          [key]: {
            ...stream,
            messages: stream.messages.filter(message => message.id !== pair.userMessageId && message.id !== pair.assistantMessageId),
            pendingPersistedPairs: stream.pendingPersistedPairs.filter(item => item.requestId !== requestId),
          },
        },
      }
    })
  }, [])

  const send = useCallback(async ({ agent, content, conversationId, onConversationCreated, preview = false }: SendStreamInput) => {
    const key = conversationKey(conversationId, preview)
    if (activeStreams.current.has(key)) return
    const requestId = createRequestId()
    const mode = preview ? 'preview' : 'conversation'
    const active: ActiveStream = { assistantMessageId: null, controller: new AbortController(), key, mode, requestId, sequence: 0 }
    activeStreams.current.set(key, active)
    const createdAt = new Date().toISOString()
    const userMessage: ChatMessage = { content, createdAt, generationStatus: 'complete', id: `local-user-${requestId}`, role: 'user' }
    const assistantMessage: ChatMessage = { content: '', createdAt, generationStatus: 'generating', id: `local-assistant-${requestId}`, role: 'assistant' }
    updateStream(key, current => ({
      ...current,
      assistantMessageId: null,
      error: null,
      messages: [...current.messages, userMessage, assistantMessage],
      sending: true,
      statusText: '正在生成回答',
      userMessageId: null,
    }))
    const path = preview
      ? `/api/agents/${encodeURIComponent(agent.id)}/preview/messages:stream`
      : `/api/conversations/messages:stream?agentId=${encodeURIComponent(agent.id)}${conversationId ? `&conversationId=${encodeURIComponent(conversationId)}` : ''}`
    const history = (storeRef.current.streams[key] ?? initialStream).messages
    const body = preview ? { content, draftAgent: agent, history: history.map(message => ({ content: message.content, role: message.role })), requestId } : { content, requestId }

    try {
      await streamChat({ body, path, signal: active.controller.signal, onEvent: event => {
        if (event.requestId !== requestId || event.mode !== mode || event.sequence <= active.sequence) return
        active.sequence = event.sequence
        if (event.type === 'message_start' && event.mode === 'conversation') {
          active.assistantMessageId = event.assistantMessageId
          const nextKey = event.conversationId
          if (active.key !== nextKey) {
            activeStreams.current.delete(active.key)
            active.key = nextKey
            activeStreams.current.set(nextKey, active)
            setStore(current => {
              const draft = current.streams[key] ?? initialStream
              const { [key]: _, ...remaining } = current.streams
              return { lastKey: nextKey, streams: { ...remaining, [nextKey]: draft } }
            })
          }
          updateStream(active.key, current => ({
            ...current,
            assistantMessageId: event.assistantMessageId,
            conversation: { agentId: '', createdAt: '', id: event.conversationId, title: null, updatedAt: '' },
            messages: current.messages.map(message => {
              if (message.id === `local-user-${requestId}`) return { ...message, id: event.userMessageId }
              if (message.id === `local-assistant-${requestId}`) return { ...message, id: event.assistantMessageId }
              return message
            }),
            userMessageId: event.userMessageId,
          }))
          onConversationCreated?.(event.conversationId)
          return
        }
        updateStream(active.key, current => applyEvent(current, event, active))
        if (event.type === 'message_end' || event.type === 'error') {
          if (activeStreams.current.get(active.key)?.requestId === requestId) activeStreams.current.delete(active.key)
        }
      } })
    } catch (error) {
      if (active.controller.signal.aborted) return
      const text = error instanceof Error ? error.message : '发送失败，请稍后重试'
      updateStream(active.key, current => ({
        ...current,
        error: text,
        messages: updateAssistant(current.messages, active.assistantMessageId, requestId, message => ({ ...message, generationStatus: 'failed' })),
        sending: false,
      }))
    } finally {
      if (activeStreams.current.get(active.key)?.requestId === requestId) activeStreams.current.delete(active.key)
    }
  }, [updateStream])

  const getStream = useCallback((conversationId: string | null) => store.streams[conversationKey(conversationId, false)] ?? initialStream, [store.streams])
  const pendingPersistedPairs = Object.values(store.streams).flatMap(stream => stream.pendingPersistedPairs)
  const legacy = store.streams[store.lastKey] ?? initialStream

  return { ...legacy, acknowledgePersistedPair, getStream, pendingPersistedPairs, reset, send, stop }
}

function applyEvent(current: ConversationStream, event: ChatStreamEvent, active: ActiveStream): ConversationStream {
  if (event.type === 'status') return { ...current, statusText: event.text }
  if (event.type === 'answer_delta') return { ...current, messages: updateAssistant(current.messages, active.assistantMessageId, active.requestId, message => ({ ...message, content: message.content + event.content })) }
  if (event.type === 'message_end') {
    const messages = updateAssistant(current.messages, active.assistantMessageId, active.requestId, message => ({ ...message, id: event.mode === 'conversation' ? event.messageId : message.id, generationStatus: event.generationStatus }))
    const pendingPair = event.mode === 'conversation' && current.conversation && current.userMessageId && active.assistantMessageId
      ? { assistantMessageId: active.assistantMessageId, conversationId: current.conversation.id, requestId: active.requestId, userMessageId: current.userMessageId }
      : null
    return { ...current, assistantMessageId: null, messages, pendingPersistedPairs: pendingPair ? [...current.pendingPersistedPairs, pendingPair] : current.pendingPersistedPairs, sending: false, statusText: null, userMessageId: null }
  }
  if (event.type === 'error') return { ...current, error: event.message, messages: updateAssistant(current.messages, active.assistantMessageId, active.requestId, message => ({ ...message, generationStatus: 'failed' })), sending: false, statusText: null }
  return current
}
