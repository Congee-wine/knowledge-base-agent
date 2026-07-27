# 开发日志

## 2026-07-27：正式聊天自动跟随与回到底部

### 任务目标

让 AI 流式回复时使用 Ant Design X 的消息列表自动跟随能力，并在用户查看较早消息后提供明确、可访问的回到底部操作。

### 实现内容

- 正式聊天页的消息区域改由 Ant Design X `Bubble.List` 自身承担滚动，避免外层容器与组件内部滚动机制冲突。
- 保留 `autoScroll`；用户停留在底部时，流式新增内容会持续跟随。
- 用户向上浏览历史消息时，显示悬浮的图标按钮；点击后调用 `Bubble.List.scrollTo({ top: 'bottom', behavior: 'smooth' })` 平滑回到底部。
- 编辑页预览没有改变原有容器布局，避免本次局部修复影响其三栏工作台。

### 主要文件

- `frontend/src/features/chat/components/ChatMessageList.tsx`：消息列表滚动容器、滚动位置判断和回到底部控件。
- `frontend/src/pages/ChatPage.tsx`：正式聊天页将滚动职责交给消息列表。

### 技术方案

复用已安装的 `@ant-design/x` `Bubble.List` 及其公开的 `autoScroll`、`scrollTo` 能力，不新增依赖，也不自行维护 DOM 滚动计算。自动跟随仅在用户仍位于底部时生效，避免阅读历史记录时被新内容强制打断。

### 接口或数据变化

无。

### 验证情况

- 通过：`frontend/` 下执行 `pnpm test -- --run`，5 个测试文件、25 项测试通过。
- 通过：`frontend/` 下执行 `pnpm build`；首次沙箱构建无法读取既有 `highlight.js` 依赖，授权环境重试后通过。
- 待执行：浏览器端以长回复和流式增量确认自动跟随、上滑后的按钮显示及平滑回到底部效果。

### 遗留问题

- 不改变阶段 4 的真实模型流式浏览器联调范围；本次仅完成前端滚动容器和交互接入。

## 2026-07-27：复制操作改为悬浮提示

### 任务目标

使助手消息下方的复制操作保持紧凑，只在鼠标悬浮时显示文字说明。

### 实现内容

- 复制操作改为仅显示图标。
- 使用 Tooltip 在悬浮时显示“复制”，并保留无障碍标签与原有点击逻辑。

### 主要文件

- `frontend/src/features/chat/components/ChatMessageList.tsx`：复制操作的 Tooltip 展示。

### 技术方案

复用已安装的 Ant Design Tooltip，不新增依赖或自定义浮层逻辑。

### 接口或数据变化

无。

### 验证情况

- 待执行前端测试和构建。

### 遗留问题

- 待浏览器端确认 Tooltip 位置和触屏设备下的可发现性。

## 2026-07-27：区分助手消息样式并添加复制操作

### 任务目标

使助手回复与用户灰色消息气泡在视觉上清晰区分，并为助手回复提供复制能力。

### 实现内容

- 助手消息改为左对齐、透明、无内边距的内容区；用户消息继续使用右侧灰色填充气泡。
- 每条非空助手消息下方增加复制操作；复制成功或失败均提供反馈。
- 流式生成中的空助手消息不显示复制操作。

### 主要文件

- `frontend/src/features/chat/components/ChatMessageList.tsx`：助手气泡变体、样式和复制交互。

### 技术方案

使用 Ant Design X `Bubble` 的 `borderless` 变体和内容插槽样式，避免通过全局 CSS 覆盖组件内部结构；复制使用浏览器 Clipboard API。

### 接口或数据变化

无。

### 验证情况

- 待执行前端测试、构建和浏览器视觉验证。

### 遗留问题

- 需在阶段 4 人工验证长 Markdown、代码块和流式增量时复制操作的位置与可用性。

## 2026-07-27：使用 Sender 内置停止生成控件

### 任务目标

消除输入区生成状态中重复的停止操作，并保持已有的正式会话中断和预览本地取消逻辑。

### 实现内容

- 移除输入区 footer 中额外渲染的“停止生成”按钮。
- 将 Ant Design X `Sender` 在 `loading` 状态下内置的取消控件绑定到既有 `stream.stop()`。

### 主要文件

- `frontend/src/features/chat/components/ChatComposer.tsx`：使用 `Sender.onCancel` 复用框架的内置停止控件。

### 技术方案

保留框架组件在加载状态下原生呈现的方形中断图标，避免重复 UI；取消回调仍复用阶段 3 已实现的正式会话持久化和预览隔离逻辑。

### 接口或数据变化

无。

### 验证情况

- 待执行前端构建和浏览器验证。

### 遗留问题

- 仍需在阶段 4 验证真实流式生成时内置控件的视觉与中断行为。

## 2026-07-27：阶段 3 前端 SSE 状态机与停止生成

### 任务目标

让正式聊天和编辑页预览以一致的流式解析及请求控制方式工作，并为用户提供可停止的生成过程。

### 实现内容

- 新增增量 SSE 解析器，支持 `\n`/`\r\n`、同帧多行 `data:`、跨分块帧和流结束时未带空行的帧。
- Hook 为每条活动流保存 `AbortController`、运行模式、请求 ID 与正式助手消息 ID，并过滤模式不匹配的事件。
- 停止正式会话时标记本地消息为 `interrupted`，调用中断接口保存部分回答；停止预览时只取消本地请求。
- 聊天页切换智能体、切换会话或新建会话前停止活动流；编辑预览切换智能体和组件卸载时停止并重置预览。
- 输入区在生成时显示“停止生成”操作。

### 主要文件

- `frontend/src/features/chat/streaming/sseParser.ts`：增量 SSE 帧解析。
- `frontend/src/api/chat.ts`：解析器接入与中断接口客户端。
- `frontend/src/features/chat/hooks/useStreamingChat.ts`：活动流和停止逻辑。
- `frontend/src/features/chat/components/ChatComposer.tsx`、`pages/ChatPage.tsx`、`features/agents/components/AgentEditorPreview.tsx`：停止生成与页面清理接入。
- `frontend/src/features/chat/streaming/sseParser.test.ts`、`useStreamingChat.test.tsx`：解析和停止行为测试。

### 技术方案

以 `AbortController` 负责本地网络中止，以后端中断接口负责正式消息终态；两者缺一不可。预览没有持久化消息 ID，因此不调用正式中断接口。

### 接口或数据变化

无新增前端依赖或数据库变更；前端开始消费阶段 2B 新增的中断接口。

### 验证情况

- 通过：`pnpm test -- --run`，5 个测试文件、25 项测试。
- 通过：`pnpm build`。
- 未执行：真实浏览器和认证后的端到端流式中断联调。

### 遗留问题

- 尚未将状态更新彻底抽取为独立 reducer；当前 Hook 已具备活动流边界，后续可在不改变协议的前提下继续拆分。
- 阶段 4 需验证正式历史覆盖、本地预览隔离、停止按钮和 Markdown 流式展示。

## 2026-07-27：阶段 2B 后端运行生命周期与数据隔离

### 任务目标

让正式聊天使用受控历史上下文并具备可持久化的中断终态，同时保证编辑预览不写入正式业务数据。

### 实现内容

- 新增查询：仅返回当前用户消息之前、内容非空且 `generation_status='complete'` 的最近 10 条历史消息。
- 正式模型调用使用该历史；正在生成、失败、已中断和空内容消息不会进入 Prompt。
- `afterSequence > 0` 在两个流式入口处统一返回 `STREAM_RESUME_UNAVAILABLE`，不伪装支持续流。
- 新增正式助手消息中断接口；它验证消息属于当前用户且仍在生成中，保存客户端提供的已生成片段并标记为 `interrupted`。
- 预览服务继续只读取草稿请求和本地历史，不调用任何业务写入方法。

### 主要文件

- `backend/repositories/conversations.py`：有效历史查询和按用户中断消息更新。
- `backend/services/conversations.py`：历史组装与中断用例。
- `backend/routers/conversations.py`、`backend/routers/agents.py`：中断路由和续流拒绝。
- `backend/schemas/streaming.py`：中断请求结构。
- `backend/tests/test_streaming_protocol.py`：历史加载、续流拒绝和部分回答持久化测试。

### 技术方案

历史查询在插入当前消息后按其 `message_order` 截断，避免将本轮用户消息重复作为历史传给模型。中断请求由后续前端状态机传入当前累计文本，以保持中断回答可回显。

### 接口或数据变化

- 新增 `POST /api/conversations/messages/{assistantMessageId}:interrupt`。
- 请求体：`{ "content": "已生成的部分回答" }`，可省略并默认空字符串。
- 无数据库迁移或新增依赖。

### 验证情况

- 通过：会话服务和 SSE 协议测试共 10 项。
- 通过：相关 Python 模块 `py_compile`。
- 未执行：认证后的真实 HTTP 中断请求和浏览器端停止生成联调，留待阶段 3。

### 遗留问题

- 前端尚未调用中断接口，`AbortController`、取消后的本地状态同步和页面卸载清理属于阶段 3。
- Redis 断线续流仍明确不在当前范围。

## 2026-07-27：阶段 2A 双模式 SSE 契约

### 任务目标

使编辑预览和正式聊天共享流式事件基础设施，同时通过显式运行模式保持草稿预览与持久化会话的边界。

### 实现内容

- 所有预览和正式 SSE 事件均增加 `mode: "preview" | "conversation"`。
- 前端将 `message_start`、`message_end` 定义为按模式区分的联合类型：预览不读取数据库 ID，正式会话必须读取真实 ID。
- 预览流只更新本地临时消息，不创建会话状态或待确认的持久化消息对。
- 预览与正式服务在创建流响应前执行资源/权限校验；未知运行期异常转换为可消费的 `error` 事件。

### 主要文件

- `frontend/src/api/chat.ts`：双模式 SSE 事件验证。
- `frontend/src/features/chat/hooks/useStreamingChat.ts`：按模式更新预览或正式会话状态。
- `backend/routers/agents.py`、`backend/routers/conversations.py`：统一注入 SSE `mode`。
- `backend/services/agent_preview.py`、`backend/services/conversations.py`：前置校验并映射未知运行异常。
- `backend/tests/test_streaming_protocol.py`：覆盖两种模式的事件载荷和预览校验时机。

### 技术方案

使用 `mode` 作为可辨别字段，而不是通过是否存在 `conversationId` 或 `messageId` 猜测调用上下文。该方式使后续取消、重试和工具事件可以在同一协议下演进。

### 接口或数据变化

- 现有流式响应新增 `mode` 字段。
- 无数据库、迁移、路由路径或依赖变更。

### 验证情况

- 通过：前端 `pnpm test -- --run`，21 项测试。
- 通过：后端 `python -m unittest tests.test_streaming_protocol`，3 项测试。
- 通过：相关 Python 模块 `py_compile`。
- 通过：前端 `pnpm build`；沙箱内首次构建因既有 `highlight.js` 读取权限失败，获准在受限环境外复跑后成功。
- 未执行：真实浏览器端和认证后的端到端流式请求联调。

### 遗留问题

- 阶段 2B 仍需实现正式会话的完整历史加载、取消终态和续流未支持的标准错误。
- 阶段 2A 在浏览器端验证前保持“进行中”。

## 2026-07-27：重排未完成的流式聊天与编辑预览阶段

### 任务目标

基于已完成的阶段 0/1 和已确认的双运行上下文原则，修正后续流式实施顺序，避免编辑页预览继续被当作正式会话处理。

### 实现内容

- 未修改应用代码。
- 将未完成工作拆分为阶段 2A、2B、3、4、5：先定义预览/正式会话的 SSE 模式边界，再完成后端生命周期、前端状态机、页面联调和回归验收。
- 明确预览使用草稿配置与页面内存历史，正式聊天使用已保存配置与持久化会话；两者共享 Agent Runtime，不共享会话存储状态。

### 主要文件

- `docs/features/agent-knowledge-platform/STREAMING_RUNTIME_PLAN.md`：记录重排后的阶段目标、协议边界和验收条件。
- `docs/features/agent-knowledge-platform/CHANGELOG.md`：记录此次已确认的设计调整。
- `docs/PROJECT_STATUS.md`：同步当前阶段与预览链路尚未验收的真实状态。

### 技术方案

使用 `mode: "preview" | "conversation"` 作为 SSE 的可辨别字段。预览事件不携带持久化会话/消息 ID，正式事件必须携带这些 ID；前端据此执行不同的状态更新分支。

