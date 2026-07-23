import { useEffect, useState } from 'react'
import { Button, message } from 'antd'
import { GlobalOutlined, PaperClipOutlined, RobotOutlined } from '@ant-design/icons'
import { Sender } from '@ant-design/x'
import type { ChatAgent } from '../../../types/chat'

type Props = { agent: ChatAgent; initialValue: string }

export function ChatComposer({ agent, initialValue }: Props) {
  const [content, setContent] = useState(initialValue)
  const [useKnowledgeBase, setUseKnowledgeBase] = useState(true)
  useEffect(() => { if (initialValue) setContent(initialValue) }, [initialValue])

  const isBuiltin = agent.kind === 'builtin'
  const notifyUnsupported = () => message.info('功能暂未支持')
  const submitPreview = () => {
    if (!content.trim()) return
    message.info('消息发送将在下一步接口联调时接入')
  }

  return (
    <div className="mt-auto w-full max-w-[810px] px-8 pb-2 pt-6 lg:ml-[18%] lg:px-0">
      <Sender
        className="prototype-chat-sender"
        value={content}
        placeholder="基于知识库提问，shift+enter换行"
        autoSize={{ minRows: 1, maxRows: 4 }}
        suffix={false}
        allowSpeech
        onChange={setContent}
        onSubmit={submitPreview}
        footer={actionNode => (
          <div className="flex items-center justify-between gap-4 pt-1">
            <div className="flex flex-wrap items-center gap-2">
              {isBuiltin && <Button size="small" type={useKnowledgeBase ? 'primary' : 'default'} onClick={() => setUseKnowledgeBase(value => !value)}>全部资料</Button>}
              <Button size="small" icon={<RobotOutlined />} onClick={notifyUnsupported}>Agent</Button>
              {isBuiltin && <Button size="small" aria-label="联网" icon={<GlobalOutlined />} onClick={notifyUnsupported} />}
              {(isBuiltin || agent.allowConversationUpload) && <Button size="small" aria-label="上传文件" icon={<PaperClipOutlined />} onClick={notifyUnsupported} />}
            </div>
            <div className="prototype-chat-actions shrink-0">{actionNode}</div>
          </div>
        )}
      />
      <p className="mt-2 text-center text-xs text-slate-300">内容由AI生成，仅供参考</p>
    </div>
  )
}
