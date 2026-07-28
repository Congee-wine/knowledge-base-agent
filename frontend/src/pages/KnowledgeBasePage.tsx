import { AppstoreFilled, CloseOutlined, DeleteOutlined, LeftOutlined, ReloadOutlined, RightOutlined, SearchOutlined, SwapOutlined, UnorderedListOutlined, UpOutlined } from '@ant-design/icons'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Empty, Input, Modal, Radio, Result, Spin, message } from 'antd'
import { useMemo, useState } from 'react'
import { createKnowledgeFolder, deleteKnowledgeNode, getKnowledgeTree, moveKnowledgeNode, renameKnowledgeNode, type KnowledgeNode } from '../api/knowledge'
import { KnowledgeActionMenus } from '../features/knowledge/components/KnowledgeActionMenus'
import { KnowledgeContextMenu } from '../features/knowledge/components/KnowledgeContextMenu'
import { KnowledgeItemGrid } from '../features/knowledge/components/KnowledgeItemGrid'
import { knowledgeKeys } from '../features/knowledge/knowledgeKeys'
import type { KnowledgeActionId, KnowledgeItem } from '../features/knowledge/types'

function flattenNodes(nodes: KnowledgeNode[]): KnowledgeItem[] {
  return nodes.flatMap(node => [{
    id: node.id, parentId: node.parentId ?? undefined, name: node.name,
    kind: node.nodeType === 'folder' ? 'folder' : 'markdown',
  }, ...flattenNodes(node.children)])
}

