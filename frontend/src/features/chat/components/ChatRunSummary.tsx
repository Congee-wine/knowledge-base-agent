import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  DownOutlined,
  LoadingOutlined,
  RightOutlined,
} from '@ant-design/icons'
import { useEffect, useRef, useState } from 'react'

export type ChatRunStep = {
  id: string
  status: 'loading' | 'success' | 'error' | 'abort'
  title: string
  description?: string
}

type RunStepGroup = ChatRunStep & { children?: ChatRunStep[] }

type Props = {
  steps: ChatRunStep[]
}

const retrievalStages = ['retrieving', 'context', 'no_match', 'retrieval_failed']

function isRetrievalStep(step: ChatRunStep) {
  return retrievalStages.some((stage) => step.id.startsWith(`${stage}-`))
}

function getGroupStatus(steps: ChatRunStep[]): ChatRunStep['status'] {
  if (steps.some((step) => step.status === 'error')) return 'error'
  if (steps.some((step) => step.status === 'loading')) return 'loading'
  if (steps.some((step) => step.status === 'abort')) return 'abort'
  return 'success'
}

function groupSteps(steps: ChatRunStep[]): RunStepGroup[] {
  const retrievalSteps = steps.filter(isRetrievalStep)
  if (retrievalSteps.length < 2) return steps

  const firstRetrievalIndex = steps.findIndex(isRetrievalStep)
  const latestStep = retrievalSteps.at(-1)
  const matchedSources = latestStep?.title.match(/已命中\s*(\d+)\s*条资料/)
  const retrievalGroup: RunStepGroup = {
    children: retrievalSteps,
    description: matchedSources ? `命中 ${matchedSources[1]} 条资料` : undefined,
    id: 'knowledge-retrieval',
    status: getGroupStatus(retrievalSteps),
    title: getGroupStatus(retrievalSteps) === 'loading' ? '正在检索知识库' : '已检索知识库',
  }
  return steps.reduce<RunStepGroup[]>((groups, step, index) => {
    if (index === firstRetrievalIndex) groups.push(retrievalGroup)
    if (!isRetrievalStep(step)) groups.push(step)
    return groups
  }, [])
}

function StepIcon({ status }: { status: ChatRunStep['status'] }) {
  if (status === 'loading') return <LoadingOutlined className="chat-run-step__icon is-loading" />
  if (status === 'error' || status === 'abort') return <CloseCircleOutlined className="chat-run-step__icon is-error" />
  return <CheckCircleOutlined className="chat-run-step__icon is-success" />
}

function StepContent({ step, compact = false }: { step: ChatRunStep; compact?: boolean }) {
  return <div className={compact ? 'chat-run-step__content is-compact' : 'chat-run-step__content'}>
    <StepIcon status={step.status} />
    <div>
      <strong>{step.title}</strong>
      {!compact && step.description && <span>{step.description}</span>}
    </div>
  </div>
}

export function ChatRunSummary({ steps }: Props) {
  const groups = groupSteps(steps)
  const initializedGroupIds = useRef(new Set<string>())
  const [expandedGroupIds, setExpandedGroupIds] = useState<string[]>([])

  useEffect(() => {
    const groupIds = groups
      .filter((group) => group.children && !initializedGroupIds.current.has(group.id))
      .map((group) => group.id)
    groupIds.forEach((id) => initializedGroupIds.current.add(id))
    setExpandedGroupIds((current) => {
      const missingIds = groupIds.filter((id) => !current.includes(id))
      return missingIds.length ? [...current, ...missingIds] : current
    })
  }, [groups])

  if (groups.length === 0) return null
  const handleGroupToggle = (groupId: string, expanded: boolean) => {
    setExpandedGroupIds((current) => expanded ? [...new Set([...current, groupId])] : current.filter((id) => id !== groupId))
  }

  return <section aria-label="回答运行过程" className="chat-run-summary">
    {groups.map((group) => group.children ? <details className="chat-run-step-group" key={group.id} open={expandedGroupIds.includes(group.id)} onToggle={(event) => handleGroupToggle(group.id, event.currentTarget.open)}>
      <summary>
        <StepContent step={group} />
        <span className="chat-run-step-group__toggle"><RightOutlined className="is-collapsed" /><DownOutlined className="is-expanded" /></span>
      </summary>
      <div className="chat-run-step-group__children">
        {group.children.map((step) => <div className="chat-run-step-group__child" key={step.id}><StepContent compact step={step} /></div>)}
      </div>
    </details> : <div className="chat-run-step" key={group.id}><StepContent step={group} /></div>)}
  </section>
}
