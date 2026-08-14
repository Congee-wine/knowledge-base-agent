import { AppstoreFilled, CloseOutlined, DeleteOutlined, ReloadOutlined, SwapOutlined, UnorderedListOutlined } from '@ant-design/icons'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Empty, Input, Modal, Radio, Result, Spin, message } from 'antd'
import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { createKnowledgeFolder, deleteKnowledgeNode, getKnowledgeTree, moveKnowledgeNode, renameKnowledgeNode, retryEmbedding, uploadKnowledgeFile, type KnowledgeNode } from '../api/knowledge'
import { KnowledgeActionMenus } from '../features/knowledge/components/KnowledgeActionMenus'
import { KnowledgeContextMenu } from '../features/knowledge/components/KnowledgeContextMenu'
import { KnowledgeItemGrid } from '../features/knowledge/components/KnowledgeItemGrid'
import { KnowledgeNavigationToolbar } from '../features/knowledge/components/KnowledgeNavigationToolbar'
import { knowledgeKeys } from '../features/knowledge/knowledgeKeys'
import type { KnowledgeActionId, KnowledgeItem } from '../features/knowledge/types'
import { routes } from '../routes/paths'

function flattenNodes(nodes: KnowledgeNode[]): KnowledgeItem[] {
  return nodes.flatMap(node => {
    const processingStatus = node.status ?? undefined
    const indexStatus = node.indexStatus ?? undefined
    const isEmbeddingFailed = processingStatus === 'ready' && indexStatus === 'failed'
    return [{
      id: node.id, parentId: node.parentId ?? undefined, name: node.name,
      kind: node.nodeType === 'folder' ? 'folder' : getFileKind(node),
      processingStatus, indexStatus,
      ...(isEmbeddingFailed ? { actions: ['preview', 'retry-embedding', 'delete'] as KnowledgeActionId[] } : {}),
    }, ...flattenNodes(node.children)]
  })
}

function getFileKind(node: KnowledgeNode): KnowledgeItem['kind'] {
  if (node.mimeType === 'application/pdf' || node.name.toLowerCase().endsWith('.pdf')) return 'pdf'
  if (node.mimeType?.includes('wordprocessingml') || node.name.toLowerCase().endsWith('.docx')) return 'word'
  return 'markdown'
}

