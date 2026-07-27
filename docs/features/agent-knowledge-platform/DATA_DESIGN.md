# 数据设计

## 2026-07-27：会话内消息稳定顺序

迁移 `20260727_0008` 为 `messages` 新增 `message_order BIGINT NOT NULL` 和唯一约束 `(conversation_id, message_order)`。该字段是消息渲染的唯一排序依据；仓储层在写入前锁定所属会话，并在同一事务中为用户消息和对应助手消息分配连续序号。历史记录按原有 `created_at, id` 顺序一次性回填，避免修改既有内容。

## 2026-07-27：流式消息关联与幂等性补充

当前 `messages` 表已通过迁移 `20260725_0006` 和 `20260727_0007` 增加以下字段：

| 字段 | 类型 | 含义 |
| --- | --- | --- |
| `client_request_id` | TEXT，可空，非空值唯一 | 正式流式请求的幂等标识；只写入 assistant 消息。 |
| `reply_to_message_id` | UUID，可空 | assistant 消息所回复的 user 消息 ID。新写入消息必须与 assistant 所在会话一致；历史数据保持 `NULL`，不猜测回填。 |

约束意图：`reply_to_message_id` 仅允许出现在 `role='assistant'` 的消息上；`(reply_to_message_id, conversation_id)` 必须引用同一会话中的 `(id, conversation_id)`。这个关系用于防止幂等重试时从整个会话中误取“最新一条 user 消息”。

> 状态说明：并发幂等请求通过保存点回滚后重读已创建记录实现幂等处理；为防止错误转换，消息终态更新仅允许作用于 `generating` 的 assistant 消息。

## 交互类型与头像对象

- 迁移 `20260724_0005` 为 `agents` 增加非空 `interaction_type`，约束为 `text`、`voice`、`digital_human`；现有及首期新建记录默认 `text`。
- `agents.avatar_key` 保存私有 MinIO 对象键，首期键前缀为 `agent-avatars/{userId}/`；图片二进制不存入 PostgreSQL，客户端不持久化对象 URL。
- 删除个人智能体后尝试移除关联头像对象；对象删除失败记录服务端异常日志，不回滚已经完成的软删除。

## 1. 存储范围

- PostgreSQL：用户偏好、智能体、会话、消息、资料树、文件版本、处理任务、分块、引用和资料范围关联。
- pgvector：`document_chunks.embedding`，与分块元数据同库保存。
- S3 兼容对象存储：原始 PDF、TXT、`.docx`、Markdown；私有 bucket，不公开暴露对象路径。
- Redis：后台任务投递、任务执行协调和可选短期状态；不是业务事实来源。

## 2. 实体关系

```text
users ──< agents ──< conversations ──< messages ──< message_citations
  │          │
  │          └──< agent_knowledge_scopes >── knowledge_nodes
  ├── user_preferences
  └──< knowledge_nodes ──< document_versions ──< document_chunks
```

内置 AI 管家是系统种子 `agents` 记录（`kind=builtin`、无 `owner_user_id`）；其会话和资料均通过当前用户关联，不能成为跨用户数据通道。

## 3. 表设计

### DB-001：`user_preferences`

| 字段 | 类型 | 约束 | 业务含义 |
| --- | --- | --- | --- |
| `user_id` | UUID | PK/FK users | 用户 |
| `default_agent_id` | UUID | 可空 FK agents | 默认自建智能体 |
| `updated_at` | TIMESTAMPTZ | 非空 | 修改时间 |

服务层确保 `default_agent_id` 只能指向该用户自建智能体；为空时入口显示内置 AI 管家。

### DB-002：`agents`

字段：`id`、`owner_user_id`（内置智能体为空）、`kind`（`builtin`/`personal`）、`name`、`description`、`avatar_key`、`system_prompt`、`welcome_message`、`allow_conversation_upload`、`allow_network_access`、`deleted_at`、`created_at`、`updated_at`。唯一约束：个人活跃智能体 `(owner_user_id, lower(name))`；内置智能体由固定种子 ID 维护。软删除只写入 `deleted_at`，不删除关联会话、消息或引用。`allow_network_access` 决定个人智能体是否显示联网入口，实际联网能力另行实现。

