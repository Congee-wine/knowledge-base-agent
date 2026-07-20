# 数据设计

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

字段：`id`、`owner_user_id`（内置智能体为空）、`kind`（`builtin`/`personal`）、`name`、`description`、`avatar_key`、`system_prompt`、`welcome_message`、`allow_conversation_upload`、`created_at`、`updated_at`。唯一约束：个人智能体 `(owner_user_id, lower(name))`；内置智能体由固定种子 ID 维护。

### DB-003：`agent_preset_questions` 与 `agent_knowledge_scopes`

- 预设问题：`id`、`agent_id`、`content`、`display_order`。
- 资料范围：`agent_id`、`knowledge_node_id`、`created_at`，联合主键 `(agent_id, knowledge_node_id)`。
- 资料范围仅保存被显式选中的文件/文件夹节点；不复制后代文件。检索时递归展开文件夹，天然覆盖未来新增后代。

### DB-004：`conversations`、`messages`、`message_citations`

- 会话：`id`、`owner_user_id`、`agent_id`、`title`、`created_at`、`updated_at`。
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

- `agents(owner_user_id, updated_at DESC)`：个人智能体列表。
- `conversations(owner_user_id, agent_id, updated_at DESC)`：当前智能体会话侧栏。
- `knowledge_nodes(owner_user_id, parent_id, name)`：文件夹浏览。
- `document_chunks(owner_user_id, document_version_id, ordinal)`：文件分块读取。
- 向量索引在实际数据规模和模型维度确认后创建。首期以带用户/文件过滤的精确查询验证正确性；达到阈值后评估 HNSW。索引方案和参数需由基准测试决定。

## 5. 删除、迁移与安全

- 本期不对资料树开放删除/移动接口，因此不定义用户触发的级联删除流程。
- 智能体删除受默认设置限制；删除后会话保留策略不在本期实现，接口暂不提供删除。
- 所有新表通过版本化迁移创建，替代新增业务表的启动时 DDL。
- 原始对象仅按 `storage_key` 引用；下载通过服务端鉴权生成临时授权，不向前端返回永久地址。
- 日志、错误和引用不得包含对象存储凭据、模型密钥或完整受限资料。
