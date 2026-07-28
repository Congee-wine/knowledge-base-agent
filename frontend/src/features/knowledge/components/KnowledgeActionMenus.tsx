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
  onCreateFolder: () => void
  onUploadFile: () => void
  onUploadFolder: () => void
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
  onCreateFolder,
  onUploadFile,
  onUploadFolder,
}: {
  title: string
  items: ActionItem[]
  otherItems?: ActionItem[]
  compact?: boolean
  onCreateFolder?: () => void
  onUploadFile?: () => void
  onUploadFolder?: () => void
}) {
  return <div className={`knowledge-action-panel ${compact ? 'knowledge-action-panel--compact' : ''}`} role="menu">
    <p className="knowledge-action-panel__section-title">{title}</p>
    <div className="knowledge-action-panel__items">
      {items.map(item => <button key={item.label} type="button" className="knowledge-action-panel__item" role="menuitem" onClick={item.label === '文件' ? onUploadFile : item.label === '文件夹' ? onUploadFolder : undefined}>
        <span className={item.tone}>{item.icon}</span>
        {item.label}
      </button>)}
    </div>
    {otherItems && <>
      <p className="knowledge-action-panel__section-title knowledge-action-panel__section-title--other">其他</p>
      <div className="knowledge-action-panel__items knowledge-action-panel__items--other">
        {otherItems.map(item => <button key={item.label} type="button" className="knowledge-action-panel__item" role="menuitem" onClick={item.label === '文件夹' ? onCreateFolder : undefined}>
          <span className={item.tone}>{item.icon}</span>
          {item.label}
        </button>)}
      </div>
    </>}
  </div>
}

export function KnowledgeActionMenus({ activeMenu, onMenuChange, onCreateFolder, onUploadFile, onUploadFolder }: Props) {
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
        onCreateFolder={onCreateFolder}
      />}
    </div>
    <div className="knowledge-actions__trigger">
      <button className="knowledge-toolbar-button" type="button" onClick={() => onMenuChange(activeMenu === 'upload' ? null : 'upload')}>
        <UploadOutlined /> 上传
      </button>
      {activeMenu === 'upload' && <ActionPanel compact title="仅支持 PDF、TXT、Markdown、DOCX" items={uploadItems} onUploadFile={onUploadFile} onUploadFolder={onUploadFolder} />}
    </div>
  </div>
}
