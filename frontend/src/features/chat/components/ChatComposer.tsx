import { useEffect, useState } from 'react'
import { Button, message, Tooltip } from 'antd'
import { DatabaseOutlined, GlobalOutlined } from '@ant-design/icons'
import { Sender } from '@ant-design/x'
import type { ChatAgent } from '../../../types/chat'

type Props = {
  agent: ChatAgent
  knowledgeBaseAvailable?: boolean
  value: string
  sending: boolean
  onChange: (value: string) => void
  onStop?: () => void
  onSubmit: (content: string, useKnowledgeBase: boolean) => void
}

export function ChatComposerSurface({ agent, knowledgeBaseAvailable = false, value, sending, onChange, onStop, onSubmit }: Props) {
  const [content, setContent] = useState(value)
  const [useKnowledgeBase, setUseKnowledgeBase] = useState(true)
  useEffect(() => { setContent(value) }, [value])
  useEffect(() => { setUseKnowledgeBase(true) }, [agent.id, knowledgeBaseAvailable])

  const isBuiltin = agent.kind === 'builtin'
  const canUseKnowledgeBase = isBuiltin || knowledgeBaseAvailable
  const notifyUnsupported = () => message.info('功能暂未支持')
  const submitMessage = () => {
    if (!content.trim()) return
    onSubmit(content, canUseKnowledgeBase && useKnowledgeBase)
  }

  return (
    <Sender
      autoSize={{ minRows: 1, maxRows: 4 }}
      className="prototype-chat-sender"
      footer={actionNode => (
        <div className="flex items-center justify-between gap-4 pt-1">
          <div className="flex flex-wrap items-center gap-2">
            {canUseKnowledgeBase && <Tooltip title={useKnowledgeBase ? '基于已导入的知识库资料回答' : '不使用知识库资料'}><Button icon={<DatabaseOutlined />} size="small" type={useKnowledgeBase ? 'primary' : 'default'} onClick={() => setUseKnowledgeBase(enabled => !enabled)}>知识库</Button></Tooltip>}
            {(isBuiltin || agent.allowNetworkAccess) && <Button aria-label="联网" icon={<GlobalOutlined />} size="small" onClick={notifyUnsupported} />}
          </div>
          <div className="prototype-chat-actions shrink-0">{actionNode}</div>
        </div>
      )}
      loading={sending}
      onCancel={onStop}
      placeholder="基于知识库提问，shift+enter换行"
      suffix={false}
      value={content}
      onChange={nextValue => {
        setContent(nextValue)
        onChange(nextValue)
      }}
      onSubmit={submitMessage}
    />
  )
}

export function ChatComposer(props: Props) {
  return (
    <div className="chat-composer mt-auto w-full max-w-[1080px] px-6 pb-2 pt-6 lg:ml-[14%] lg:px-0">
      <ChatComposerSurface {...props} />
      <p className="mt-2 text-center text-xs text-slate-300">内容由AI生成，仅供参考</p>
    </div>
  )
}
