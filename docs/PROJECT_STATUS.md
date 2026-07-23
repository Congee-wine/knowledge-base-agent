# 项目当前状态

## 当前阶段

功能开发阶段（阶段 2：智能体、默认打开与会话基础）。PostgreSQL 认证基线迁移、Redis、MinIO 与 Docker Linux 标准 RQ Worker 已完成本地联调和验证。智能体、默认打开与会话数据层/API 已完成真实 PostgreSQL 集成验证；模型、RAG、文件解析和前端业务页面仍未实现。

## 当前目标

按已确认的 `agent-knowledge-platform` 设计进入阶段 2：实现智能体、默认打开与会话的数据层和 API，但暂不接入模型、RAG 或文件解析。

认证前端路由现已按匿名区、受保护应用区和 404 页面划分；后续新增 AI、智能体和知识库页面应继续挂载在 `/app/*` 下。

## 已完成功能

- 认证 API：`POST /api/auth/register`、`/login`、`/refresh`、`/logout` 和 `GET /api/auth/me` 已在 `backend/routers/auth.py` 定义；请求与响应模型位于 `backend/schemas/auth.py`。
- 认证持久化：`users`、`auth_sessions`、`revoked_tokens` 表和 `vector` 扩展由 Alembic 基线迁移 `20260720_0001` 管理；已与本地 PostgreSQL 现有表对齐并完成集成验证。
- 密码与令牌：服务层使用 Argon2 密码哈希、JWT 访问令牌和可轮换的刷新令牌；实现位于 `backend/services/auth.py`。
- 前端认证界面与状态：注册/登录页面、认证 API 封装、浏览器存储会话、刷新令牌逻辑和基于用户状态的路由已存在于 `frontend/src/`。
- 前端路由边界：`/login`、`/register`、`/app/*` 与 404 页已拆分；受保护页面会在登录后回跳至原始访问地址。已通过 `pnpm build`（2026-07-18）。
- 受保护接口骨架：`POST /api/chat` 需要 Bearer 认证，但当前仅返回回显文本，不是 AI 或 RAG 回答。
- 已验证的构建检查（2026-07-18）：后端关键 Python 模块的 `py_compile` 通过；前端 `pnpm build` 通过。
- PostgreSQL 认证迁移与集成验证（2026-07-22）：确认现有 `users`、`auth_sessions`、`revoked_tokens` 表与认证基线迁移一致后，已执行 Alembic `stamp head`；注册、登录、`/me`、刷新令牌、登出、撤销令牌校验和受保护聊天回显接口均通过真实 PostgreSQL 验证。
- 认证自动化测试（2026-07-22）：新增 5 个 `unittest` 集成测试，覆盖重复注册、错误密码、刷新令牌轮换与重放拒绝、登出后令牌撤销和过期会话拒绝；均已通过，且测试数据已清理。
- 本地异步基础设施（2026-07-22）：Docker Compose 启动 Redis、MinIO 与 Linux 标准 RQ Worker；验证 Redis `ping`、私有 Bucket 创建、测试文本写读删除及由 Linux Worker 执行的 RQ 测试任务均通过。
- 智能体与会话后端基础（2026-07-23）：Alembic `20260723_0002` 创建智能体、用户默认设置、预设问题、会话和消息表，并写入内置 AI 管家种子记录；智能体 CRUD、默认设置/清空、聊天入口和会话查询 API 通过真实 PostgreSQL 集成测试。

## 正在进行

- 前端 AI 管家、智能体与知识库页面仍为空组件，尚未消费阶段 2 API。
- 阶段 2 后端基础已完成：智能体 CRUD、默认打开/清空、聊天入口和会话创建/查询已实现；尚未实现消息发送、回显持久化、SSE 和前端联调。

## 下一步计划

1. 实现智能体列表、配置、默认打开和会话侧栏前端页面，并以回显消息验证持久化交互。
2. 完成阶段 2 消息写入与回显接口，再进行前后端联调。
3. 建立知识库领域的数据迁移、异步文件处理、检索与流式回答，并执行完整验收测试。

## 阻塞问题

- 无当前代码级阻塞。Redis 与 MinIO 容器需在本地开发时保持运行；生产环境需以独立的受控服务和非默认凭据替代本地 Compose 配置。

## 已知风险与技术债务

- 后续业务表必须继续通过 Alembic 迁移管理，禁止恢复启动时自动建表；部署环境必须在应用启动前执行迁移并设置强随机 `AUTH_SECRET_KEY`。
- 前端将访问令牌和刷新令牌存入 `localStorage`；XSS 发生时令牌可能暴露。生产场景应重新评估 HttpOnly Cookie 等方案。
- 当前生产构建的未压缩 JavaScript 主包约为 857 kB；路由结构已具备后续按页面进行懒加载和代码分割的边界，但尚未实施。
- 本地 Compose 中的 MinIO 初始账号仅限开发环境；部署前必须改为受控凭据、私有网络和最小权限访问策略。
- 阶段 2 的会话列表尚未实现 cursor 翻页，当前以最多 100 条的参数限制返回；前端接入和数据量增长前应补齐游标契约。
- `frontend/docs/login.md` 中的部分描述与当前实现不一致（例如其提及 SQLite/后续刷新令牌，而当前代码使用 PostgreSQL 且已实现刷新令牌）。该文件不在本次统一 `docs/` 文档范围内，需后续单独校正。

## 最近更新时间

2026-07-23

## 阶段 1 实施更正（2026-07-20）

- 状态：已完成。
- 已完成：Alembic 认证基线迁移、配置项、对象存储和 RQ 队列适配边界；FastAPI 不再在启动时直接建表。
- 已验证：新增 Python 依赖安装、Python 静态编译和 Alembic 离线 SQL 生成。
- 已验证：Alembic 可连接现有 PostgreSQL，API 健康检查和 RQ 队列对象构造通过。
- 已验证：旧认证表结构与基线一致后已执行 `stamp`；Redis、MinIO 连通、私有 Bucket 写读删除和 RQ 测试任务执行通过。
- 本地运行：通过 `docker-compose.infrastructure.yml` 启动 Redis、MinIO 与 Linux 标准 RQ Worker；验证任务已由容器内的标准 Worker 成功执行。
