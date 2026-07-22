# 接口设计

## 1. 通用约定

- 基础路径：`/api`。
- 认证：除已有认证接口外，均使用 `Authorization: Bearer <access token>`。
- 标识符：UUID；时间：ISO 8601 UTC。
- 成功响应：普通接口返回对应 JSON 对象；列表使用 `{ "items": [], "nextCursor": null }`。
- 错误响应：`{ "code": "RESOURCE_NOT_FOUND", "message": "资源不存在或无权访问", "requestId": "..." }`。
- 分页：会话和消息使用 cursor，默认 30 条；服务端按更新时间倒序。
- 所有资源接口通过当前令牌识别用户，不接收 `userId` 参数。

## 2. 接口列表

| 编号 | 方法 | 路径 | 用途 | 对应需求 |
| --- | --- | --- | --- | --- |
| API-001 | GET | `/chat/entry` | 解析 AI 管家入口当前智能体 | FR-001 |
| API-002 | GET | `/agents` | 获取内置 AI 管家和本人智能体 | FR-002 |
| API-003 | POST | `/agents` | 创建智能体 | FR-002 |
| API-004 | GET/PATCH/DELETE | `/agents/{agentId}` | 获取、更新、删除本人智能体 | FR-002 |
| API-005 | PUT | `/agents/{agentId}/default` | 设为默认打开 | FR-002 |
| API-006 | GET/POST | `/conversations` | 查询/创建会话 | FR-003 |
| API-007 | GET | `/conversations/{conversationId}` | 获取会话与消息 | FR-003 |
| API-008 | POST | `/conversations/{conversationId}/messages:stream` | 发送消息并接收 SSE | FR-003、FR-005 |
| API-009 | GET/POST | `/knowledge/nodes` | 获取资料树/创建文件夹 | FR-004 |
| API-010 | POST | `/knowledge/files` | 上传文件 | FR-004 |
| API-011 | POST | `/knowledge/files/{fileId}/reprocess` | 重新处理失败文件 | FR-004 |

## API-001：解析聊天入口

- **响应**：

```json
{
  "agent": { "id": "system-ai-manager", "kind": "builtin", "name": "AI管家" }
}
```

- 默认自建智能体存在时，`agent.kind` 为 `personal`。
- 当前智能体的 ID 必须作为会话列表查询条件；会话接口不提供“全部智能体会话”模式。

## API-003/004：智能体请求与响应

```json
{
  "name": "销售助手",
  "description": "回答产品销售问题",
  "avatarKey": "sales",
  "systemPrompt": "你是专业销售助手。",
  "welcomeMessage": "你好，有什么可以帮助你？",
  "presetQuestions": ["介绍产品优势"],
  "allowConversationUpload": true,
  "knowledgeScopes": [
    { "nodeId": "folder-uuid", "nodeType": "folder" },
    { "nodeId": "file-uuid", "nodeType": "file" }
  ]
}
```

- `name`：1–80 字符；`description`：最多 500 字符；`systemPrompt`：最多 8000 字符。
- `knowledgeScopes` 节点必须属于当前用户；空数组合法。
- 内置智能体的 PATCH/DELETE 返回 `AGENT_IMMUTABLE`。
- 删除默认智能体返回 `DEFAULT_AGENT_MUST_BE_CLEARED`；删除成功仅写入软删除标记，响应 `204 No Content`。

## API-005：设为默认打开

- 请求为空。
- 成功响应：`{ "defaultAgentId": "uuid" }`。
- 智能体不属于当前用户时返回 `RESOURCE_NOT_FOUND`。
- 该操作幂等；同一用户事务内只保留一个默认值。

## API-006/007：会话

创建请求：`{ "agentId": "system-ai-manager 或个人智能体 UUID" }`。

会话响应包含 `id`、`agent`、`title`、`updatedAt`、`messages`。会话列表请求必须传入当前智能体 ID；读取会话时，当前智能体与会话归属不匹配应返回资源不存在。

## API-008：流式发送消息

请求：`{ "content": "请介绍报价政策" }`。

响应类型为 `text/event-stream`，事件数据：

| 事件 | 数据 | 用途 |
| --- | --- | --- |
| `status` | `{ "phase": "retrieving" }` | 展示处理阶段 |
| `token` | `{ "text": "..." }` | 追加助手回答 |
| `citation` | `{ "fileId": "...", "fileName": "...", "page": 3, "excerpt": "..." }` | 展示引用 |
| `complete` | `{ "messageId": "..." }` | 刷新会话与消息 |
| `error` | `{ "code": "MODEL_UNAVAILABLE", "message": "回答生成失败，请重试" }` | 显示可理解错误 |

消息为空返回 `VALIDATION_ERROR`；会话不存在/无权访问返回 `RESOURCE_NOT_FOUND`；同一会话存在生成中的消息时返回 `CONVERSATION_BUSY`。

## API-009/010/011：知识库

- 创建文件夹：`{ "parentId": "uuid 或 null", "name": "销售资料" }`。
- 资料树响应节点包含 `id`、`parentId`、`nodeType`、`name`、`status`、`children`；文件的 `status` 为 `processing`、`ready` 或 `failed`。
- 上传使用 `multipart/form-data`，字段为 `parentId` 和 `file`；仅接受 PDF、TXT、`.docx` 和 Markdown 的 MIME/文件签名，超出服务端配置的大小返回 `FILE_TOO_LARGE`。
- 重新处理仅允许 `failed` 文件；处理中或可用文件分别返回 `FILE_PROCESSING`、`FILE_ALREADY_READY`。
