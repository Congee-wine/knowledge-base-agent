import { Prompts, Welcome } from '@ant-design/x'
import { PersonalAgentWelcome } from '../../agents/components/PersonalAgentWelcome'
import type { ChatAgent } from '../../../types/chat'

type Props = { agent: ChatAgent; onPromptClick: (prompt: string) => void }

export function ChatWelcome({ agent, onPromptClick }: Props) {
  if (agent.kind === 'personal') {
    return (
      <PersonalAgentWelcome
        agent={agent}
        className="chat-personal-agent-welcome"
        onPromptClick={onPromptClick}
      />
    )
  }

  return (
    <div className="w-full max-w-[810px] px-8 pt-1 lg:ml-[18%] lg:px-0">
      <Welcome
        className="ai-manager-welcome"
        description={
          agent.welcomeMessage ??
          '我是 AI 管家，可以协助你整理信息、解答问题和完成文本工作。'
        }
        title="你好，欢迎使用 AI 管家"
        variant="borderless"
      />
      {agent.presetQuestions.length > 0 && (
        <Prompts
          className="ai-manager-prompts"
          items={agent.presetQuestions.map((prompt, index) => ({
            icon: <span className="text-base">{index < 4 ? '🔥' : '🌟'}</span>,
            key: String(index),
            label: prompt,
          }))}
          title="💡 你可能还想问："
          vertical
          styles={{
            item: { borderRadius: 12, padding: '8px 12px' },
            itemContent: { fontSize: 14, lineHeight: '20px' },
            list: { gap: 8 },
            title: { fontSize: 16, marginBottom: 10 },
          }}
          onItemClick={(info) => onPromptClick(String(info.data.label))}
        />
      )}
    </div>
  )
}
