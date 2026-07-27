# 流式智能体运行、正式聊天与编辑预览实施计划

> 2026-07-27 修正：早期版本中 Redis 断线续流的描述不属于当前阶段 A 的实现范围。本次阶段 0 只固化协议和测试基础；续流能力延后。

## 2026-07-27 阶段 0：测试与协议基础（已完成）

- 新增 Vitest、jsdom、React Testing Library 和 jest-dom 作为前端开发依赖；不进入生产构建产物。
- 使用 `pnpm test` 运行前端测试，基于 jsdom 环境。
- 流式事件的共同字段固定为 `requestId` 和 `sequence`。后续阶段将为 `message_start`、`status`、`answer_delta`、`message_end`、`error` 建立严格类型。
- 本阶段不修改聊天业务流程、数据库或 Redis 续流能力。

## 文档状态

实现中；用户已确认阶段 A，并已完成首次前后端 SSE 接线。停止生成、Redis 缓冲、断线续流和浏览器端真实模型验证仍未完成。

## 1. 最终范围与原则

### 阶段 A 必须完成

- DeepSeek 真实文本问答。
- HTTP `POST` + SSE 响应的流式通信。
- 最终答案增量输出、简单“正在生成回答”状态、停止生成、错误处理。
- 全事件 `requestId` 关联、递增 `sequence`、前端去重、断线续流和正式聊天幂等。
- 正式聊天持久化；编辑页预览使用未保存草稿且完全不持久化。
- 正式聊天与编辑预览复用消息列表、输入区和流式事件消费逻辑。

### 阶段 A 明确不做

- 不展示模型原始 `reasoning_content`，不做复杂思考摘要。
- 不做知识库检索、引用、真实联网、对话文件上传、语音或 Agent 工具。
- 不将未保存草稿写入智能体、会话或消息表。

## 2. 流式协议

客户端在提交前生成 UUID `requestId`。同一个用户动作发生重试、恢复或重复点击时必须复用该值；新的用户发送才生成新值。

所有 SSE 事件使用标准 SSE `id: {requestId}:{sequence}`，JSON 数据也必须包含相同的 `requestId` 与 `sequence`。

```ts
type StreamEventBase = {
  requestId: string
  sequence: number
}

type ChatStreamEvent =
  | (StreamEventBase & {
      type: 'message_start'
      mode: 'conversation' | 'preview'
      conversationId?: string
      userMessageId?: string
      assistantMessageId?: string
    })
  | (StreamEventBase & {
      type: 'status'
      stage: 'generating'
      text: string
    })
  | (StreamEventBase & {
      type: 'answer_delta'
      content: string
    })
  | (StreamEventBase & {
      type: 'message_end'
      generationStatus: 'complete' | 'interrupted'
      conversationId?: string
      messageId?: string
    })
  | (StreamEventBase & {
      type: 'error'
      code: string
      message: string
      retryable: boolean
    })
```

协议约束：

1. 同一 `requestId` 的 `sequence` 从 1 开始严格递增。
2. 前端仅处理 `sequence === lastSequence + 1` 的事件；小于等于 `lastSequence` 的事件忽略。
3. 出现序号跳跃时，前端以 `requestId` 和 `afterSequence=lastSequence` 续流；未收到的事件必须先回放，再继续实时推送。
4. `message_end` 或 `error` 是终止事件；终止后同一 `requestId` 不得再次调用模型。
5. 预览事件不含数据库 `conversationId`、`messageId`；正式会话事件必须在 `message_start` 中提供这些标识。

## 3. 数据与幂等设计

### 3.1 数据库迁移

在 `messages` 增加 `client_request_id UUID NULL`，并对非空值建立唯一索引；同一请求的用户消息与助手生成由该 ID 关联。将 `generation_status` 扩展为 `generating`、`complete`、`interrupted`、`failed`。

正式聊天首次发送在短事务内完成：创建或锁定会话、创建 `user` 消息、创建空内容的 `assistant` 消息（状态 `generating`）、保存 `client_request_id`。模型请求在事务外执行，避免长时间占用数据库连接。

完成时更新助手内容和状态；取消时保存已收到的部分文本并标记 `interrupted`；失败时标记 `failed`。对于遗留超过超时阈值的 `generating` 消息，后台或发送前检查会将其修正为 `failed`。

### 3.2 Redis 流状态

Redis 保存 `requestId` 对应的短期流状态和事件缓冲区，TTL 建议 10 分钟：

- 当前状态：`generating` / `complete` / `interrupted` / `failed`。
- 最后 `sequence`、已生成文本、可回放的 SSE 事件。
- 正式会话键包含用户 ID 与请求 ID；预览键也包含用户 ID，避免跨用户附着或回放。

重复请求处理：

- 正式聊天命中已完成 `client_request_id`：返回已完成消息或重放缓存，绝不二次扣费/二次写消息。
- 命中生成中请求：附着并从 `afterSequence` 回放，不二次调用模型。
- 预览命中生成中或刚完成请求：从 Redis 回放；缓存过期或服务重启后返回明确的 `STREAM_EXPIRED`，前端提示重新发送，不从头自动拼接。

## 4. 后端实施顺序

### A1：基础依赖与配置