### DB-003：`agent_preset_questions`

- 预设问题：`id`、`agent_id`、`content`、`display_order`。
- 本阶段只创建预设问题表。`agent_knowledge_scopes` 依赖尚未创建的 `knowledge_nodes`，延后到阶段 3 与知识库数据表一并创建。

### DB-004：`conversations`、`messages`、`message_citations`

- 会话：`id`、`owner_user_id`、`agent_id`、`title`、`is_draft`、`created_at`、`updated_at`。聊天页面不创建 `is_draft=true` 记录：空白新会话仅存在于前端。该字段和部分唯一索引 `(owner_user_id, agent_id) WHERE is_draft` 保留用于兼容历史/直接创建接口；正常聊天首次发送直接创建 `is_draft=false` 的会话并写入消息。
- 消息：`id`、`conversation_id`、`role`（`user`/`assistant`）、`content`、`generation_status`（`complete`/`interrupted`/`failed`）、`created_at`。
- 引用：`message_id`、`document_chunk_id`、`file_name_snapshot`、`page_number`、`excerpt`、`display_order`。

### DB-005：`knowledge_nodes` 与 `document_versions`

- 节点：`id`、`owner_user_id`、`parent_id`（自关联）、`node_type`（`folder`/`file`）、`name`、`created_at`、`updated_at`。
- 文件版本：`id`、`knowledge_node_id`、`storage_key`、`mime_type`、`byte_size`、`content_hash`、`processing_status`、`failure_code`、`failure_message`、`created_at`、`processed_at`。
- 唯一约束：同一父节点下 `(owner_user_id, parent_id, lower(name))`；文件节点只允许一个当前版本。

### DB-006：`document_chunks` 与 `ingestion_jobs`

- 分块：`id`、`owner_user_id`、`document_version_id`、`ordinal`、`content`、`page_number`、`metadata_json`、`embedding`、`embedding_model`、`created_at`。
- 任务：`id`、`document_version_id`、`status`、`attempt_count`、`last_error_code`、`started_at`、`finished_at`。
- `metadata_json` 仅保存非固定的解析位置（如图片区域），不得替代文件、用户、状态、模型等结构化字段。

## 4. 索引与查询

- `agents(owner_user_id, deleted_at, updated_at DESC)`：个人活跃智能体列表。
- `conversations(owner_user_id, agent_id, updated_at DESC)`：当前智能体会话侧栏。
- `knowledge_nodes(owner_user_id, parent_id, name)`：文件夹浏览。
- `document_chunks(owner_user_id, document_version_id, ordinal)`：文件分块读取。
- 向量索引在实际数据规模和模型维度确认后创建。首期以带用户/文件过滤的精确查询验证正确性；达到阈值后评估 HNSW。索引方案和参数需由基准测试决定。

## 5. 删除、迁移与安全

- 本期不对资料树开放删除/移动接口，因此不定义用户触发的级联删除流程。
- 智能体删除使用软删除；删除前必须清空默认设置。已删除智能体关联会话、消息和引用保留，但首期不提供恢复或已删除智能体历史查看入口。
- 所有新表通过版本化迁移创建，替代新增业务表的启动时 DDL。
- 原始对象仅按 `storage_key` 引用；下载通过服务端鉴权生成临时授权，不向前端返回永久地址。
- 日志、错误和引用不得包含对象存储凭据、模型密钥或完整受限资料。
## 运行态 Redis 数据（已确认，未实现）

本阶段不新增 PostgreSQL 表或迁移。每个正式会话生成使用助手消息 ID 作为 Redis 运行对象标识，包含 `meta` Hash、`events` Stream 和 `cancel` 标记三个键，统一 TTL 为 1800 秒。事件 Stream 最多保留 4096 条；若恢复游标早于首条缓存事件，则接口返回 `STREAM_RESUME_UNAVAILABLE`，客户端回读 PostgreSQL 中已保存的消息状态。

Redis 中不得存储访问令牌、模型密钥或用户上传文件。事件正文仅在恢复窗口中临时保存，窗口结束后由 Redis TTL 自动清除；正式回答内容只以 PostgreSQL 中的 `messages.content` 为准。
