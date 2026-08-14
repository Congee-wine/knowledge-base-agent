import { useEffect, useState } from 'react'
import { Button, message } from 'antd'
import { DatabaseOutlined, GlobalOutlined } from '@ant-design/icons'
import { Sender } from '@ant-design/x'
import type { ChatAgent } from '../../../types/chat'

type Props = {
  agent: ChatAgent
  value: string
  sending: boolean
  onChange: (value: string) => void
  onStop?: () => void
  onSubmit: (content: string, useKnowledgeBase: boolean) => void
}

export function ChatComposerSurface({ agent, value, sending, onChange, onStop, onSubmit }: Props) {
  const [content, setContent] = useState(value)
  const [useKnowledgeBase, setUseKnowledgeBase] = useState(true)
  useEffect(() => { setContent(value) }, [value])

  const isBuiltin = agent.kind === 'builtin'
  const notifyUnsupported = () => message.info('功能暂未支持')
  const submitMessage = () => {
    if (!content.trim()) return
    onSubmit(content, isBuiltin && useKnowledgeBase)
  }

  return (
    <Sender
      autoSize={{ minRows: 1, maxRows: 4 }}
      className="prototype-chat-sender"
      footer={actionNode => (
        <div className="flex items-center justify-between gap-4 pt-1">
          <div className="flex flex-wrap items-center gap-2">
            {isBuiltin && <Button icon={<DatabaseOutlined />} size="small" type={useKnowledgeBase ? 'primary' : 'default'} onClick={() => setUseKnowledgeBase(enabled => !enabled)}>全部资料</Button>}
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
