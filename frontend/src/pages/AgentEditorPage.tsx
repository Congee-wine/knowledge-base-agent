import {
  ArrowLeftOutlined,
  DeleteOutlined,
  GlobalOutlined,
  PaperClipOutlined,
  PlusOutlined,
  SaveOutlined,
  UserOutlined,
} from '@ant-design/icons'
import { Button, Form, Input, Radio, Result, Spin, Tag, message } from 'antd'
import { useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { getAgentAvatar, updateAgent } from '../api/agents'
import { agentKeys } from '../features/agents/agentKeys'
import { useAgent } from '../features/agents/hooks/useAgent'
import { routes } from '../routes/paths'
import type { AgentFormValues } from '../types/agents'
import type { ChatAgent } from '../types/chat'

function toFormValues(agent: ChatAgent): AgentFormValues {
  return {
    // Compatible with agents created before these configuration fields were returned.
    // Explicit false remains respected; only a missing value defaults to enabled.
    allowConversationUpload: agent.allowConversationUpload ?? true,
    allowNetworkAccess: agent.allowNetworkAccess ?? true,
    avatarKey: agent.avatarKey,
    description: agent.description,
    interactionType: agent.interactionType,
    name: agent.name,
    presetQuestions: agent.presetQuestions,
    systemPrompt: agent.systemPrompt,
    welcomeMessage: agent.welcomeMessage,
  }
}

function toPayload(values: AgentFormValues, agent: ChatAgent): AgentFormValues {
  return {
    ...values,
    avatarKey: values.avatarKey ?? agent.avatarKey,
    description: values.description?.trim() || null,
    interactionType: values.interactionType ?? agent.interactionType,
    name: values.name?.trim() || agent.name,
    presetQuestions: values.presetQuestions
      .map((question) => question.trim())
      .filter(Boolean),
    systemPrompt: values.systemPrompt?.trim() || null,
    welcomeMessage: values.welcomeMessage?.trim() || null,
  }
}

function AgentPreview({
  agentId,
  values,
}: {
  agentId: string
  values: AgentFormValues
}) {
  const [avatarUrl, setAvatarUrl] = useState<string | null>(null)

  useEffect(() => {
    if (!values.avatarKey?.startsWith('agent-avatars/')) {
      setAvatarUrl(null)
      return
    }
    let active = true
    let objectUrl: string | null = null
    void getAgentAvatar(agentId)
      .then((blob) => {
        objectUrl = URL.createObjectURL(blob)
        if (active) setAvatarUrl(objectUrl)
        else URL.revokeObjectURL(objectUrl)
      })
      .catch(() => undefined)
    return () => {
      active = false
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
  }, [values.avatarKey])

  const welcomeMessage =
    values.welcomeMessage ||
    `你好，我是${values.name || '智能体'}，有什么可以帮助你？`
  return (
    <aside className="agent-workbench__preview">
      <div className="agent-workbench__preview-welcome">
        <div className="agent-workbench__preview-avatar">
          {avatarUrl ? <img alt="" src={avatarUrl} /> : <UserOutlined />}
        </div>
        <h2>{values.name || '未命名智能体'}</h2>
        <p>{welcomeMessage}</p>
        {values.presetQuestions.length > 0 && (
          <div className="agent-workbench__questions">
            {values.presetQuestions.map((question, index) => (
              <Tag key={`${question}-${index}`}>{question}</Tag>
            ))}
          </div>
        )}
      </div>
      <div className="agent-workbench__composer-preview">
        <span>请将遇到的问题告诉我</span>
        <div>
          {values.allowConversationUpload && (
            <Button
              className="agent-workbench__preview-entry"
              icon={<PaperClipOutlined />}
              size="small"
              type="text"
            >
              上传文件
            </Button>
          )}
          {values.allowNetworkAccess && (
            <Button
              className="agent-workbench__preview-entry"
              icon={<GlobalOutlined />}
              size="small"
              type="text"
            >
              联网搜索
            </Button>
          )}
          <Button disabled size="small" type="primary">
            发送
          </Button>
        </div>
      </div>
    </aside>
  )
}

export function AgentEditorPage() {
  const { agentId } = useParams()
  const agentQuery = useAgent(agentId)
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [form] = Form.useForm<AgentFormValues>()
  const allowConversationUpload = Form.useWatch('allowConversationUpload', form)
  const allowNetworkAccess = Form.useWatch('allowNetworkAccess', form)
  const [previewValues, setPreviewValues] = useState<AgentFormValues | null>(
    null,
  )
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (!agentQuery.data || agentQuery.data.kind !== 'personal') return
    const values = toFormValues(agentQuery.data)
    form.setFieldsValue(values)
    setPreviewValues(values)
  }, [agentQuery.data, form])

  if (agentQuery.isPending)
    return (
      <div className="grid h-full place-items-center">
        <Spin tip="正在加载智能体" />
      </div>
    )
  if (
    agentQuery.isError ||
    !agentQuery.data ||
    agentQuery.data.kind === 'builtin'
  ) {
    return (
      <Result
        status="404"
        title="智能体不存在或不可编辑"
        extra={
          <Button type="primary" onClick={() => navigate(routes.app.agents)}>
            返回智能体列表
          </Button>
        }
      />
    )
  }

  const agent = agentQuery.data
  const submit = async (values: AgentFormValues) => {
    setSaving(true)
    try {
      const savedAgent = await updateAgent(agent.id, toPayload(values, agent))
      const savedValues = toFormValues(savedAgent)
      form.setFieldsValue(savedValues)
      setPreviewValues(savedValues)
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: agentKeys.all }),
        queryClient.invalidateQueries({ queryKey: agentKeys.entry }),
        queryClient.invalidateQueries({
          queryKey: agentKeys.detail(savedAgent.id),
        }),
      ])
      message.success('智能体配置已保存，预览已刷新')
    } catch (error) {
      message.error(
        error instanceof Error ? error.message : '保存智能体失败，请重试',
      )
    } finally {
      setSaving(false)
    }
  }

  return (
    <section className="agent-workbench">
      <header className="agent-workbench__header">
        <Button
          icon={<ArrowLeftOutlined />}
          type="text"
          onClick={() => navigate(routes.app.agents)}
        >
          返回
        </Button>
        <div className="agent-workbench__title">
          <span>{agent.name.slice(0, 1).toUpperCase()}</span>
          <strong>{agent.name}</strong>
        </div>
        <Button
          icon={<SaveOutlined />}
          loading={saving}
          type="primary"
          onClick={() => form.submit()}
        >
          保存并刷新预览
        </Button>
      </header>
      <Form
        className="agent-workbench__body"
        form={form}
        initialValues={toFormValues(agent)}
        layout="vertical"
        onFinish={(values) => void submit(values)}
        onValuesChange={(_, values) => setPreviewValues(values)}
      >
        <aside className="agent-workbench__settings">
          <Form.Item label="预置问题">
            <Form.List name="presetQuestions">
              {(fields, { add, remove }) => (
                <div className="agent-workbench__preset-list">
                  {fields.map((field) => (
                    <div key={field.key}>
                      <Form.Item className="!mb-0" name={field.name}>
                        <Input maxLength={500} placeholder="请输入预置问题" />
                      </Form.Item>
                      <Button
                        aria-label="删除预置问题"
                        className="agent-workbench__preset-remove"
                        danger
                        icon={<DeleteOutlined />}
                        shape="circle"
                        type="text"
                        onClick={() => remove(field.name)}
                      />
                    </div>
                  ))}
                  <Button
                    className="agent-workbench__preset-add"
                    disabled={fields.length >= 10}
                    icon={<PlusOutlined />}
                    size="small"
                    type="text"
                    onClick={() => add()}
                  >
                    添加预置问题
                  </Button>
                  <p className="agent-workbench__field-help">
                    用户在与该智能体初始会话时，建议的预置交互问题。
                  </p>
                </div>
              )}
            </Form.List>
          </Form.Item>
          <Form.Item
            className="agent-workbench__hotwords"
            label="语音识别热词(,分隔)"
          >
            <Input disabled placeholder="请输入语音识别热词" />
            <p className="agent-workbench__field-help">
              用于识别上传音频文件的热词替换。
            </p>
          </Form.Item>
          <Form.Item
            label="开场欢迎语"
            name="welcomeMessage"
            rules={[{ max: 1000, message: '欢迎语不能超过 1000 个字符' }]}
            extra={
              <span className="agent-workbench__field-help">
                用户首次进入对话时，AI 助手主动发送的欢迎消息。
              </span>
            }
          >
            <Input.TextArea
              maxLength={1000}
              placeholder="例如：你好！我是你的智能助手，有什么可以帮助你？"
              rows={3}
              showCount
            />
          </Form.Item>
          <section className="agent-workbench__knowledge-set">
            <strong>绑定知识集</strong>
            <Button
              className="agent-workbench__preset-add"
              icon={<PlusOutlined />}
              size="small"
              type="text"
              onClick={() => message.info('知识集选择将在知识库功能完成后开放')}
            >
              请选择知识集
            </Button>
            <p className="agent-workbench__field-help">
              选择此智能体所引用的专属资料，用于增强回复的专业性和准确性。
            </p>
          </section>
          <Form.Item
            label="显示上传文件入口"
            name="allowConversationUpload"
            extra={
              <span className="agent-workbench__field-help">
                选择不需要上传文件入口后，用户在对话中无法上传文件；选择需要上传文件入口，则用户可以在对话中上传文件。
              </span>
            }
          >
            <Radio.Group>
              <Radio value={false}>不需要</Radio>
              <Radio value={true}>需要</Radio>
            </Radio.Group>
          </Form.Item>
          <Form.Item
            label="显示联网搜索入口"
            name="allowNetworkAccess"
            extra={
              <span className="agent-workbench__field-help">
                选择不需要显示联网搜索入口后，用户在对话中无法使用联网搜索功能；选择需要显示联网搜索入口，则用户可以在对话中自主选择是否使用联网搜索功能。
              </span>
            }
          >
            <Radio.Group>
              <Radio value={false}>不需要</Radio>
              <Radio value={true}>需要</Radio>
            </Radio.Group>
          </Form.Item>
          <Form.Item
            label="智能体描述"
            name="description"
            rules={[{ max: 200, message: '描述不能超过 200 个字符' }]}
          >
            <Input.TextArea
              maxLength={200}
              placeholder="请输入智能体描述"
              rows={4}
              showCount
            />
          </Form.Item>
        </aside>
        <main className="agent-workbench__prompt">
          <div className="agent-workbench__prompt-title">
            <strong>编辑提示词</strong>
            <span>系统提示词会在每次对话时作为行为边界传给模型。</span>
          </div>
          <Form.Item
            name="systemPrompt"
            rules={[{ max: 8000, message: '系统提示词不能超过 8000 个字符' }]}
          >
            <Input.TextArea
              className="agent-workbench__prompt-input"
              maxLength={8000}
              placeholder="请编写提示词，例如：你是一名专业的销售助手……"
              showCount
            />
          </Form.Item>
        </main>
        {previewValues && (
          <AgentPreview
            agentId={agent.id}
            values={{
              ...previewValues,
              allowConversationUpload:
                allowConversationUpload ??
                previewValues.allowConversationUpload,
              allowNetworkAccess:
                allowNetworkAccess ?? previewValues.allowNetworkAccess,
            }}
          />
        )}
      </Form>
    </section>
  )
}
