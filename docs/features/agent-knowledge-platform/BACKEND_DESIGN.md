# 后端设计

## 1. 模块边界

| 模块 | 职责 |
| --- | --- |
| `routers` | 参数绑定、认证依赖、SSE 响应和统一错误转换 |
| `schemas` | HTTP 请求、响应与 SSE 事件模型 |
| `services/agents` | 智能体 CRUD、默认打开规则、资料范围校验 |
| `services/conversations` | 会话/消息创建、读取和持久化 |
| `services/knowledge` | 文件树、上传授权、处理状态和资料范围展开 |
| `repositories` | 所有 PostgreSQL 和 pgvector 查询 |
| `retrieval` | 文本提取、切分、嵌入、向量检索与引用组装 |
| `integrations` | S3、模型、Embedding、Redis 队列适配 |
| `workflows` | LangGraph 聊天状态、节点和流式事件映射 |

路由、LangGraph 节点和模型工具不得直接执行 SQL。业务服务不得依赖 FastAPI 请求/响应对象。

## 2. 文件处理流程

1. `KnowledgeService` 验证父文件夹属于当前用户并创建文件、版本和任务记录。
2. 原始文件写入对象存储；数据库文件状态变更为 `processing`。
3. Worker 根据 MIME 类型调用 PDF 文本提取、TXT/Markdown 读取或 `.docx` 正文提取，得到统一文本和页码/段落位置元数据；扫描版 PDF 因无 OCR 不支持而标记失败。
4. Worker 将解析出的文本持久化为 `document_chunks`（本阶段 `embedding` 为空）：PDF 按页保存，其余格式先保存为单个文本分块。该结果同时供后续预览与向量化复用；标题和递归切分将在向量化阶段实现。
5. 后续 Embedding 阶段批量补写这些分块的 pgvector 向量，不重复解析源文件。
6. 文本持久化成功后文件标记 `ready`；任一不可恢复错误标记 `failed` 并写入安全的错误摘要。

## 3. 聊天 LangGraph 工作流

工作流是服务端约束的条件图。模型只负责在受限结构中分析任务和组织回答；资料检索、后续联网与其他工具均由服务端策略节点决定是否执行，模型不能获得数据库、对象存储或任意工具访问能力。

```text
START
  → guard_identity
  → answer_public_profile（身份、能力或内部技术配置问题，直接结束）
  → load_context（普通问题）
  → analyze_request
  → decide_strategy
  → retrieve_context（仅资料策略）
  → evaluate_evidence（仅资料策略）
  → generate_answer
  → persist_result
  → END
```

- `load_context`：调用会话服务，验证用户拥有会话和智能体，加载有限历史消息与智能体配置。
- `guard_identity`：以服务端规则识别身份、能力、模型、版本和内部配置问题；命中后不调用模型、检索或工具。
- `answer_public_profile`：仅以服务端构造的公开档案回答智能体名称、职责和真实启用能力；公开档案不包含模型、供应商、版本、密钥或内部参数。
- `analyze_request`：基于当前问题和有限历史识别任务目标、是否依赖私有事实，以及是否缺少会改变结论的关键条件。它只能返回受 schema 约束的分类，不输出或持久化模型原始思维链。
- `decide_strategy`：将分类映射为 `direct_answer`、`knowledge_answer`、`hybrid_answer` 或 `clarify`。无知识范围、通用写作/分析或不需要私有事实的问题直接进入普通模型回答；不以“先检索”作为默认前置条件。
- `retrieve_context`：仅在资料策略下调用检索服务，先计算资料范围，再执行带 `owner_user_id` 与文件范围过滤的向量检索。
- `evaluate_evidence`：根据召回结果数量、相似度与问题对私有事实的依赖性判断证据是否足够。无命中或证据不足时，若问题可由通用知识回答则降级到 `direct_answer`；只有用户明确要求依据私有资料时才生成具体的资料补充建议。
- `generate_answer`：使用 LangChain Chat Model、策略专用 Prompt Template 和已授权上下文生成令牌事件。资料只作为受控上下文；通用回答不伪造资料来源，混合回答明确区分资料依据与通用建议。
- `persist_result`：调用会话服务写入助手消息、引用和完成/中断状态。

