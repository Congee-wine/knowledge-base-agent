import { Prompts, Welcome } from '@ant-design/x'
import type { ChatAgent } from '../../../types/chat'

type Props = { agent: ChatAgent; onPromptClick: (prompt: string) => void }

const builtinPrompts = [
  '产品品类多，生产资料一大堆，如何利用软小筑快速找到生产信息？',
  '怎么维护我的知识库才能在软小筑轻松地写一份合同？',
  '如何搭建我的智能客服应用？',
  '我创建的文档，其他同事可以看到吗？',
  '怎么才能快速地把我现有的资料一次性放到知识库中？',
  '支持在线编辑吗？',
  '文件一个个传太麻烦！软小筑支持上传文件夹吗？',
]

export function ChatWelcome({ agent, onPromptClick }: Props) {
  const prompts = agent.presetQuestions.length ? agent.presetQuestions : builtinPrompts

  return (
    <div className="w-full max-w-[810px] px-8 pt-1 lg:ml-[18%] lg:px-0">
      <Welcome
        className="ai-manager-welcome"
        description={agent.welcomeMessage ?? '我是 AI 管家，可以协助你整理信息、解答问题和完成文本工作。'}
        title="你好，欢迎使用 AI 管家"
        variant="borderless"
      />
      <Prompts
        className="ai-manager-prompts"
        items={prompts.map((prompt, index) => ({
          icon: <span className="text-base">{index < 4 ? '🔥' : '👍'}</span>,
          key: String(index),
          label: prompt,
        }))}
        title="🤔 你可能还想问："
        vertical
        styles={{
          item: { borderRadius: 12, padding: '8px 12px' },
          itemContent: { fontSize: 14, lineHeight: '20px' },
          list: { gap: 8 },
          title: { fontSize: 16, marginBottom: 10 },
        }}
        onItemClick={info => onPromptClick(String(info.data.label))}
      />
    </div>
  )
}
