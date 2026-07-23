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
| API-005A | DELETE | `/agents/default` | 清空默认打开设置 | FR-001、FR-002 |
| API-006 | GET/POST | `/conversations` | 查询/创建会话 | FR-003 |
| API-007 | GET | `/conversations/{conversationId}` | 获取会话与消息 | FR-003 |
| API-007A | POST | `/conversations/{conversationId}/messages` | 写入用户消息并返回阶段 2 回显 | FR-003 |
| API-008 | POST | `/conversations/{conversationId}/messages:stream` | 发送消息并接收 SSE | FR-003、FR-005 |
| API-009 | GET/POST | `/knowledge/nodes` | 获取资料树/创建文件夹 | FR-004 |
| API-010 | POST | `/knowledge/files` | 上传文件 | FR-004 |
| API-011 | POST | `/knowledge/files/{fileId}/reprocess` | 重新处理失败文件 | FR-004 |

## API-001：解析聊天入口

- **响应**：

```json
{
  "agent": { "id": "00000000-0000-0000-0000-000000000001", "kind": "builtin", "name": "AI管家" }
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
  "allowNetworkAccess": false,
  "knowledgeScopes": [
    { "nodeId": "folder-uuid", "nodeType": "folder" },
    { "nodeId": "file-uuid", "nodeType": "file" }
  ]
}
```

- `name`：1–80 字符；`description`：最多 500 字符；`systemPrompt`：最多 8000 字符。
- 本阶段暂不接收 `knowledgeScopes`；待阶段 3 的 `knowledge_nodes` 与资料范围表完成后再开放该字段。
- `allowNetworkAccess` 由创建/编辑个人智能体时保存，决定是否显示联网入口；实际联网调用后续单独实现。
- 内置智能体的 PATCH/DELETE 返回 `AGENT_IMMUTABLE`。
- 删除默认智能体返回 `DEFAULT_AGENT_MUST_BE_CLEARED`；删除成功仅写入软删除标记，响应 `204 No Content`。

## API-005：设为默认打开

- 请求为空。
- 成功响应：`{ "defaultAgentId": "uuid" }`。
- 智能体不属于当前用户时返回 `RESOURCE_NOT_FOUND`。
- 该操作幂等；同一用户事务内只保留一个默认值。

## API-005A：清空默认打开

- 请求为空，成功响应 `204 No Content`。
- 此接口只将当前用户的 `user_preferences.default_agent_id` 置为空，**不会删除任何智能体**。
- 清空后，聊天入口回退为 `kind: "builtin"` 的内置 AI 管家。
- 删除某个默认个人智能体前必须先调用本接口；这样不会留下指向已软删除智能体的默认设置。

## API-006/007：会话

创建请求：`{ "agentId": "内置 AI 管家的固定 UUID 或个人智能体 UUID" }`。

会话响应包含 `id`、`agent`、`title`、`updatedAt`、`messages`。会话列表请求必须传入当前智能体 ID；读取会话时，当前智能体与会话归属不匹配应返回资源不存在。

## API-007A：阶段 2 消息回显

- 请求：`{ "content": "请介绍报价政策" }`，内容去除首尾空白后必须为 1–4000 字符。
- 服务端先验证会话归属当前用户且关联智能体仍处于活跃状态，再在同一数据库事务中写入一条 `user` 消息和一条 `assistant` 消息。
- 助手消息固定返回“已收到你的消息：{内容}”，仅用于验证消息持久化、顺序和会话更新时间；不调用模型、不检索资料，也不表示 AI 能力已实现。
- 若会话标题为空，首次用户消息的前 50 个字符作为标题；响应包含更新后的会话和两条已保存消息。
- 会话不存在、无权访问或关联智能体已删除时返回 `RESOURCE_NOT_FOUND`。

## API-008：流式发送消息

请求：`{ "content": "请介绍报价政策", "useKnowledgeBase": true }`。

- `useKnowledgeBase` 仅适用于内置 AI 管家；首次进入时前端默认传 `true`，用户关闭“全部资料”后传 `false`。个人智能体的检索范围由其绑定资料决定，前端不显示该开关。

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
