# 项目架构

## 总体说明

当前项目是前后端分离的 Web 应用。`frontend/` 提供 React 单页应用，`backend/` 提供 FastAPI API。已实现的核心业务是基于邮箱密码的认证和受保护的聊天接口骨架；知识库、向量检索和智能体回答尚未实现。

```text
浏览器（React + Vite）
  ├─ /api/auth/* ────────────────> FastAPI 认证路由 ─> 认证服务 ─> PostgreSQL
  └─ /api/chat（Bearer Token） ─> FastAPI 聊天路由 ─> 当前仅回显请求
```

## 目录与模块职责

### 前端：`frontend/`

- `src/main.tsx`：创建 React 根节点并注入 React Query。
- `src/App.tsx`：认证状态恢复、令牌刷新调度和应用路由组装。
- `src/routes/paths.ts`：前端路径常量；导航与路由声明共用。
- `src/routes/GuestOnly.tsx`、`src/routes/RequireAuth.tsx`：匿名与受保护路由边界，支持登录后回跳。
- `src/api/`：HTTP 请求和认证接口封装。
- `src/lib/auth.ts`：浏览器会话令牌的读取、保存、刷新和登出协调。
- `src/stores/auth.ts`：Zustand 维护当前用户状态。
- `src/pages/AuthPage.tsx`：由 `/login`、`/register` 路径决定模式的认证表单。
- `src/pages/NotFoundPage.tsx`：未知路径的 404 页面。
- `src/layouts/AppLayout.tsx`：已登录后的应用布局、导航和登出入口。
- `src/pages/AiManagerPage.tsx`、`src/pages/EmptyPage.tsx`：当前为空内容页面；AI 管家、智能体和知识库 UI 均未实现。
- `public/auth-hero.png`：认证页使用的静态图片资源。

前端使用 `VITE_API_BASE_URL` 指定 API 基地址；默认值是本地后端地址。环境变量的真实值不应写入文档。

### 后端：`backend/`

- `main.py`：FastAPI 应用、开发环境 CORS、健康检查与路由注册；启动时不修改数据库结构。
- `config.py`：从 `.env` 读取数据库地址和认证配置；`DATABASE_URL` 为必需配置。
- `database.py`：psycopg PostgreSQL 连接；业务代码不在此处创建或修改表。
- `migrations/`：Alembic 版本化数据库迁移；当前包含认证基线和 pgvector 扩展启用。
- `integrations/object_storage.py`：MinIO/S3 兼容私有对象存储客户端适配。
- `workers/queue.py`：Redis/RQ 文档处理队列适配。
- `workers/tasks.py`：无副作用的基础设施测试任务；不承担文档解析业务。
- `workers/runner.py`：文档处理标准 RQ Worker 进程入口，仅在 Linux Worker 容器中运行。
- `Dockerfile.worker`：Worker 的 Python Linux 运行镜像定义；构建时不复制本机 `.env`。
- `scripts/verify_infrastructure.py`：验证 Redis、私有 Bucket、对象写读删除和 RQ 测试任务的本地脚本。
- `docker-compose.infrastructure.yml`：本地 Redis、MinIO 及持久化数据卷的启动配置。
- `dependencies.py`：HTTP Bearer 认证依赖和当前用户解析。
- `routers/auth.py`：认证 HTTP 路由、请求绑定和响应状态。
- `routers/chat.py`：认证保护的聊天路由；尚未连接模型或检索服务。
- `schemas/`：Pydantic 请求/响应模型。
- `services/auth.py`：密码哈希、JWT 签发/校验、会话轮换与撤销业务规则。
- `tests/test_auth_integration.py`：认证 API 到 PostgreSQL 的集成测试；使用唯一测试用户并在每个用例结束后清理测试数据。

## 数据库与存储

当前可由代码确认的 PostgreSQL 对象：

- `users`：用户 ID、唯一邮箱、密码哈希、创建时间和最近登录时间。
- `auth_sessions`：会话 ID、用户 ID、当前刷新令牌标识、会话和刷新令牌到期时间、撤销时间。
- `revoked_tokens`：已撤销访问令牌的标识和过期时间。
- `vector` 扩展：由认证基线迁移请求启用。

已验证：认证表已初始化并由 Alembic `20260720_0001` 管理；本地 MinIO 私有 Bucket 可创建并完成测试对象写读删除。尚未实现：文档元数据、分片、嵌入向量表、向量索引、检索和重排。

## 认证流程

