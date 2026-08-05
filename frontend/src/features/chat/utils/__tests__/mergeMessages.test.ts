import { describe, expect, it } from 'vitest'
import type { ChatMessage } from '../../../../types/chat'
import { mergeMessages } from '../mergeMessages'

function msg(id: string, role: 'user' | 'assistant', content: string, generationStatus: ChatMessage['generationStatus'] = 'complete'): ChatMessage {
  return { id, role, content, generationStatus, createdAt: '2026-01-01T00:00:00Z' }
}

describe('mergeMessages', () => {
  it('merges non-overlapping messages', () => {
    const server = [msg('1', 'user', 'hello')]
    const local = [msg('2', 'assistant', 'hi')]
    const result = mergeMessages(server, local, new Set())
    expect(result).toHaveLength(2)
    expect(result.map(m => m.id)).toEqual(['1', '2'])
  })

  it('deduplicates by id, keeping server when local assistant is not in priority set', () => {
    const server = [msg('1', 'assistant', 'server done')]
    const local = [msg('1', 'assistant', 'local old')]
    const result = mergeMessages(server, local, new Set())
    expect(result).toHaveLength(1)
    expect(result[0].content).toBe('server done')
  })

  it('uses local assistant content when id is in priority set', () => {
    const server = [msg('1', 'assistant', 'server empty')]
    const local = [msg('1', 'assistant', 'local streaming')]
    const result = mergeMessages(server, local, new Set(['1']))
    expect(result).toHaveLength(1)
    expect(result[0].content).toBe('local streaming')
  })

  it('keeps a completed local answer when a stale server response is still generating', () => {
    const server = [msg('1', 'assistant', '', 'generating')]
    const local = [msg('1', 'assistant', 'local final answer')]
    const result = mergeMessages(server, local, new Set(['1']))
    expect(result[0]).toMatchObject({ content: 'local final answer', generationStatus: 'complete' })
  })

  it('keeps streaming content when the local assistant also has run steps', () => {
    const server = [msg('1', 'assistant', 'server empty', 'generating')]
    const local = [{
      ...msg('1', 'assistant', 'local streaming', 'generating'),
      runSteps: [{ id: 'retrieving-1', status: 'success' as const, title: '正在检索资料' }],
    }]
    const result = mergeMessages(server, local, new Set(['1']))
    expect(result[0].content).toBe('local streaming')
    expect(result[0].runSteps).toHaveLength(1)
  })

  it('never overrides server user messages with local', () => {
    const server = [msg('1', 'user', 'server final')]
    const local = [msg('1', 'user', 'local temp')]
    const result = mergeMessages(server, local, new Set(['1']))
    expect(result).toHaveLength(1)
    expect(result[0].content).toBe('server final')
  })

  it('returns server messages when local is empty', () => {
    const server = [msg('1', 'user', 'a'), msg('2', 'assistant', 'b')]
    const result = mergeMessages(server, [], new Set())
    expect(result).toHaveLength(2)
  })

  it('returns local messages when server is empty', () => {
    const local = [msg('1', 'user', 'a'), msg('2', 'assistant', 'b')]
    const result = mergeMessages([], local, new Set(['2']))
    expect(result).toHaveLength(2)
  })

  it('returns empty array when both are empty', () => {
    expect(mergeMessages([], [], new Set())).toEqual([])
  })

  it('preserves server message order and appends new local messages at end', () => {
    const server = [msg('1', 'user', 'first'), msg('2', 'assistant', 'second')]
    const local = [msg('3', 'user', 'third')]
    const result = mergeMessages(server, local, new Set())
    expect(result.map(m => m.id)).toEqual(['1', '2', '3'])
  })

  it('each id appears exactly once in result', () => {
    const server = [msg('1', 'user', 'a'), msg('2', 'assistant', 'b'), msg('3', 'user', 'c')]
    const local = [msg('2', 'assistant', 'b-override'), msg('4', 'assistant', 'd')]
    const result = mergeMessages(server, local, new Set(['2']))
    const ids = result.map(m => m.id)
    expect(new Set(ids).size).toBe(ids.length)
    expect(ids).toEqual(['1', '2', '3', '4'])
  })
})