export function KnowledgeBasePage() {
  const queryClient = useQueryClient()
  const treeQuery = useQuery({ queryKey: knowledgeKeys.tree, queryFn: getKnowledgeTree })
  const [activeMenu, setActiveMenu] = useState<'new' | 'upload' | null>(null)
  const [selectedIds, setSelectedIds] = useState<string[]>([])
  const [searchText, setSearchText] = useState('')
  const [view, setView] = useState<'grid' | 'list'>('grid')
  const [currentFolderId, setCurrentFolderId] = useState<string | undefined>()
  const [folderHistory, setFolderHistory] = useState<Array<string | undefined>>([undefined])
  const [historyIndex, setHistoryIndex] = useState(0)
  const [moveModalOpen, setMoveModalOpen] = useState(false)
  const [targetFolderId, setTargetFolderId] = useState<string | null>(null)
  const [moveItemIds, setMoveItemIds] = useState<string[]>([])
  const [renameItem, setRenameItem] = useState<KnowledgeItem | null>(null)
  const [renameValue, setRenameValue] = useState('')
  const [createModalOpen, setCreateModalOpen] = useState(false)
  const [folderName, setFolderName] = useState('')
  const [contextItem, setContextItem] = useState<{ item: KnowledgeItem; position: { x: number; y: number } } | null>(null)
  const invalidateTree = () => queryClient.invalidateQueries({ queryKey: knowledgeKeys.tree })
  const createMutation = useMutation({ mutationFn: () => createKnowledgeFolder(currentFolderId ?? null, folderName.trim()), onSuccess: () => { void invalidateTree(); setCreateModalOpen(false); setFolderName(''); message.success('文件夹已创建') }, onError: () => message.error('创建文件夹失败，请检查名称后重试') })
  const renameMutation = useMutation({ mutationFn: () => renameKnowledgeNode(renameItem!.id, renameValue.trim()), onSuccess: () => { void invalidateTree(); setRenameItem(null); message.success('已重命名') }, onError: () => message.error('重命名失败，请检查名称是否重复') })
  const moveMutation = useMutation({ mutationFn: async () => Promise.all(moveItemIds.map(id => moveKnowledgeNode(id, targetFolderId))), onSuccess: () => { void invalidateTree(); setSelectedIds([]); setMoveItemIds([]); setMoveModalOpen(false); message.success('已移动') }, onError: () => message.error('移动失败；目标不能是自身或其子文件夹，且不能同名') })
  const deleteMutation = useMutation({ mutationFn: async (ids: string[]) => Promise.all(ids.map(deleteKnowledgeNode)), onSuccess: () => { void invalidateTree(); setSelectedIds([]); message.success('已删除') }, onError: () => message.error('删除失败，请重试') })
  const items = useMemo(() => flattenNodes(treeQuery.data?.items ?? []), [treeQuery.data])
  const breadcrumbs = useMemo(() => {
    const trail: KnowledgeItem[] = []
    let node = currentFolderId ? items.find(item => item.id === currentFolderId) : undefined
    while (node) {
      trail.unshift(node)
      node = node.parentId ? items.find(item => item.id === node!.parentId) : undefined
    }
    return trail
  }, [currentFolderId, items])
  const visibleItems = useMemo(() => {
    const keyword = searchText.trim().toLocaleLowerCase()
    return items.filter(item => item.parentId === currentFolderId && (!keyword || item.name.toLocaleLowerCase().includes(keyword)))
  }, [currentFolderId, items, searchText])
  const moveTargets = items.filter(item => item.kind === 'folder' && !moveItemIds.includes(item.id))
  const folderCount = visibleItems.filter(item => item.kind === 'folder').length
  const openMoveDialog = (ids: string[]) => { setMoveItemIds(ids); setTargetFolderId(null); setMoveModalOpen(true) }
  const navigateToFolder = (folderId: string | undefined) => {
    setCurrentFolderId(folderId)
    setFolderHistory(history => [...history.slice(0, historyIndex + 1), folderId])
    setHistoryIndex(index => index + 1)
    setSelectedIds([])
  }
  const goBack = () => {
    if (historyIndex === 0) return
    const nextIndex = historyIndex - 1
    setHistoryIndex(nextIndex)
    setCurrentFolderId(folderHistory[nextIndex])
    setSelectedIds([])
  }
  const goForward = () => {
    if (historyIndex >= folderHistory.length - 1) return
    const nextIndex = historyIndex + 1
    setHistoryIndex(nextIndex)
    setCurrentFolderId(folderHistory[nextIndex])
    setSelectedIds([])
  }
  const removeItems = (ids: string[]) => Modal.confirm({ title: `永久删除 ${ids.length} 项？`, content: '文件夹会递归删除全部后代，且无法恢复。', okButtonProps: { danger: true }, okText: '删除', cancelText: '取消', onOk: () => deleteMutation.mutateAsync(ids) })
  const handleAction = (action: KnowledgeActionId, item: KnowledgeItem) => {
    setContextItem(null); setSelectedIds([item.id])
    if (action === 'open' && item.kind === 'folder') return navigateToFolder(item.id)
    if (action === 'rename') { setRenameItem(item); setRenameValue(item.name); return }
    if (action === 'move') return openMoveDialog([item.id])
    if (action === 'delete') return removeItems([item.id])
    message.info('预览、编辑和下载将在资料上传阶段开放')
  }
  if (treeQuery.isPending) return <div className="grid h-full place-items-center"><Spin tip="正在加载资料树" /></div>
  if (treeQuery.isError) return <Result status="error" title="无法加载资料树" extra={<button type="button" onClick={() => void invalidateTree()}>重试</button>} />
  return <section className="knowledge-page" onClick={() => { setActiveMenu(null); setContextItem(null) }}>
    <header className="knowledge-hero"><div className="knowledge-hero__title"><div className="knowledge-hero__folder" aria-hidden="true">▰</div><div><h1>文档管理</h1><p>深度解析文档内容，精准提取关键信息，为您构建专属知识库。</p></div></div>
      <div className="knowledge-toolbar" onClick={event => event.stopPropagation()}><div className="knowledge-toolbar__path"><button aria-label="后退" className={historyIndex > 0 ? 'is-enabled' : ''} disabled={historyIndex === 0} type="button" onClick={goBack}><LeftOutlined /></button><button aria-label="前进" className={historyIndex < folderHistory.length - 1 ? 'is-enabled' : ''} disabled={historyIndex >= folderHistory.length - 1} type="button" onClick={goForward}><RightOutlined /></button><button aria-label="返回上一级" className={currentFolderId ? 'is-enabled' : ''} disabled={!currentFolderId} type="button" onClick={() => navigateToFolder(items.find(item => item.id === currentFolderId)?.parentId)}><UpOutlined /></button><nav className="knowledge-breadcrumb" aria-label="资料路径"><button type="button" onClick={() => navigateToFolder(undefined)}>根目录</button>{breadcrumbs.map(item => <span key={item.id}><i>/</i><button type="button" onClick={() => navigateToFolder(item.id)}>{item.name}</button></span>)}</nav><Input allowClear onChange={event => setSearchText(event.target.value)} placeholder="搜索名称" prefix={<SearchOutlined />} value={searchText} /></div>
        <KnowledgeActionMenus activeMenu={activeMenu} onMenuChange={setActiveMenu} onCreateFolder={() => { setActiveMenu(null); setCreateModalOpen(true) }} /><div className="knowledge-view-actions"><button aria-label="网格视图" className={view === 'grid' ? 'is-active' : ''} type="button" onClick={() => setView('grid')}><AppstoreFilled /></button><button aria-label="列表视图" className={view === 'list' ? 'is-active' : ''} type="button" onClick={() => setView('list')}><UnorderedListOutlined /></button><button aria-label="刷新资料" type="button" onClick={() => void invalidateTree()}><ReloadOutlined /></button></div></div></header>
    <div className="knowledge-page__summary"><span>{folderCount} 个文件夹，{visibleItems.length - folderCount} 个文件</span>{selectedIds.length > 0 && <div className="knowledge-batch-actions"><strong>已选择 {selectedIds.length} 项</strong><button className="knowledge-batch-actions__move" type="button" onClick={() => openMoveDialog(selectedIds)}><SwapOutlined /> 移动</button><button className="knowledge-batch-actions__delete" type="button" onClick={() => removeItems(selectedIds)}><DeleteOutlined /> 删除</button><button type="button" onClick={() => setSelectedIds([])}><CloseOutlined /> 取消</button></div>}</div>
    <main className={`knowledge-canvas ${view === 'list' ? 'is-list-view' : ''}`}>{visibleItems.length ? <KnowledgeItemGrid items={visibleItems} selectedIds={selectedIds} onOpenFolder={item => navigateToFolder(item.id)} onSelectionChange={(id, selected) => setSelectedIds(ids => selected ? [...ids, id] : ids.filter(value => value !== id))} onContextMenu={(item, position) => { setSelectedIds([item.id]); setContextItem({ item, position }) }} /> : <Empty description="暂无资料" image={Empty.PRESENTED_IMAGE_SIMPLE} />}</main>
    <Modal cancelText="取消" okButtonProps={{ disabled: !folderName.trim() }} okText="创建" onCancel={() => setCreateModalOpen(false)} onOk={() => createMutation.mutate()} open={createModalOpen} title="新建文件夹"><Input autoFocus onChange={event => setFolderName(event.target.value)} value={folderName} /></Modal>
    <Modal cancelText="取消" okButtonProps={{ disabled: !renameValue.trim() }} okText="保存" onCancel={() => setRenameItem(null)} onOk={() => renameMutation.mutate()} open={renameItem !== null} title="重命名"><Input autoFocus onChange={event => setRenameValue(event.target.value)} value={renameValue} /></Modal>
    <Modal cancelText="取消" okButtonProps={{ disabled: targetFolderId === null }} okText="移动" onCancel={() => setMoveModalOpen(false)} onOk={() => moveMutation.mutate()} open={moveModalOpen} title={`移动 ${moveItemIds.length} 项到文件夹`}><Radio.Group className="knowledge-move-modal__options" onChange={event => setTargetFolderId(event.target.value)} value={targetFolderId}><Radio value={null}>根目录</Radio>{moveTargets.map(folder => <Radio key={folder.id} value={folder.id}>{folder.name}</Radio>)}</Radio.Group></Modal>
    {contextItem && <KnowledgeContextMenu item={contextItem.item} onAction={handleAction} position={contextItem.position} />}
  </section>
}
