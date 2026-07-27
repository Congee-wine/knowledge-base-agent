export class StreamProtocolError extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'StreamProtocolError'
  }
}

type ParseResult = { frames: unknown[]; pending: string }

export function parseSseChunk(pending: string, chunk: string, isFinal = false): ParseResult {
  const content = pending + chunk
  const frames = content.split(/\r?\n\r?\n/)
  const tail = frames.pop() ?? ''
  if (isFinal && tail) frames.push(tail)

  return {
    frames: frames.filter(Boolean).map(parseFrame),
    pending: isFinal ? '' : tail,
  }
}

function parseFrame(frame: string): unknown {
  const data = frame
    .split(/\r?\n/)
    .filter(line => line.startsWith('data:'))
    .map(line => line.slice(5).replace(/^ /, ''))

  if (data.length === 0) throw new StreamProtocolError('SSE 帧缺少 data 字段')
  try {
    return JSON.parse(data.join('\n'))
  } catch {
    throw new StreamProtocolError('SSE data 不是有效 JSON')
  }
}