### 接口或数据变化

无实际接口、数据库或依赖变更。本次仅更新未完成阶段的设计与验收要求。

### 验证情况

- 已完成文档一致性检查：阶段 0/1 保持已完成，阶段 2A 仍未实现。
- 未执行代码测试或构建：本次没有修改代码。

### 遗留问题

- 需要在阶段 2A 实现并测试双模式 SSE 契约后，才能继续前端状态机与编辑预览联调。

## 2026-07-27：流式消息重复渲染修复

### 任务目标

修复流式聊天中同一对用户/助手消息被渲染两次的问题：前端在 `message_start` 拿到服务端真实消息 ID 后未替换本地临时 ID，导致数据库详情和本地流式消息同时存在于 `displayedMessages`。

### 实现内容

- 将 `ChatStreamEvent` 从扁平可选字段改为可区分联合类型，`message_start` 的 `userMessageId`/`assistantMessageId` 变为必填。
- `useStreamingChat` 在 `message_start` 时将 `local-user-*`/`local-assistant-*` 替换为服务端真实 ID；`StreamState` 新增 `assistantMessageId` 用于后续 `answer_delta` 定位。
- `message_end` 不立即删除本地消息，而是将消息对记录到 `pendingPersistedPairs`，等待服务端详情确认后再清理。
- 新增 `acknowledgePersistedPair(requestId)` 方法，仅在 React Query 会话详情缓存中确认包含该对完成消息后移除本地副本。
- 新增 `mergeMessages` 纯函数：按 ID 合并服务端与本地消息，流式中的助手消息仅在 `sending === true` 或消息对尚处于 `pendingPersistedPairs` 时优先于服务端内容。
- `ChatPage` 使用 `mergeMessages` 替代直接拼接；`message_end` 后 `invalidateQueries` 触发后台刷新；详情确认完成后调用 `acknowledgePersistedPair` 清理本地消息。
- 每次发送流式请求前清空上一请求的真实消息 ID，避免新请求在收到自身 `message_start` 前失败时，把上一轮已完成助手消息误标记为失败。
- SSE 消费端在分发前校验事件类型、请求 ID、序号及各事件必填字段；`answer_delta.content` 允许空字符串，避免合法的空增量被误判为协议错误。
- `ChatPage` 的确认清理 effect 改为依赖具体状态和回调，避免依赖整个 hook 返回对象而增加无意义的重复执行。

### 主要文件

- `frontend/src/api/chat.ts`：`ChatStreamEvent` 改为联合类型，并增加 SSE 事件运行时结构校验。
- `frontend/src/api/__tests__/chat.test.ts`：2 项 SSE 协议校验测试，覆盖合法事件分发与缺失必填字段拒绝。
- `frontend/src/features/chat/hooks/useStreamingChat.ts`：真实 ID 替换、`pendingPersistedPairs`、`acknowledgePersistedPair`。
- `frontend/src/features/chat/utils/mergeMessages.ts`：新增按 ID 去重合并纯函数。
- `frontend/src/pages/ChatPage.tsx`：使用 `mergeMessages`、`invalidateQueries` 和 `acknowledgePersistedPair`。
- `frontend/src/features/chat/utils/__tests__/mergeMessages.test.ts`：9 项合并逻辑测试。
- `frontend/src/features/chat/hooks/__tests__/useStreamingChat.test.tsx`：7 项 hook 测试，覆盖新请求在 `message_start` 前失败时不污染上一轮消息状态。

### 技术方案

本地流式消息在服务端详情确认包含同一对完成消息前不删除。渲染时始终按真实消息 ID 去重；流式助手内容仅在发送进行中或尚未确认时优先显示，确认后由服务端数据接管。

### 接口或数据变化

无。后端、接口路径、数据库和迁移均未修改。

### 验证情况

- 通过：`pnpm test`，4 个测试文件共 19 项测试全部通过。
- 通过：`pnpm build`（tsc + vite build）。
- 未执行：浏览器人工联调；需验证新会话首条消息和已有会话续发两种场景下不出现重复消息。

### 遗留问题

- 浏览器端需人工验证：流式完成后消息不闪烁、不重复；详情查询失败时本地完成消息仍可见。
- 停止生成、Redis 断线续流不在本次修复范围。

## 2026-07-27：阶段 1 消息显示顺序修复

### 任务目标

消除用户消息与对应助手消息使用相同时间戳时，因 UUID 次序随机而出现助手消息显示在用户消息之前的问题。

### 实现内容

- 新增 `messages.message_order`，作为会话内唯一、连续的显示序号。
- Echo 和流式写入均在同一事务中锁定会话并为用户/助手消息连续分配序号。
- 历史消息查询改为按 `message_order` 排序；历史数据由迁移按旧的 `created_at, id` 顺序回填。

### 主要文件

- `backend/migrations/versions/20260727_0008_message_order.py`：新增字段、历史回填和会话内唯一约束。
- `backend/repositories/conversations.py`：分配序号并改用稳定排序。
- `backend/tests/test_conversations_repository.py`：覆盖相同会话内时间戳反转时的显示顺序。

### 接口或数据变化

- 数据库新增非空 `message_order`，并增加 `(conversation_id, message_order)` 唯一约束。
- 未新增或修改 HTTP 接口。

### 验证情况

- `py_compile` 通过。
- Alembic `upgrade head` 已应用至 `20260727_0008`。
- 仓储、服务、智能体/会话集成和认证集成测试分模块共 33 项通过。

### 遗留问题

- 以单个 120 秒超时运行全部后端测试会超时；四个模块分开运行均通过，后续应优化测试数据库连接和执行时长。

## 2026-07-27：阶段 1 验收修正

### 实现内容

- 将流式消息写入放在 PostgreSQL 保存点中；同一 `client_request_id` 的并发写入命中唯一约束时，回滚仅本次尝试并重读已创建的 user/assistant 消息对。
- 向已创建的草稿会话首次发送流式消息时，在同一事务中填充标题、设置 `is_draft=false` 并更新 `updated_at`。
- 流式终态更新限定为 `role='assistant' AND generation_status='generating'`，防止覆盖 user 消息、已完成消息或已中断消息。
- 旧流式记录缺少 `reply_to_message_id` 时，返回 `STREAM_REQUEST_UNRECOVERABLE` 而非构造不完整的消息对。

### 测试与验收

- 仓储层测试增加到 14 项，包含双连接同步起点的并发幂等测试、草稿激活、跨会话约束、状态更新保护和旧请求拒绝。
- 后端相关测试共 32 项通过。
- 未执行共享数据库的 `downgrade -1` 回滚验证，因为该操作会删除已存在的 `reply_to_message_id` 数据。

## 2026-07-27：阶段 1 独立验证更正

### 实际验证结果

- PostgreSQL `127.0.0.1:5432` 可连接，Alembic 当前版本为 `20260727_0007 (head)`。
- `py_compile` 通过；新增仓储层/服务层测试与现有集成测试共 27 项通过。
- 数据库实测确认：assistant 消息无法引用另一会话的 user 消息。

### 验收未通过项

- `start_stream_generation()` 先查询、后插入，未使用行锁、`ON CONFLICT` 恢复或唯一冲突重试。两个独立连接的竞态实测确认：同一 `client_request_id` 的第二个写入触发数据库唯一约束异常，不符合幂等性验收标准。
- 向已创建的 `is_draft=true` 会话首次发送流式消息时，代码未将其转为 `is_draft=false`、未更新标题和 `updated_at`。
- `_update_stream_status()` 仅按 `id` 更新消息，没有限定 `role='assistant'`。虽然当前服务层传入的是 assistant ID，但仓储层仍未独立保证“只更新正在生成的 assistant 消息”。
- 幂等查询对早期、`reply_to_message_id IS NULL` 的历史流式记录使用 `LEFT JOIN`，可能构造出空的 user 消息对象。需要明确把它们视为不可恢复的旧请求，而不是继续返回不完整的消息对。
- 新增测试没有覆盖跨会话约束、并发幂等性、流式开始时激活草稿会话和 `updated_at` 更新。
- 没有在共享环境中执行 `downgrade -1` 及再次 `upgrade head`：这会删除已存在的 `reply_to_message_id` 数据，不应将其写成已验证事实。

### 结论

不接受“阶段 1 已完成”的文档声明。上述项目修正并添加对应测试后，才可进入阶段 2。

## 2026-07-27：流式聊天修复阶段 1：消息仓储层事务与幂等性

### 任务目标

修复消息持久化的三个根本问题：`_append_echo_messages()` 被截断返回 `None` 导致上层解包崩溃、`finish_stream_generation()` 存在死代码和职责混乱、流式消息缺少用户-助手回复关联且幂等查询可能关联到错误的 user 消息。

### 实现内容

- 修复 `_append_echo_messages()`：补全 assistant 消息插入、会话标题更新和 `return` 语句，返回完整三元组。
- 删除 `finish_stream_generation()` 及其死代码，拆分为 `complete_stream_generation()`、`interrupt_stream_generation()`、`fail_stream_generation()` 三个职责清晰的方法，均通过 `RETURNING` 更新并抛出明确异常。
- 修改 `start_stream_generation()`：在同一事务中为 assistant 消息写入 `reply_to_message_id`，指向对应的 user 消息。
- 重写幂等查询 `_find_existing_stream_request()`：通过 `assistant.reply_to_message_id` 关联 user 消息，不再从整个 conversation 取最新 user 消息。
- 服务层适配：替换 `finish_stream_generation` 调用为 `complete_stream_generation` / `fail_stream_generation`；对 `generating` 状态的重复请求返回 `REQUEST_IN_PROGRESS` 错误，对 `failed` / `interrupted` 状态返回可重试错误。

### 主要文件

- `backend/repositories/conversations.py`：仓储层修复与重写。
- `backend/services/conversations.py`：服务层适配新仓储方法。
- `backend/migrations/versions/20260727_0007_message_reply_relation.py`：新增 `reply_to_message_id` 字段、索引、检查约束、唯一约束和外键。
- `backend/tests/test_conversations_repository.py`：9 项仓储层测试。
- `backend/tests/test_conversations_service.py`：4 项服务层测试。

### 技术方案

在 `messages` 表新增 `reply_to_message_id UUID NULL`，由 `assistant` 消息指向其回复的 `user` 消息。通过 `(id, conversation_id)` 唯一约束和复合外键保证 assistant 不能引用其他会话的消息。检查约束确保只有 `assistant` 角色可设置该字段。历史数据不回填，保持 `NULL`。

### 接口或数据变化

- 新增数据库迁移 `20260727_0007`，已在本地 PostgreSQL 执行 `alembic upgrade head`。
- 新增 `messages.reply_to_message_id` 字段、`ix_messages_reply_to_message_id` 索引、`uq_messages_id_conversation_id` 唯一约束、`ck_messages_reply_to_role` 检查约束、`fk_messages_reply_to_message_id` 和 `fk_messages_reply_conversation` 外键。
- 无新增 HTTP 接口。

### 验证情况

- 通过：`py_compile` 编译 `repositories/conversations.py`、`services/conversations.py`、迁移文件。
- 通过：Alembic `upgrade head` 和 `downgrade -1` / 再次 `upgrade head`。
- 通过：9 项仓储层测试（echo 三元组、流式开始写入 reply_to_message_id、complete/interrupt/fail 状态更新、幂等单次创建、幂等返回相同消息、不存在消息抛异常、检查约束拒绝 user 消息设置 reply_to_message_id）。
- 通过：4 项服务层测试（echo 不崩溃、已完成重复请求不调用模型、生成中返回 REQUEST_IN_PROGRESS、失败返回可重试错误）。
- 通过：9 项已有集成测试（智能体/会话）和 5 项已有认证集成测试，无回归。

### 遗留问题

- 前端 SSE 解析、停止生成、Redis 断线续流不在阶段 1 范围。
- `GENERATION_FAILED` 状态的重复请求当前返回可重试错误，后续阶段可改为自动重新生成。

## 2026-07-27：流式聊天修复阶段 0：测试基础与协议边界

### 任务目标

为后续 SSE 解析、事件去重、取消与聊天联调修复建立前端测试入口，同时纠正早期计划中与当前范围冲突的 Redis 续流描述。

### 实现内容

- 新增 Vitest、jsdom、React Testing Library 与 jest-dom 开发依赖。
- 新增 `pnpm test` 和 `pnpm test:watch` 脚本。
- 配置 jsdom 测试环境、DOM 断言和基础烟雾测试。

