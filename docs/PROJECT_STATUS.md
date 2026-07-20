# 项目当前状态

## 当前阶段

功能设计完成，待实施阶段。当前仓库已具备认证基础设施和受认证保护的前端壳页面；AI 管家、智能体、会话和知识库的首期正式设计已确认，但业务代码仍未实现。

## 当前目标

在保持现有认证能力可构建、可运行的基础上，按已确认的 `agent-knowledge-platform` 设计实施智能体、会话、文件处理和 RAG 能力。

认证前端路由现已按匿名区、受保护应用区和 404 页面划分；后续新增 AI、智能体和知识库页面应继续挂载在 `/app/*` 下。

## 已完成功能

- 认证 API：`POST /api/auth/register`、`/login`、`/refresh`、`/logout` 和 `GET /api/auth/me` 已在 `backend/routers/auth.py` 定义；请求与响应模型位于 `backend/schemas/auth.py`。
- 认证持久化：后端启动时创建 `users`、`auth_sessions`、`revoked_tokens` 表，并启用 PostgreSQL 的 `vector` 扩展；实现位于 `backend/database.py`。是否已在任一实际数据库成功初始化：待确认。
- 密码与令牌：服务层使用 Argon2 密码哈希、JWT 访问令牌和可轮换的刷新令牌；实现位于 `backend/services/auth.py`。
- 前端认证界面与状态：注册/登录页面、认证 API 封装、浏览器存储会话、刷新令牌逻辑和基于用户状态的路由已存在于 `frontend/src/`。
- 前端路由边界：`/login`、`/register`、`/app/*` 与 404 页已拆分；受保护页面会在登录后回跳至原始访问地址。已通过 `pnpm build`（2026-07-18）。
- 受保护接口骨架：`POST /api/chat` 需要 Bearer 认证，但当前仅返回回显文本，不是 AI 或 RAG 回答。
- 已验证的构建检查（2026-07-18）：后端关键 Python 模块的 `py_compile` 通过；前端 `pnpm build` 通过。

## 正在进行

- 认证功能的端到端验证：代码和构建已检查，但未在本次核查中连接 PostgreSQL、启动服务或执行浏览器/API 集成测试。
- AI 管家与知识库功能：`AiManagerPage` 当前为空组件，`/app` 和 `/document` 使用空页面；相关业务功能尚未实现。
- 智能体与知识库首期设计：已在 `docs/features/agent-knowledge-platform/` 确认需求、前后端、接口、数据和验收设计，当前待实现。

## 下一步计划

1. 配置本地 PostgreSQL 和所需环境变量后，执行注册、登录、刷新、登出、`/me` 及 `/api/chat` 的集成测试。
2. 为认证服务补充自动化测试，覆盖重复注册、错误密码、令牌刷新/轮换、撤销和过期会话。
3. 建立版本化数据库迁移、对象存储、Redis Worker 和模型/OCR/Embedding 适配基础，并实现资料树与异步文件处理。
4. 实现智能体配置、默认打开、会话持久化和 LangGraph 聊天工作流，再接入资料范围检索和流式回答。
5. 将 `AiManagerPage`、智能体和知识库空页面替换为实际功能页面，并执行设计文档中的验收测试。

## 阻塞问题

- 无代码级阻塞。本次未获得可用于验证的 PostgreSQL 实例和非敏感运行配置，因此数据库初始化与认证集成结果为待确认。

## 已知风险与技术债务

- 后端数据库表通过启动时的 `CREATE TABLE IF NOT EXISTS` 维护，尚无迁移工具或版本化迁移脚本；结构演进时存在部署与数据兼容风险。
- `AUTH_SECRET_KEY` 在未配置时有开发默认值；部署环境必须显式设置强随机密钥，否则存在令牌安全风险。
- 前端将访问令牌和刷新令牌存入 `localStorage`；XSS 发生时令牌可能暴露。生产场景应重新评估 HttpOnly Cookie 等方案。
- 当前生产构建的未压缩 JavaScript 主包约为 857 kB；路由结构已具备后续按页面进行懒加载和代码分割的边界，但尚未实施。
- 智能体与知识库需要新增对象存储、Redis Worker、本地 `bge-m3` 推理依赖及版本化迁移；这些运行依赖尚未部署或验证。
- `frontend/docs/login.md` 中的部分描述与当前实现不一致（例如其提及 SQLite/后续刷新令牌，而当前代码使用 PostgreSQL 且已实现刷新令牌）。该文件不在本次统一 `docs/` 文档范围内，需后续单独校正。

## 最近更新时间

2026-07-20
