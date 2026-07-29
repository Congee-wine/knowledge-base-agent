import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { ChatRunSummary, type ChatRunStep } from '../ChatRunSummary'

const steps: ChatRunStep[] = [
  { id: 'retrieving-1', status: 'success', title: '正在检索资料' },
  { id: 'context-2', status: 'success', title: '已命中 5 条资料，正在构造上下文' },
  { id: 'generating-3', status: 'loading', title: '正在生成回答' },
]

describe('ChatRunSummary', () => {
  it('keeps every main step and respects a collapsed retrieval group', async () => {
    const view = render(<ChatRunSummary steps={steps} />)
    const group = screen.getByText('已检索知识库').closest('details')
    expect(group).not.toBeNull()
    expect(screen.getByText('正在生成回答')).toBeInTheDocument()

    await waitFor(() => expect(group).toHaveAttribute('open'))
    group!.open = false
    fireEvent(group!, new Event('toggle'))
    await waitFor(() => expect(group).not.toHaveAttribute('open'))

    view.rerender(<ChatRunSummary steps={steps} />)
    expect(group).not.toHaveAttribute('open')
  })
})
