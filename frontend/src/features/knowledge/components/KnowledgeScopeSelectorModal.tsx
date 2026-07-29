import {
  FilePdfFilled,
  FileTextFilled,
  FileWordFilled,
  FolderFilled,
} from '@ant-design/icons'
import { Button, Checkbox, Empty, Modal, Spin } from 'antd'
import { useEffect, useMemo, useState } from 'react'
import { getKnowledgeTree, type KnowledgeNode } from '../../../api/knowledge'
import { KnowledgeNavigationToolbar } from './KnowledgeNavigationToolbar'

type Props = {
  open: boolean
  selectedIds: string[]
  onCancel: () => void
  onConfirm: (nodeIds: string[]) => void
}

type FlatNode = Omit<KnowledgeNode, 'parentId'> & { parentId: string | undefined }

function flattenNodes(nodes: KnowledgeNode[]): FlatNode[] {
  return nodes.flatMap((node) => [
    { ...node, parentId: node.parentId ?? undefined },
    ...flattenNodes(node.children),
  ])
}

function getNodeIcon(node: FlatNode) {
  if (node.nodeType === 'folder') return <FolderFilled className="knowledge-scope-selector__icon is-folder" />
  if (node.mimeType === 'application/pdf' || node.name.toLowerCase().endsWith('.pdf')) return <FilePdfFilled className="knowledge-scope-selector__icon is-pdf" />
  if (node.mimeType?.includes('wordprocessingml') || node.name.toLowerCase().endsWith('.docx')) return <FileWordFilled className="knowledge-scope-selector__icon is-word" />
  return <FileTextFilled className="knowledge-scope-selector__icon is-text" />
}

export function KnowledgeScopeSelectorModal({ open, selectedIds, onCancel, onConfirm }: Props) {
  const [nodes, setNodes] = useState<KnowledgeNode[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [draftIds, setDraftIds] = useState<string[]>(selectedIds)
  const [currentFolderId, setCurrentFolderId] = useState<string | undefined>()
  const [history, setHistory] = useState<Array<string | undefined>>([undefined])
  const [historyIndex, setHistoryIndex] = useState(0)
  const [searchText, setSearchText] = useState('')
  const flatNodes = useMemo(() => flattenNodes(nodes), [nodes])

  useEffect(() => {
    if (!open) return
    setDraftIds(selectedIds)
    setCurrentFolderId(undefined)
    setHistory([undefined])
    setHistoryIndex(0)
    setSearchText('')
    setLoading(true)
    setError(null)
    void getKnowledgeTree()
      .then((tree) => setNodes(tree.items))
      .catch((requestError: unknown) => setError(requestError instanceof Error ? requestError.message : '资料树加载失败'))
      .finally(() => setLoading(false))
  }, [open, selectedIds])

  const visibleNodes = useMemo(() => {
    const keyword = searchText.trim().toLocaleLowerCase()
    return flatNodes.filter((node) => node.parentId === currentFolderId && (!keyword || node.name.toLocaleLowerCase().includes(keyword)))
  }, [currentFolderId, flatNodes, searchText])
  const navigateTo = (folderId: string | undefined) => {
    setCurrentFolderId(folderId)
    setHistory((entries) => [...entries.slice(0, historyIndex + 1), folderId])
    setHistoryIndex((index) => index + 1)
  }
  const toggleSelection = (nodeId: string, checked: boolean) => {
    setDraftIds((ids) => checked ? [...new Set([...ids, nodeId])] : ids.filter((id) => id !== nodeId))
  }
  const goBack = () => {
    const nextIndex = historyIndex - 1
    setHistoryIndex(nextIndex)
    setCurrentFolderId(history[nextIndex])
  }
  const goForward = () => {
    const nextIndex = historyIndex + 1
    setHistoryIndex(nextIndex)
    setCurrentFolderId(history[nextIndex])
  }

  return <Modal centered className="knowledge-scope-selector" footer={null} onCancel={onCancel} open={open} title="绑定知识集" width={1240}>
    <KnowledgeNavigationToolbar
      canGoForward={historyIndex < history.length - 1}
      currentFolderId={currentFolderId}
      historyIndex={historyIndex}
      items={flatNodes}
      searchPlaceholder="搜索名称或类型，例如：pdf、docx"
      searchText={searchText}
      onGoBack={goBack}
      onGoForward={goForward}
      onNavigateToFolder={navigateTo}
      onSearchTextChange={setSearchText}
    />
    <main className="knowledge-scope-selector__canvas">
      {loading ? <Spin tip="正在加载资料树" /> : error ? <Empty description={error} /> : visibleNodes.length ? <div className="knowledge-scope-selector__grid">
        {visibleNodes.map((node) => <article className={draftIds.includes(node.id) ? 'is-selected' : ''} key={node.id}>
          <Checkbox aria-label={`选择${node.name}`} checked={draftIds.includes(node.id)} onChange={(event) => toggleSelection(node.id, event.target.checked)} />
          <button type="button" onDoubleClick={() => node.nodeType === 'folder' && navigateTo(node.id)} onClick={() => toggleSelection(node.id, !draftIds.includes(node.id))}>
            {getNodeIcon(node)}
            <span className="knowledge-scope-selector__name" title={node.name}>{node.name}</span>
          </button>
        </article>)}
      </div> : <Empty description={searchText ? '未找到匹配资料' : '当前目录暂无资料'} />}
    </main>
    <footer className="knowledge-scope-selector__footer">
      <span>已选择 {draftIds.length} 项资料</span>
      <div><Button onClick={onCancel}>取消</Button><Button type="primary" onClick={() => onConfirm(draftIds)}>确定</Button></div>
    </footer>
  </Modal>
}