### 主要文件

- `frontend/vite.config.ts`：Vitest 测试环境。
- `frontend/src/test/setup.ts`：jest-dom 断言加载。
- `frontend/src/test/environment.test.tsx`：jsdom 和 Testing Library 烟雾测试。

### 接口或数据变化

无。

### 验证情况

- `pnpm test`：通过，1 个测试文件、1 个测试。
- `pnpm build`：通过。普通受限环境下无法读取现有 `highlight.js` 依赖，以提升权限重跑后构建成功。

### 遗留问题

阶段 1 将修复消息仓储层事务不完整与幂等性缺陷。

## 2026-07-25：确认智能体推理摘要展示策略

### 任务目标

确认真实模型问答、知识库检索和联网能力向用户展示过程的产品边界。

### 实现内容

- 确认展示简短、受控的模型推理摘要。
- 确认知识库检索、联网搜索和文件处理以独立执行步骤、状态和引用呈现，不展示完整原始思维链。
- 更新共享运行与预览设计、问题记录和技术决策。

### 接口或数据变化

无代码或 API 变更；后续运行结果会预留 `reasoningSummary` 与 `executionSteps`。

### 验证情况

- 设计确认阶段，无运行代码或测试变更。

## 2026-07-25：共享智能体运行与实时预览设计

### 任务目标

为编辑页右侧预览和正式聊天定义同一套真实模型运行链路，避免预览继续停留在静态展示或伪造回答。

### 实现内容

- 新增设计文档 `RUNTIME_PREVIEW_DESIGN.md`，定义共享运行服务、DeepSeek 适配、正式持久化聊天和无持久化预览的边界。
- 明确知识库、联网和对话上传分别依赖的后续能力与实施顺序。

### 接口或数据变化

- 规划新增 `POST /api/agents/{agentId}/preview/messages`；当前未修改代码、接口或数据库。

### 验证情况

- 设计阶段，无运行代码或测试变更。

## 2026-07-25：修复预设问题实时预览丢失条目

### 任务目标

修复编辑工作台中添加多个预设问题后，右侧预览只显示最后一个问题的状态同步错误。

### 实现内容

- 表单变更时不再将 `Form.List` 的局部 `changedValues` 直接覆盖预览草稿。
- 改为从表单实例读取完整当前值，再合并到预览草稿，确保所有预设问题都传给右侧欢迎组件。

### 主要文件

- `frontend/src/pages/AgentEditorPage.tsx`：完整表单值到预览草稿的同步。

### 技术方案

`Form.List` 的局部变更数据不能作为整个数组字段的权威值；使用 `form.getFieldsValue(true)` 获取当前表单快照，避免数组被最后一次变更截断。

### 接口或数据变化

无。

### 验证情况

- 待执行：TypeScript 检查和浏览器中连续填写多个预设问题的验证。

### 遗留问题

- 无代码级遗留问题。

## 2026-07-25：统一智能体配置展示与编辑预览

### 任务目标

修复编辑页、列表卡片、顶部标题和侧栏头像/名称来源不一致的问题；明确区分 AI 管家与自建智能体的欢迎区，并让 AI 管家的预设问题由数据库提供。

### 实现内容

- 新增共享头像组件，统一按 `avatarKey` 读取受保护头像 Blob；无头像或读取失败时回退到名称首字。
- 自建智能体聊天欢迎区和编辑页右侧预览复用同一头像欢迎组件；预览输入框复用聊天输入框主体，上传与联网入口随当前草稿配置变化。
- 编辑表单改为按变更字段合并预览草稿，避免单字段更新覆盖名称和头像；保存后立即更新智能体详情、列表和默认入口缓存。
- 内置 AI 管家继续使用既有欢迎区样式，删除前端硬编码预设问题；新增 Alembic 迁移写入内置 AI 管家的预设问题种子数据。

### 主要文件

- `frontend/src/features/agents/components/AgentAvatar.tsx`：共享受保护头像加载与回退展示。
- `frontend/src/features/agents/components/PersonalAgentWelcome.tsx`：自建智能体统一欢迎区。
- `frontend/src/features/agents/components/AgentEditorPreview.tsx`：编辑工作台的实时预览组合。
- `frontend/src/features/chat/components/ChatWelcome.tsx`、`ChatComposer.tsx`：区分内置/自建欢迎区并复用输入主体。
- `frontend/src/pages/AgentEditorPage.tsx`、`frontend/src/layouts/AppLayout.tsx`、`AgentCard.tsx`：消除各处独立头像与缓存状态。
- `backend/migrations/versions/20260725_0005_builtin_agent_preset_questions.py`：补齐内置 AI 管家预设问题数据。

### 技术方案

展示层只接收同一份 `ChatAgent` 配置，头像读取收敛为共享组件；表单草稿通过增量合并保持非表单字段。预览复用真实输入 UI，但因模型和消息工作流尚未接入，发送只给出明确提示，不伪造会话或回答。

### 接口或数据变化

- 无新增 HTTP API 或响应字段。
- 新增数据库数据迁移，向现有 `agent_preset_questions` 表插入内置 AI 管家问题；本地 PostgreSQL 已执行 `alembic upgrade head`。

### 验证情况

- 通过：在 `frontend/` 执行 `pnpm exec tsc --noEmit`。
- 通过：本地 PostgreSQL 已执行 `alembic upgrade head`，查询确认内置 AI 管家有 7 条预设问题。
- 待执行：浏览器端验证头像上传、保存后缓存同步、两类欢迎区和预览入口。

### 遗留问题

- 当前预览不能发送真实消息；需待模型、会话与工具能力接入后新增受控的预览会话接口。

## 2026-07-24：更正 UIW 单栏配置

### 任务目标

按 UIW 组件原生配置固定单栏编辑模式，避免将默认双栏布局误判为不可关闭。

### 实现内容

- 恢复 `@uiw/react-md-editor/nohighlight` 编辑器本体，设置受控 `preview="edit"` 作为编辑态。
- 编辑区只配置设计图要求的 Markdown 命令；不添加 `codeLive`，因此用户无法进入双栏模式。
- 自定义预览按钮只在 `edit` 和 `preview` 间切换，预览内容和编辑内容仍使用同一表单值。
- 为中栏的 `Form.Item`、表单控制容器和编辑器壳显式设置 `width: 100%`，修正其收缩为工具栏内容宽度后导致预览/帮助按钮被挤出的布局问题。
- 为自定义帮助和预览命令补充 `keyCommand`；UIW 工具栏会跳过缺少该字段的命令，因此这是按钮未渲染的直接原因。
- 将 Ant Design 自动生成的 `.ant-form-item-row` 纳入中栏的宽高 flex 链路；它是 `Form.Item` 的直接子元素，未拉伸会使编辑器只占用 row 的内容宽度并在右侧留下空白。
- 将 UIW 工具栏的两组命令从 `space-between` 改为左对齐；`extraCommands`（帮助、预览）应紧跟表格命令，而不是被推到工具栏最右侧。
- 标题工具使用 UIW 的 `group([heading1, …, heading6])`，而非单个 `heading` 命令；前者才会显示可选择 1–6 级的标题菜单。
- 覆盖标题菜单项的默认“包裹选区”执行逻辑，改为替换当前行已存在的 `#` 前缀，防止重复选择标题级别时不断叠加井号。

### 主要文件

- `frontend/src/features/agents/components/SystemPromptEditor.tsx`：UIW 单栏编辑器配置、工具栏命令和预览切换。
- `frontend/src/style.css`：UIW 编辑态和预览态的全高样式。
- `docs/DECISIONS.md`、`docs/features/agent-knowledge-platform/*`、`docs/PROJECT_STATUS.md`：更正技术方案。

### 技术方案

UIW 的 `preview="edit"` 原生将输入区宽度设为 100%、预览区宽度设为 0；预览时反向设置。通过只传入指定命令和自定义预览命令，避免默认的三种模式切换按钮暴露双栏模式。

### 接口或数据变化

无。

### 验证情况

- 通过：`pnpm exec tsc --noEmit`。
- 通过：`git diff --check`。
- 待执行：浏览器人工验证单栏宽度、文本选中、预览往返和保存回填。

### 遗留问题

- 上次 `pnpm build` 在本机命令超时前未完成，不作为通过记录。

## 2026-07-24：提示词编辑器单栏重构

### 任务目标

消除提示词编辑器默认双栏造成的右侧空白区域，使编辑和预览都在中栏同一编辑区域全宽显示。

### 实现内容

- 移除 `@uiw/react-md-editor` 的完整编辑器外壳，避免继续用 CSS 覆盖其输入/预览双栏布局。
- 新增原生受控 `textarea` 和自定义工具栏，所有 Markdown 插入操作直接更新既有 `systemPrompt` 表单值。
- 保留 `@uiw/react-md-editor` 的 Markdown 渲染组件；预览状态在同一内容容器中替换文本框，并可以切回编辑且不丢失内容。

### 主要文件

- `frontend/src/features/agents/components/SystemPromptEditor.tsx`：单栏编辑、Markdown 命令、帮助弹窗和同区预览。
- `frontend/src/style.css`：全宽全高编辑区和工具栏样式。
- `docs/DECISIONS.md`、`docs/features/agent-knowledge-platform/*`、`docs/PROJECT_STATUS.md`：更正技术方案与验证状态。

### 技术方案

`@uiw/react-md-editor` 的完整布局内置输入/预览两列，不适合设计图的单栏编辑体验。将编辑职责收回项目组件，依赖仅用于 Markdown 渲染，从布局上消除空白预览列。

### 接口或数据变化

无。继续使用 `systemPrompt` 字符串和既有 8000 字符限制。

### 验证情况

- 通过：`pnpm exec tsc --noEmit`。
- 待执行：浏览器人工验证单栏全宽、文本选中、工具栏插入、预览往返、保存后回填。

### 遗留问题

- 需要用户在当前浏览器页面刷新后进行视觉和交互复验；在未完成该验证前，不能标记为已验收。

## 2026-07-24：Markdown 编辑器交互与布局修正

### 任务目标

修正 Markdown 编辑器与设计图不一致的尺寸，以及文本选中、预览模式无法返回编辑的问题。

### 实现内容

- 切换到 `@uiw/react-md-editor/nohighlight` 并关闭高亮层，避免选中时文本层和高亮层重叠显示。
- 将预览改为受控状态切换：编辑时显示预览按钮，预览时显示返回编辑按钮，编辑内容始终保留在同一受控值中。
- 为编辑器增加全宽、全高 flex 容器，放大工具栏点击区域和图标，使中栏编辑区填满可用空间。

### 主要文件

- `frontend/src/features/agents/components/SystemPromptEditor.tsx`：无高亮编辑器、可逆预览切换。
- `frontend/src/style.css`：编辑器全高布局和工具栏尺寸。
- `docs/features/agent-knowledge-platform/CHANGELOG.md`、`docs/PROJECT_STATUS.md`：记录实现修正与待验证项。

### 技术方案

保留 Markdown 原始字符串为唯一表单值；预览只切换渲染视图，不改变内容。无高亮构建移除编辑层的语法高亮叠加，以保证浏览器原生选区稳定显示。

### 接口或数据变化

无。未修改依赖、接口、数据库或迁移。

### 验证情况

- 通过：`pnpm exec tsc --noEmit`。
- 未执行：浏览器人工验收；需验证选中文本、预览后返回编辑、编辑区全高以及工具栏尺寸。

### 遗留问题

- 无代码级阻塞；需依据浏览器截图继续进行像素级对比。

### 补充更正

- 浏览器截图确认首轮 flex 调整没有覆盖编辑器内部默认的输入区 `50%` 宽度。现已通过编辑/预览状态类显式控制输入区和预览区宽度，避免再次依赖库内部模式类；`pnpm exec tsc --noEmit` 已通过，仍待浏览器复验。
- 浏览器截图继续确认高度链未建立：工作台原先的 `height: 100%` 没有可靠视口基准，编辑器的百分比高度退化为内容高度。现将工作台设为 `100dvh`，内容网格和表单/编辑器容器按剩余高度拉伸；`pnpm exec tsc --noEmit` 已通过，仍待浏览器复验。
- DevTools 尺寸检查确认 textarea 实际仅为 `382 × 44`，且编辑态仍保留预览列。现将编辑器内容区扣除工具栏高度，强制 `.w-md-editor-area`、`.w-md-editor-text` 与 textarea 继承 100% 高度；编辑态隐藏预览列、预览态隐藏输入区。`pnpm exec tsc --noEmit` 已通过，仍待浏览器复验。