export function KnowledgeBasePage() {
  const navigate = useNavigate()
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
  const uploadInputRef = useRef<HTMLInputElement>(null)
  const folderUploadInputRef = useRef<HTMLInputElement>(null)
  const pendingItemIdsRef = useRef(new Set<string>())
  const invalidateTree = () => queryClient.invalidateQueries({ queryKey: knowledgeKeys.tree })
  const createMutation = useMutation({ mutationFn: () => createKnowledgeFolder(currentFolderId ?? null, folderName.trim()), onSuccess: () => { void invalidateTree(); setCreateModalOpen(false); setFolderName(''); message.success('文件夹已创建') }, onError: () => message.error('创建文件夹失败，请检查名称后重试') })
  const renameMutation = useMutation({ mutationFn: () => renameKnowledgeNode(renameItem!.id, renameValue.trim()), onSuccess: () => { void invalidateTree(); setRenameItem(null); message.success('已重命名') }, onError: () => message.error('重命名失败，请检查名称是否重复') })
  const moveMutation = useMutation({ mutationFn: async () => Promise.all(moveItemIds.map(id => moveKnowledgeNode(id, targetFolderId))), onSuccess: () => { void invalidateTree(); setSelectedIds([]); setMoveItemIds([]); setMoveModalOpen(false); message.success('已移动') }, onError: () => message.error('移动失败；目标不能是自身或其子文件夹，且不能同名') })
  const deleteMutation = useMutation({ mutationFn: async (ids: string[]) => Promise.all(ids.map(deleteKnowledgeNode)), onSuccess: () => { void invalidateTree(); setSelectedIds([]); message.success('已删除') }, onError: () => message.error('删除失败，请重试') })
  const retryEmbeddingMutation = useMutation({ mutationFn: (nodeId: string) => retryEmbedding(nodeId), onSuccess: () => { void invalidateTree(); message.success('已重新提交向量化任务') }, onError: () => message.error('重试失败，请稍后再试') })
  const uploadMutation = useMutation({
    mutationFn: (file: File) => uploadKnowledgeFile(currentFolderId ?? null, file),
    onSuccess: node => { pendingItemIdsRef.current.add(node.id); void invalidateTree(); message.success('文件已上传，等待后续处理') },
    onError: error => { void invalidateTree(); message.error(error instanceof Error ? `上传失败：${error.message}` : '上传失败，请重试') },
  })
  const items = useMemo(() => flattenNodes(treeQuery.data?.items ?? []), [treeQuery.data])
  const isItemPending = (item: KnowledgeItem) =>
    item.processingStatus === 'uploaded' || item.processingStatus === 'processing' || item.indexStatus === 'pending' || item.indexStatus === 'processing'
  const hasPendingDocuments = items.some(isItemPending)
  useEffect(() => {
    const itemIds = new Set(items.map(item => item.id))
    if ([...pendingItemIdsRef.current].some(itemId => !itemIds.has(itemId))) {
      message.error('文件处理失败，未加入知识库')
    }
    pendingItemIdsRef.current = new Set(items.filter(isItemPending).map(item => item.id))
  }, [items])
  useEffect(() => {
    if (!hasPendingDocuments) return
    const timer = window.setInterval(() => { void queryClient.invalidateQueries({ queryKey: knowledgeKeys.tree }) }, 3000)
    return () => window.clearInterval(timer)
  }, [hasPendingDocuments, queryClient])
  useEffect(() => {
    if (!currentFolderId || items.some(item => item.id === currentFolderId)) return
    setCurrentFolderId(undefined)
    setFolderHistory([undefined])
    setHistoryIndex(0)
    setSelectedIds([])
  }, [currentFolderId, items])
  const visibleItems = useMemo(() => {
    const keyword = searchText.trim().toLocaleLowerCase()
    return items.filter(item => {
      if (item.processingStatus === 'failed') return false
      if (item.parentId !== currentFolderId) return false
      if (keyword && !item.name.toLocaleLowerCase().includes(keyword)) return false
      return true
    })
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
    if (action === 'preview') return openFilePreview(item)
    if (action === 'retry-embedding') return retryEmbeddingMutation.mutate(item.id)
    message.info('编辑和下载将在后续阶段开放')
  }
  const openFilePreview = (item: KnowledgeItem) => {
    if (item.processingStatus !== 'ready') {
      message.info(item.processingStatus === 'failed' ? '文件处理失败，无法预览' : '文件仍在处理中，请稍后再试')
      return
    }
    navigate(routes.app.knowledgeFilePreview(item.id))
  }
  const handleUploadFile = (file: File | undefined) => {
    if (!file) return
    const extension = file.name.slice(file.name.lastIndexOf('.')).toLowerCase()
    if (!['.pdf', '.txt', '.md', '.markdown', '.docx'].includes(extension)) {
      message.error('当前仅支持 PDF、TXT、Markdown、DOCX 文档')
      return
    }
    uploadMutation.mutate(file)
  }
  const handleFolderUpload = async (files: File[]) => {
    const supportedExtensions = ['.pdf', '.txt', '.md', '.markdown', '.docx']
    if (files.some(file => !supportedExtensions.includes(file.name.slice(file.name.lastIndexOf('.')).toLowerCase()))) {
      message.error('文件夹中包含不支持的文件；当前仅支持 PDF、TXT、Markdown、DOCX')
      return
    }
    const folderIds = new Map<string, string | null>([['', currentFolderId ?? null]])
    try {
      for (const file of files) {
        const relativePath = (file as File & { webkitRelativePath?: string }).webkitRelativePath || file.name
        const directories = relativePath.split('/').slice(0, -1)
        let path = ''
        for (const directory of directories) {
          const parentId = folderIds.get(path) ?? null
          path = path ? `${path}/${directory}` : directory
          if (!folderIds.has(path)) folderIds.set(path, (await createKnowledgeFolder(parentId, directory)).id)
        }
        const uploadedNode = await uploadKnowledgeFile(folderIds.get(path) ?? null, file)
        pendingItemIdsRef.current.add(uploadedNode.id)
      }
      await invalidateTree()
      message.success(`已上传文件夹中的 ${files.length} 个文件，等待后续处理`)
    } catch (error) {
      void invalidateTree()
      message.error(error instanceof Error ? `文件夹上传未完全完成：${error.message}` : '文件夹上传未完全完成，请刷新资料树后检查结果')
    }
  }
  if (treeQuery.isPending) return <div className="grid h-full place-items-center"><Spin tip="正在加载资料树" /></div>
  if (treeQuery.isError) return <Result status="error" title="无法加载资料树" extra={<button type="button" onClick={() => void invalidateTree()}>重试</button>} />
  return <section className="knowledge-page" onClick={() => { setActiveMenu(null); setContextItem(null) }}>
    <header className="knowledge-hero"><div className="knowledge-hero__title"><div><h1>文档管理</h1><p>深度解析文档内容，精准提取关键信息，为您构建专属知识库。</p></div></div>
      <div className="knowledge-toolbar" onClick={event => event.stopPropagation()}><KnowledgeNavigationToolbar canGoForward={historyIndex < folderHistory.length - 1} currentFolderId={currentFolderId} historyIndex={historyIndex} items={items} searchPlaceholder="搜索名称" searchText={searchText} onGoBack={goBack} onGoForward={goForward} onNavigateToFolder={navigateToFolder} onSearchTextChange={setSearchText} />
        <KnowledgeActionMenus activeMenu={activeMenu} onMenuChange={setActiveMenu} onCreateFolder={() => { setActiveMenu(null); setCreateModalOpen(true) }} onUploadFile={() => { setActiveMenu(null); uploadInputRef.current?.click() }} onUploadFolder={() => { setActiveMenu(null); folderUploadInputRef.current?.click() }} /><div className="knowledge-view-actions"><button aria-label="网格视图" className={view === 'grid' ? 'is-active' : ''} type="button" onClick={() => setView('grid')}><AppstoreFilled /></button><button aria-label="列表视图" className={view === 'list' ? 'is-active' : ''} type="button" onClick={() => setView('list')}><UnorderedListOutlined /></button><button aria-label="刷新资料" type="button" onClick={() => void invalidateTree()}><ReloadOutlined /></button></div></div></header>
    <div className="knowledge-page__summary"><span>{folderCount} 个文件夹，{visibleItems.length - folderCount} 个文件</span>{selectedIds.length > 0 && <div className="knowledge-batch-actions"><strong>已选择 {selectedIds.length} 项</strong><button className="knowledge-batch-actions__move" type="button" onClick={() => openMoveDialog(selectedIds)}><SwapOutlined /> 移动</button><button className="knowledge-batch-actions__delete" type="button" onClick={() => removeItems(selectedIds)}><DeleteOutlined /> 删除</button><button type="button" onClick={() => setSelectedIds([])}><CloseOutlined /> 取消</button></div>}</div>
    <main className={`knowledge-canvas ${view === 'list' ? 'is-list-view' : ''}`}>{visibleItems.length ? <KnowledgeItemGrid items={visibleItems} selectedIds={selectedIds} onOpenFolder={item => navigateToFolder(item.id)} onOpenFile={openFilePreview} onSelectionChange={(id, selected) => setSelectedIds(ids => selected ? [...ids, id] : ids.filter(value => value !== id))} onContextMenu={(item, position) => { setSelectedIds([item.id]); setContextItem({ item, position }) }} /> : <Empty description="暂无资料" image={Empty.PRESENTED_IMAGE_SIMPLE} />}</main>
    <input ref={uploadInputRef} accept=".pdf,.txt,.md,.markdown,.docx" hidden type="file" onChange={event => { handleUploadFile(event.target.files?.[0]); event.target.value = '' }} />
    <input ref={input => { folderUploadInputRef.current = input; input?.setAttribute('webkitdirectory', '') }} accept=".pdf,.txt,.md,.markdown,.docx" hidden multiple type="file" onChange={event => { void handleFolderUpload(Array.from(event.target.files ?? [])); event.target.value = '' }} />
    <Modal cancelText="取消" okButtonProps={{ disabled: !folderName.trim() }} okText="创建" onCancel={() => setCreateModalOpen(false)} onOk={() => createMutation.mutate()} open={createModalOpen} title="新建文件夹"><Input autoFocus onChange={event => setFolderName(event.target.value)} value={folderName} /></Modal>
    <Modal cancelText="取消" okButtonProps={{ disabled: !renameValue.trim() }} okText="保存" onCancel={() => setRenameItem(null)} onOk={() => renameMutation.mutate()} open={renameItem !== null} title="重命名"><Input autoFocus onChange={event => setRenameValue(event.target.value)} value={renameValue} /></Modal>
    <Modal cancelText="取消" okButtonProps={{ disabled: targetFolderId === null }} okText="移动" onCancel={() => setMoveModalOpen(false)} onOk={() => moveMutation.mutate()} open={moveModalOpen} title={`移动 ${moveItemIds.length} 项到文件夹`}><Radio.Group className="knowledge-move-modal__options" onChange={event => setTargetFolderId(event.target.value)} value={targetFolderId}><Radio value={null}>根目录</Radio>{moveTargets.map(folder => <Radio key={folder.id} value={folder.id}>{folder.name}</Radio>)}</Radio.Group></Modal>
    {contextItem && <KnowledgeContextMenu item={contextItem.item} onAction={handleAction} position={contextItem.position} />}
  </section>
}
