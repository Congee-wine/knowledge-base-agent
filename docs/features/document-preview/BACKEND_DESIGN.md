# 后端设计

路由层只解析 `nodeId` 与当前用户，调用预览服务。Repository 以 `knowledge_node_id`、`owner_user_id` 和 `is_current` 查询文件版本；服务层校验文件状态和类型，读取私有对象并构造响应。

- 文本与 DOCX 返回 JSON，避免前端直接接触对象存储。
- PDF 返回 `application/pdf` 二进制内容，添加 `X-Content-Type-Options: nosniff` 与 `Content-Disposition: inline`。
- DOCX 使用现有 `python-docx` 读取段落和表格；生成器只输出固定标签与经 `html.escape` 转义的文字。
- 对象存储读取或转换异常转换为可定位的服务端日志和用户可理解的预览失败响应。
