# 项目架构

## 总体说明

前后端分离的 Web 应用。`frontend/` 提供 React 单页应用，`backend/` 提供 FastAPI API。核心链路为：用户通过智能体发起对话 → LangGraph 工作流决定路由策略 → 知识库混合检索 + Rerank → DeepSeek 流式生成回答 → SSE 推送到前端。

```text
浏览器（React + Vite）
  ├─ /api/auth/* ────────────────> FastAPI 认证路由 ─> 认证服务 ─> PostgreSQL
  ├─ /api/agents/* ──────────────> FastAPI 智能体路由 ─> 智能体服务 ─> PostgreSQL
  ├─ /api/conversations/* ───────> FastAPI 会话路由 ─> 会话服务 ─> LangGraph ─> DeepSeek
  │                                                              └─> RAG 检索 ─> pgvector + BGE-M3 + Reranker
  └─ /api/knowledge/* ───────────> FastAPI 知识库路由 ─> 知识库服务 ─> MinIO + PostgreSQL
                                                           └─> RQ 队列 ─> Worker（解析/Embedding/检索）
```

## 目录与模块职责

### 前端：`frontend/`

**入口与路由**
- `src/main.tsx`：创建 React 根节点并注入 React Query。
- `src/App.tsx`：认证状态恢复、令牌刷新调度、应用路由组装、按需加载。
- `src/routes/paths.ts`：前端路径常量；导航与路由声明共用。
- `src/routes/GuestOnly.tsx`、`src/routes/RequireAuth.tsx`：匿名与受保护路由边界，支持登录后回跳。

**API 层**
- `src/api/http.ts`：统一 HTTP 请求封装（JSON / Form / Blob），`ApiError` 错误提取。
- `src/api/auth.ts`：认证接口（注册、登录、刷新、登出、获取当前用户）。
- `src/api/agents.ts`：智能体 CRUD 接口。
- `src/api/chat.ts`：SSE 流式聊天、中断生成接口。
- `src/api/knowledge.ts`：知识库资料树、上传、重命名、移动、删除、预览接口。

**业务模块**
- `src/features/chat/hooks/useStreamingChat.ts`：流式对话核心 Hook，管理多会话并行流、乐观更新、中断恢复。
- `src/features/chat/hooks/useConversations.ts`：会话列表与详情管理。
- `src/features/chat/streaming/sseParser.ts`：自研 SSE 解析器（分块、CRLF、多行 data）。
- `src/features/chat/utils/mergeMessages.ts`：本地/服务端消息合并逻辑。
- `src/features/chat/components/ChatMessageList.tsx`：消息列表（Bubble.List + Markdown 流式渲染 + 引用展示）。
- `src/features/chat/components/ChatRunSummary.tsx`：运行步骤可视化（可折叠大步骤 + 子步骤）。
- `src/features/chat/components/ChatComposer.tsx`：聊天输入框（Ant Design X Sender）。
- `src/features/agents/hooks/useAgents.ts`、`useAgent.ts`：智能体列表与详情管理。
- `src/features/agents/components/AgentEditorPreview.tsx`：编辑页实时对话预览。
- `src/features/agents/components/SystemPromptEditor.tsx`：Markdown 系统提示词编辑器。
- `src/features/agents/components/AgentKnowledgeScopeField.tsx`：知识范围绑定入口。
- `src/features/knowledge/components/KnowledgeItemGrid.tsx`：资料网格视图（多选、右键菜单）。
- `src/features/knowledge/components/KnowledgeScopeSelectorModal.tsx`：资料范围选择器弹窗。
- `src/features/knowledge/components/KnowledgeNavigationToolbar.tsx`：资料树导航工具栏。

**状态与工具**
- `src/stores/auth.ts`：Zustand 维护当前用户状态。
- `src/lib/auth.ts`：浏览器会话令牌的读取、保存、刷新和登出协调（单例 Promise 防并发）。
- `src/types/`：共享 TypeScript 类型定义。

**页面**
- `src/pages/AuthPage.tsx`：注册/登录表单。
- `src/pages/AiManagerPage.tsx`：AI 管家欢迎页。
- `src/pages/AgentListPage.tsx`：智能体列表页。
- `src/pages/AgentEditorPage.tsx`：智能体编辑工作台（三栏布局）。
- `src/pages/ChatPage.tsx`：正式聊天页。
- `src/pages/KnowledgeBasePage.tsx`：知识库管理页。
- `src/pages/DocumentPreviewPage.tsx`：文件预览页。

### 后端：`backend/`

