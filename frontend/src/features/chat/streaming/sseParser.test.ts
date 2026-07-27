import { describe, expect, it } from 'vitest'
import { StreamProtocolError, parseSseChunk } from './sseParser'

describe('parseSseChunk', () => {
  it('parses CRLF frames and multi-line data across chunks', () => {
    const first = parseSseChunk('', 'data: {\r\n', false)
    const second = parseSseChunk(first.pending, 'data: "type":"answer_delta","content":"hi"}\r\n\r\n', false)

    expect(second.frames).toEqual([{ type: 'answer_delta', content: 'hi' }])
    expect(second.pending).toBe('')
  })

  it('consumes a final frame without a trailing blank line', () => {
    const parsed = parseSseChunk('', 'data: {"type":"message_end"}', true)

    expect(parsed.frames).toEqual([{ type: 'message_end' }])
  })

  it('rejects malformed JSON', () => {
    expect(() => parseSseChunk('', 'data: {invalid}\n\n')).toThrow(StreamProtocolError)
  })
})
