import { CheckOutlined, PlusOutlined } from '@ant-design/icons'
import { Button, Form, Input, Modal, Radio, Upload, message } from 'antd'
import type { UploadFile, UploadProps } from 'antd'
import { useEffect, useState } from 'react'
import { bootstrapAgent } from '../../../api/agents'

type Props = {
  onCreated: (agentId: string) => void
  onOpenChange: (open: boolean) => void
  open: boolean
}

type FormValues = {
  description?: string
  name: string
}

const acceptedTypes = ['image/png', 'image/jpeg', 'image/gif', 'image/webp']
const maxAvatarSize = 5 * 1024 * 1024

export function CreateAgentModal({ onCreated, onOpenChange, open }: Props) {
  const [form] = Form.useForm<FormValues>()
  const [avatar, setAvatar] = useState<File | null>(null)
  const [avatarList, setAvatarList] = useState<UploadFile[]>([])
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  const reset = () => {
    form.resetFields()
    setAvatar(null)
    setAvatarList([])
  }
  useEffect(() => {
    if (!avatar) {
      setPreviewUrl(null)
      return
    }
    const nextPreviewUrl = URL.createObjectURL(avatar)
    setPreviewUrl(nextPreviewUrl)
    return () => URL.revokeObjectURL(nextPreviewUrl)
  }, [avatar])
  const close = () => {
    if (submitting) return
    reset()
    onOpenChange(false)
  }
  const beforeUpload: UploadProps['beforeUpload'] = file => {
    if (!acceptedTypes.includes(file.type)) {
      message.error('头像仅支持 PNG、JPG、JPEG、GIF 或 WEBP 格式')
      return Upload.LIST_IGNORE
    }
    if (file.size > maxAvatarSize) {
      message.error('头像文件不能超过 5MB')
      return Upload.LIST_IGNORE
    }
    setAvatar(file)
    setAvatarList([{ uid: file.uid, name: file.name, status: 'done', originFileObj: file }])
    return false
  }
  const submit = async (values: FormValues) => {
    setSubmitting(true)
    try {
      const agent = await bootstrapAgent({ avatar, description: values.description?.trim() ?? '', name: values.name.trim() })
      message.success('基础信息已创建，请继续完成智能体配置')
      reset()
      onOpenChange(false)
      onCreated(agent.id)
    } catch (error) {
      message.error(error instanceof Error ? error.message : '创建智能体失败，请稍后重试')
    } finally {
      setSubmitting(false)
    }
  }

  return <Modal destroyOnHidden footer={null} maskClosable={!submitting} open={open} title="创建智能体" width={840} onCancel={close}>
    <Form className="create-agent-modal" form={form} layout="vertical" onFinish={values => void submit(values)} onFinishFailed={() => message.warning('请先填写智能体名称') }>
      <Form.Item label="头像">
        <Upload accept="image/png,image/jpeg,image/gif,image/webp" beforeUpload={beforeUpload} fileList={avatarList} maxCount={1} showUploadList={false} onRemove={() => { setAvatar(null); setAvatarList([]) }}>
          <button className="create-agent-modal__upload" type="button" aria-label="上传头像" style={{ position: 'relative' }}>
            {previewUrl ? <><img alt="已选择的头像预览" src={previewUrl} /><span className="create-agent-modal__selected" style={{ position: 'absolute', right: 0, top: 0, zIndex: 1 }}><CheckOutlined /></span></> : <PlusOutlined />}
          </button>
        </Upload>
        <p className="create-agent-modal__hint">请上传大小不超过 <strong>5MB</strong>、格式为 <strong>png/jpg/jpeg/gif/webp</strong> 的文件</p>
      </Form.Item>
      <Form.Item label="名称" name="name" rules={[{ required: true, whitespace: true, message: '请输入智能体名称' }, { max: 50, message: '名称不能超过 50 个字符' }]}>
        <Input maxLength={50} placeholder="请输入智能体名称" showCount />
      </Form.Item>
      <Form.Item label="交互类型">
        <Radio.Group defaultValue="text">
          <Radio value="text">文本交互</Radio>
          <Radio disabled value="voice">语音交互（暂未开放）</Radio>
          <Radio disabled value="digital-human">数字人交互（暂未开放）</Radio>
        </Radio.Group>
      </Form.Item>
      <Form.Item label="描述" name="description" rules={[{ max: 200, message: '描述不能超过 200 个字符' }]}>
        <Input.TextArea maxLength={200} placeholder="请输入智能体描述（选填）" rows={3} showCount />
      </Form.Item>
      <div className="create-agent-modal__actions"><Button onClick={close}>取消</Button><Button htmlType="button" loading={submitting} type="primary" onClick={() => form.submit()}>确定</Button></div>
    </Form>
  </Modal>
}