1. 新增 `httpx` 生产依赖；不引入 LangChain/LangGraph。
2. 将 `DEEPSEEK_MODEL` 设为部署时必须确认的环境变量，不继续依赖将淘汰的模型别名。
3. 增加模型超时、最大输出长度、每用户并发数和请求频率的配置项；真实值不写入仓库。

### A2：模型适配与共享运行服务

1. 新建 `integrations/deepseek.py`，只负责 OpenAI 兼容流式响应、超时和上游错误转换。
2. 新建 `services/agent_runtime.py`，组装系统提示词、最近有限历史和当前消息；输出统一增量事件，不做 SQL。
3. 首期只发出 `status(generating)`、`answer_delta`、终止和错误事件。

### A3：正式会话流

1. 新建 Alembic 迁移和 Repository 方法，实现生成中消息、请求幂等与完成/中断/失败更新。
2. 将现有回显接口替换为 `POST /api/conversations/messages:stream`。
3. 该路由先创建可恢复的正式消息，再调用共享运行服务，并将事件写入 Redis 缓冲和 SSE 响应。
4. 新增续流请求：同一路径允许 `requestId` 与 `afterSequence`；服务端校验当前用户、会话和请求归属。

### A4：编辑预览流

1. 新增 `POST /api/agents/{agentId}/preview/messages:stream`。
2. 请求包含完整 `draftAgent`、本地历史、`content`、`requestId` 和可选 `afterSequence`。
3. 服务端验证当前用户拥有个人智能体，并用与 PATCH 相同的字段规则校验草稿。
4. 预览只使用 Redis 流状态，禁止调用任何会话/消息/智能体写入方法。

### A5：安全、限制与观测

1. 对请求体、历史条数、历史长度、并发数和每分钟调用次数设置硬限制。
2. 日志只记录 requestId、用户 ID、智能体 ID、模型名、耗时和错误码；不记录密钥、完整提示词或完整用户内容。
3. 所有资源归属校验在进入 Redis 回放和模型调用前完成。

## 5. 前端实施顺序

### A6：统一流式客户端

1. 新建 `streamChat` API：使用 `fetch` 读取 POST 的 `ReadableStream`，解析 SSE，支持 `AbortController`。
2. 新建流式事件 reducer：按 `requestId + sequence` 管理每条生成消息；重复事件忽略，序号跳跃触发续流。
3. 新建 `useStreamingChat`：管理发送、恢复、停止、失败重试及生成状态。

### A7：正式聊天页

1. `useSendMessage` 改为使用 `useStreamingChat`，不再等待一次性回显响应。
2. 收到 `message_start` 后立即在 React Query 会话缓存创建用户消息和生成中的助手消息。
3. `answer_delta` 只追加到对应 requestId 的助手消息；`message_end` 写入完成状态并刷新历史列表。
4. 停止生成中止网络请求，并调用正式取消路径，保留部分回答。

### A8：编辑页预览

1. `AgentEditorPreview` 使用同一流式 Hook，但存储在组件本地 state，不使用正式会话缓存。
2. 每次发送提交完整 `previewAgent` 草稿；预设问题点击只填入或直接发送，具体交互沿用现有输入框规则。
3. 增加“重置预览”；离开编辑页清空历史；预览取消、错误和续流与正式页面表现一致。

## 6. 测试与验收

### 后端

- 同一 `requestId` 连续提交两次：只有一组正式消息和一次模型调用。
- 重复或乱序 `sequence` 不造成重复文本；序号缺失可按 `afterSequence` 回放。
- 用户 A 无法续流或预览用户 B 的请求。
- 预览请求前后 `agents`、`conversations`、`messages` 记录数不变。
- 模型超时、限流、断线和取消后，正式助手消息状态分别正确为 `failed` 或 `interrupted`。

### 前端

- 最终答案逐段显示；重复 SSE 事件不重复追加文本。
- 切换会话或预览重置不会把旧请求的 delta 写入新消息。
- 断线后自动续流；续流失败提示重试且不伪造完成结果。
- 预览草稿未保存时，下一条回答使用新 `systemPrompt`；刷新页面后预览消息消失。

## 7. 后续阶段

### 阶段 B：知识库与真实执行步骤

先实现资料树、私有上传、异步解析、文本分块、`bge-m3` 向量化、pgvector 检索、智能体资料范围绑定。完成后扩展事件：`status(retrieving)`、`retrieval_result`。文件解析状态在知识库页面展示，不伪装为每次问答的思考过程。

### 阶段 C：引用来源

检索稳定后增加 `citation` 事件和来源卡片。引用必须绑定真实文件、页码/片段和摘要；模型未使用资料时不得创建伪引用。

### 阶段 D：受控处理思路摘要

根据阶段 A–C 的真实执行事件生成可折叠“处理思路”，而非直接展示完整模型原始思维链。该阶段再决定是否使用模型生成摘要、长度限制、过滤规则和正式会话的持久化字段。

## 8. 不开始编码前仍需锁定的参数

1. DeepSeek 具体模型名、是否启用模型 thinking mode、单次最大输出和请求超时。
2. 阶段 A 的每用户并发和限流阈值。
3. 正式流生成中的部分回答是否按固定间隔写入数据库，或仅在结束/取消时写入。
4. 预览流的 Redis 缓存 TTL；本计划建议 10 分钟。
