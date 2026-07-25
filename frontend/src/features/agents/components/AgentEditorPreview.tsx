import { message } from 'antd'
import { useState } from 'react'
import { ChatComposerSurface } from '../../chat/components/ChatComposer'
import type { ChatAgent } from '../../../types/chat'
import { PersonalAgentWelcome } from './PersonalAgentWelcome'

type AgentEditorPreviewProps = {
  agent: ChatAgent
}

export function AgentEditorPreview({ agent }: AgentEditorPreviewProps) {
  const [draftMessage, setDraftMessage] = useState('')

  return (
    <aside className="agent-workbench__preview">
      <PersonalAgentWelcome agent={agent} className="agent-workbench__preview-welcome" onPromptClick={setDraftMessage} />
      <div className="agent-workbench__preview-composer">
        <ChatComposerSurface
          agent={agent}
          sending={false}
          value={draftMessage}
          onChange={setDraftMessage}
          onSubmit={() => {
            setDraftMessage('')
            message.info('预览消息不会创建真实会话，请保存后在聊天页使用智能体。')
          }}
        />
      </div>
    </aside>
  )
}