## 2026-07-24：完整 Markdown 提示词编辑器

### 任务目标

按用户确认的设计图，将智能体配置页中栏的普通系统提示词文本框替换为带完整 Markdown 工具栏和预览的编辑器。

### 实现内容

- 新增 `@uiw/react-md-editor@4.1.1`，使用其原生 Markdown 编辑、表格与预览命令。
- 新增 `SystemPromptEditor` 组件，提供加粗、斜体、标题、引用、无序列表、有序列表、代码、表格、帮助和预览。
- 帮助按钮改为站内中文 Markdown 语法弹窗；编辑值继续通过 Ant Design 表单保存为既有 `systemPrompt` 字符串，并限制为 8000 字符。
- 更新工作台样式，使编辑器占满中栏可用高度并保持设计图的浅色工具栏与无边框编辑区。

### 主要文件

- `frontend/src/features/agents/components/SystemPromptEditor.tsx`：Markdown 编辑器、工具栏与语法帮助弹窗。
- `frontend/src/pages/AgentEditorPage.tsx`：将 `systemPrompt` 表单控件替换为独立编辑器组件。
- `frontend/src/style.css`：工作台编辑器布局、工具栏和帮助弹窗样式。
- `frontend/package.json`、`frontend/pnpm-lock.yaml`：记录新增生产依赖。
- `docs/features/agent-knowledge-platform/*`、`docs/DECISIONS.md`、`docs/PROJECT_STATUS.md`：同步已确认需求、技术决策、状态和验收条件。

### 技术方案

采用基于 textarea 的 React Markdown 编辑器，而不引入完整代码编辑器内核；使用组件的受控 `value/onChange` 契约与 Ant Design `Form.Item` 集成，避免改变已有 API 和数据结构。

### 接口或数据变化

无。复用 `PATCH /api/agents/{agentId}` 的 `systemPrompt` 字段；未修改数据库或迁移。

### 验证情况

- 通过：`pnpm exec tsc --noEmit`。
- Vite 已输出成功的生产构建产物（未压缩主 JS 约 2.13 MB），但命令宿主在输出完成后超时回收；不能将该次执行记为完整通过。
- 未执行：浏览器人工验收、工具栏命令和保存回填的端到端测试。

### 遗留问题

- 新增编辑器使主包显著增大；后续应按路由懒加载编辑器并评估是否使用无高亮构建。
- 仍需在浏览器中验证各工具按钮、帮助弹窗、预览切换、8000 字符上限及保存后回填。

## 2026-07-24：智能体三栏搭建工作台

### 任务目标

将原有卡片式编辑表单调整为“配置 / 提示词 / 预览”三栏工作台，并明确当前能力与后续知识库、联网能力的边界。

### 实现内容

- 编辑页提供预设问题、欢迎语、描述、上传入口和联网入口的可保存配置。
- 系统提示词在中栏独立编辑；右栏随表单变化实时预览固定头像式欢迎页、预设问题和输入入口。
- 保留已有 `PATCH /api/agents/{id}` 契约；保存后以服务端返回值重新初始化表单和预览。
- 明确不实现嵌入网站与卡片式头像布局；绑定知识集区域仅说明后续依赖，不提供无后端支持的选择控件。
- 工作台路由隐藏应用级全局侧栏，仅保留工作台自身的配置栏，使三栏结构与确认原型一致。
- 预置问题调整为原型中的整行输入、红色删除圆钮、蓝色添加入口及说明文案；增加置灰的语音识别热词输入以明确其依赖未来语音能力。
- 左侧后续配置改为绑定知识集、上传入口、联网入口、登录要求和描述五个纵向区块；上传/联网使用“需要/不需要”单选，欢迎语、知识集和各入口均补充原型说明文案。
- 右侧预览将上传/联网入口改为清晰的文字按钮，随对应单选值即时显示或隐藏；实际文件上传和联网检索仍待后端能力接入。

### 主要文件

- `frontend/src/pages/AgentEditorPage.tsx`：三栏工作台、保存和实时预览。
- `frontend/src/style.css`：工作台布局与预览样式。
- `docs/features/agent-knowledge-platform/*`：同步需求、前端设计、接口与变更范围。

### 接口或数据变化

无新增接口或迁移；复用智能体更新接口。

### 验证情况

- 通过：`pnpm exec tsc --noEmit`。
- 未执行：浏览器视觉和交互人工验收；完整生产构建仍受本机依赖读取权限问题影响。

### 遗留问题

- 知识集绑定、实际文件上传/联网搜索、语音热词、公开访问和提示词助手等待各自后端能力与权限设计。

## 2026-07-24：智能体创建基础信息与私有头像

### 任务目标

将新建智能体调整为先填写基础信息，再进入完整配置页，并让用户上传的头像存入私有 MinIO。

### 实现内容

- 增加 `interaction_type` 数据列及文本/语音/数字人约束，首期创建固定为文本交互。
- 增加 multipart 基础创建接口、图片签名和大小校验、私有对象写入及经认证头像读取。
- 新增前端基础信息弹窗、客户端文件校验、创建后跳转编辑页和卡片头像 Blob 展示。
- 上传成功选择本地文件后，上传区域直接展示 object URL 图片预览与右上角选中标记；重新点击预览可替换头像。
- 创建确认按钮显式调用表单提交；未通过名称校验时给出提示，避免用户误以为点击没有响应。
- MinIO 认证失败时，头像创建接口改为返回 `503 OBJECT_STORAGE_UNAVAILABLE`，不再将底层 S3 异常堆栈暴露为未处理的 500。

### 接口或数据变化

- 新增 `POST /api/agents/bootstrap`、`GET /api/agents/{agentId}/avatar`。
- `agents` 新增 `interaction_type`，已本地执行 Alembic 升级。

### 验证情况

- 通过：Alembic `upgrade head`、前端 TypeScript `pnpm exec tsc --noEmit`、后端 `compileall`。
- 未执行：后端集成测试，当前虚拟环境未安装 pytest；完整 Vite 构建因本地 `highlight.js` 依赖读取权限被拒绝而未完成。

### 遗留问题

- 仍需在浏览器中实际验证头像上传、私有头像读取和创建后跳转。

## 2026-07-24：认证刷新中断误登出修复

### 任务目标

修复 Vite 热更新或网络中断刷新令牌时，前端错误清除本地会话并跳转登录页的问题。

### 实现内容

- 新增明确的认证拒绝判断：仅缺少刷新令牌，或服务端返回 401/403 时清除本地会话。
- 定时刷新和应用启动认证恢复遇到网络错误、请求取消或热更新中断时保留 token 与当前登录状态。
- 整页重载期间使用已保存的用户摘要作为路由守卫的临时身份，直到服务端明确拒绝凭证。

### 主要文件

- `frontend/src/lib/auth.ts`：认证拒绝类型、判断函数和用户摘要读取。
- `frontend/src/App.tsx`：启动恢复、定时刷新与路由守卫使用认证用户的策略。

### 技术方案

将“请求失败”与“凭证已失效”区分处理。前者可能由 HMR 重载、浏览器取消或临时网络问题引起，不能作为删除会话的依据；后者才触发登出。

### 接口或数据变化

无。继续使用既有认证接口和浏览器存储键。

### 验证情况

- 通过：`frontend/` 中 `pnpm build`。
- 未执行：浏览器中主动中断刷新请求的自动化测试；需在 Vite 开发服务器中人工验证 HMR 期间不会跳转登录页。

### 遗留问题

- 生产构建仍有超过 500 kB 的代码块警告，后续可按路由懒加载处理。

## 2026-07-24：智能体列表设计稿视觉还原

### 任务目标

根据用户提供的智能体列表设计稿，重构此前功能优先版本的页面视觉，不改变智能体、默认打开、删除或聊天跳转的既有规则。

### 实现内容

- 重构顶部横幅、分类栏、卡片网格、卡片标签和底部编辑信息，使布局密度与设计稿对齐。
- 调整左侧侧栏宽度和导航节奏，并补齐设计稿中的自动化任务展示项。
- 原设计插画和头像资源暂未提供；以可替换的本地 CSS 占位图形维持相同的空间结构和视觉层级。
- 根据后续视觉反馈，缩小横幅标题、说明、新建按钮和卡片内部字号；随后确认需要收紧的是顶部“新建智能体”横幅，将其高度从 144px 调整为 112px，列表卡片保持 158px。
- 补充可点击分类筛选：官方筛选只显示内置 AI 管家，现有会话智能体归入文本会话；数字人与语音筛选在尚无对应数据时展示空状态。网格改为不拉伸的最大 496px 卡片宽度，操作菜单使用横向省略号。
- 根据浏览器实际显示效果，将卡片网格最大宽度进一步收紧至 330px，并在分类栏与卡片网格之间增加 16px 间距，避免筛选标签紧贴卡片。

### 主要文件

- `frontend/src/pages/AgentListPage.tsx`：智能体列表页面的横幅、分类栏与网格结构。
- `frontend/src/features/agents/components/AgentCard.tsx`：卡片内容、标签、编辑信息和操作菜单布局。
- `frontend/src/layouts/AppLayout.tsx`、`frontend/src/style.css`：侧栏和页面级视觉规则。

### 技术方案

保留真实 API 列表、默认排序和操作菜单，仅替换展示组件与 CSS。头像与横幅插画隔离为视觉位，避免未来获取原 SVG 后牵连业务数据或路由逻辑。

### 接口或数据变化

无。未新增依赖、后端接口或数据库变更。

### 验证情况

- 通过：`frontend/` 中 `pnpm build`。
- 未执行：浏览器截图与设计稿的像素级人工比对；原设计插画和头像资源未提供。

### 遗留问题

- 后续取得原始 SVG 或头像资源后，需替换当前占位图形并完成最终视觉验收。

## 2026-07-24：智能体管理前后端联调

### 任务目标

实现个人智能体的列表、创建、编辑、默认打开、删除和聊天切换，并让内置 AI 管家可重新作为默认打开对象。

### 实现内容

- 新增智能体列表页、创建/编辑表单和指定智能体聊天路由；聊天页面复用既有会话与消息回显链路。
- 左侧“我的智能体”改为真实数据：默认项置顶，AI 管家与其他个人智能体按规则展示。
- 卡片三点菜单支持个人智能体设默认、编辑、删除；AI 管家仅支持恢复默认打开。
- 新增 `allow_network_access` 数据库字段、API 契约和聊天输入区显示逻辑；实际联网仍未调用外部服务。

### 主要文件

- `frontend/src/pages/AgentListPage.tsx`、`AgentEditorPage.tsx`：智能体管理页面与表单。
- `frontend/src/pages/ChatPage.tsx`、`layouts/AppLayout.tsx`：指定智能体聊天复用与动态侧栏。
- `frontend/src/api/agents.ts`、`frontend/src/features/agents/`：智能体 API、查询键、查询 Hook 与卡片组件。
- `backend/migrations/versions/20260724_0004_agent_network_access.py`：联网入口显示配置迁移。
- `backend/schemas/agents.py`、`repositories/agents.py`、`services/agents.py`：配置字段的读写与响应映射。

### 技术方案

默认智能体继续由服务端入口解析结果作为唯一事实来源。AI 管家“设为默认”调用清空个人默认配置的既有接口，从而保持数据库只保存个人默认智能体、为空即回退 AI 管家的既定模型。删除维持软删除，前端不暴露已删除智能体及其会话入口。

### 接口或数据变化

- 新增并已执行 Alembic 迁移 `20260724_0004`，为 `agents` 添加非空布尔字段 `allow_network_access`，已有记录默认 `false`。
- `POST/PATCH/GET /api/agents` 的请求或响应增加 `allowNetworkAccess`。
- 新增前端路由 `/app/chat/agents/:agentId`、`/app/agents/new`、`/app/agents/:agentId/edit`；未新增后端 HTTP 路由。

### 验证情况

- 通过：`backend/.venv/Scripts/python.exe -m unittest tests.test_agents_conversations_integration -v`，9 项真实 PostgreSQL 集成测试通过。
- 通过：`backend/.venv/Scripts/python.exe -m compileall -q .`。
- 通过：`frontend/` 中 `pnpm build`；首次沙箱内构建因既有依赖读取权限失败，在获批的受限环境外重跑后通过。
- 未执行：浏览器人工端到端检查与像素级原型比对。