工作流状态仅保存请求级数据：用户 ID、智能体 ID、会话 ID、消息 ID、短历史、策略、受控的检索引用、证据结论和生成结果。不得将完整文件、密钥或模型原始推理写入状态。SSE 仅映射白名单事件：`status`、`answer_delta`、`sources`、`message_end`、`error`；阶段文本只能描述可验证系统动作，例如“正在检索已授权资料”。

首次发送前会话 ID 可以为空。消息服务必须先在一个数据库事务内创建会话并持久化用户消息，随后才进入模型工作流；阶段 2 尚未接入模型时，同一事务内写入回显助手消息。点击“新会话”不触发任何后端写操作。

## 4. 安全与隔离

- 每个入口先通过现有 Bearer 认证获取用户 ID；请求中的 `user_id` 一律忽略。
- 用户自有资源读取、写入和检索均通过仓储查询的 `owner_user_id = current_user_id` 强制过滤。
- 内置 AI 管家可被所有用户使用，但每个会话、消息、引用和检索上下文仍仅属于当前用户。
- 模型调用前完成资料范围校验；模型不获得对象存储凭据、数据库连接或未授权文件名。
- 模型调用前注入不可由用户智能体配置覆盖的身份保密规则；模型输出命中自我披露模式时，服务端替换为公开身份答复。
- 上传校验扩展名、MIME、大小和文件签名；对象存储使用私有 bucket 和短期下载授权。

## 5. 错误与降级

- 模型超时/失败：保留用户消息，助手消息标记失败；SSE 返回可重试错误。
- 解析/Embedding 失败：文件标记失败，不影响其他 `ready` 文件的检索。
- 空资料范围或无召回：它们只是策略输入。对可由通用知识安全回答的问题继续生成普通回答；对明确要求私有依据的问题说明缺少的资料类型并建议补充，不创建伪引用。
- 问题目标或关键条件不明确：输出简洁澄清问题，不假设用户未提供的关键事实。
- Worker 重试使用任务 ID 幂等；重复上传请求不重复写入同一版本的分块。

## 6. 依赖与部署

聊天模型采用 DeepSeek 的 OpenAI 兼容 Chat Completions 接口；实施前仍需锁定具体聊天模型。Embedding 使用本地 `BAAI/bge-m3`：Worker 进程启动时加载模型，批量编码文档分块和查询文本，并将向量写入 pgvector；模型权重与推理不通过云端 Embedding API。还需评估并锁定：LangChain 对应集成、LangGraph、BGE 推理库、PyMuPDF、`python-docx`、S3 客户端、Redis 客户端、后台任务框架和版本化迁移工具。开发与部署需分别运行 API、Worker、PostgreSQL/pgvector、Redis 和 S3 兼容对象存储。真实模型密钥只通过环境变量注入。
## 7. Redis 事件缓冲与 RQ 生成运行时（已确认，未实现）

正式会话的首次请求由会话服务创建数据库消息对、创建 Redis 运行元数据并提交 RQ 任务；路由只负责参数、认证和 SSE 响应。`chat_generation` 服务在 Worker 中调用 `agent_runtime.stream_answer`，将可公开展示的状态与增量追加至 Redis Stream，并在终态时更新 PostgreSQL 消息。`stream_events` 仓储隔离 Redis 协议、键名、TTL、序号和补读逻辑。

恢复订阅不调用模型也不写数据库：它先验证当前用户对助手消息及会话的所有权，再由事件仓储按 `afterSequence` 读取和阻塞等待新事件。取消接口仅写 Redis 取消标记，Worker 负责写入最终 `interrupted` 状态，避免客户端断线导致部分内容丢失。
