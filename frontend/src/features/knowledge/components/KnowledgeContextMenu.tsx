import {
  DeleteOutlined,
  DownloadOutlined,
  EditOutlined,
  EyeOutlined,
  FolderOpenOutlined,
  FormOutlined,
  SwapOutlined,
} from '@ant-design/icons'
import type { ReactNode } from 'react'
import type { KnowledgeActionId, KnowledgeItem } from '../types'

type Props = {
  item: KnowledgeItem
  position: { x: number; y: number }
  onAction: (action: KnowledgeActionId, item: KnowledgeItem) => void
}

type MenuEntry = { id: KnowledgeActionId; label: string; icon: ReactNode; destructive?: boolean }

const menuEntries: MenuEntry[] = [
  { id: 'open', label: '打开', icon: <FolderOpenOutlined /> },
  { id: 'preview', label: '预览', icon: <EyeOutlined /> },
  { id: 'edit', label: '编辑', icon: <EditOutlined /> },
  { id: 'rename', label: '重命名', icon: <FormOutlined /> },
  { id: 'move', label: '移动到', icon: <SwapOutlined /> },
  { id: 'download', label: '下载', icon: <DownloadOutlined /> },
  { id: 'delete', label: '删除', icon: <DeleteOutlined />, destructive: true },
]

function defaultActions(item: KnowledgeItem): KnowledgeActionId[] {
  return item.kind === 'folder'
    ? ['open', 'rename', 'move', 'delete']
    : ['preview', 'edit', 'rename', 'move', 'download', 'delete']
}

export function KnowledgeContextMenu({ item, position, onAction }: Props) {
  const actions = item.actions ?? defaultActions(item)
  const entries = menuEntries.filter(entry => actions.includes(entry.id))
  return <div className="knowledge-context-menu" role="menu" style={{ left: position.x, top: position.y }}>
    {item.ownerName && <p>所有者：{item.ownerName}</p>}
    {entries.map((entry, index) => <div key={entry.id}>
      {index > 0 && entry.id === 'delete' && <div className="knowledge-context-menu__divider" />}
      <button
        className={entry.destructive ? 'is-destructive' : ''}
        role="menuitem"
        type="button"
        onClick={() => onAction(entry.id, item)}
      >
        <span>{entry.icon}</span>{entry.label}{item.shortcuts?.[entry.id] && <kbd>{item.shortcuts[entry.id]}</kbd>}
      </button>
    </div>)}
  </div>
}
