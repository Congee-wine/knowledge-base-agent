import {
  FileAddOutlined,
  FileExcelFilled,
  FilePptFilled,
  FileTextFilled,
  FolderOpenFilled,
  UploadOutlined,
} from '@ant-design/icons'
import type { ReactNode } from 'react'

type MenuKind = 'new' | 'upload' | null

type Props = {
  activeMenu: MenuKind
  onMenuChange: (menu: MenuKind) => void
}

type ActionItem = { label: string; icon: ReactNode; tone?: string }

const createItems: ActionItem[] = [
  { label: '文字', icon: <FileTextFilled />, tone: 'is-word' },
  { label: '表格', icon: <FileExcelFilled />, tone: 'is-sheet' },
  { label: '演示', icon: <FilePptFilled />, tone: 'is-presentation' },
]

function ActionPanel({
  title,
  items,
  otherItems,
  compact = false,
}: {
  title: string
  items: ActionItem[]
  otherItems?: ActionItem[]
  compact?: boolean
}) {
  return <div className={`knowledge-action-panel ${compact ? 'knowledge-action-panel--compact' : ''}`} role="menu">
    <p className="knowledge-action-panel__section-title">{title}</p>
    <div className="knowledge-action-panel__items">
      {items.map(item => <button key={item.label} type="button" className="knowledge-action-panel__item" role="menuitem">
        <span className={item.tone}>{item.icon}</span>
        {item.label}
      </button>)}
    </div>
    {otherItems && <>
      <p className="knowledge-action-panel__section-title knowledge-action-panel__section-title--other">其他</p>
      <div className="knowledge-action-panel__items knowledge-action-panel__items--other">
        {otherItems.map(item => <button key={item.label} type="button" className="knowledge-action-panel__item" role="menuitem">
          <span className={item.tone}>{item.icon}</span>
          {item.label}
        </button>)}
      </div>
    </>}
  </div>
}

export function KnowledgeActionMenus({ activeMenu, onMenuChange }: Props) {
  const uploadItems: ActionItem[] = [
    { label: '文件', icon: <UploadOutlined />, tone: 'is-upload' },
    { label: '文件夹', icon: <FolderOpenFilled />, tone: 'is-folder-upload' },
  ]

  return <div className="knowledge-actions">
    <div className="knowledge-actions__trigger">
      <button className="knowledge-toolbar-button" type="button" onClick={() => onMenuChange(activeMenu === 'new' ? null : 'new')}>
        <FileAddOutlined /> 新建
      </button>
      {activeMenu === 'new' && <ActionPanel
        title="Office 文档"
        items={createItems}
        otherItems={[{ label: '文件夹', icon: <FolderOpenFilled />, tone: 'is-folder-upload' }]}
      />}
    </div>
    <div className="knowledge-actions__trigger">
      <button className="knowledge-toolbar-button" type="button" onClick={() => onMenuChange(activeMenu === 'upload' ? null : 'upload')}>
        <UploadOutlined /> 上传
      </button>
      {activeMenu === 'upload' && <ActionPanel compact title="从本地上传" items={uploadItems} />}
    </div>
  </div>
}
