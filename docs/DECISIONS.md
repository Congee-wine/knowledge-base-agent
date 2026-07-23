# 技术决策记录

## ADR-008：前端统一升级至 Ant Design 6 与 Ant Design X 2

- **日期**：2026-07-23
- **状态**：已采用

### 背景

用户要求聊天界面使用最新 Ant Design X。最新 `@ant-design/x` 2.8 要求 Ant Design 6，而项目原有 Ant Design 5.29 与 `@ant-design/pro-components` 2.8。

### 可选方案

1. 保持 Ant Design 5，降级使用 Ant Design X 1.x。
2. 升级 Ant Design 及图标库至 6.x，使用 Ant Design X 2.x；移除不支持 Ant Design 6 的 Pro Components。

### 最终决定

采用方案 2。升级到 Ant Design 6.5.1、Ant Design X 2.8.0 和 Ant Design X Markdown 2.8.0；登录页唯一的 `ProCard` 使用替换为 Ant Design 原生 `Card`，移除 `@ant-design/pro-components`。

### 选择理由

满足使用最新 AI 组件库的明确要求，同时避免让一个只使用一次的 Pro Components 依赖阻塞整个组件栈升级。原生 `Card` 足以承担登录卡片职责，减少额外依赖。

### 影响与代价

这是前端主组件库升级，可能影响后续 Ant Design 组件样式或 API；本次已通过 TypeScript 和 Vite 生产构建。JavaScript 压缩包约 1 MB，后续需要通过路由懒加载降低首屏体积。

### 后续条件

新增或改造页面时继续运行 `pnpm build`；页面数量增长后实施路由级动态导入和代码分割。

## ADR-007：内置智能体使用固定 UUID，默认设置显式清空

- **日期**：2026-07-23
- **状态**：已采用

### 背景

AI 管家是所有用户可用但不可编辑、不可删除的系统记录；同时用户可以选择某个个人智能体作为默认入口，或取消这一选择。资料范围依赖阶段 3 尚未存在的知识库表。

### 可选方案

1. 使用字符串哨兵表示内置 AI 管家，删除默认个人智能体时隐式回退。
2. 使用固定 UUID 和 `kind=builtin` 表示内置记录，提供独立的清空默认接口，资料范围延后实施。

### 最终决定

采用方案 2。内置 AI 管家固定为 UUID `00000000-0000-0000-0000-000000000001`，`kind` 为 `builtin`；个人智能体为 `kind=personal`。`DELETE /api/agents/default` 仅把当前用户的默认设置置空，不删除智能体；默认智能体必须先清空设置才能软删除。`knowledgeScopes` 和 `agent_knowledge_scopes` 延后到阶段 3。

### 选择理由

UUID 保持所有资源标识符格式一致并可安全作为外键；`kind` 让接口和前端明确区分系统内置与个人资源，但权限仍由后端强制校验。将“取消默认”和“删除实体”拆开，避免一个接口含有两种不可逆语义，也不会留下指向软删除记录的默认值。资料范围不能引用尚未创建的知识库节点。

### 影响与代价

新增 `agents`、`user_preferences` 等业务表及迁移；前端需要基于 `kind` 决定展示标签和可用操作。阶段 2 不提供资料范围配置，相关 UI/API 必须等待阶段 3。

### 后续条件

阶段 3 创建 `knowledge_nodes` 后，再迁移并实现 `agent_knowledge_scopes`、所有权校验和文件夹范围展开。

## ADR-006：第一阶段基础设施依赖与迁移边界

- **日期**：2026-07-20
- **状态**：已采用

### 背景

认证表当前由 FastAPI 启动时的 DDL 创建，无法记录数据库实际版本；知识库还需要私有文件存储和不阻塞 HTTP 请求的后台处理。用户要求每个开发阶段都有详细且可解释的后端与 AI 开发计划。

### 可选方案

1. 继续由应用启动代码创建、修改数据库表，并在 HTTP 请求中同步解析文件。
2. 采用 Alembic 维护数据库迁移，使用 MinIO S3 兼容 SDK 保存私有源文件，使用 Redis + RQ 执行后台任务。
3. 改为完整 ORM、Celery 和云厂商专有存储服务。

### 最终决定

采用方案 2。保留现有 psycopg Repository 访问模式；Alembic 仅作为迁移执行器，避免无必要地同时引入 SQLAlchemy ORM。MinIO SDK 通过适配器使用，RQ 仅用于文件解析、切分和向量化等可重试的耗时任务。

### 选择理由

