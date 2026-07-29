import { CloseOutlined, PlusOutlined } from '@ant-design/icons'
import { Button } from 'antd'
import { useEffect, useMemo, useState } from 'react'
import { getKnowledgeTree, type KnowledgeNode } from '../../../api/knowledge'

type Props = {
  selectedIds: string[]
  onChange: (nodeIds: string[]) => void
  onOpenSelector: () => void
}

type ScopeSummary = { fileCount: number; folderCount: number }

function getScopeSummary(nodes: KnowledgeNode[], selectedIds: string[]): ScopeSummary {
  const selectedIdSet = new Set(selectedIds)
  const summary: ScopeSummary = { fileCount: 0, folderCount: 0 }
  const visit = (node: KnowledgeNode) => {
    if (selectedIdSet.has(node.id)) {
      if (node.nodeType === 'file') summary.fileCount += 1
      else summary.folderCount += 1
    }
    node.children.forEach(visit)
  }
  nodes.forEach(visit)
  return summary
}

export function AgentKnowledgeScopeField({ selectedIds, onChange, onOpenSelector }: Props) {
  const [nodes, setNodes] = useState<KnowledgeNode[] | null>(null)
  const summary = useMemo(() => nodes ? getScopeSummary(nodes, selectedIds) : null, [nodes, selectedIds])

  useEffect(() => {
    void getKnowledgeTree().then((tree) => setNodes(tree.items)).catch(() => setNodes([]))
  }, [])

  if (selectedIds.length === 0) {
    return <Button className="agent-workbench__preset-add" icon={<PlusOutlined />} size="small" type="text" onClick={onOpenSelector}>请选择知识集</Button>
  }

  const summaryText = summary
    ? `已绑定${summary.fileCount}篇资料，${summary.folderCount}个文件夹`
    : `已绑定${selectedIds.length}项资料`
  return <div className="agent-workbench__knowledge-summary">
    <button type="button" onClick={onOpenSelector}>{summaryText}</button>
    <Button aria-label="清空绑定知识集" icon={<CloseOutlined />} size="small" type="text" onClick={() => onChange([])} />
  </div>
}
