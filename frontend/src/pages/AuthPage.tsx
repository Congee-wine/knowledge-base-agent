import { useEffect, useState } from 'react'
import type { FormProps } from 'antd'
import { Alert, Button, Card, Checkbox, Form, Input, Typography } from 'antd'
import { EyeInvisibleOutlined, EyeTwoTone, LockOutlined, MailOutlined, RobotOutlined } from '@ant-design/icons'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { login, register } from '../api/auth'
import { saveTokens } from '../lib/auth'
import { routes } from '../routes/paths'
import type { User } from '../types/auth'

type AuthMode = 'login' | 'register'
type AuthFormValues = { email: string; password: string; confirmPassword?: string; acceptedTerms?: boolean }
type Props = { mode: AuthMode; onAuthenticated: (user: User) => void }
type AuthLocationState = { notice?: string }

export function AuthPage({ mode, onAuthenticated }: Props) {
  const location = useLocation()
  const navigate = useNavigate()
  const [form] = Form.useForm<AuthFormValues>()
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const isRegister = mode === 'register'

  useEffect(() => {
    form.resetFields()
    setError('')
    setNotice((location.state as AuthLocationState | null)?.notice ?? '')
  }, [form, location.key, location.state, mode])
  const submitAuth: FormProps<AuthFormValues>['onFinish'] = async values => {
    setError(''); setNotice(''); setSubmitting(true)
    try {
      const credentials = { email: values.email.trim().toLowerCase(), password: values.password }
      if (isRegister) { await register({ ...credentials, acceptedTerms: Boolean(values.acceptedTerms) }); navigate(routes.login, { replace: true, state: { notice: '注册成功，请使用新账号登录' } }); return }
      const data = await login(credentials)
      saveTokens(data); onAuthenticated(data.user)
    } catch (requestError) { setError(requestError instanceof Error ? requestError.message : '网络异常，请确认后端服务已启动') } finally { setSubmitting(false) }
  }
  return <main className="grid h-screen grid-cols-1 overflow-hidden bg-white lg:grid-cols-2"><aside className="hidden h-screen w-full overflow-hidden lg:block"><img className="h-full w-full object-cover object-top" src="/auth-hero.png" alt="软小筑 AI 管家" /></aside><section className="flex h-screen min-h-0 w-full items-center justify-center overflow-y-auto bg-slate-50 px-4 py-4 sm:px-8"><Card className="w-full max-w-[500px] border border-slate-200 shadow-xl shadow-slate-200/45"><div className="px-1 py-1 sm:px-3"><div className="mb-5 text-center"><RobotOutlined className="text-3xl text-indigo-500" /><Typography.Title level={2} className="!mb-1 !mt-2 !text-3xl">{isRegister ? '创建账号' : '欢迎回来'}</Typography.Title><Typography.Text type="secondary">{isRegister ? '注册后即可使用 AI 管家与知识库' : '登录后继续你的智能工作与知识体验'}</Typography.Text></div>{error && <Alert className="!mb-3" type="error" showIcon message={error} />}{notice && <Alert className="!mb-3" type="success" showIcon message={notice} />}<Form form={form} layout="vertical" requiredMark={false} size="middle" onFinish={submitAuth}><Form.Item className="!mb-3" label="邮箱" name="email" rules={[{ required: true, message: '请输入邮箱地址' }, { type: 'email', message: '请输入有效的邮箱地址' }]}><Input prefix={<MailOutlined className="text-slate-400" />} placeholder="请输入邮箱地址" autoComplete="email" /></Form.Item><Form.Item className="!mb-3" label="密码" name="password" extra={isRegister ? '至少 8 位密码' : undefined} rules={[{ required: true, message: '请输入密码' }, { min: 8, message: '密码至少需要 8 位' }]}><Input.Password prefix={<LockOutlined className="text-slate-400" />} placeholder="请输入密码" autoComplete={isRegister ? 'new-password' : 'current-password'} iconRender={visible => visible ? <EyeTwoTone /> : <EyeInvisibleOutlined />} /></Form.Item>{isRegister && <Form.Item className="!mb-3" label="确认密码" name="confirmPassword" dependencies={['password']} rules={[{ required: true, message: '请再次输入密码' }, ({ getFieldValue }) => ({ validator(_, value) { return !value || getFieldValue('password') === value ? Promise.resolve() : Promise.reject(new Error('两次输入的密码不一致')) } })]}><Input.Password prefix={<LockOutlined className="text-slate-400" />} placeholder="请再次输入密码" autoComplete="new-password" /></Form.Item>}{isRegister && <Form.Item className="!mb-4" name="acceptedTerms" valuePropName="checked" rules={[{ validator: (_, value) => value ? Promise.resolve() : Promise.reject(new Error('请先同意服务条款和隐私政策')) }]}><Checkbox className="text-xs text-slate-500">我已阅读并同意 <a href="#terms" className="text-indigo-500">《服务条款》</a> 与 <a href="#privacy" className="text-indigo-500">《隐私政策》</a></Checkbox></Form.Item>}<Button className="!h-11 !text-base !font-semibold" type="primary" htmlType="submit" block loading={submitting}>{isRegister ? '注册' : '登录'}</Button></Form><div className="mt-5 border-t border-slate-100 pt-4 text-center text-sm text-slate-500">{isRegister ? '已有账号？' : '还没有账号？'} <Link className="text-indigo-500 hover:text-indigo-400" to={isRegister ? routes.login : routes.register}>{isRegister ? '立即登录' : '立即注册'}</Link></div></div></Card></section></main>
}