**应用入口**
- `main.py`：FastAPI 应用、CORS、全局异常处理器（DomainError）、健康检查与路由注册；通过生命周期管理 PostgreSQL 连接池。
- `config.py`：从 `.env` 读取数据库、认证、模型、存储、队列等配置。
- `database.py`：psycopg PostgreSQL 连接池（`ConnectionPool`），业务 Repository 通过 `get_connection()` 借用并归还连接。
- `dependencies.py`：HTTP Bearer 认证依赖和当前用户解析。

**路由层（`routers/`）**
- `auth.py`：认证路由（注册、登录、刷新、登出、获取当前用户）。
- `agents.py`：智能体 CRUD 路由。
- `conversations.py`：会话管理与 SSE 流式聊天路由。
- `knowledge.py`：知识库资料树、上传、重命名、移动、删除、预览路由。
- `chat.py`：保留认证保护的旧聊天回显路由（骨架）。

**服务层（`services/`）**
- `auth.py`：密码哈希、JWT 签发/校验、会话轮换与撤销。
- `agents.py`：智能体业务规则（CRUD、默认设置、内置不可变保护）。
- `conversations.py`：会话与消息业务规则（创建、查询、流式生成、中断）。
- `knowledge.py`：知识库业务规则（资料树、上传、重命名、移动、删除、任务投递）。
- `agent_runtime.py`：LangGraph 智能体工作流（状态图编排、条件路由、流式输出）。
- `agent_strategy.py`：运行时策略决策（直接回答 / 知识库回答 / 目录查询）。
- `agent_identity.py`：模型信息隐藏守卫（身份、能力、内部配置问题固定答复）。
- `agent_preview.py`：智能体编辑预览逻辑。
- `retrieval.py`：RAG 检索服务（向量 + 关键字 + RRF 融合 + Rerank + 上下文筛选）。
- `document_preview.py`：文件预览内容提取。
- `document_validation.py`：文档上传校验。
- `errors.py`：领域错误定义（`DomainError` + 错误码 + HTTP 状态码）。

**仓储层（`repositories/`）**
- `agents.py`：智能体数据访问（CRUD、所有权校验、可见性过滤）。
- `conversations.py`：会话与消息数据访问（创建、查询、流式生成状态管理、幂等性）。
- `knowledge.py`：知识库数据访问（资料树、文件版本、处理任务、Embedding 任务、递归查询、Agent 资料范围）。
- `knowledge_retrieval.py`：检索数据访问（向量检索、关键字检索、文档列表、检索诊断记录）。

**检索模块（`retrieval/`）**
- `chunking.py`：智能文档分块（标题检测 + 语义边界 + 180 字符重叠窗口）。
- `models.py`：检索结果模型（`RetrievalSource` + 引用格式化）。

**集成层（`integrations/`）**
- `deepseek.py`：DeepSeek 模型客户端（LangChain OpenAI 兼容）。
- `embeddings.py`：BGE-M3 Embedding 模型（`BGEM3FlagModel`，延迟加载）。
- `reranker.py`：BGE-Reranker 重排模型（`FlagReranker`，延迟加载）。
- `query_embeddings.py`：RQ 远程调用封装（Embedding 和 Rerank 通过任务队列异步执行）。
- `object_storage.py`：MinIO 对象存储客户端（上传、读取、删除）。

**异步任务（`workers/`）**
- `queue.py`：RQ 队列定义（`document-processing`、`embedding`、`retrieval`）。
- `tasks.py`：Worker 任务（文档解析、Embedding 生成、查询 Embedding、Rerank）。
- `runner.py`：Worker 进程入口。

**数据库迁移（`migrations/`）**
- 15 个 Alembic 迁移文件，覆盖认证、智能体、会话、知识库、Embedding、检索可观测性、对话续流与内置预设问题。

**测试（`tests/`）**
- 16 个测试文件，覆盖认证集成、智能体会话集成、会话仓储/服务、分块、检索、文档处理、Agent 运行时/策略/身份、流式协议等。

## 数据库与存储

### PostgreSQL

Web API 使用 `psycopg_pool.ConnectionPool` 复用连接，默认最小 1、最大 10 条。Alembic 迁移使用独立的 `NullPool` 短连接。

