# 前端设计

新增受 `RequireAuth` 保护的 `/app/knowledge-bases/files/:fileId/preview` 路由。

- `KnowledgeBasePage`：双击 ready 文件或右键“预览”导航到预览页；文件夹双击保持进入目录。
- `DocumentPreviewPage`：负责 React Query 加载、返回资料树和全局错误状态。
- 类型组件：TXT 以文本节点渲染；Markdown 使用现有安全 Markdown 预览组件渲染，原始 HTML 不执行；PDF 使用认证获取的 Blob URL；DOCX 使用后端生成的 HTML。
- 页面须展示加载、处理中、空内容、无权限/不存在与转换失败状态。PDF Blob URL 在刷新、失败或卸载时释放。
