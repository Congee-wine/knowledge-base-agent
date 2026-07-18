import { Button, Result } from 'antd'
import { useNavigate } from 'react-router-dom'
import { routes } from '../routes/paths'

export function NotFoundPage() {
  const navigate = useNavigate()

  return <Result status="404" title="页面不存在" subTitle="你访问的地址不存在或已被移动。" extra={<Button type="primary" onClick={() => navigate(routes.app.chat)}>返回 AI 管家</Button>} />
}