主要数据表：
- `users`：用户 ID、唯一邮箱、密码哈希、创建时间、最近登录时间。
- `auth_sessions`：会话 ID、用户 ID、刷新令牌标识、会话/刷新到期时间、撤销时间。
- `revoked_tokens`：已撤销访问令牌的标识和过期时间。
- `agents`：智能体 ID、所有者、名称、描述、系统提示词、头像存储键、交互类型、联网入口、是否内置。
- `user_preferences`：用户默认智能体设置。
- `agent_preset_questions`：智能体预设问题。
- `conversations`：会话 ID、用户 ID、智能体 ID、标题。
- `messages`：消息 ID、会话 ID、角色、内容、消息序号、回复关系、生成状态、创建时间。
- `knowledge_nodes`：资料节点 ID、所有者、父节点、类型（folder/file）、名称。
- `document_versions`：文档版本 ID、资料节点、版本号、存储键、MIME 类型、字节大小、内容哈希、处理状态、索引状态、是否当前版本。
- `ingestion_jobs`：文档解析任务（状态、尝试次数、错误信息）。
- `embedding_jobs`：Embedding 任务（状态、尝试次数、错误信息）。
- `document_chunks`：文档分块（内容、页码、元数据 JSON、Embedding 向量、Embedding 模型）。
- `agent_knowledge_scopes`：Agent 知识范围授权（Agent ID → 资料节点 ID）。
- `message_citations`：消息引用持久化。
- `retrieval_runs`：检索运行记录（查询摘要、时间）。
- `retrieval_candidates`：检索候选记录（分块 ID、向量排名、关键字排名、融合排名、重排分数、是否选中、丢弃原因）。

### Redis

- RQ 任务队列消息中间件（三个队列：`document-processing`、`embedding`、`retrieval`）。

### MinIO

- 私有对象存储（`ai-platform-private` Bucket）。
- 存储内容：知识库文件、智能体头像。
- 存储路径格式：`knowledge-files/{user_id}/{uuid}/{filename}`、`agent-avatars/{user_id}/{uuid}/{filename}`。

### pgvector

- `vector` 扩展由迁移 `20260720_0001` 启用。
- `document_chunks.embedding` 列类型为 `vector`，使用余弦相似度（`<=>` 运算符）检索。

## 认证流程

1. 前端认证页调用注册或登录 API。
2. 注册时后端校验邮箱、密码长度，随后创建带 Argon2 哈希的用户记录。
3. 登录时后端验证密码，创建会话，返回访问 JWT、刷新 JWT 和用户信息。
4. 前端将令牌和用户信息写入 `localStorage`，启动时以访问令牌调用 `/api/auth/me`。
5. 访问令牌过期前 3 分钟，前端自动调用 `/api/auth/refresh`；后端验证会话、轮换刷新令牌标识并返回新令牌对。并发请求通过单例 Promise 锁防止重复刷新。
6. 受保护接口通过 `Authorization: Bearer <access token>` 解析当前用户。
7. 登出时前端请求撤销（访问令牌加入 `revoked_tokens`、会话标记 `revoked_at`），随后清除本地存储。
8. 未登录访问 `/app/*` 时，`RequireAuth` 将原路径写入路由状态并跳转 `/login`；登录成功后回跳。

## RAG 检索流程

1. 用户发送消息，`conversations.py` 调用 `agent_runtime.py` 的 `stream_with_retrieval()`。
2. LangGraph 工作流执行 `guard_identity` 节点：检测是否为身份/能力/配置问题，是则固定答复并跳过模型调用。
3. 执行 `check_knowledge_availability` 节点：检查 Agent 资料范围内是否存在 ready 索引文件。
4. 执行 `analyze_request` 节点：`agent_strategy.py` 决定路由策略（`document_catalog` / `semantic_search` / `direct_answer`）。
5. 若为 `semantic_search`，执行 `execute_knowledge_operation` 节点：
   - `retrieval.py` 调用 `embed_query()` 通过 RQ 远程获取查询向量。
   - `knowledge_retrieval.py` 执行向量检索（pgvector 余弦相似度，Top 20）和关键字检索（ILIKE，Top 20）。
   - `_fuse_candidates()` 使用 RRF 融合算法合并两种候选。
   - `rerank_query_candidates()` 通过 RQ 远程调用 BGE-Reranker 重排。
   - `_select_context_sources()` 按重排分数阈值（0.30）和文件级上下文限额（每文件最多 2 个片段，总计最多 5 个片段）筛选。
   - `_record_retrieval_diagnostics()` 持久化候选集和选中原因。
6. 执行 `evaluate_evidence` 节点：判断是否有有效证据。
7. 执行 `generate_answer` 节点：构造检索上下文，调用 DeepSeek 流式生成。
8. SSE 生成器逐块将模型输出转换为 `answer_delta` 事件推送到前端。
9. 生成完成后，`conversations.py` 持久化助手消息和引用。

## LangGraph 工作流节点