### 遗留问题

- 联网按钮目前仅控制显示并提示“功能暂未支持”；DeepSeek、检索和 SSE 尚未接入。
- 生产构建仍有超过 500 kB 的代码块警告，后续可按路由懒加载处理。

## 2026-07-23：PostgreSQL 连接池优化

### 任务目标

定位并消除受保护 API 每次请求反复建立 PostgreSQL 连接造成的明显等待。

### 实现内容

- 新增 `psycopg_pool`，在 FastAPI 生命周期启动时创建共享连接池、关闭时释放。
- 保持 Repository 既有 `with get_connection()` 调用形态：现在它借用并归还池中连接，不再执行新的 TCP/数据库认证连接。
- 新增 `DATABASE_POOL_MIN_SIZE`、`DATABASE_POOL_MAX_SIZE` 配置，默认分别为 1、10，并校验最大值不小于最小值。
- 保留面向独立脚本和测试的延迟初始化兜底；Alembic 不接入 Web API 连接池。

### 主要文件

- `backend/database.py`：共享连接池生命周期和连接借还上下文。
- `backend/main.py`：FastAPI `lifespan` 初始化/关闭连接池。
- `backend/config.py`、`backend/.env.example`：连接池配置与校验。
- `backend/requirements.txt`：新增 `psycopg_pool` 依赖。

### 技术方案

数据库连接是昂贵资源，应在进程生命周期内复用而不是按 Repository 调用新建。池大小采用本地开发保守默认值，避免单进程占用过多 PostgreSQL 连接；迁移是短时管理任务，继续使用 Alembic 自己的 `NullPool`。

### 接口或数据变化

- 无 HTTP 接口、请求响应或数据库 schema 变化，无需 Alembic 迁移。
- 新增环境变量 `DATABASE_POOL_MIN_SIZE`、`DATABASE_POOL_MAX_SIZE`。

### 验证情况

- 直接测量：反复新建 PostgreSQL 连接平均约 605ms；连接池借还约 0.02ms；同一已连接会话的简单查询约 70–230ms。
- 通过：Python 静态编译。
- 通过：认证与智能体/会话真实 PostgreSQL 集成测试共 13 项，耗时约 73 秒。

### 遗留问题

- 连接池不减少 SQL 查询本身的往返或重复查询。若仍需优化，应先记录每个接口的 SQL 数量和耗时，再处理查询合并、索引或 PostgreSQL/容器网络延迟。

## 2026-07-23：聊天会话延迟创建与消息回显联调

### 任务目标

将“点击新会话即创建数据库记录”改为常见聊天产品的延迟创建方式，避免慢请求和无消息的历史记录。

### 实现内容

- 新会话按钮仅清空前端当前会话状态和输入内容，不再调用创建会话接口。
- 新增统一消息入口 `POST /api/conversations/messages`：无 `conversationId` 时在一个事务内创建会话、保存用户消息和阶段 2 回显助手消息；有 ID 时继续既有会话。
- 新增 Ant Design X `Bubble.List` 消息展示；首次发送成功后才选择响应会话并刷新右侧历史记录。
- 发送接口同时校验会话归属和请求中的智能体 ID，防止将其他智能体会话作为当前智能体继续写入。
- 发送采用乐观更新：立即展示用户消息和 Ant Design X 加载气泡；服务端响应后替换为真实消息，失败时恢复输入内容。
- 发送成功后直接更新 React Query 会话详情缓存，只后台刷新会话列表；避免首次发送或旧会话续聊时额外读取完整会话历史。
- 打开未缓存的历史会话时展示左右交错的消息骨架屏；首次发送与继续发送仍优先展示即时消息和加载气泡，不误显示历史加载状态。

### 主要文件

- `backend/schemas/conversations.py`、`backend/routers/conversations.py`：延迟发送请求模型和受保护接口。
- `backend/services/conversations.py`、`backend/repositories/conversations.py`：事务式首次发送及会话/智能体归属校验。
- `frontend/src/api/chat.ts`、`frontend/src/features/chat/hooks/useSendMessage.ts`：消息 API 和 React Query 写操作。
- `frontend/src/pages/AiManagerPage.tsx`、`frontend/src/features/chat/components/ChatMessageList.tsx`、`ChatComposer.tsx`：空白会话状态、消息渲染和发送联调。

### 技术方案

空白会话只存在于页面状态。首条消息提交时由后端在一个事务中完成创建和持久化，避免创建成功但消息失败的孤立会话。当前助手消息仍是阶段 2 回显；后续 SSE 模型接口沿用“首次发送时创建”的契约，不恢复点击即创建。

### 接口或数据变化

- 新增 `POST /api/conversations/messages`，请求包含 `agentId`、`content` 和可选 `conversationId`。
- 未新增数据库迁移；既有 `is_draft` 字段仅保留给兼容接口和历史数据。

### 验证情况

- 通过：新增的真实 PostgreSQL 集成测试，确认首次消息前列表为空，发送后创建会话并按用户、助手顺序保存消息；也确认不能使用另一智能体 ID 向既有会话写入。
- 通过：`pnpm exec tsc --noEmit`。
- 通过：原有 7 项完整智能体/会话集成套件（143 秒）；新增的跨智能体拒绝用例单独通过。

### 遗留问题

- 当前响应是一次性 JSON 回显，不是真实 SSE 或模型答案；模型接入后需在同一延迟创建语义下实现流式 token、取消和失败状态。

## 2026-07-23：AI 管家聊天页步骤 1 与组件库升级

### 任务目标

根据确认的 AI 管家原型实现欢迎态和历史记录的只读联调，并使用最新版 Ant Design X 构建聊天交互区域。

### 实现内容

- 将 Ant Design 升级至 6.5.1，新增 Ant Design X 2.8.0 与 Markdown 2.8.0；移除不兼容的 Pro Components，以原生 `Card` 保持认证页登录卡片。
- 新增聊天领域类型、API 模块和 React Query Hook，调用 `GET /api/chat/entry` 与 `GET /api/conversations`。
- 将空 `AiManagerPage` 拆分为欢迎区、输入区和历史记录抽屉；欢迎区使用 Ant Design X `Welcome`、`Prompts`，输入区使用 `Sender`。
- 实现 AI 管家“全部资料”默认选中、历史记录默认收起、推荐问题预填输入框，以及未实现入口的明确提示；不展示新建文档卡片。

### 主要文件

- `frontend/src/api/chat.ts`、`frontend/src/types/chat.ts`：聊天 API 契约与领域类型。
- `frontend/src/features/chat/`：聊天查询 Hook、欢迎区、输入区和历史记录抽屉组件。
- `frontend/src/pages/AiManagerPage.tsx`：页面组合、加载/失败状态和历史抽屉开关。
- `frontend/src/pages/AuthPage.tsx`：用 Ant Design 原生 `Card` 替代已移除的 ProCard。
- `frontend/package.json`、`frontend/pnpm-lock.yaml`：统一组件库版本。

### 技术方案

页面只组合状态，查询 Hook 管理服务器数据，API 模块统一添加 Bearer 令牌，展示组件不直接发 HTTP 请求。步骤 1 不提前调用创建会话或发送消息接口，所有尚未实现的按钮均显示清晰提示；步骤 2 再接入写操作。

### 接口或数据变化

- 前端开始消费既有 `GET /api/chat/entry` 与 `GET /api/conversations`。
- 未新增后端接口、数据库迁移或模型/RAG 调用。
- 前端依赖升级并移除 `@ant-design/pro-components`。

### 验证情况

- 通过：`pnpm exec tsc --noEmit`。
- 通过：提升权限后的 `pnpm build`，TypeScript 与 Vite 生产构建成功。
- 风险：普通沙箱构建无法读取 Markdown 的语法高亮依赖，但提升权限构建成功；这属于本机文件访问限制，不是代码或依赖兼容错误。

### 遗留问题

- 尚未实现创建会话、选中会话、读取历史消息和发送回显消息，属于聊天页步骤 2。
- 生产包超过 500 kB，后续通过路由级懒加载改善。

## 2026-07-23：阶段 2 消息写入与回显闭环

### 任务目标

在不接入模型、RAG 或 SSE 的前提下，验证聊天消息的持久化、会话所有权、标题更新和顺序读取链路。

### 实现内容

- 新增 `POST /api/conversations/{conversationId}/messages`，接收 1–4000 字符的非空消息，去除首尾空白后处理。
- 在同一 PostgreSQL 事务内验证会话归属和智能体活跃状态，写入 `user` 消息、明确标识为回显的 `assistant` 消息，并更新会话标题/时间。
- 首次未命名会话使用用户首条消息前 50 字作为标题；助手回显的创建时间紧随用户消息，保证现有读取排序稳定呈现“用户在前、助手在后”。
- 扩展集成测试，覆盖消息顺序、标题生成、空白输入拒绝和其他用户发送消息的越权拒绝。

### 主要文件

- `backend/schemas/conversations.py`：消息请求与回显响应模型、空白内容校验。
- `backend/repositories/conversations.py`：事务内消息写入、标题/时间更新和活跃会话查询。
- `backend/services/conversations.py`：消息用例编排和资源不存在映射。
- `backend/routers/conversations.py`：受保护的消息回显 HTTP 接口。
- `backend/tests/test_agents_conversations_integration.py`：消息持久化与越权集成测试。
- `docs/features/agent-knowledge-platform/API_DESIGN.md`：新增 API-007A 的阶段边界说明。

### 技术方案

回显接口与未来 SSE 模型接口并存：前者只验证数据持久化，不承担模型调用；后者仍按既有 API-008 设计在模型/RAG 阶段实现。两条消息和会话更新时间放在一个事务中，避免局部成功。通过不同的微秒级创建时间维持消息逻辑顺序，不引入额外且没有业务含义的排序字段。

### 接口或数据变化

- 新增 `POST /api/conversations/{conversationId}/messages`，成功响应为更新后的会话、用户消息和回显助手消息。
- 无数据库迁移；复用 `messages`、`conversations` 表。
- 未新增依赖；未实现模型调用、检索、SSE 或取消生成。

### 验证情况

- 通过：Python 静态编译。
- 通过：消息回显/顺序/空白校验与跨用户越权拒绝的真实 PostgreSQL 集成测试。
- 通过：完整智能体/会话集成测试共 5 项，以及既有认证集成测试 5 项。

### 遗留问题

- 回显助手消息不是 AI 回答，不能用于模型功能验收。
- 取消生成、流式 token、失败状态和引用持久化仍待阶段 4 的模型/RAG 工作流。

## 2026-07-23：阶段 2 智能体、默认打开与会话后端基础

### 任务目标

实现不依赖模型或知识库的智能体和会话持久化基础，使默认打开、资源所有权、软删除和会话侧栏范围可被后端独立验证。

### 实现内容

- 新增 Alembic 迁移 `20260723_0002`，创建 `agents`、`user_preferences`、`agent_preset_questions`、`conversations` 和 `messages`，并写入固定 UUID 的内置 AI 管家种子记录。
- 新增 Repository、Service、Schema 和 Router 分层，实现个人智能体 CRUD、软删除、默认设置与清空、聊天入口解析、会话创建/读取/按智能体列表查询。
- 所有自有资源查询强制带当前认证用户 ID；内置智能体使用 `kind=builtin`，后端拒绝编辑/删除；删除默认个人智能体前必须先清空默认设置。
- 资料范围字段和 `agent_knowledge_scopes` 未在本阶段实现，等待阶段 3 创建 `knowledge_nodes`。

### 主要文件

- `backend/migrations/versions/20260723_0002_agents_conversations.py`：阶段 2 业务表、约束、索引和内置种子迁移。
- `backend/repositories/agents.py`、`backend/repositories/conversations.py`：集中 PostgreSQL 访问与所有权过滤。
- `backend/services/agents.py`、`backend/services/conversations.py`、`backend/services/errors.py`：业务规则和统一领域错误。
- `backend/routers/agents.py`、`backend/routers/conversations.py`：受保护 API 入口。
- `backend/tests/test_agents_conversations_integration.py`：真实 PostgreSQL 的默认回退、不可变、软删除、用户隔离和会话范围测试。
- `docs/features/agent-knowledge-platform/`、`docs/PROJECT_STATUS.md`、`docs/ARCHITECTURE.md`、`docs/DECISIONS.md`、`docs/QUESTIONS.md`：同步确认的接口、数据模型、决策和进度。

