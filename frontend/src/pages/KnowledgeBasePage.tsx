import {
  AppstoreFilled,
  LeftOutlined,
  ReloadOutlined,
  RightOutlined,
  SearchOutlined,
  UnorderedListOutlined,
  UpOutlined,
} from '@ant-design/icons'
import { Empty, Input } from 'antd'
import { useMemo, useState } from 'react'
import { KnowledgeActionMenus } from '../features/knowledge/components/KnowledgeActionMenus'
import { KnowledgeItemGrid } from '../features/knowledge/components/KnowledgeItemGrid'
import type { KnowledgeItem } from '../features/knowledge/types'

const prototypeItems: KnowledgeItem[] = [
  { id: 'folder-1', kind: 'folder', name: '测试文档' },
  { id: 'folder-2', kind: 'folder', name: '软小筑公开文档' },
  { id: 'folder-3', kind: 'folder', name: '智能体资料' },
  { id: 'file-1', kind: 'pdf', name: '我的简历_PIEVKP.pdf', size: '399.4KB' },
  { id: 'file-2', kind: 'markdown', name: '游标分页和传统分页.md', size: '6.2KB' },
  { id: 'file-3', kind: 'word', name: '11.docx', size: '9.9KB' },
]

export function KnowledgeBasePage() {
  const [activeMenu, setActiveMenu] = useState<'new' | 'upload' | null>(null)
  const [selectedIds, setSelectedIds] = useState<string[]>([])
  const [searchText, setSearchText] = useState('')
  const [view, setView] = useState<'grid' | 'list'>('grid')
  const visibleItems = useMemo(() => {
    const keyword = searchText.trim().toLocaleLowerCase()
    return keyword ? prototypeItems.filter(item => item.name.toLocaleLowerCase().includes(keyword)) : prototypeItems
  }, [searchText])
  const folderCount = visibleItems.filter(item => item.kind === 'folder').length
  const fileCount = visibleItems.length - folderCount
  const changeSelection = (itemId: string, selected: boolean) => {
    setSelectedIds(ids => selected ? [...ids, itemId] : ids.filter(id => id !== itemId))
  }

  return <section className="knowledge-page" onClick={() => activeMenu && setActiveMenu(null)}>
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
      {folderCount} 个文件夹，{fileCount} 个文件
      <span>展示样例将在资料树接口接入后替换为真实数据</span>
    </div>
    <main className={`knowledge-canvas ${view === 'list' ? 'is-list-view' : ''}`}>
      {visibleItems.length ? <KnowledgeItemGrid items={visibleItems} onSelectionChange={changeSelection} selectedIds={selectedIds} /> : <Empty description="没有匹配的资料" image={Empty.PRESENTED_IMAGE_SIMPLE} />}
    </main>
  </section>
}