```text
START
  └─> guard_identity（身份守卫）
        ├─ 需要回答身份问题 ─> answer_public_profile ─> END
        └─ 正常问题 ─> check_knowledge_availability（知识可用性检查）
              ├─ 无 ready 文件 ─> knowledge_unavailable ─> END
              └─ 有 ready 文件 ─> analyze_request（策略分析）
                    ├─ direct_answer ─> generate_answer ─> END
                    └─ knowledge_answer ─> execute_knowledge_operation（检索）
                                            └─> evaluate_evidence（证据评估）
                                                  ├─ 有证据 ─> generate_answer ─> END
                                                  ├─ 无证据 ─> no_match ─> END
                                                  └─ 检索失败 ─> retrieval_failed ─> END
```

## 2026-08-14 路由规则补充

个人 Agent 的知识库能力以 `agent_knowledge_scopes` 是否存在绑定为准：未绑定范围时不检索，SSE 推送“未绑定知识库，正在由模型直接回答”后进入普通模型生成；已绑定范围但不存在 ready/current/已索引资料时才进入 `knowledge_unavailable` 终态。内置 AI 管家继续由 `useKnowledgeBase` 控制是否使用当前用户全部资料库。存在可用资料时，目录问题直接查询目录，其余问题固定进入语义检索与证据评估。

## 前端路由

```text
/
├─ /login                         匿名登录页
├─ /register                      匿名注册页
├─ /app                           受保护应用入口，重定向至 /app/chat
│  ├─ /app/chat                   AI 管家欢迎页
│  ├─ /app/chat/agents/:agentId   正式聊天页（SSE 流式对话）
│  ├─ /app/agents                 智能体列表页
│  ├─ /app/agents/:agentId/edit   智能体编辑工作台
│  ├─ /app/knowledge-bases        知识库管理页
│  └─ /app/knowledge-bases/files/:fileId/preview  文件预览页
└─ *                              404 页面
```

## 当前接口

| 接口 | 职责 | 状态 |
| --- | --- | --- |
| `GET /api/health` | 服务健康检查 | 已实现 |
| `POST /api/auth/register` | 创建用户 | 已实现，集成测试通过 |
| `POST /api/auth/login` | 验证密码并签发令牌 | 已实现，集成测试通过 |
| `POST /api/auth/refresh` | 刷新并轮换令牌 | 已实现，轮换与重放拒绝测试通过 |
| `GET /api/auth/me` | 获取当前用户 | 已实现，过期/撤销拒绝测试通过 |
| `POST /api/auth/logout` | 撤销令牌/会话 | 已实现，撤销测试通过 |
| `GET /api/chat/entry` | 解析当前用户默认智能体 | 已实现 |
| `GET/POST/PATCH/DELETE /api/agents` | 智能体 CRUD | 已实现，所有权与内置不可变规则已测试 |
| `PUT /api/agents/{agentId}/default` | 设为默认智能体 | 已实现 |
| `DELETE /api/agents/default` | 清空默认设置 | 已实现 |
| `GET /api/agents/{agentId}/avatar` | 获取智能体头像 | 已实现 |
| `POST /api/agents/{agentId}/avatar` | 上传智能体头像 | 已实现 |
| `POST /api/agents/{agentId}/preview/messages:stream` | 编辑预览 SSE 流式对话 | 已实现 |
| `GET/POST /api/conversations` | 会话列表/创建 | 已实现，用户与智能体隔离已测试 |
| `GET /api/conversations/{conversationId}` | 会话详情与消息 | 已实现 |
| `POST /api/conversations/messages:stream` | 正式会话 SSE 流式对话 | 已实现 |
| `POST /api/conversations/messages/{messageId}/interrupt` | 中断生成 | 已实现 |
| `GET /api/knowledge/tree` | 资料树读取 | 已实现 |
| `POST /api/knowledge/folders` | 创建文件夹 | 已实现 |
| `POST /api/knowledge/upload` | 上传文件 | 已实现 |
| `PATCH /api/knowledge/nodes/{nodeId}` | 重命名/移动 | 已实现 |
| `DELETE /api/knowledge/nodes/{nodeId}` | 递归删除 | 已实现 |
| `GET /api/knowledge/files/{nodeId}/preview` | 文件预览 | 已实现 |

## 外部依赖

**前端主要依赖**：React 18、React Router、React Query、Zustand、Ant Design 6、Ant Design X、Ant Design X Markdown、`@uiw/react-md-editor`、Vite、TypeScript、Tailwind CSS。

**后端主要依赖**：FastAPI、PyJWT、pwdlib（Argon2）、psycopg、pgvector、python-dotenv、Alembic、SQLAlchemy（仅迁移执行）、LangChain OpenAI、LangGraph、MinIO SDK、Redis、RQ、PyMuPDF、python-docx、FlagEmbedding（BGE-M3 + Reranker）。

**基础设施**：PostgreSQL（pgvector 扩展）、Redis、MinIO、Docker Compose。
