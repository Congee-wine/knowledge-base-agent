import { ArrowLeftOutlined, MinusCircleOutlined, PlusOutlined } from '@ant-design/icons'
import { Button, Card, Form, Input, Result, Spin, Switch, message } from 'antd'
import { useQueryClient } from '@tanstack/react-query'
import { useNavigate, useParams } from 'react-router-dom'
import { createAgent, updateAgent } from '../api/agents'
import { agentKeys } from '../features/agents/agentKeys'
import { useAgent } from '../features/agents/hooks/useAgent'
import { routes } from '../routes/paths'
import type { AgentFormValues } from '../types/agents'

type FormState = Omit<AgentFormValues, 'description' | 'avatarKey' | 'systemPrompt' | 'welcomeMessage'> & {
  description?: string
  systemPrompt?: string
  welcomeMessage?: string
}

const initialValues: FormState = {
  allowConversationUpload: false,
  allowNetworkAccess: false,
  interactionType: 'text',
  name: '',
  presetQuestions: [],
}

function toPayload(values: FormState): AgentFormValues {
  return {
    ...values,
    avatarKey: null,
    description: values.description?.trim() || null,
    name: values.name.trim(),
    presetQuestions: values.presetQuestions.map(question => question.trim()).filter(Boolean),
    systemPrompt: values.systemPrompt?.trim() || null,
    welcomeMessage: values.welcomeMessage?.trim() || null,
  }
}

export function AgentEditorPage() {
  const { agentId } = useParams()
  const isCreating = !agentId
  const agentQuery = useAgent(agentId)
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [form] = Form.useForm<FormState>()

  if (!isCreating && agentQuery.isPending) return <div className="grid h-full place-items-center"><Spin tip="正在加载智能体" /></div>
  if (!isCreating && (agentQuery.isError || !agentQuery.data || agentQuery.data.kind === 'builtin')) {
    return <Result status="404" title="智能体不存在或不可编辑" extra={<Button type="primary" onClick={() => navigate(routes.app.agents)}>返回智能体列表</Button>} />
  }
  const agent = agentQuery.data
  const formValues = agent ? { ...agent, description: agent.description ?? undefined, systemPrompt: agent.systemPrompt ?? undefined, welcomeMessage: agent.welcomeMessage ?? undefined } : initialValues
  const submit = async (values: FormState) => {
    try {
      const savedAgent = isCreating ? await createAgent(toPayload(values)) : await updateAgent(agentId!, toPayload(values))
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: agentKeys.all }),
        queryClient.invalidateQueries({ queryKey: agentKeys.entry }),
        queryClient.invalidateQueries({ queryKey: agentKeys.detail(savedAgent.id) }),
      ])
      message.success(isCreating ? '智能体已创建' : '智能体已保存')
      navigate(routes.app.agents)
    } catch {
      message.error(isCreating ? '创建智能体失败，请重试' : '保存智能体失败，请重试')
    }
  }

  return <section className="h-full overflow-y-auto bg-slate-50 p-6 lg:p-8">
    <div className="mx-auto max-w-3xl">
      <Button className="mb-5 !px-0" icon={<ArrowLeftOutlined />} type="link" onClick={() => navigate(routes.app.agents)}>返回智能体列表</Button>
      <Card title={isCreating ? '新建智能体' : `编辑智能体：${agent!.name}`}>
        <Form form={form} initialValues={formValues} layout="vertical" onFinish={values => void submit(values)}>
          <Card className="mb-5" size="small" title="基础信息">
            <Form.Item label="名称" name="name" rules={[{ required: true, message: '请输入智能体名称' }, { max: 80, message: '名称不能超过 80 个字符' }]}><Input maxLength={80} placeholder="例如：销售助手" /></Form.Item>
            <Form.Item label="简介" name="description" rules={[{ max: 500, message: '简介不能超过 500 个字符' }]}><Input.TextArea maxLength={500} placeholder="说明智能体擅长处理的问题" rows={3} /></Form.Item>
          </Card>
          <Card className="mb-5" size="small" title="对话配置">
            <Form.Item label="系统提示词" name="systemPrompt" rules={[{ max: 8000, message: '系统提示词不能超过 8000 个字符' }]}><Input.TextArea maxLength={8000} rows={5} /></Form.Item>
            <Form.Item label="欢迎语" name="welcomeMessage" rules={[{ max: 1000, message: '欢迎语不能超过 1000 个字符' }]}><Input.TextArea maxLength={1000} rows={2} /></Form.Item>
            <Form.List name="presetQuestions">{(fields, { add, remove }) => <Form.Item label="预设问题"><div className="space-y-2">{fields.map(field => <div key={field.key} className="flex gap-2"><Form.Item className="!mb-0 flex-1" name={field.name}><Input maxLength={500} placeholder="用户可一键发送的问题" /></Form.Item><Button aria-label="删除预设问题" icon={<MinusCircleOutlined />} type="text" onClick={() => remove(field.name)} /></div>)}<Button disabled={fields.length >= 10} icon={<PlusOutlined />} size="small" type="dashed" onClick={() => add()}>添加预设问题</Button></div></Form.Item>}</Form.List>
          </Card>
          <Card className="mb-6" size="small" title="入口显示"><p className="mb-4 text-sm text-slate-400">按钮仅控制聊天页面是否展示；上传和联网能力将在后续阶段接入。</p><Form.Item label="显示上传按钮" name="allowConversationUpload" valuePropName="checked"><Switch /></Form.Item><Form.Item className="!mb-0" label="显示联网按钮" name="allowNetworkAccess" valuePropName="checked"><Switch /></Form.Item></Card>
          <div className="flex justify-end gap-3"><Button onClick={() => navigate(routes.app.agents)}>取消</Button><Button htmlType="submit" type="primary">保存</Button></div>
        </Form>
      </Card>
    </div>
  </section>
}