### 技术方案

使用固定 UUID 而非字符串哨兵表示内置 AI 管家，使所有智能体 ID 都可作为 UUID 外键使用；以 `kind` 区分内置和个人类型，但不把权限交给前端。将清空默认设置设计为独立接口，避免“删除智能体”同时隐式更改用户偏好。路由层只绑定 HTTP 和认证，服务层处理业务规则，仓储层集中 SQL，便于隔离测试和后续扩展消息生成流程。

### 接口或数据变化

- 新增 `GET /api/chat/entry`、`GET/POST/PATCH/DELETE /api/agents`、`PUT /api/agents/{agentId}/default`、`DELETE /api/agents/default`、`GET/POST /api/conversations`、`GET /api/conversations/{conversationId}`。
- 新增阶段 2 数据库迁移，已在本地 PostgreSQL 执行 `alembic upgrade head`，当前版本为 `20260723_0002`。
- 未新增依赖；未实现消息发送、SSE、模型、RAG 或知识库资料范围。

### 验证情况

- 通过：`python -m compileall -q main.py routers schemas services repositories migrations tests`。
- 通过：`alembic upgrade head` 和 `alembic current`，当前版本 `20260723_0002 (head)`。
- 通过：4 个智能体/会话真实 PostgreSQL 集成测试，覆盖内置默认、内置不可删除、更新、默认清空、软删除、用户隔离和按智能体会话过滤。
- 通过：既有 5 个认证集成测试全部通过。
- 通过：`git diff --check`。
- 警告：测试仍输出既有 `TestClient/httpx` 弃用提示；本次未升级依赖。

### 遗留问题

- 会话列表暂未提供 cursor 翻页，阶段 2 前端联调前需要补齐。
- 消息写入/回显、SSE 与前端页面仍未实现；知识库资料范围需等待阶段 3。

## 2026-07-22：认证服务自动化集成测试

### 任务目标

将已完成的认证手工验证固化为可重复执行的测试，覆盖令牌轮换、撤销和会话过期等核心安全行为，为阶段 2 的受保护业务接口提供回归安全网。

### 实现内容

- 新增 `backend/tests/test_auth_integration.py`，使用 Python 标准库 `unittest` 与 FastAPI `TestClient` 执行真实 PostgreSQL 集成测试。
- 覆盖重复注册拒绝、错误密码拒绝、刷新令牌轮换与旧令牌重放拒绝、登出后的访问/刷新令牌失效，以及过期会话拒绝。
- 每个用例生成唯一测试邮箱，并在结束后删除该测试用户的会话、用户记录和撤销令牌，避免污染开发数据库。

### 主要文件

- `backend/tests/test_auth_integration.py`：认证路由、服务、JWT 与 PostgreSQL 的集成测试。
- `backend/tests/__init__.py`：测试包标记，支持模块化执行。
- `docs/PROJECT_STATUS.md`、`docs/ARCHITECTURE.md`：同步认证验证状态和测试模块职责。

### 技术方案

使用 `unittest` 避免为当前有限的测试集引入额外依赖。测试不模拟数据库连接，因为令牌轮换、会话撤销和过期判断都依赖真实 PostgreSQL 状态；通过唯一标识和精确清理实现与本地开发数据隔离。

### 接口或数据变化

无新增 HTTP API、业务表或依赖。测试运行期间临时写入并清理认证相关记录。

### 验证情况

- 通过：`python -m unittest tests.test_auth_integration -v`，5 个测试全部通过。
- 通过：测试后确认无残留 `auth-test-*` 用户。
- 警告：FastAPI 依赖中的 `TestClient` 输出上游弃用提示；本次未升级依赖，测试结果不受影响。

### 遗留问题

- 当前测试使用本地开发 PostgreSQL；后续 CI 应配置隔离测试数据库，避免共享环境并发执行。

## 2026-07-22：Linux 标准 RQ Worker 构建与执行验证

### 任务目标

完成 Docker Linux Worker 镜像构建，并验证由本机投递、容器内标准 RQ Worker 执行的任务链路。

### 实现内容

- 在 Docker Desktop 的用户级 daemon 配置中保留原有构建设置并添加一个本地开发镜像加速器，重启 Docker Engine 后确认配置生效。
- 成功拉取 `python:3.12-slim` 并构建 Worker 镜像；恢复 Redis、MinIO 和 Worker 容器。
- 从 Windows 本机运行验证脚本投递任务，Worker 容器日志确认标准 RQ Worker 成功执行；任务结果校验执行平台为 Linux。
- 清理本次探针任务记录，未修改业务队列、业务文件或数据库数据。

### 主要文件

- `backend/Dockerfile.worker`、`backend/.dockerignore`：Worker 镜像定义与构建上下文安全边界。
- `docker-compose.infrastructure.yml`：Redis、MinIO 与 Linux Worker 的本地编排。
- `backend/workers/runner.py`、`backend/workers/tasks.py`、`backend/scripts/verify_infrastructure.py`：标准 Worker 入口与 Linux 执行验证。

### 技术方案

Docker Desktop 的 Linux 容器支持 RQ 标准 Worker 所需的 Unix 子进程模型。镜像加速器仅作用于本机 Docker 拉取，不写入项目源码或文档中的敏感凭据；生产部署仍应使用受控镜像仓库和镜像摘要管理。

### 接口或数据变化

无新增 HTTP API、业务表或生产依赖。新增本机 Docker 镜像缓存、Worker 容器及开发镜像加速器配置。

### 验证情况

- 通过：Docker Engine 已识别配置的 registry mirror，`python:3.12-slim` 拉取成功。
- 通过：Worker 镜像构建，Redis、MinIO、Worker 容器运行。
- 通过：验证脚本通过；Worker 日志确认标准 RQ Worker 在 Linux 容器中成功执行探针任务。
- 通过：探针任务记录已清理，队列无待处理探针任务。

### 遗留问题

- `backend/.env` 仍需由开发者持久化 Redis 与 MinIO 的本地开发配置，避免后续脚本依赖临时环境变量。

## 2026-07-22：Linux 标准 RQ Worker 容器化尝试

### 任务目标

将 RQ Worker 从 Windows 本地兼容模式调整为 Docker Linux 容器中的标准 Worker，使其运行模型与后续部署保持一致。

### 实现内容

- 新增 `backend/Dockerfile.worker` 和 `.dockerignore`，镜像安装现有后端依赖且不复制本机 `.env`。
- 为 Compose 新增 `worker` 服务，容器内通过 `redis`、`minio` 服务名访问基础设施，并挂载后端源码用于本地开发。
- 移除 `SimpleWorker` 分支；Worker 入口现在统一使用标准 RQ `Worker`。
- 测试任务增加 Linux 平台标识，验证脚本只有在任务由 Linux 容器执行时才通过。

### 主要文件

- `backend/Dockerfile.worker`：标准 Worker 镜像定义。
- `backend/.dockerignore`：防止本机环境文件和虚拟环境进入镜像构建上下文。
- `docker-compose.infrastructure.yml`：新增 Worker 服务及容器内网络配置。
- `backend/workers/runner.py`、`backend/workers/tasks.py`、`backend/scripts/verify_infrastructure.py`：标准 Worker 运行与 Linux 执行结果验证。

### 技术方案

Docker Desktop 运行 Linux 容器，因此 RQ 标准 Worker 可以使用 Unix 子进程模型。FastAPI 仍可在 Windows 本机通过映射端口投递任务；Worker 在 Compose 网络内使用服务名访问 Redis 和 MinIO。后续 Worker 如需连接当前本机 PostgreSQL，必须显式使用 Docker Desktop 宿主机地址，不能使用容器内 `127.0.0.1`。

### 接口或数据变化

无新增 HTTP API、业务表或生产依赖。新增待构建的 Worker 镜像与 Compose 服务。

### 验证情况

- 通过：新增 Python 模块静态编译和 Compose 配置校验。
- 未通过：Docker 构建 `python:3.12-slim` 时无法连接 `auth.docker.io` 获取令牌，重试后同样失败；本地不存在可离线使用的 Python 基础镜像。
- 未执行：Linux 容器中的标准 Worker 任务执行验证；需在镜像成功构建后执行。

### 遗留问题

- 需恢复 Docker Hub 网络访问或在 Docker Desktop 配置可用的镜像加速器/代理后重试构建。

## 2026-07-22：Redis、MinIO 与 RQ Worker 本地联调

### 任务目标

完成第一阶段剩余的对象存储、任务队列与 Worker 可运行性验证，不引入文件解析、Embedding、模型调用或 RAG 业务代码。

### 实现内容

- 新增 `docker-compose.infrastructure.yml`，用 Docker Desktop 启动 Redis 7.4.2 与 MinIO，并使用命名数据卷保留本地开发数据。
- 新增无副作用的 RQ 测试任务、跨平台 Worker 进程入口和基础设施验证脚本。
- 验证 Redis `ping`、私有 Bucket 自动创建、测试文本写入/读取/删除，以及测试任务投递和执行。
- Windows 本地将 RQ Worker 切换为 `SimpleWorker`，避免标准 `Worker` 对 Unix 子进程模型的依赖；Linux 环境仍使用标准 Worker。
- 为避免覆盖现有数据库与 JWT 配置，本次仅在验证进程中注入本地 Redis/MinIO 配置；`backend/.env` 尚待开发者手动补齐相应变量。

### 主要文件

- `docker-compose.infrastructure.yml`：本地 Redis、MinIO 和数据卷配置。
- `backend/workers/tasks.py`：无副作用的 Worker 探针任务。
- `backend/workers/runner.py`：根据操作系统选择 RQ Worker 实现的进程入口。
- `backend/scripts/verify_infrastructure.py`：Redis、MinIO 与 RQ 的端到端基础设施验证。
- `docs/PROJECT_STATUS.md`、`docs/ARCHITECTURE.md`、`docs/DECISIONS.md`：同步真实运行状态和平台差异。

### 技术方案

Redis 只保存队列和任务状态，MinIO 保存原始大文件，PostgreSQL 继续负责关系数据和元数据。验证脚本对 MinIO 使用临时对象并立即删除，避免将测试文件误当作业务资料。Windows 使用 `SimpleWorker` 是本地兼容性措施，生产 Linux 仍保留隔离性更好的标准 RQ Worker。

### 接口或数据变化

未新增 HTTP API、业务表或生产依赖。Docker 新增本地 Redis/MinIO 容器、网络与命名数据卷；MinIO 创建了私有开发 Bucket。

### 验证情况

- 通过：Docker Compose 配置校验，Redis 容器健康，MinIO 容器运行。
- 通过：Redis `ping`、MinIO Bucket 创建与测试文件写读删除。
- 通过：RQ 测试任务返回“Worker 已运行”。
- 通过：对象存储配置缺失时明确列出 `OBJECT_STORAGE_ENDPOINT`、`OBJECT_STORAGE_ACCESS_KEY` 和 `OBJECT_STORAGE_SECRET_KEY`。
- 通过：新增 Python 模块静态编译。
- 未执行：浏览器端到端测试、真实文件解析、向量化、模型调用和 RAG 测试；均不属于第一阶段范围。

### 遗留问题

- 进入阶段 2 前仍需为认证服务补充自动化测试。
- 本地 MinIO 初始账号只限开发环境，后续部署必须替换为非默认凭据。

## 2026-07-22：认证基础设施真实集成验证

### 任务目标

验证本地 PostgreSQL 的认证表与 Alembic 认证基线迁移一致，并完成认证接口的真实数据库集成检查。

### 实现内容

- 检查本机 PostgreSQL 连接、现有认证表结构及 Alembic 版本状态。
- 确认旧认证表与 `20260720_0001` 迁移定义一致后，使用 `alembic stamp head` 将现有结构纳入版本管理，未重复创建表。
- 使用临时测试用户完成注册、登录、获取当前用户、刷新令牌、登出、撤销令牌拒绝及受保护聊天回显接口验证；测试结束后清理测试用户、会话和撤销令牌。

### 主要文件

- `docs/PROJECT_STATUS.md`：同步 PostgreSQL 验证结果、Redis/MinIO 联调阻塞和后续计划。
- `docs/DEVELOPMENT_LOG.md`：记录本次真实集成验证过程。

### 技术方案

对已存在但无 Alembic 版本记录的认证表，先逐字段比对迁移定义再执行 `stamp`，避免对已有表重复运行建表迁移。集成测试通过 FastAPI `TestClient` 调用真实 PostgreSQL，覆盖令牌轮换和撤销行为。

