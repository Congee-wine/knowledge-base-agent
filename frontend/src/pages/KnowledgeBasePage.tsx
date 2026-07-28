import {
  AppstoreFilled,
  CloseOutlined,
  DeleteOutlined,
  LeftOutlined,
  ReloadOutlined,
  RightOutlined,
  SearchOutlined,
  SwapOutlined,
  UnorderedListOutlined,
  UpOutlined,
} from '@ant-design/icons'
import { Empty, Input, Modal, Radio, message } from 'antd'
import { useMemo, useState } from 'react'
import { KnowledgeActionMenus } from '../features/knowledge/components/KnowledgeActionMenus'
import { KnowledgeContextMenu } from '../features/knowledge/components/KnowledgeContextMenu'
import { KnowledgeItemGrid } from '../features/knowledge/components/KnowledgeItemGrid'
import type { KnowledgeActionId, KnowledgeItem } from '../features/knowledge/types'
import { getStoredUser } from '../lib/auth'
import { useAuthStore } from '../stores/auth'

const prototypeItems: KnowledgeItem[] = [
  { id: 'folder-1', kind: 'folder', name: '测试文档' },
  { id: 'folder-2', kind: 'folder', name: '软小筑公开文档' },
  { id: 'folder-3', kind: 'folder', name: '智能体资料', actions: ['open'], isBuiltin: true },
  { id: 'file-1', kind: 'pdf', name: '我的简历_PIEVKP.pdf', size: '399.4KB' },
  { id: 'file-2', kind: 'markdown', name: '游标分页和传统分页.md', size: '6.2KB' },
  { id: 'file-3', kind: 'word', name: '11.docx', size: '9.9KB' },
]

