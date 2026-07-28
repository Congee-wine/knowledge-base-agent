import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { KnowledgeItemGrid } from './KnowledgeItemGrid'

describe('KnowledgeItemGrid', () => {
  it('opens files on double click and folders through the folder handler', () => {
    const onOpenFile = vi.fn()
    const onOpenFolder = vi.fn()
    render(
      <KnowledgeItemGrid
        items={[
          { id: 'file-1', kind: 'pdf', name: 'guide.pdf', processingStatus: 'ready' },
          { id: 'folder-1', kind: 'folder', name: '资料' },
        ]}
        selectedIds={[]}
        onContextMenu={vi.fn()}
        onOpenFile={onOpenFile}
        onOpenFolder={onOpenFolder}
        onSelectionChange={vi.fn()}
      />,
    )

    fireEvent.doubleClick(screen.getByText('guide.pdf'))
    fireEvent.doubleClick(screen.getByText('资料'))

    expect(onOpenFile).toHaveBeenCalledWith(expect.objectContaining({ id: 'file-1' }))
    expect(onOpenFolder).toHaveBeenCalledWith(expect.objectContaining({ id: 'folder-1' }))
  })
})
