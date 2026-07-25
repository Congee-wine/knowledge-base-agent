import type { ChatAgent } from '../../../types/chat'
import { AgentAvatar } from './AgentAvatar'

type PersonalAgentWelcomeProps = {
  agent: ChatAgent
  className?: string
  onPromptClick?: (prompt: string) => void
}

export function PersonalAgentWelcome({
  agent,
  className,
  onPromptClick,
}: PersonalAgentWelcomeProps) {
  return (
    <section className={`personal-agent-welcome ${className ?? ''}`.trim()}>
      <AgentAvatar agent={agent} className="personal-agent-welcome__avatar" imageClassName="personal-agent-welcome__avatar-image" />
      <h2>{agent.name}</h2>
      <p>{agent.welcomeMessage || `你好，我是${agent.name}，有什么可以帮助你？`}</p>
      {agent.presetQuestions.length > 0 && (
        <div className="personal-agent-welcome__questions">
          {agent.presetQuestions.map((question, index) => (
            <button key={`${question}-${index}`} type="button" onClick={() => onPromptClick?.(question)}>
              {question}
            </button>
          ))}
        </div>
      )}
    </section>
  )
}
