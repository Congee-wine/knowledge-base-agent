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
4. `retrieval` 使用 LangChain 文本切分器生成分块；Markdown 优先按标题结构切分，其余文本采用递归切分。
5. Embedding 适配器批量生成向量；仓储层写入分块、元数据和 pgvector 向量。
6. 事务成功后文件标记 `ready`；任一不可恢复错误标记 `failed` 并写入安全的错误摘要。

## 3. 聊天 LangGraph 工作流

工作流是固定的有向图，不含条件循环或模型自主工具调用。

```text
START
  → load_context
  → retrieve_context
  → generate_answer
  → persist_result
  → END
```

- `load_context`：调用会话服务，验证用户拥有会话和智能体，加载有限历史消息与智能体配置。
- `retrieve_context`：调用检索服务，先计算资料范围，再执行带 `owner_user_id` 与文件范围过滤的向量检索。
- `generate_answer`：使用 LangChain Chat Model、Prompt Template 和检索结果生成令牌事件；无结果时使用无资料提示词。
- `persist_result`：调用会话服务写入助手消息、引用和完成/中断状态。

工作流状态仅保存请求级数据：用户 ID、智能体 ID、会话 ID、消息 ID、短历史、检索引用和生成结果。不得将完整文件或密钥写入状态。SSE 仅映射白名单事件：`status`、`token`、`citation`、`complete`、`error`。

## 4. 安全与隔离

- 每个入口先通过现有 Bearer 认证获取用户 ID；请求中的 `user_id` 一律忽略。
- 用户自有资源读取、写入和检索均通过仓储查询的 `owner_user_id = current_user_id` 强制过滤。
- 内置 AI 管家可被所有用户使用，但每个会话、消息、引用和检索上下文仍仅属于当前用户。
- 模型调用前完成资料范围校验；模型不获得对象存储凭据、数据库连接或未授权文件名。
- 上传校验扩展名、MIME、大小和文件签名；对象存储使用私有 bucket 和短期下载授权。

## 5. 错误与降级

- 模型超时/失败：保留用户消息，助手消息标记失败；SSE 返回可重试错误。
- 解析/Embedding 失败：文件标记失败，不影响其他 `ready` 文件的检索。
- 空资料范围或无召回：生成普通回答或明确的“未找到相关资料”说明，不创建伪引用。
- Worker 重试使用任务 ID 幂等；重复上传请求不重复写入同一版本的分块。

## 6. 依赖与部署

聊天模型采用 DeepSeek 的 OpenAI 兼容 Chat Completions 接口；实施前仍需锁定具体聊天模型。Embedding 使用本地 `BAAI/bge-m3`：Worker 进程启动时加载模型，批量编码文档分块和查询文本，并将向量写入 pgvector；模型权重与推理不通过云端 Embedding API。还需评估并锁定：LangChain 对应集成、LangGraph、BGE 推理库、PyMuPDF、`python-docx`、S3 客户端、Redis 客户端、后台任务框架和版本化迁移工具。开发与部署需分别运行 API、Worker、PostgreSQL/pgvector、Redis 和 S3 兼容对象存储。真实模型密钥只通过环境变量注入。