export function KnowledgeBasePage() {
  const currentUser = useAuthStore(state => state.user) ?? getStoredUser()
  const [activeMenu, setActiveMenu] = useState<'new' | 'upload' | null>(null)
  const [selectedIds, setSelectedIds] = useState<string[]>([])
  const [searchText, setSearchText] = useState('')
  const [view, setView] = useState<'grid' | 'list'>('grid')
  const [items, setItems] = useState(() => prototypeItems.map(item => (
    item.isBuiltin ? item : { ...item, ownerName: currentUser?.email }
  )))
  const [moveModalOpen, setMoveModalOpen] = useState(false)
  const [targetFolderId, setTargetFolderId] = useState<string | null>(null)
  const [moveItemIds, setMoveItemIds] = useState<string[]>([])
  const [renameItem, setRenameItem] = useState<KnowledgeItem | null>(null)
  const [renameValue, setRenameValue] = useState('')
  const [contextItem, setContextItem] = useState<{ item: KnowledgeItem; position: { x: number; y: number } } | null>(null)
  const visibleItems = useMemo(() => {
    const keyword = searchText.trim().toLocaleLowerCase()
    const rootItems = items.filter(item => item.parentId === undefined)
    return keyword ? rootItems.filter(item => item.name.toLocaleLowerCase().includes(keyword)) : rootItems
  }, [items, searchText])
  const folderCount = visibleItems.filter(item => item.kind === 'folder').length
  const fileCount = visibleItems.length - folderCount
  const moveTargets = items.filter(item => item.kind === 'folder' && !selectedIds.includes(item.id))
  const changeSelection = (itemId: string, selected: boolean) => {
    setSelectedIds(ids => selected ? [...ids, itemId] : ids.filter(id => id !== itemId))
  }
  const removeItems = (itemIds: string[]) => {
    Modal.confirm({
      title: `删除已选择的 ${itemIds.length} 项？`,
      content: '当前仅影响本地展示样例；接入资料树 API 后将由服务端执行真实删除。',
      okButtonProps: { danger: true },
      okText: '删除',
      cancelText: '取消',
      onOk: () => {
        setItems(currentItems => currentItems.filter(item => !itemIds.includes(item.id)))
        setSelectedIds([])
        message.success('已从当前展示样例中删除')
      },
    })
  }
  const openMoveDialog = (itemIds: string[]) => {
    setMoveItemIds(itemIds)
    setTargetFolderId(null)
    setMoveModalOpen(true)
  }
  const moveItems = () => {
    if (!targetFolderId) return
    setItems(currentItems => currentItems.map(item => moveItemIds.includes(item.id) ? { ...item, parentId: targetFolderId } : item))
    setSelectedIds([])
    setMoveItemIds([])
    setTargetFolderId(null)
    setMoveModalOpen(false)
    message.success('已移动当前展示样例中的资料')
  }
  const openRenameDialog = (item: KnowledgeItem) => {
    setRenameItem(item)
    setRenameValue(item.name)
  }
  const renameCurrentItem = () => {
    const nextName = renameValue.trim()
    if (!renameItem || !nextName) return
    setItems(currentItems => currentItems.map(item => item.id === renameItem.id ? { ...item, name: nextName } : item))
    setRenameItem(null)
    message.success('已重命名当前展示样例')
  }
  const handleContextAction = (action: KnowledgeActionId, item: KnowledgeItem) => {
    setContextItem(null)
    setSelectedIds([item.id])
    if (action === 'rename') return openRenameDialog(item)
    if (action === 'move') return openMoveDialog([item.id])
    if (action === 'delete') return removeItems([item.id])
    message.info(`${action === 'open' ? '打开' : action === 'preview' ? '预览' : action === 'edit' ? '编辑' : '下载'}将在资料服务接入后开放`)
  }

  return <section className="knowledge-page" onClick={() => { setActiveMenu(null); setContextItem(null) }}>
    <header className="knowledge-hero">
      <div className="knowledge-hero__title">
        <div className="knowledge-hero__folder" aria-hidden="true">▰</div>
        <div><h1>文档管理</h1><p>深度解析文档内容，精准提取关键信息，为您构建专属知识库。</p></div>
      </div>
      <div className="knowledge-toolbar" onClick={event => event.stopPropagation()}>
        <div className="knowledge-toolbar__path">
          <button aria-label="后退" disabled type="button"><LeftOutlined /></button>
          <button aria-label="前进" disabled type="button"><RightOutlined /></button>
          <button aria-label="返回上一级" disabled type="button"><UpOutlined /></button>
          <strong>根目录</strong>
          <Input allowClear onChange={event => setSearchText(event.target.value)} placeholder="搜索名称或类型，例如：png、doc、pdf等" prefix={<SearchOutlined />} value={searchText} />
        </div>
        <KnowledgeActionMenus activeMenu={activeMenu} onMenuChange={setActiveMenu} />
        <div className="knowledge-view-actions">
          <button aria-label="网格视图" className={view === 'grid' ? 'is-active' : ''} type="button" onClick={() => setView('grid')}><AppstoreFilled /></button>
          <button aria-label="列表视图" className={view === 'list' ? 'is-active' : ''} type="button" onClick={() => setView('list')}><UnorderedListOutlined /></button>
          <button aria-label="刷新资料" type="button" onClick={() => setSearchText('')}><ReloadOutlined /></button>
        </div>
      </div>
    </header>
    <div className="knowledge-page__summary">
      <span>{folderCount} 个文件夹，{fileCount} 个文件</span>
      {selectedIds.length > 0 ? <div className="knowledge-batch-actions">
        <strong>已选择 {selectedIds.length} 项</strong>
        <button className="knowledge-batch-actions__move" type="button" onClick={() => openMoveDialog(selectedIds)}><SwapOutlined /> 移动</button>
        <button className="knowledge-batch-actions__delete" type="button" onClick={() => removeItems(selectedIds)}><DeleteOutlined /> 删除</button>
        <button type="button" onClick={() => setSelectedIds([])}><CloseOutlined /> 取消</button>
      </div> : <span>展示样例将在资料树接口接入后替换为真实数据</span>}
    </div>
    <main className={`knowledge-canvas ${view === 'list' ? 'is-list-view' : ''}`}>
      {visibleItems.length ? <KnowledgeItemGrid
        items={visibleItems}
        onContextMenu={(item, position) => { setSelectedIds([item.id]); setContextItem({ item, position }) }}
        onSelectionChange={changeSelection}
        selectedIds={selectedIds}
      /> : <Empty description="没有匹配的资料" image={Empty.PRESENTED_IMAGE_SIMPLE} />}
    </main>
    <Modal
      cancelText="取消"
      okButtonProps={{ disabled: targetFolderId === null }}
      okText="移动"
      onCancel={() => { setMoveModalOpen(false); setTargetFolderId(null) }}
      onOk={moveItems}
      open={moveModalOpen}
      title={`移动 ${moveItemIds.length} 项到文件夹`}
    >
      <p className="knowledge-move-modal__hint">选择目标文件夹。当前操作只作用于本地展示样例。</p>
      <Radio.Group className="knowledge-move-modal__options" onChange={event => setTargetFolderId(event.target.value)} value={targetFolderId}>
        {moveTargets.map(folder => <Radio key={folder.id} value={folder.id}>{folder.name}</Radio>)}
      </Radio.Group>
    </Modal>
    <Modal
      cancelText="取消"
      okButtonProps={{ disabled: !renameValue.trim() }}
      okText="保存"
      onCancel={() => setRenameItem(null)}
      onOk={renameCurrentItem}
      open={renameItem !== null}
      title="重命名"
    >
      <Input autoFocus onChange={event => setRenameValue(event.target.value)} value={renameValue} />
    </Modal>
    {contextItem && <KnowledgeContextMenu item={contextItem.item} onAction={handleContextAction} position={contextItem.position} />}
  </section>
}
