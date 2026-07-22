# 项目当前状态

## 当前阶段

功能开发阶段（阶段 1：运行基础设施与数据迁移已完成）。PostgreSQL 认证基线迁移、Redis、MinIO 与 Docker Linux 标准 RQ Worker 已完成本地联调和验证。AI 管家、智能体、会话和知识库的首期正式设计已确认，业务代码仍未实现。

## 当前目标

按已确认的 `agent-knowledge-platform` 设计进入阶段 2：实现智能体、默认打开与会话的数据层和 API，但暂不接入模型、RAG 或文件解析。

认证前端路由现已按匿名区、受保护应用区和 404 页面划分；后续新增 AI、智能体和知识库页面应继续挂载在 `/app/*` 下。

## 已完成功能

- 认证 API：`POST /api/auth/register`、`/login`、`/refresh`、`/logout` 和 `GET /api/auth/me` 已在 `backend/routers/auth.py` 定义；请求与响应模型位于 `backend/schemas/auth.py`。
- 认证持久化：后端启动时创建 `users`、`auth_sessions`、`revoked_tokens` 表，并启用 PostgreSQL 的 `vector` 扩展；实现位于 `backend/database.py`。是否已在任一实际数据库成功初始化：待确认。
- 密码与令牌：服务层使用 Argon2 密码哈希、JWT 访问令牌和可轮换的刷新令牌；实现位于 `backend/services/auth.py`。
- 前端认证界面与状态：注册/登录页面、认证 API 封装、浏览器存储会话、刷新令牌逻辑和基于用户状态的路由已存在于 `frontend/src/`。
- 前端路由边界：`/login`、`/register`、`/app/*` 与 404 页已拆分；受保护页面会在登录后回跳至原始访问地址。已通过 `pnpm build`（2026-07-18）。
- 受保护接口骨架：`POST /api/chat` 需要 Bearer 认证，但当前仅返回回显文本，不是 AI 或 RAG 回答。
- 已验证的构建检查（2026-07-18）：后端关键 Python 模块的 `py_compile` 通过；前端 `pnpm build` 通过。
- PostgreSQL 认证迁移与集成验证（2026-07-22）：确认现有 `users`、`auth_sessions`、`revoked_tokens` 表与认证基线迁移一致后，已执行 Alembic `stamp head`；注册、登录、`/me`、刷新令牌、登出、撤销令牌校验和受保护聊天回显接口均通过真实 PostgreSQL 验证。
- 本地异步基础设施（2026-07-22）：Docker Compose 启动 Redis、MinIO 与 Linux 标准 RQ Worker；验证 Redis `ping`、私有 Bucket 创建、测试文本写读删除及由 Linux Worker 执行的 RQ 测试任务均通过。

## 正在进行

- AI 管家与知识库功能：`AiManagerPage` 当前为空组件，`/app` 和 `/document` 使用空页面；相关业务功能尚未实现。
- 智能体与知识库首期实现：下一步进入阶段 2，待建立智能体、默认设置、会话与消息的数据模型、服务和 API。

## 下一步计划

1. 为认证服务补充自动化测试，覆盖重复注册、错误密码、令牌刷新/轮换、撤销和过期会话。
2. 建立智能体、默认设置、会话和消息的版本化迁移，实现所有权校验、默认打开和会话隔离 API。
3. 实现智能体列表、配置、默认打开和会话侧栏前端页面，并以回显消息验证持久化交互。
4. 建立知识库领域的数据迁移、异步文件处理、检索与流式回答，并执行完整验收测试。

## 阻塞问题

- 无当前代码级阻塞。Redis 与 MinIO 容器需在本地开发时保持运行；生产环境需以独立的受控服务和非默认凭据替代本地 Compose 配置。
- `backend/.env` 中尚未持久化本地 Redis/MinIO 配置；本次联调仅对验证进程注入了开发配置，以避免覆盖既有数据库与 JWT 配置。开始依赖对象存储或队列的后续开发前，需由开发者补齐这些变量。

## 已知风险与技术债务

- 后端数据库表通过启动时的 `CREATE TABLE IF NOT EXISTS` 维护，尚无迁移工具或版本化迁移脚本；结构演进时存在部署与数据兼容风险。
- `AUTH_SECRET_KEY` 在未配置时有开发默认值；部署环境必须显式设置强随机密钥，否则存在令牌安全风险。
- 前端将访问令牌和刷新令牌存入 `localStorage`；XSS 发生时令牌可能暴露。生产场景应重新评估 HttpOnly Cookie 等方案。
- 当前生产构建的未压缩 JavaScript 主包约为 857 kB；路由结构已具备后续按页面进行懒加载和代码分割的边界，但尚未实施。
- 本地 Compose 中的 MinIO 初始账号仅限开发环境；部署前必须改为受控凭据、私有网络和最小权限访问策略。
- `frontend/docs/login.md` 中的部分描述与当前实现不一致（例如其提及 SQLite/后续刷新令牌，而当前代码使用 PostgreSQL 且已实现刷新令牌）。该文件不在本次统一 `docs/` 文档范围内，需后续单独校正。

## 最近更新时间

2026-07-22

## 阶段 1 实施更正（2026-07-20）

- 状态：已完成。
- 已完成：Alembic 认证基线迁移、配置项、对象存储和 RQ 队列适配边界；FastAPI 不再在启动时直接建表。
- 已验证：新增 Python 依赖安装、Python 静态编译和 Alembic 离线 SQL 生成。
- 已验证：Alembic 可连接现有 PostgreSQL，API 健康检查和 RQ 队列对象构造通过。
- 已验证：旧认证表结构与基线一致后已执行 `stamp`；Redis、MinIO 连通、私有 Bucket 写读删除和 RQ 测试任务执行通过。
- 本地运行：通过 `docker-compose.infrastructure.yml` 启动 Redis、MinIO 与 Linux 标准 RQ Worker；验证任务已由容器内的标准 Worker 成功执行。
