# API 与 SSE 事件设计

不新增 HTTP 接口，复用正式会话流式接口的 `useKnowledgeBase` 请求字段和既有 SSE 事件结构。

## 请求语义

- 内置 AI 管家：`useKnowledgeBase=true` 使用当前用户全部资料库；`false` 走普通模型回答。
- 个人 Agent：资料范围由服务端已保存的绑定关系决定；客户端 `useKnowledgeBase` 不得使未绑定范围的个人 Agent 访问全部资料库。

## SSE 状态语义

| 场景 | `type` | `stage` | 前端展示文案要求 |
|---|---|---|---|
| 个人 Agent 未绑定范围 | `status` | `generating` | 明确说明未绑定知识库，当前由模型直接回答 |
| AI 管家关闭全部资料库 | `status` | `generating` | 正在生成回答 |
| 已启用但无 ready 文档 | `status` | `no_documents` | 说明资料范围内无完成索引的文件 |
| 语义检索 | `status` | `retrieving` | 正在检索资料 |
| 有可靠资料 | `status` + `sources` | `context` | 说明正在构造资料上下文并提供来源 |
| 无可靠资料 | `status` | `no_match` | 说明未找到相关资料 |
| 检索异常 | `status` | `retrieval_failed` | 说明检索服务暂不可用 |

终态继续使用既有 `message_end` 或 `error`，不修改 SSE 帧格式。