### 接口或数据变化

数据库新增 `alembic_version` 记录，值为 `20260720_0001`；认证业务表结构、API 契约和应用依赖均未修改。

### 验证情况

- 通过：Alembic 认证基线版本已记录为 `20260720_0001`。
- 通过：注册（201）、登录（200）、`/me`（200）、受保护 `/api/chat`（200）、刷新令牌（200）、登出（204）和已撤销访问令牌拒绝（401）。
- 未执行：Redis、MinIO、RQ Worker 与浏览器端到端测试；本机未发现 Redis/MinIO 服务且对象存储配置未填写。

### 遗留问题

- 需启动并配置 Redis、MinIO 后再验证对象存储和异步文档处理能力。

## 2026-07-20：阶段 1 数据库迁移与基础设施边界

### 任务目标

将认证表从 FastAPI 启动时直接执行的 DDL 迁移到版本化脚本，并为私有对象存储和后台任务建立独立适配边界。

### 实现内容

- 新增 Alembic 迁移环境和认证基线迁移。
- 移除应用启动时自动建表逻辑；服务启动不再隐式修改数据库结构。
- 集中补充 Redis、对象存储、DeepSeek 和 BGE 的环境变量定义。
- 新增 MinIO 和 RQ 的最小适配器；尚未投递真实文档任务。

### 主要文件

- `backend/migrations/`：数据库版本化迁移及旧认证数据库的安全接入说明。
- `backend/integrations/object_storage.py`：私有对象存储客户端创建边界。
- `backend/workers/queue.py`：文档处理队列创建边界。
- `backend/config.py`：集中、显式的运行配置。

### 技术方案

使用 Alembic 管理结构变更，保留 psycopg 作为业务 Repository 的数据库访问驱动；文件和异步任务均不由路由直接处理。

### 接口或数据变化

- 新增数据库迁移基线 `20260720_0001`，数据库须执行 `alembic upgrade head` 后才能运行 API。
- 未新增业务 API。

### 验证情况

- 新增依赖已在 `backend/.venv` 安装成功。
- `python -m compileall -q .` 通过。
- `alembic upgrade head --sql` 通过，已生成认证基线的 PostgreSQL DDL，但未对真实数据库执行。
- `alembic current` 已成功连接现有 PostgreSQL；修复了 Alembic 默认尝试使用 psycopg2 的兼容问题，改为显式使用项目已有的 psycopg 3 方言。
- FastAPI `/api/health` 测试和 RQ 队列对象构造测试通过；对象存储缺少配置时会明确列出缺失环境变量。
- Redis、MinIO 与真实 PostgreSQL 尚未运行，连通性和 Worker 执行仍待验证。

### 遗留问题

- 开发机未检测到 Docker；需要后续提供可用的 PostgreSQL/pgvector、Redis 和 MinIO 服务后执行联调。

## 2026-07-20：AI 管家会话侧栏规则修正

### 任务目标

根据用户纠正，移除 AI 管家显示其他智能体会话的规则，统一会话历史隔离边界。

### 实现内容

- 统一内置 AI 管家与自建智能体的会话侧栏规则：只展示当前智能体自身会话。
- 移除聊天入口返回会话范围、全局会话查询和来源智能体展示的设计。

### 主要文件

- `docs/features/agent-knowledge-platform/`：更新需求、前端、接口、数据、验收和变更设计。
- `docs/QUESTIONS.md`：同步最终确认的会话规则。

### 技术方案

会话列表统一使用当前用户和当前智能体作为查询条件，减少分支逻辑并避免 AI 管家成为跨智能体会话聚合入口。

### 接口或数据变化

设计中的 API-001 去除 `conversationScope`；会话列表统一按 `agent_id` 过滤。尚未实现接口或数据库迁移。

### 验证情况

- 已完成：需求、前端、接口、数据和验收文档一致性更新。
- 未执行：代码构建、接口、数据库或端到端测试；本次未修改运行代码。

### 遗留问题

- 无新增阻塞；后续实施必须将会话查询限制为当前用户和当前智能体。

## 2026-07-20：首期 AI 界面与 Embedding 技术选型确认

### 任务目标

锁定 AI 聊天界面组件库与知识库向量模型，消除前后端实施依赖中的两个关键待定项。

### 实现内容

- 确认聊天展示使用 Ant Design X 和 `@ant-design/x-markdown`，继续以自有 SSE API 管理会话数据流。
- 确认知识库向量由独立 Worker 本地运行 `BAAI/bge-m3` 生成，不使用云端 Embedding API。

### 主要文件

- `docs/features/agent-knowledge-platform/`：更新需求、前端、后端和变更设计。
- `docs/DECISIONS.md`、`docs/QUESTIONS.md`：同步已确认技术选型。

### 技术方案

Ant Design X 仅承担 AI 交互展示，避免与业务接口、鉴权和状态管理重叠；`bge-m3` 将本地计算与 DeepSeek 的聊天生成职责分离，向量只在 Worker 和 PostgreSQL/pgvector 内流转。

### 接口或数据变化

无已实现接口或数据变化。设计中 `document_chunks.embedding_model` 将记录 `bge-m3`。

### 验证情况

- 已完成：技术方案与功能设计文档同步检查。
- 未执行：依赖安装、模型下载、前端构建、本地向量生成或集成测试；本次未修改运行代码。

### 遗留问题

- 实施前锁定 DeepSeek 具体聊天模型、BGE 推理库、后台任务框架和数据库迁移工具版本。

## 2026-07-23：单智能体草稿会话约束

### 任务目标

防止同一智能体因重复点击“新会话”产生多个无消息、无标题的空白会话。

### 实现内容

- 为 `conversations` 新增 `is_draft` 字段和按用户、智能体生效的部分唯一索引。
- 重复创建空白会话时复用已有草稿并返回 `200 OK`；首次创建返回 `201 Created`。
- 首条消息写入时将会话从草稿标记为非草稿，之后允许创建下一条新会话。
- 迁移保留每组现有空白会话中最新的一条为草稿，避免历史重复数据阻塞唯一索引创建。

### 主要文件

- `backend/migrations/versions/20260723_0003_single_draft_conversation.py`：字段、历史数据整理和唯一索引迁移。
- `backend/repositories/conversations.py`：草稿会话的原子创建/复用和首条消息状态转换。
- `backend/services/conversations.py`、`backend/routers/conversations.py`：复用结果及 HTTP 状态码。
- `backend/tests/test_agents_conversations_integration.py`：重复创建与首条消息后再创建的集成测试。

### 接口或数据变化

- 新增数据库迁移 `20260723_0003`，已执行 `alembic upgrade head`。
- `POST /api/conversations` 在复用既有草稿时返回 `200 OK`，响应结构不变。

### 验证情况

- 通过：Alembic 已升级至 `20260723_0003`。
- 通过：`backend/.venv/Scripts/python.exe -m unittest tests.test_agents_conversations_integration -v`，6 项通过。

### 遗留问题

- 前端消息发送和历史消息渲染仍待下一步接入；该步骤将使草稿会话转为普通会话。

## 2026-07-23：聊天会话创建与历史选择联调

### 任务目标

将 AI 管家页的“新会话”和右侧历史会话列表从静态提示改为真实 API 调用，同时不提前实现消息发送和消息列表展示。

### 实现内容

- 新增会话创建和会话详情读取 API 封装。
- 使用 React Query Mutation 创建会话，并在成功后失效、刷新当前智能体的会话列表缓存。
- 页面本地保存已选会话 ID；选择历史记录时读取会话详情，右侧列表显示选中状态。
- 新建会话期间禁用对应按钮并显示加载状态；创建或详情请求失败时显示可理解的错误提示。

### 主要文件

- `frontend/src/api/chat.ts`：创建和读取单个会话的 HTTP 请求。
- `frontend/src/types/chat.ts`：会话详情与消息响应类型。
- `frontend/src/features/chat/hooks/useCreateConversation.ts`：创建会话和列表缓存失效。
- `frontend/src/features/chat/hooks/useConversationDetail.ts`：选中会话详情查询。
- `frontend/src/features/chat/components/ConversationHistoryDrawer.tsx`：创建状态、选中样式和选择回调。
- `frontend/src/pages/AiManagerPage.tsx`：组合页面本地状态与会话 API 行为。

### 接口或数据变化

无新增后端接口或数据库迁移。前端开始调用既有 `POST /api/conversations` 与 `GET /api/conversations/{conversationId}`。

### 验证情况

- 通过：`pnpm exec tsc --noEmit`。
- 通过：`pnpm build`。
- 通过：`backend/.venv/Scripts/python.exe -m unittest tests.test_agents_conversations_integration -v`，5 项通过。

### 遗留问题

- 已读取的历史会话详情暂未渲染为消息列表；该展示与发送回显将作为下一步完成。

## 2026-07-23：认证刷新并发保护

### 任务目标

修复刷新令牌请求返回 401 时可能错误清除有效登录状态的问题。

### 实现内容

- 同一浏览器标签页内的多个刷新触发共用同一个进行中的请求，避免 refresh token 轮换产生竞争。
- 刷新失败时，如浏览器存储中的 refresh token 已被其他标签页更新，保留该更新后的会话而不是退出登录。
- 仅当 `/api/auth/me` 明确返回 401 时才尝试刷新；网络失败和服务端错误不再被误判为登录失效。

### 主要文件

- `frontend/src/lib/auth.ts`：刷新请求单飞控制和跨标签页 token 更新识别。
- `frontend/src/App.tsx`：限制自动刷新触发条件为认证 401。

### 接口或数据变化

无。继续使用既有 `POST /api/auth/refresh` 接口。

### 验证情况

- 通过：`pnpm exec tsc --noEmit`。
- 待验证：使用两个浏览器标签页同时接近过期令牌的人工刷新场景。

### 遗留问题

- 服务端明确拒绝当前 refresh token（过期、已退出或密钥变更）时，前端仍会安全退出，用户需要重新登录。

## 2026-07-23：AI 管家欢迎页视觉重做

### 任务目标

将此前功能导向的聊天欢迎页调整为与用户确认原型一致的页面结构，不改变既定的接口边界和按钮能力范围。

### 实现内容

- 重写 `AppLayout` 的侧栏视觉结构，保留真实导航和当前登录账户信息。
- 移除 AI 管家页的大型圆角容器和标题栏，改为纯白聊天画布与右上角文字操作。
- 将欢迎区调整为左对齐问候语和纵向编号预设问题；移除用户明确排除的“新建一个文档”卡片。
- 使用 Ant Design X `Sender` 保留可复用的 AI 输入能力，并将其调整为原型中的紧凑底部输入区。

### 主要文件

- `frontend/src/layouts/AppLayout.tsx`：应用级侧栏与账户区域布局。
- `frontend/src/pages/AiManagerPage.tsx`：聊天欢迎页的区域组合和历史抽屉状态。
- `frontend/src/features/chat/components/ChatWelcome.tsx`：问候语与纵向预设问题展示。
- `frontend/src/features/chat/components/ChatComposer.tsx`：输入区和已确认的能力入口展示规则。
- `frontend/src/style.css`：Ant Design X 输入组件的局部原型样式覆盖。

### 接口或数据变化

无。本次仅调整前端视觉和组件布局，既有聊天入口、会话列表接口保持不变。

### 验证情况

- 通过：`pnpm exec tsc --noEmit`。
- 通过：`pnpm build`（在允许读取依赖文件的环境中执行）。
- 警告：生产包仍超过 Vite 默认 500 kB 阈值；尚未进行浏览器像素级截图比对。

### 遗留问题

- 侧栏个人智能体列表待对应列表接口和创建功能完成后使用真实数据渲染。
- 新建会话、发送回显消息与历史消息展示仍待下一步前端接口联调。

## 2026-07-20：首期知识库资料类型调整

### 任务目标

根据用户确认，降低首期文件处理和部署复杂度，同时保留文字资料 RAG 的完整链路。

### 实现内容

- 将首期支持格式调整为 PDF、TXT、Word（`.docx`）和 Markdown。
- 将图片、扫描版 PDF、OCR 和 PaddleOCR 移出首期范围。
- 明确普通文本 PDF 仍使用 PyMuPDF，`.docx` 使用 `python-docx` 提取正文；扫描版 PDF 处理失败并提示不支持。

### 主要文件