1. 前端认证页调用注册或登录 API。
2. 注册时后端校验邮箱、密码长度和条款同意，随后创建带密码哈希的用户记录。
3. 登录时后端验证密码，创建会话，并返回访问 JWT、刷新 JWT 和用户信息。
4. 前端将令牌和用户信息写入浏览器 `localStorage`，并在启动时以访问令牌调用 `/api/auth/me`。
5. 访问令牌无效时，前端尝试用刷新令牌调用 `/api/auth/refresh`；后端验证会话、轮换刷新令牌标识并返回新令牌对。
6. 受保护接口通过 `Authorization: Bearer <access token>` 解析当前用户。登出时前端请求撤销，随后清除本地会话。
7. 未登录访问 `/app/*` 时，`RequireAuth` 将原路径写入路由状态并跳转 `/login`；登录成功后 `GuestOnly` 回到原路径。已登录用户访问 `/login` 或 `/register` 会跳转至原目标或 `/app/chat`。

## 前端路由

```text
/
├─ /login                 匿名登录页
├─ /register              匿名注册页
├─ /app                   受保护应用入口，重定向至 /app/chat
│  ├─ /app/chat           AI 管家（当前为空页面）
│  ├─ /app/agents         智能体（当前为空页面）
│  └─ /app/knowledge-bases 知识库（当前为空页面）
└─ *                      404 页面
```

## 当前接口

| 接口 | 当前职责 | 状态 |
| --- | --- | --- |
| `GET /api/health` | 返回服务健康状态 | 已实现，未在本次启动验证 |
| `POST /api/auth/register` | 创建用户 | 已实现，PostgreSQL 集成与重复注册测试通过 |
| `POST /api/auth/login` | 验证密码并签发令牌 | 已实现，PostgreSQL 集成与错误密码测试通过 |
| `POST /api/auth/refresh` | 刷新并轮换令牌 | 已实现，轮换与旧令牌重放拒绝测试通过 |
| `GET /api/auth/me` | 获取当前用户 | 已实现，过期会话与撤销访问令牌拒绝测试通过 |
| `POST /api/auth/logout` | 撤销令牌/会话 | 已实现，访问令牌和刷新会话撤销测试通过 |
| `POST /api/chat` | 认证后返回回显文本 | 接口骨架，不是 AI 回答 |
| `GET /api/chat/entry` | 解析当前用户默认智能体，未设置时回退内置 AI 管家 | 已实现，PostgreSQL 集成测试通过 |
| `GET/POST/PATCH/DELETE /api/agents` | 智能体读取、创建、更新、软删除 | 已实现，所有权与内置不可变规则已测试 |
| `PUT /api/agents/{agentId}/default` | 设为当前用户默认个人智能体 | 已实现，集成测试通过 |
| `DELETE /api/agents/default` | 仅清空当前用户默认设置 | 已实现，集成测试通过 |
| `GET/POST /api/conversations` | 按当前智能体列出/创建当前用户会话 | 已实现，用户与智能体隔离已测试 |
| `GET /api/conversations/{conversationId}` | 获取当前用户单个会话及消息 | 已实现，用户隔离已测试 |

## 知识库与智能体工作流

智能体与会话的持久化基础已实现：`routers/agents.py`、`routers/conversations.py` 处理鉴权和 HTTP 契约；`services/agents.py`、`services/conversations.py` 执行业务规则；`repositories/` 集中 PostgreSQL 查询。`agents`、`user_preferences`、`agent_preset_questions`、`conversations`、`messages` 由迁移 `20260723_0002` 创建，内置 AI 管家为固定 UUID 的种子记录。

文档加载、解析、切分、Embedding、向量存储读写、检索、重排、Prompt 管理、模型适配、工具调用或工作流状态定义仍未实现。虽然数据库初始化启用了 pgvector，但这不构成已实现的 RAG 流程。

后续实现应将上述能力放入职责独立的模块（如 `retrieval/`、`agents/`、`workflows/` 与模型/存储 `integrations/`），避免把完整流程堆积到路由或单一服务中。

## 外部依赖与验证

- 前端主要依赖：React、React Router、React Query、Zustand、Ant Design、Vite、TypeScript 和 Tailwind CSS。
- 后端主要依赖：FastAPI、PyJWT、pwdlib（Argon2）、psycopg、pgvector、python-dotenv、Alembic、SQLAlchemy（仅迁移执行）、MinIO SDK、Redis 和 RQ。
- CI：GitHub Actions 对后端运行 Python 编译检查，对前端运行 `pnpm install --frozen-lockfile` 与 `pnpm build`。

本次本地核查已通过后端 Python 编译、Alembic 认证基线对齐、真实 PostgreSQL 认证集成、Redis、MinIO 私有 Bucket 写读删除和 Docker Linux 标准 RQ Worker 测试任务执行；浏览器端到端行为仍待验证。
