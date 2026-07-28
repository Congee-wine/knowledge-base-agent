import { ArrowLeftOutlined, FileTextOutlined } from '@ant-design/icons'
import { useQuery } from '@tanstack/react-query'
import { Alert, Button, Result, Spin } from 'antd'
import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { ApiError } from '../api/http'
import { getDocumentPreview } from '../api/knowledge'
import { routes } from '../routes/paths'

function getPreviewError(error: unknown) {
  if (!(error instanceof ApiError)) return { title: '预览加载失败', detail: '请检查网络连接后重试。' }
  if (error.status === 409) return { title: '文件仍在处理中', detail: '处理完成后即可预览。' }
  if (error.status === 422) return { title: '文件内容为空', detail: '该文件没有可预览的文本内容。' }
  if (error.status === 404) return { title: '文件不存在或无权访问', detail: '请返回资料树后确认文件状态。' }
  return { title: '预览暂时不可用', detail: error.message }
}

export function DocumentPreviewPage() {
  const navigate = useNavigate()
  const { fileId } = useParams<{ fileId: string }>()
  const previewQuery = useQuery({
    queryKey: ['knowledge', 'preview', fileId],
    queryFn: () => getDocumentPreview(fileId!),
    enabled: Boolean(fileId),
    retry: false,
  })
  const [pdfUrl, setPdfUrl] = useState<string | null>(null)

  useEffect(() => {
    if (previewQuery.data?.kind !== 'pdf') return
    const url = URL.createObjectURL(previewQuery.data.blob)
    setPdfUrl(url)
    return () => {
      URL.revokeObjectURL(url)
      setPdfUrl(null)
    }
  }, [previewQuery.data])

  if (!fileId) return <Result status="404" title="文件不存在" extra={<Button onClick={() => navigate(routes.app.knowledgeBases)}>返回资料树</Button>} />
  if (previewQuery.isPending) return <div className="document-preview__loading"><Spin tip="正在加载预览" /></div>
  if (previewQuery.isError) {
    const error = getPreviewError(previewQuery.error)
    return <Result status="warning" title={error.title} subTitle={error.detail} extra={<><Button type="primary" onClick={() => void previewQuery.refetch()}>重试</Button><Button onClick={() => navigate(routes.app.knowledgeBases)}>返回资料树</Button></>} />
  }

  const preview = previewQuery.data
  return <section className="document-preview">
    <header className="document-preview__header">
      <Button icon={<ArrowLeftOutlined />} type="text" onClick={() => navigate(routes.app.knowledgeBases)}>返回资料树</Button>
      <strong><FileTextOutlined /> {preview.name}</strong>
    </header>
    <main className="document-preview__content">
      {preview.kind === 'pdf' && (pdfUrl ? <iframe className="document-preview__pdf" src={pdfUrl} title={preview.name} /> : <Spin tip="正在准备 PDF" />)}
      {preview.kind === 'text' && <><Alert className="document-preview__format" message={preview.isMarkdown ? 'Markdown 文本预览' : 'TXT 文本预览'} type="info" showIcon /><pre className="document-preview__text">{preview.content}</pre></>}
      {preview.kind === 'html' && <iframe className="document-preview__docx" sandbox="" srcDoc={`<!doctype html><html><head><style>body{font-family:Arial,'Microsoft YaHei',sans-serif;color:#26364a;line-height:1.75;padding:28px;max-width:920px;margin:auto}table{border-collapse:collapse;width:100%;margin:16px 0}td{border:1px solid #d9e1eb;padding:8px;vertical-align:top}h1,h2,h3,h4,h5,h6{color:#1f3858}pre{white-space:pre-wrap}</style></head><body>${preview.html}</body></html>`} title={preview.name} />}
    </main>
  </section>
}