- `docs/features/agent-knowledge-platform/`：更新需求、后端、接口、数据、验收和变更设计。
- `docs/DECISIONS.md`、`docs/QUESTIONS.md`：同步调整后的技术与需求范围。

### 技术方案

继续保留 Redis Worker 处理解析、切分和 Embedding，但不再为 OCR 引入模型运行时和独立依赖，从而减少首期部署资源与故障面。

### 接口或数据变化

设计上的 API-010 文件类型白名单变更；尚未实现接口、数据库迁移或依赖变更。

### 验证情况

- 已完成：需求、后端、接口与验收文档的一致性更新。
- 未执行：代码构建、文件解析、Worker、API 或端到端测试；本次未修改运行代码。

### 遗留问题

- 实施前仍需确定 Embedding 模型和具体依赖版本。
- 图片知识库与 OCR 如需恢复，必须作为后续独立功能重新确认和设计。

## 2026-07-20：智能体与知识库首期功能设计确认

### 任务目标

将 AI 管家、个人智能体、会话、私有知识库和 RAG 的确认需求固化为后续实施依据，不在设计阶段提前实现业务代码。

### 实现内容

- 创建首期功能设计目录，覆盖需求、前端、后端、接口、数据、验收和变更记录。
- 确认多账号数据隔离、内置 AI 管家、默认打开及会话侧栏范围规则。
- 确认文件/文件夹资料范围和文件夹自动纳入后续新增文件的规则。
- 确认保留现有技术栈并受控使用 LangChain/LangGraph 的工作流边界。

### 主要文件

- `docs/features/agent-knowledge-platform/`：首期功能的正式设计与验收依据。
- `docs/DECISIONS.md`：ADR-005 更新为已采用的技术方案。
- `docs/PROJECT_STATUS.md`：更新为设计完成、待实施状态。

### 技术方案

使用 FastAPI、PostgreSQL/pgvector、对象存储、Redis Worker 和可替换模型/OCR/Embedding 适配层；LangChain 负责模型相关标准能力，LangGraph 负责固定聊天工作流编排，不承担权限和数据库访问。

### 接口或数据变化

设计了 API-001 至 API-011、DB-001 至 DB-006；尚未实现接口、数据库迁移或依赖变更。

### 验证情况

- 已完成：需求、前端、后端、接口、数据和验收设计的文档一致性检查。
- 未执行：代码构建、数据库迁移、API 集成、Worker、模型和浏览器测试；本次未修改运行代码。

### 遗留问题

- 实施前需锁定模型供应商、Embedding 模型、OCR 部署方式和依赖版本。
- 会话删除及资料移动/删除不在首期范围，后续需单独确认。

## 2026-07-18：前端认证与业务路由边界重构

### 任务目标

将模糊的通配符认证路由调整为具备明确 URL 语义、鉴权边界、登录回跳与 404 处理的路由结构。

### 实现内容

- 新增路径常量、匿名路由守卫和受保护路由守卫。
- 将认证入口拆为 `/login` 与 `/register`，认证表单模式由路由确定。
- 将业务入口统一为 `/app/chat`、`/app/agents`、`/app/knowledge-bases`，并新增未知路径 404 页。
- 未登录访问有效受保护页面时保留原地址，认证成功后恢复访问。

### 主要文件

- `frontend/src/routes/paths.ts`：集中定义前端路径。
- `frontend/src/routes/GuestOnly.tsx`、`frontend/src/routes/RequireAuth.tsx`：认证路由边界与回跳逻辑。
- `frontend/src/App.tsx`：组装新的嵌套路由树。
- `frontend/src/layouts/AppLayout.tsx`：使用路径常量生成导航和登出跳转。
- `frontend/src/pages/AuthPage.tsx`、`frontend/src/pages/NotFoundPage.tsx`：认证 URL 语义和 404 展示。

### 技术方案

基于已有 React Router 依赖实现守卫组件与嵌套路由，不引入新依赖；用集中路径常量避免导航和路由声明出现重复字符串。

### 接口或数据变化

无。未修改后端 API、数据库结构或认证令牌格式。

### 验证情况

- 通过：在 `frontend/` 执行 `pnpm build`（`tsc && vite build`）。
- 警告：Vite 提示压缩后部分代码块超过 500 kB；pnpm 读取用户级配置时产生权限警告，但构建退出码为 0。
- 未执行：浏览器端到端测试和后端数据库/API 集成测试。

### 遗留问题

- `/app/*` 对应的 AI、智能体与知识库业务页面尚未实现。
- 旧路径未提供兼容重定向；如已有外部链接，应在发布前评估兼容策略。

## 2026-07-18：项目文档基线核查与补全

### 任务目标

依据当前目录、源代码、依赖配置和可执行检查，建立统一项目文档；不把尚未运行验证的功能或规划内容记为已完成。

### 实现内容

- 创建统一文档索引、项目状态、开发日志、问题记录、技术决策和架构说明。
- 核查前端 React/Vite 目录、后端 FastAPI 目录、认证实现、数据库初始化逻辑和 CI 配置。
- 明确 AI 管家页面、知识库页面与真实 RAG/智能体流程尚未实现。

### 主要文件

- `docs/README.md`：统一文档的职责索引。
- `docs/PROJECT_STATUS.md`：当前功能状态、验证范围、下一步和风险。
- `docs/QUESTIONS.md`：记录本次形成的文档真实性约束结论。
- `docs/DECISIONS.md`：记录从现有代码核查得到的长期技术选择。
- `docs/ARCHITECTURE.md`：记录实际目录职责、认证数据流和未实现边界。

### 技术方案

以代码、依赖清单、CI 工作流和本地命令输出为证据来源。对已存在但未实际联调的功能采用“已实现、待集成验证”的表述；对只有路由或空页面的功能标记为“规划中”或“未实现”。

### 接口或数据变化

无。本次只新增项目文档，未修改 API、数据库结构或依赖。

### 验证情况

- 通过：使用 `backend/.venv/Scripts/python.exe -m py_compile` 编译 `main.py`、配置、数据库、依赖、路由、模型和认证服务模块。
- 通过：在 `frontend/` 执行 `pnpm build`（`tsc && vite build`）。
- 警告：Vite 报告主 JavaScript 包超过 500 kB；pnpm 读取用户级配置时出现权限警告，但构建退出码为 0。
- 未执行：数据库连接/建表、HTTP 集成测试、浏览器交互测试和认证自动化测试；本次未配置可验证的数据库服务。

### 遗留问题

- 认证流程需要连接真实 PostgreSQL 后完成端到端验证。
- 知识库、向量检索、智能体工作流及真实聊天回答仍待实现。
- 需校正 `frontend/docs/login.md` 与当前认证实现之间的历史描述差异。
## 2026-07-24：智能体入口配置默认值修正

### 任务目标

修正智能体完整配置页中上传文件和联网搜索入口在接口字段缺失时显示为未选择的问题。

### 实现内容

- 为上传文件和联网搜索配置增加前端初始化兜底：字段为 `undefined` 时默认选择“需要”。
- 为两个 Ant Design 表单字段声明 `initialValue=true`，使单选组件在字段未注册或接口值缺失时也能立即显示“需要”。
- 保持用户明确保存的 `false` 值不变，不会将“不需要”覆盖为“需要”。

### 主要文件

- `frontend/src/pages/AgentEditorPage.tsx`：将智能体接口数据转换为表单值，并处理历史/不完整响应字段。
- `docs/PROJECT_STATUS.md`：同步当前修正状态。

### 技术方案

使用空值合并运算符只处理缺失值，而不使用逻辑或运算符，避免错误改变有效的布尔值 `false`。

### 接口或数据变化

无。未修改后端接口、数据库结构或依赖。

### 验证情况

- 通过：在 `frontend/` 执行 `pnpm build`（`tsc && vite build`）。
- 警告：Vite 提示压缩后部分代码块超过 500 kB；首次沙箱构建无法读取本地 `highlight.js` 依赖文件，授权环境重跑后通过。
- 未执行：浏览器人工验证；需确认新建智能体与缺失配置字段的历史智能体均默认显示“需要”。

### 遗留问题

- 若后端持续返回缺失字段，应继续排查其实际响应和历史数据迁移状态；本次前端兜底可避免配置页出现未选择状态。

## 2026-07-24：智能体配置表单绑定更正

### 任务目标

修复上传文件与联网搜索单选项未显示当前值的问题，并消除相同模式对欢迎语控件的影响。

### 实现内容

- 将上传、联网和欢迎语帮助文字移动到 Ant Design `Form.Item` 的 `extra` 属性。
- 保证带 `name` 的表单项只有一个直接表单控件，使表单可向控件注入 `value` 和 `onChange`。
- 删除字段级重复 `initialValue` 及 Radio 的重复预览更新逻辑，统一由表单初始值和 `onValuesChange` 管理。

### 主要文件

- `frontend/src/pages/AgentEditorPage.tsx`：智能体编辑表单绑定和帮助文字布局。
- `docs/PROJECT_STATUS.md`：更正当前问题的根因和处理状态。

### 技术方案

使用 Ant Design `Form.Item.extra` 渲染说明内容，避免命名表单项包含多个直接子节点；默认值仍由 `toFormValues` 统一提供。

### 接口或数据变化

无。未修改后端接口、数据库结构或依赖。

### 验证情况

- 通过：在 `frontend/` 执行 `pnpm build`（`tsc && vite build`）。
- 警告：Vite 提示压缩后部分代码块超过 500 kB。
- 未执行：浏览器人工验证；需确认上传、联网单选分别默认勾选“需要”，并确认选择“不需要”后保存和预览同步正确。

### 遗留问题

- 无代码级阻塞；仍需完成浏览器人工验收。
# 2026-07-25：流式聊天前后端首次联调

### 任务目标

让正式聊天和智能体编辑预览都调用同一套 DeepSeek 流式运行能力，而不是继续使用回显或静态提示。

### 实现内容

- 前端新增 POST SSE 消费逻辑与 `useStreamingChat`，按 `requestId` 和递增 `sequence` 忽略重复事件。
- 正式聊天页改为实时追加模型 `answer_delta`；编辑页预览改为将当前草稿配置提交到预览流接口，消息仅保留在页面内存。
- 应用 `20260725_0006` 迁移，为正式消息增加请求幂等字段及 `generating` 状态。

### 主要文件

- `frontend/src/api/chat.ts`：流式请求与 SSE 帧解析。
- `frontend/src/features/chat/hooks/useStreamingChat.ts`：前端流式消息状态。
- `frontend/src/pages/ChatPage.tsx`：正式聊天入口接线。
- `frontend/src/features/agents/components/AgentEditorPreview.tsx`：草稿预览入口接线。

### 接口或数据变化

- 使用 `POST /api/conversations/messages:stream` 和 `POST /api/agents/{agentId}/preview/messages:stream`。
- 已执行 Alembic `20260725_0006`。

### 验证情况

- 后端相关模块 `py_compile` 通过。
- 前端 `pnpm build` 通过。
- 尚未完成浏览器真实模型请求、停止生成、断线续流与 Redis 缓冲验证。

### 遗留问题

- 阶段 A 仍为进行中，不应作为完整流式聊天能力验收。

# 2026-07-25：流式聊天渲染与工作流纠正

### 任务目标

纠正流式聊天加载态、Markdown 渲染与模型运行架构，使阶段 A 不再以直接 HTTP 调用替代智能体工作流边界。

### 实现内容

- 恢复生成中空助手消息的三点 loading，并展示 SSE `status` 文案。
- 助手气泡改用项目已安装的 `@ant-design/x-markdown`，支持流式 Markdown 安全渲染。
- DeepSeek 改由 LangChain `ChatOpenAI` 的 OpenAI 兼容适配调用；LangGraph 执行 `prepare_input -> model` 最小运行图。

### 接口或数据变化

- 不新增数据库迁移或 HTTP 路由。
- 新增生产依赖：`langchain-core`、`langchain-openai`、`langgraph`。

### 验证情况

- LangGraph 图编译通过。
- 使用已配置 DeepSeek 完成最小真实调用，返回 `runtime-ok`。
- 后端模块编译与应用导入通过；`http://127.0.0.1:8001/docs` 可访问。
- 前端 `pnpm build` 通过。

### 遗留问题

- 停止生成、Redis 续流、幂等回放和浏览器端人工验收未完成。
- 受控处理摘要、检索步骤和引用仍是后续阶段，当前不展示模型原始思维链。
