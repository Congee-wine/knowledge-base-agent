import { useState } from 'react'
import { ChatComposerSurface } from '../../chat/components/ChatComposer'
import { ChatMessageList } from '../../chat/components/ChatMessageList'
import { useStreamingChat } from '../../chat/hooks/useStreamingChat'
import type { ChatAgent } from '../../../types/chat'
import { PersonalAgentWelcome } from './PersonalAgentWelcome'

type AgentEditorPreviewProps = { agent: ChatAgent }

export function AgentEditorPreview({ agent }: AgentEditorPreviewProps) {
  const [draftMessage, setDraftMessage] = useState('')
  const stream = useStreamingChat()

  return (
    <aside className="agent-workbench__preview">
      {stream.messages.length === 0
        ? <PersonalAgentWelcome agent={agent} className="agent-workbench__preview-welcome" onPromptClick={setDraftMessage} />
        : <ChatMessageList className="w-full px-4 pt-4" messages={stream.messages} pendingAssistant={false} statusText={stream.statusText} />}
      <div className="agent-workbench__preview-composer">
        <ChatComposerSurface
          agent={agent}
          sending={stream.sending}
          value={draftMessage}
          onChange={setDraftMessage}
          onSubmit={content => {
            setDraftMessage('')
            void stream.send({ agent, content, conversationId: null, preview: true })
          }}
        />
      </div>
    </aside>
  )
}
