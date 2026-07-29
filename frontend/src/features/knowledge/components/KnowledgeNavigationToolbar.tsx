import { LeftOutlined, RightOutlined, SearchOutlined, UpOutlined } from '@ant-design/icons'
import { Input } from 'antd'
import { useMemo } from 'react'

export type KnowledgeNavigationNode = {
  id: string
  parentId?: string
  name: string
}

type Props = {
  className?: string
  currentFolderId?: string
  historyIndex: number
  canGoForward: boolean
  items: KnowledgeNavigationNode[]
  searchPlaceholder: string
  searchText: string
  onGoBack: () => void
  onGoForward: () => void
  onNavigateToFolder: (folderId: string | undefined) => void
  onSearchTextChange: (value: string) => void
}

export function KnowledgeNavigationToolbar({
  className,
  currentFolderId,
  historyIndex,
  canGoForward,
  items,
  searchPlaceholder,
  searchText,
  onGoBack,
  onGoForward,
  onNavigateToFolder,
  onSearchTextChange,
}: Props) {
  const breadcrumbs = useMemo(() => {
    const trail: KnowledgeNavigationNode[] = []
    let node = currentFolderId ? items.find((item) => item.id === currentFolderId) : undefined
    while (node) {
      trail.unshift(node)
      node = node.parentId ? items.find((item) => item.id === node!.parentId) : undefined
    }
    return trail
  }, [currentFolderId, items])
  const parentId = currentFolderId ? items.find((item) => item.id === currentFolderId)?.parentId : undefined

  return <div className={`knowledge-toolbar__path ${className ?? ''}`}>
    <button aria-label="后退" className={historyIndex > 0 ? 'is-enabled' : ''} disabled={historyIndex === 0} type="button" onClick={onGoBack}><LeftOutlined /></button>
    <button aria-label="前进" className={canGoForward ? 'is-enabled' : ''} disabled={!canGoForward} type="button" onClick={onGoForward}><RightOutlined /></button>
    <button aria-label="返回上一级" className={currentFolderId ? 'is-enabled' : ''} disabled={!currentFolderId} type="button" onClick={() => onNavigateToFolder(parentId)}><UpOutlined /></button>
    <nav aria-label="资料路径" className="knowledge-breadcrumb">
      <button type="button" onClick={() => onNavigateToFolder(undefined)}>根目录</button>
      {breadcrumbs.map((item) => <span key={item.id}><i>/</i><button type="button" onClick={() => onNavigateToFolder(item.id)}>{item.name}</button></span>)}
    </nav>
    <Input allowClear placeholder={searchPlaceholder} prefix={<SearchOutlined />} value={searchText} onChange={(event) => onSearchTextChange(event.target.value)} />
  </div>
}
