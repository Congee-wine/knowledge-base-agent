import { FilePdfFilled, FileTextFilled, FileWordFilled, FolderFilled } from '@ant-design/icons'
import { Checkbox } from 'antd'
import type { KnowledgeItem } from '../types'

type Props = {
  items: KnowledgeItem[]
  selectedIds: string[]
  onSelectionChange: (itemId: string, selected: boolean) => void
  onContextMenu: (item: KnowledgeItem, position: { x: number; y: number }) => void
  onOpenFolder: (item: KnowledgeItem) => void
}

const itemIcons = {
  folder: <FolderFilled className="knowledge-item__icon knowledge-item__icon--folder" />,
  pdf: <FilePdfFilled className="knowledge-item__icon knowledge-item__icon--pdf" />,
  markdown: <FileTextFilled className="knowledge-item__icon knowledge-item__icon--markdown" />,
  word: <FileWordFilled className="knowledge-item__icon knowledge-item__icon--word" />,
}

export function KnowledgeItemGrid({ items, selectedIds, onSelectionChange, onContextMenu, onOpenFolder }: Props) {
  return <div className="knowledge-item-grid">
    {items.map(item => {
      const selected = selectedIds.includes(item.id)
      return <article
        className={`knowledge-item ${selected ? 'is-selected' : ''}`}
        key={item.id}
        onContextMenu={event => {
          event.preventDefault()
          onContextMenu(item, { x: event.clientX, y: event.clientY })
        }}
        onDoubleClick={() => {
          if (item.kind === 'folder') onOpenFolder(item)
        }}
      >
        <Checkbox
          aria-label={`选择${item.name}`}
          checked={selected}
          className="knowledge-item__checkbox"
          onChange={event => onSelectionChange(item.id, event.target.checked)}
        />
        {itemIcons[item.kind]}
        <p className="knowledge-item__name" title={item.name}>{item.name}</p>
        {item.size && <span className="knowledge-item__size">{item.size}</span>}
      </article>
    })}
  </div>
}
