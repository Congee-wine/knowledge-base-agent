import { ThoughtChain, type ThoughtChainItemType } from '@ant-design/x'
import { BulbOutlined } from '@ant-design/icons'

export type ChatRunStep = {
  id: string
  status: 'loading' | 'success' | 'error' | 'abort'
  title: string
  description?: string
}

type Props = {
  steps: ChatRunStep[]
}

function toThoughtChainItem(step: ChatRunStep): ThoughtChainItemType {
  const isRunning = step.status === 'loading'

  return {
    blink: isRunning,
    description: step.description,
    icon: isRunning ? <BulbOutlined /> : undefined,
    key: step.id,
    status: isRunning ? undefined : step.status,
    title: step.title,
  }
}

export function ChatRunSummary({ steps }: Props) {
  if (steps.length === 0) return null

  return (
    <section aria-label="回答运行过程" className="chat-run-summary">
      <ThoughtChain
        items={steps.map(toThoughtChainItem)}
        line="dashed"
        styles={{ root: { marginBlock: 0 } }}
      />
    </section>
  )
}
