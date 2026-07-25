import { EditOutlined, EyeOutlined, QuestionCircleOutlined } from '@ant-design/icons'
import { Modal } from 'antd'
import MDEditor, {
  bold,
  codeBlock,
  divider,
  group,
  heading1,
  heading2,
  heading3,
  heading4,
  heading5,
  heading6,
  italic,
  orderedListCommand,
  quote,
  table,
  unorderedListCommand,
  type ICommand,
} from '@uiw/react-md-editor/nohighlight'
import { useMemo, useState } from 'react'
import '@uiw/react-md-editor/markdown-editor.css'

type SystemPromptEditorProps = {
  onChange?: (value: string) => void
  value?: string | null
}

const markdownHelpItems = [
  ['加粗', '**文本**'],
  ['斜体', '*文本*'],
  ['标题', '# 一级标题'],
  ['引用', '> 引用内容'],
  ['列表', '- 无序项 或 1. 有序项'],
  ['代码', '`行内代码` 或 ```代码块```'],
  ['表格', '| 表头 | 表头 |'],
]

function replaceLineHeading(
  state: Parameters<NonNullable<ICommand['execute']>>[0],
  api: Parameters<NonNullable<ICommand['execute']>>[1],
  level: number,
) {
  const lineStart = state.text.lastIndexOf('\n', state.selection.start - 1) + 1
  const nextLine = state.text.indexOf('\n', state.selection.end)
  const lineEnd = nextLine === -1 ? state.text.length : nextLine
  const content = state.text.slice(lineStart, lineEnd).replace(/^#{1,6}\s+/, '')
  const prefix = `${'#'.repeat(level)} `

  api.setSelectionRange({ start: lineStart, end: lineEnd })
  api.replaceSelection(`${prefix}${content}`)
  api.setSelectionRange({ start: lineStart, end: lineStart + prefix.length + content.length })
}

function createHeadingCommand(command: ICommand, level: number): ICommand {
  return {
    ...command,
    execute: (state, api) => replaceLineHeading(state, api, level),
  }
}

const editorCommands = [
  bold,
  italic,
  group([
    createHeadingCommand(heading1, 1),
    createHeadingCommand(heading2, 2),
    createHeadingCommand(heading3, 3),
    createHeadingCommand(heading4, 4),
    createHeadingCommand(heading5, 5),
    createHeadingCommand(heading6, 6),
  ], {
    name: 'heading',
    groupName: 'heading',
    buttonProps: {
      'aria-label': '插入标题',
      title: '插入标题',
    },
  }),
  divider,
  quote,
  unorderedListCommand,
  orderedListCommand,
  divider,
  codeBlock,
  table,
]

export function SystemPromptEditor({ onChange, value }: SystemPromptEditorProps) {
  const [helpOpen, setHelpOpen] = useState(false)
  const [isPreviewOpen, setIsPreviewOpen] = useState(false)
  const extraCommands = useMemo<ICommand[]>(
    () => [
      divider,
      {
        name: 'markdown-help',
        keyCommand: 'markdown-help',
        icon: <QuestionCircleOutlined />,
        buttonProps: { 'aria-label': 'Markdown 语法帮助', title: 'Markdown 语法帮助' },
        execute: () => setHelpOpen(true),
      },
      {
        name: 'toggle-preview',
        keyCommand: 'toggle-preview',
        icon: isPreviewOpen ? <EditOutlined /> : <EyeOutlined />,
        buttonProps: {
          'aria-label': isPreviewOpen ? '返回编辑' : '预览 Markdown',
          title: isPreviewOpen ? '返回编辑' : '预览 Markdown',
        },
        execute: () => setIsPreviewOpen((current) => !current),
      },
    ],
    [isPreviewOpen],
  )

  return (
    <div className="system-prompt-editor-shell">
      <MDEditor
        className="system-prompt-editor"
        commands={editorCommands}
        extraCommands={extraCommands}
        height="100%"
        highlightEnable={false}
        preview={isPreviewOpen ? 'preview' : 'edit'}
        textareaProps={{ maxLength: 8000, placeholder: '请编辑提示词' }}
        value={value ?? ''}
        visibleDragbar={false}
        onChange={(nextValue) => onChange?.(nextValue ?? '')}
      />
      <Modal footer={null} open={helpOpen} title="Markdown 语法帮助" onCancel={() => setHelpOpen(false)}>
        <p>可使用工具栏插入语法，也可以直接输入以下 Markdown：</p>
        <ul className="system-prompt-editor__help-list">
          {markdownHelpItems.map(([name, syntax]) => (
            <li key={name}>
              <strong>{name}</strong>
              <code>{syntax}</code>
            </li>
          ))}
        </ul>
      </Modal>
    </div>
  )
}