Alembic 使每次结构变化成为可审查、可升级的脚本；MinIO Python SDK 同时兼容 MinIO 与 S3 兼容存储；RQ 不需要预先定义复杂消息路由，适合当前单人维护且任务类型有限的项目。[Alembic 文档](https://alembic.sqlalchemy.org/en/latest/)、[MinIO Python SDK 文档](https://docs.min.io/aistor/developers/sdk/python/)、[RQ 文档](https://python-rq.org/docs/)

### 影响与代价

新增 `alembic`、`SQLAlchemy`、`minio`、`redis`、`rq` 依赖，并需要运行 PostgreSQL/pgvector、Redis 和 S3 兼容存储。本地开发通过 Docker Desktop 和 `docker-compose.infrastructure.yml` 运行 Redis、MinIO 与 Linux Worker，已验证对象存储和标准 RQ 测试任务。为统一开发与部署，标准 `Worker` 运行在 Linux 容器中，而不是在 Windows 使用 `SimpleWorker`；镜像通过配置的本地开发镜像加速器成功构建。

### 后续条件

阶段 3 才增加 PyMuPDF、python-docx、LangChain 文本切分器和本地 bge-m3 推理依赖；阶段 4 才增加 LangGraph 与 DeepSeek Chat 适配。每次新增依赖均先说明作用和验证结果。

> 本文件中的“已采用”表示该选择可由当前代码直接观察到；历史决策日期未保留时，使用本次核查日期记录。

## ADR-005：智能体、会话和知识库的首期技术方案

- **日期**：2026-07-20
- **状态**：已采用

### 背景

项目已确认需要多账号隔离的内置 AI 管家、用户自建智能体、默认打开规则、会话历史，以及支持 PDF、Markdown、图片的可选文件/文件夹检索范围。现有仓库已有 React、FastAPI、PostgreSQL 和 pgvector 基础，但业务页面和真实问答流程尚未实现。

### 可选方案

1. 更换为一体化智能体/RAG 平台或直接在前端调用模型服务。
2. 保留现有前后端分离架构，在后端以自有模块实现首期会话和 RAG 流程；模型、Embedding、OCR 和对象存储通过适配接口隔离。
3. 一开始引入 LangChain、LangGraph、独立向量数据库和复杂多智能体工作流。

### 最终决定

采用方案 2：保留 React + TypeScript + Vite + Ant Design + Ant Design X + React Query + Zustand 前端，保留 FastAPI + Pydantic 后端和 PostgreSQL + pgvector；原始文件存入 S3 兼容对象存储（本地开发可用 MinIO），长耗时解析与嵌入通过 Redis 队列和独立 Worker 执行。首期受控采用 LangChain 和 LangGraph：LangChain 负责聊天模型与 Embedding 适配、提示词模板、统一 `Document` 对象和文本切分；LangGraph 使用显式、无循环的状态图编排“加载会话上下文 → 检索资料 → 生成回答 → 持久化结果”，并将状态和令牌事件流式传给 API 层。首期聊天模型供应商确定为 DeepSeek，通过其 OpenAI 兼容 Chat Completions 接口适配；Embedding 采用本地 `BAAI/bge-m3`，在独立 Worker 中运行，模型权重不经云端 Embedding API 传输。PDF 使用 PyMuPDF 提取文本，TXT/Markdown 使用本地解析，Word（`.docx`）使用 `python-docx` 提取正文；首期不支持图片、扫描版 PDF 和 OCR。

### 选择理由

现有架构已能承载该方案，避免在需求仍增长时更换前后端基础设施。PostgreSQL 同时保存账号、会话、智能体和知识库元数据，pgvector 保存分块向量，便于在同一事务和查询中强制 `user_id` 隔离。对象存储避免把大文件放入关系表；后台任务避免上传/索引阻塞 HTTP 请求，并可记录处理状态和重试。LangChain 为模型、Embedding、提示词和文本切分提供统一且可替换的接口；LangGraph 以显式状态与节点输出保留流程追踪、流式状态通知和将来添加节点的边界。首期需求尚未出现多工具规划、循环决策或人工审批流程，因此不使用通用 Agent/ReAct 循环，不让图节点直接访问数据库，也不向路由层暴露 LangChain/LangGraph 类型；节点只调用职责独立的业务服务，确保仍可单独测试和定位问题。

### 影响与代价

需要在正式实施前新增并评估数据库迁移工具、对象存储客户端、DOCX 解析、Redis、后台任务、Ant Design X 和本地 BGE 推理依赖；还需要部署 PostgreSQL/pgvector、Redis、对象存储和 Worker。`bge-m3` 模型权重和本地推理需要磁盘、内存与 CPU 资源，但没有按次 Embedding API 费用。不能把 DeepSeek 密钥或其他供应商地址写入代码或文档。大规模向量数据时需评估 pgvector 索引参数、召回率、延迟和成本；首期应先以可验证的精确检索/小规模索引开始，再基于实际数据选择 HNSW 或 IVFFlat。

### 后续条件

在实施前锁定 DeepSeek 的具体聊天模型、`bge-m3` 推理库及依赖版本，并完成本地资源与成本评估。图片/OCR 作为后续独立需求重新设计。若后续增加网页搜索、外部系统操作、多轮工具规划或审批工作流，再在现有 LangGraph 工作流上新增受控节点、工具白名单和审批边界，而非将其放入聊天路由。

## ADR-004：前端按认证边界组织嵌套路由

- **日期**：2026-07-18
- **状态**：已采用

### 背景

原前端根据用户状态渲染两套路由，并以通配符承接所有匿名地址，无法表达登录、注册、404 与登录后回跳的独立语义。

### 可选方案

1. 维持条件渲染的两套路由。
2. 使用集中定义的路径常量，并通过匿名与认证守卫组织单套路由树。
3. 引入数据路由配置和额外路由框架能力。

### 最终决定

采用 React Router 现有能力，在 `routes/` 中定义路径常量、`GuestOnly` 和 `RequireAuth`，业务页面统一置于 `/app/*`。

### 选择理由

不新增依赖即可使认证边界、URL 语义、404 和登录回跳成为独立职责；现有 `AppLayout` 可作为受保护应用区的嵌套布局复用。

### 影响与代价

旧业务路径不再可用；未来如需兼容外部链接，应显式增加过渡重定向。当前业务页面仍为占位内容，尚未实施路由级懒加载。

### 后续条件

页面数量或包体积继续增长时，评估将页面导入调整为 `lazy` 和 `Suspense`，并为业务子路由增加更细粒度的权限策略。

## ADR-001：前后端分离的 Web 应用结构

- **日期**：2026-07-18
- **状态**：已采用

### 背景

仓库分为 `frontend/` 和 `backend/`，需要明确当前已采用的职责边界。

### 可选方案

1. React/Vite 前端与 FastAPI 后端独立开发和部署。
2. 由后端直接渲染页面。
3. 单一全栈框架承载前后端。

### 最终决定

当前实现采用 React + TypeScript + Vite 前端与 FastAPI 后端，通过 HTTP API 通信。

### 选择理由

该结构已在目录、依赖和 CI 中落实，前端可独立执行 TypeScript 构建，后端可独立进行 Python 编译检查。

### 影响与代价

前后端职责清晰，但需要维护跨域配置、环境变量和接口契约；当前后端 CORS 仅允许本地 `localhost`/`127.0.0.1` 的 HTTP 开发地址。

### 后续条件

部署、服务端渲染或多客户端需求出现时，重新评估部署拓扑和跨域策略。

## ADR-002：基于 PostgreSQL 的认证数据与 pgvector 预留

- **日期**：2026-07-18
- **状态**：已采用

### 背景

用户、会话和令牌撤销状态需要持久化；项目定位包含知识库能力。

### 可选方案

1. PostgreSQL 保存关系数据并启用 pgvector。
2. SQLite 作为本地关系数据库。
3. 仅使用外部认证和向量服务。

### 最终决定

当前后端使用 `psycopg` 连接 PostgreSQL，在启动时启用 `vector` 扩展，并创建认证相关表。

### 选择理由

`backend/database.py` 与 `requirements.txt` 已直接采用 PostgreSQL 和 `pgvector`。但当前尚无文档向量表或检索实现，pgvector 仅为已启用的基础能力，不能视为知识库已完成。

### 影响与代价

需要可用的 PostgreSQL 实例及支持扩展安装的权限；目前缺少版本化数据库迁移。

### 后续条件

引入实际文档索引、分片和检索时，需单独记录向量表设计、索引参数、召回与成本取舍。

## ADR-003：JWT 访问令牌配合可轮换刷新令牌

- **日期**：2026-07-18
- **状态**：已采用

### 背景

前端需要保持登录状态，后端需要识别会话撤销和令牌过期。

### 可选方案

1. 短期 JWT 访问令牌，加服务端会话记录和可轮换刷新令牌。
2. 仅使用长期 JWT。
3. 服务端 Cookie Session。

### 最终决定

当前代码签发短期访问 JWT，并在 `auth_sessions` 保存刷新令牌标识、会话有效期与撤销时间；刷新时轮换标识，登出时撤销访问令牌和刷新会话。

### 选择理由

该方案已由 `backend/services/auth.py`、认证路由和前端会话工具实现，可兼顾 API Bearer 认证和会话撤销。

### 影响与代价

需要额外数据库查询验证令牌/会话；前端当前使用 `localStorage` 保存两类令牌，存在 XSS 暴露风险。

### 后续条件

面向生产部署前，应评估改用 HttpOnly Cookie、CSRF 防护、限流、密钥轮换和审计策略。
