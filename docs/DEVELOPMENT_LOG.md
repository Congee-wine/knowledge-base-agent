# 开发日志

## 2026-07-23：阶段 2 智能体、默认打开与会话后端基础

### 任务目标

实现不依赖模型或知识库的智能体和会话持久化基础，使默认打开、资源所有权、软删除和会话侧栏范围可被后端独立验证。

### 实现内容

- 新增 Alembic 迁移 `20260723_0002`，创建 `agents`、`user_preferences`、`agent_preset_questions`、`conversations` 和 `messages`，并写入固定 UUID 的内置 AI 管家种子记录。
- 新增 Repository、Service、Schema 和 Router 分层，实现个人智能体 CRUD、软删除、默认设置与清空、聊天入口解析、会话创建/读取/按智能体列表查询。
- 所有自有资源查询强制带当前认证用户 ID；内置智能体使用 `kind=builtin`，后端拒绝编辑/删除；删除默认个人智能体前必须先清空默认设置。
- 资料范围字段和 `agent_knowledge_scopes` 未在本阶段实现，等待阶段 3 创建 `knowledge_nodes`。

### 主要文件

- `backend/migrations/versions/20260723_0002_agents_conversations.py`：阶段 2 业务表、约束、索引和内置种子迁移。
- `backend/repositories/agents.py`、`backend/repositories/conversations.py`：集中 PostgreSQL 访问与所有权过滤。
- `backend/services/agents.py`、`backend/services/conversations.py`、`backend/services/errors.py`：业务规则和统一领域错误。
- `backend/routers/agents.py`、`backend/routers/conversations.py`：受保护 API 入口。
- `backend/tests/test_agents_conversations_integration.py`：真实 PostgreSQL 的默认回退、不可变、软删除、用户隔离和会话范围测试。
- `docs/features/agent-knowledge-platform/`、`docs/PROJECT_STATUS.md`、`docs/ARCHITECTURE.md`、`docs/DECISIONS.md`、`docs/QUESTIONS.md`：同步确认的接口、数据模型、决策和进度。

### 技术方案

使用固定 UUID 而非字符串哨兵表示内置 AI 管家，使所有智能体 ID 都可作为 UUID 外键使用；以 `kind` 区分内置和个人类型，但不把权限交给前端。将清空默认设置设计为独立接口，避免“删除智能体”同时隐式更改用户偏好。路由层只绑定 HTTP 和认证，服务层处理业务规则，仓储层集中 SQL，便于隔离测试和后续扩展消息生成流程。

### 接口或数据变化

- 新增 `GET /api/chat/entry`、`GET/POST/PATCH/DELETE /api/agents`、`PUT /api/agents/{agentId}/default`、`DELETE /api/agents/default`、`GET/POST /api/conversations`、`GET /api/conversations/{conversationId}`。
- 新增阶段 2 数据库迁移，已在本地 PostgreSQL 执行 `alembic upgrade head`，当前版本为 `20260723_0002`。
- 未新增依赖；未实现消息发送、SSE、模型、RAG 或知识库资料范围。

### 验证情况

- 通过：`python -m compileall -q main.py routers schemas services repositories migrations tests`。
- 通过：`alembic upgrade head` 和 `alembic current`，当前版本 `20260723_0002 (head)`。
- 通过：4 个智能体/会话真实 PostgreSQL 集成测试，覆盖内置默认、内置不可删除、更新、默认清空、软删除、用户隔离和按智能体会话过滤。
- 通过：既有 5 个认证集成测试全部通过。
- 通过：`git diff --check`。
- 警告：测试仍输出既有 `TestClient/httpx` 弃用提示；本次未升级依赖。

### 遗留问题

- 会话列表暂未提供 cursor 翻页，阶段 2 前端联调前需要补齐。
- 消息写入/回显、SSE 与前端页面仍未实现；知识库资料范围需等待阶段 3。

## 2026-07-22：认证服务自动化集成测试

### 任务目标

将已完成的认证手工验证固化为可重复执行的测试，覆盖令牌轮换、撤销和会话过期等核心安全行为，为阶段 2 的受保护业务接口提供回归安全网。

### 实现内容

- 新增 `backend/tests/test_auth_integration.py`，使用 Python 标准库 `unittest` 与 FastAPI `TestClient` 执行真实 PostgreSQL 集成测试。
- 覆盖重复注册拒绝、错误密码拒绝、刷新令牌轮换与旧令牌重放拒绝、登出后的访问/刷新令牌失效，以及过期会话拒绝。
- 每个用例生成唯一测试邮箱，并在结束后删除该测试用户的会话、用户记录和撤销令牌，避免污染开发数据库。

### 主要文件

- `backend/tests/test_auth_integration.py`：认证路由、服务、JWT 与 PostgreSQL 的集成测试。
- `backend/tests/__init__.py`：测试包标记，支持模块化执行。
- `docs/PROJECT_STATUS.md`、`docs/ARCHITECTURE.md`：同步认证验证状态和测试模块职责。

### 技术方案

使用 `unittest` 避免为当前有限的测试集引入额外依赖。测试不模拟数据库连接，因为令牌轮换、会话撤销和过期判断都依赖真实 PostgreSQL 状态；通过唯一标识和精确清理实现与本地开发数据隔离。

### 接口或数据变化

无新增 HTTP API、业务表或依赖。测试运行期间临时写入并清理认证相关记录。

### 验证情况

- 通过：`python -m unittest tests.test_auth_integration -v`，5 个测试全部通过。
- 通过：测试后确认无残留 `auth-test-*` 用户。
- 警告：FastAPI 依赖中的 `TestClient` 输出上游弃用提示；本次未升级依赖，测试结果不受影响。

### 遗留问题

- 当前测试使用本地开发 PostgreSQL；后续 CI 应配置隔离测试数据库，避免共享环境并发执行。

## 2026-07-22：Linux 标准 RQ Worker 构建与执行验证

### 任务目标

完成 Docker Linux Worker 镜像构建，并验证由本机投递、容器内标准 RQ Worker 执行的任务链路。

### 实现内容

- 在 Docker Desktop 的用户级 daemon 配置中保留原有构建设置并添加一个本地开发镜像加速器，重启 Docker Engine 后确认配置生效。
- 成功拉取 `python:3.12-slim` 并构建 Worker 镜像；恢复 Redis、MinIO 和 Worker 容器。
- 从 Windows 本机运行验证脚本投递任务，Worker 容器日志确认标准 RQ Worker 成功执行；任务结果校验执行平台为 Linux。
- 清理本次探针任务记录，未修改业务队列、业务文件或数据库数据。

### 主要文件

- `backend/Dockerfile.worker`、`backend/.dockerignore`：Worker 镜像定义与构建上下文安全边界。
- `docker-compose.infrastructure.yml`：Redis、MinIO 与 Linux Worker 的本地编排。
- `backend/workers/runner.py`、`backend/workers/tasks.py`、`backend/scripts/verify_infrastructure.py`：标准 Worker 入口与 Linux 执行验证。

### 技术方案

Docker Desktop 的 Linux 容器支持 RQ 标准 Worker 所需的 Unix 子进程模型。镜像加速器仅作用于本机 Docker 拉取，不写入项目源码或文档中的敏感凭据；生产部署仍应使用受控镜像仓库和镜像摘要管理。

### 接口或数据变化

无新增 HTTP API、业务表或生产依赖。新增本机 Docker 镜像缓存、Worker 容器及开发镜像加速器配置。

### 验证情况

- 通过：Docker Engine 已识别配置的 registry mirror，`python:3.12-slim` 拉取成功。
- 通过：Worker 镜像构建，Redis、MinIO、Worker 容器运行。
- 通过：验证脚本通过；Worker 日志确认标准 RQ Worker 在 Linux 容器中成功执行探针任务。
- 通过：探针任务记录已清理，队列无待处理探针任务。

### 遗留问题

- `backend/.env` 仍需由开发者持久化 Redis 与 MinIO 的本地开发配置，避免后续脚本依赖临时环境变量。

## 2026-07-22：Linux 标准 RQ Worker 容器化尝试

### 任务目标

将 RQ Worker 从 Windows 本地兼容模式调整为 Docker Linux 容器中的标准 Worker，使其运行模型与后续部署保持一致。

### 实现内容

- 新增 `backend/Dockerfile.worker` 和 `.dockerignore`，镜像安装现有后端依赖且不复制本机 `.env`。
- 为 Compose 新增 `worker` 服务，容器内通过 `redis`、`minio` 服务名访问基础设施，并挂载后端源码用于本地开发。
- 移除 `SimpleWorker` 分支；Worker 入口现在统一使用标准 RQ `Worker`。
- 测试任务增加 Linux 平台标识，验证脚本只有在任务由 Linux 容器执行时才通过。

### 主要文件

- `backend/Dockerfile.worker`：标准 Worker 镜像定义。
- `backend/.dockerignore`：防止本机环境文件和虚拟环境进入镜像构建上下文。
- `docker-compose.infrastructure.yml`：新增 Worker 服务及容器内网络配置。
- `backend/workers/runner.py`、`backend/workers/tasks.py`、`backend/scripts/verify_infrastructure.py`：标准 Worker 运行与 Linux 执行结果验证。

### 技术方案

Docker Desktop 运行 Linux 容器，因此 RQ 标准 Worker 可以使用 Unix 子进程模型。FastAPI 仍可在 Windows 本机通过映射端口投递任务；Worker 在 Compose 网络内使用服务名访问 Redis 和 MinIO。后续 Worker 如需连接当前本机 PostgreSQL，必须显式使用 Docker Desktop 宿主机地址，不能使用容器内 `127.0.0.1`。

### 接口或数据变化

无新增 HTTP API、业务表或生产依赖。新增待构建的 Worker 镜像与 Compose 服务。

### 验证情况

- 通过：新增 Python 模块静态编译和 Compose 配置校验。
- 未通过：Docker 构建 `python:3.12-slim` 时无法连接 `auth.docker.io` 获取令牌，重试后同样失败；本地不存在可离线使用的 Python 基础镜像。
- 未执行：Linux 容器中的标准 Worker 任务执行验证；需在镜像成功构建后执行。

### 遗留问题

- 需恢复 Docker Hub 网络访问或在 Docker Desktop 配置可用的镜像加速器/代理后重试构建。

## 2026-07-22：Redis、MinIO 与 RQ Worker 本地联调

### 任务目标

完成第一阶段剩余的对象存储、任务队列与 Worker 可运行性验证，不引入文件解析、Embedding、模型调用或 RAG 业务代码。

### 实现内容

- 新增 `docker-compose.infrastructure.yml`，用 Docker Desktop 启动 Redis 7.4.2 与 MinIO，并使用命名数据卷保留本地开发数据。
- 新增无副作用的 RQ 测试任务、跨平台 Worker 进程入口和基础设施验证脚本。
- 验证 Redis `ping`、私有 Bucket 自动创建、测试文本写入/读取/删除，以及测试任务投递和执行。
- Windows 本地将 RQ Worker 切换为 `SimpleWorker`，避免标准 `Worker` 对 Unix 子进程模型的依赖；Linux 环境仍使用标准 Worker。
- 为避免覆盖现有数据库与 JWT 配置，本次仅在验证进程中注入本地 Redis/MinIO 配置；`backend/.env` 尚待开发者手动补齐相应变量。

### 主要文件

- `docker-compose.infrastructure.yml`：本地 Redis、MinIO 和数据卷配置。
- `backend/workers/tasks.py`：无副作用的 Worker 探针任务。
- `backend/workers/runner.py`：根据操作系统选择 RQ Worker 实现的进程入口。
- `backend/scripts/verify_infrastructure.py`：Redis、MinIO 与 RQ 的端到端基础设施验证。
- `docs/PROJECT_STATUS.md`、`docs/ARCHITECTURE.md`、`docs/DECISIONS.md`：同步真实运行状态和平台差异。

### 技术方案

Redis 只保存队列和任务状态，MinIO 保存原始大文件，PostgreSQL 继续负责关系数据和元数据。验证脚本对 MinIO 使用临时对象并立即删除，避免将测试文件误当作业务资料。Windows 使用 `SimpleWorker` 是本地兼容性措施，生产 Linux 仍保留隔离性更好的标准 RQ Worker。

### 接口或数据变化

未新增 HTTP API、业务表或生产依赖。Docker 新增本地 Redis/MinIO 容器、网络与命名数据卷；MinIO 创建了私有开发 Bucket。

### 验证情况

- 通过：Docker Compose 配置校验，Redis 容器健康，MinIO 容器运行。
- 通过：Redis `ping`、MinIO Bucket 创建与测试文件写读删除。
- 通过：RQ 测试任务返回“Worker 已运行”。
- 通过：对象存储配置缺失时明确列出 `OBJECT_STORAGE_ENDPOINT`、`OBJECT_STORAGE_ACCESS_KEY` 和 `OBJECT_STORAGE_SECRET_KEY`。
- 通过：新增 Python 模块静态编译。
- 未执行：浏览器端到端测试、真实文件解析、向量化、模型调用和 RAG 测试；均不属于第一阶段范围。

### 遗留问题

- 进入阶段 2 前仍需为认证服务补充自动化测试。
- 本地 MinIO 初始账号只限开发环境，后续部署必须替换为非默认凭据。

## 2026-07-22：认证基础设施真实集成验证

### 任务目标

验证本地 PostgreSQL 的认证表与 Alembic 认证基线迁移一致，并完成认证接口的真实数据库集成检查。

### 实现内容

- 检查本机 PostgreSQL 连接、现有认证表结构及 Alembic 版本状态。
- 确认旧认证表与 `20260720_0001` 迁移定义一致后，使用 `alembic stamp head` 将现有结构纳入版本管理，未重复创建表。
- 使用临时测试用户完成注册、登录、获取当前用户、刷新令牌、登出、撤销令牌拒绝及受保护聊天回显接口验证；测试结束后清理测试用户、会话和撤销令牌。

### 主要文件

- `docs/PROJECT_STATUS.md`：同步 PostgreSQL 验证结果、Redis/MinIO 联调阻塞和后续计划。
- `docs/DEVELOPMENT_LOG.md`：记录本次真实集成验证过程。

### 技术方案

对已存在但无 Alembic 版本记录的认证表，先逐字段比对迁移定义再执行 `stamp`，避免对已有表重复运行建表迁移。集成测试通过 FastAPI `TestClient` 调用真实 PostgreSQL，覆盖令牌轮换和撤销行为。

### 接口或数据变化

数据库新增 `alembic_version` 记录，值为 `20260720_0001`；认证业务表结构、API 契约和应用依赖均未修改。

### 验证情况

- 通过：Alembic 认证基线版本已记录为 `20260720_0001`。
- 通过：注册（201）、登录（200）、`/me`（200）、受保护 `/api/chat`（200）、刷新令牌（200）、登出（204）和已撤销访问令牌拒绝（401）。
- 未执行：Redis、MinIO、RQ Worker 与浏览器端到端测试；本机未发现 Redis/MinIO 服务且对象存储配置未填写。

### 遗留问题

- 需启动并配置 Redis、MinIO 后再验证对象存储和异步文档处理能力。

## 2026-07-20：阶段 1 数据库迁移与基础设施边界

### 任务目标

将认证表从 FastAPI 启动时直接执行的 DDL 迁移到版本化脚本，并为私有对象存储和后台任务建立独立适配边界。

### 实现内容

- 新增 Alembic 迁移环境和认证基线迁移。
- 移除应用启动时自动建表逻辑；服务启动不再隐式修改数据库结构。
- 集中补充 Redis、对象存储、DeepSeek 和 BGE 的环境变量定义。
- 新增 MinIO 和 RQ 的最小适配器；尚未投递真实文档任务。

### 主要文件

- `backend/migrations/`：数据库版本化迁移及旧认证数据库的安全接入说明。
- `backend/integrations/object_storage.py`：私有对象存储客户端创建边界。
- `backend/workers/queue.py`：文档处理队列创建边界。
- `backend/config.py`：集中、显式的运行配置。

### 技术方案

使用 Alembic 管理结构变更，保留 psycopg 作为业务 Repository 的数据库访问驱动；文件和异步任务均不由路由直接处理。

### 接口或数据变化

- 新增数据库迁移基线 `20260720_0001`，数据库须执行 `alembic upgrade head` 后才能运行 API。
- 未新增业务 API。

### 验证情况

- 新增依赖已在 `backend/.venv` 安装成功。
- `python -m compileall -q .` 通过。
- `alembic upgrade head --sql` 通过，已生成认证基线的 PostgreSQL DDL，但未对真实数据库执行。
- `alembic current` 已成功连接现有 PostgreSQL；修复了 Alembic 默认尝试使用 psycopg2 的兼容问题，改为显式使用项目已有的 psycopg 3 方言。
- FastAPI `/api/health` 测试和 RQ 队列对象构造测试通过；对象存储缺少配置时会明确列出缺失环境变量。
- Redis、MinIO 与真实 PostgreSQL 尚未运行，连通性和 Worker 执行仍待验证。

### 遗留问题

- 开发机未检测到 Docker；需要后续提供可用的 PostgreSQL/pgvector、Redis 和 MinIO 服务后执行联调。

## 2026-07-20：AI 管家会话侧栏规则修正

### 任务目标

根据用户纠正，移除 AI 管家显示其他智能体会话的规则，统一会话历史隔离边界。

### 实现内容

- 统一内置 AI 管家与自建智能体的会话侧栏规则：只展示当前智能体自身会话。
- 移除聊天入口返回会话范围、全局会话查询和来源智能体展示的设计。

### 主要文件

- `docs/features/agent-knowledge-platform/`：更新需求、前端、接口、数据、验收和变更设计。
- `docs/QUESTIONS.md`：同步最终确认的会话规则。

### 技术方案

会话列表统一使用当前用户和当前智能体作为查询条件，减少分支逻辑并避免 AI 管家成为跨智能体会话聚合入口。

### 接口或数据变化

设计中的 API-001 去除 `conversationScope`；会话列表统一按 `agent_id` 过滤。尚未实现接口或数据库迁移。

### 验证情况

- 已完成：需求、前端、接口、数据和验收文档一致性更新。
- 未执行：代码构建、接口、数据库或端到端测试；本次未修改运行代码。

### 遗留问题

- 无新增阻塞；后续实施必须将会话查询限制为当前用户和当前智能体。

## 2026-07-20：首期 AI 界面与 Embedding 技术选型确认

### 任务目标

锁定 AI 聊天界面组件库与知识库向量模型，消除前后端实施依赖中的两个关键待定项。

### 实现内容

- 确认聊天展示使用 Ant Design X 和 `@ant-design/x-markdown`，继续以自有 SSE API 管理会话数据流。
- 确认知识库向量由独立 Worker 本地运行 `BAAI/bge-m3` 生成，不使用云端 Embedding API。

### 主要文件

- `docs/features/agent-knowledge-platform/`：更新需求、前端、后端和变更设计。
- `docs/DECISIONS.md`、`docs/QUESTIONS.md`：同步已确认技术选型。

### 技术方案

Ant Design X 仅承担 AI 交互展示，避免与业务接口、鉴权和状态管理重叠；`bge-m3` 将本地计算与 DeepSeek 的聊天生成职责分离，向量只在 Worker 和 PostgreSQL/pgvector 内流转。

### 接口或数据变化

无已实现接口或数据变化。设计中 `document_chunks.embedding_model` 将记录 `bge-m3`。

### 验证情况

- 已完成：技术方案与功能设计文档同步检查。
- 未执行：依赖安装、模型下载、前端构建、本地向量生成或集成测试；本次未修改运行代码。

### 遗留问题

- 实施前锁定 DeepSeek 具体聊天模型、BGE 推理库、后台任务框架和数据库迁移工具版本。

## 2026-07-20：首期知识库资料类型调整

### 任务目标

根据用户确认，降低首期文件处理和部署复杂度，同时保留文字资料 RAG 的完整链路。

### 实现内容

- 将首期支持格式调整为 PDF、TXT、Word（`.docx`）和 Markdown。
- 将图片、扫描版 PDF、OCR 和 PaddleOCR 移出首期范围。
- 明确普通文本 PDF 仍使用 PyMuPDF，`.docx` 使用 `python-docx` 提取正文；扫描版 PDF 处理失败并提示不支持。

### 主要文件

- `docs/features/agent-knowledge-platform/`：更新需求、后端、接口、数据、验收和变更设计。
- `docs/DECISIONS.md`、`docs/QUESTIONS.md`：同步调整后的技术与需求范围。

### 技术方案

继续保留 Redis Worker 处理解析、切分和 Embedding，但不再为 OCR 引入模型运行时和独立依赖，从而减少首期部署资源与故障面。

### 接口或数据变化

设计上的 API-010 文件类型白名单变更；尚未实现接口、数据库迁移或依赖变更。

### 验证情况

- 已完成：需求、后端、接口与验收文档的一致性更新。
- 未执行：代码构建、文件解析、Worker、API 或端到端测试；本次未修改运行代码。

### 遗留问题

- 实施前仍需确定 Embedding 模型和具体依赖版本。
- 图片知识库与 OCR 如需恢复，必须作为后续独立功能重新确认和设计。

## 2026-07-20：智能体与知识库首期功能设计确认

### 任务目标

将 AI 管家、个人智能体、会话、私有知识库和 RAG 的确认需求固化为后续实施依据，不在设计阶段提前实现业务代码。

### 实现内容

- 创建首期功能设计目录，覆盖需求、前端、后端、接口、数据、验收和变更记录。
- 确认多账号数据隔离、内置 AI 管家、默认打开及会话侧栏范围规则。
- 确认文件/文件夹资料范围和文件夹自动纳入后续新增文件的规则。
- 确认保留现有技术栈并受控使用 LangChain/LangGraph 的工作流边界。

### 主要文件

- `docs/features/agent-knowledge-platform/`：首期功能的正式设计与验收依据。
- `docs/DECISIONS.md`：ADR-005 更新为已采用的技术方案。
- `docs/PROJECT_STATUS.md`：更新为设计完成、待实施状态。

### 技术方案

使用 FastAPI、PostgreSQL/pgvector、对象存储、Redis Worker 和可替换模型/OCR/Embedding 适配层；LangChain 负责模型相关标准能力，LangGraph 负责固定聊天工作流编排，不承担权限和数据库访问。

### 接口或数据变化

设计了 API-001 至 API-011、DB-001 至 DB-006；尚未实现接口、数据库迁移或依赖变更。

### 验证情况

- 已完成：需求、前端、后端、接口、数据和验收设计的文档一致性检查。
- 未执行：代码构建、数据库迁移、API 集成、Worker、模型和浏览器测试；本次未修改运行代码。

### 遗留问题

- 实施前需锁定模型供应商、Embedding 模型、OCR 部署方式和依赖版本。
- 会话删除及资料移动/删除不在首期范围，后续需单独确认。

## 2026-07-18：前端认证与业务路由边界重构

### 任务目标

将模糊的通配符认证路由调整为具备明确 URL 语义、鉴权边界、登录回跳与 404 处理的路由结构。

### 实现内容

- 新增路径常量、匿名路由守卫和受保护路由守卫。
- 将认证入口拆为 `/login` 与 `/register`，认证表单模式由路由确定。
- 将业务入口统一为 `/app/chat`、`/app/agents`、`/app/knowledge-bases`，并新增未知路径 404 页。
- 未登录访问有效受保护页面时保留原地址，认证成功后恢复访问。

### 主要文件

- `frontend/src/routes/paths.ts`：集中定义前端路径。
- `frontend/src/routes/GuestOnly.tsx`、`frontend/src/routes/RequireAuth.tsx`：认证路由边界与回跳逻辑。
- `frontend/src/App.tsx`：组装新的嵌套路由树。
- `frontend/src/layouts/AppLayout.tsx`：使用路径常量生成导航和登出跳转。
- `frontend/src/pages/AuthPage.tsx`、`frontend/src/pages/NotFoundPage.tsx`：认证 URL 语义和 404 展示。

### 技术方案

基于已有 React Router 依赖实现守卫组件与嵌套路由，不引入新依赖；用集中路径常量避免导航和路由声明出现重复字符串。

### 接口或数据变化

无。未修改后端 API、数据库结构或认证令牌格式。

### 验证情况

- 通过：在 `frontend/` 执行 `pnpm build`（`tsc && vite build`）。
- 警告：Vite 提示压缩后部分代码块超过 500 kB；pnpm 读取用户级配置时产生权限警告，但构建退出码为 0。
- 未执行：浏览器端到端测试和后端数据库/API 集成测试。

### 遗留问题

- `/app/*` 对应的 AI、智能体与知识库业务页面尚未实现。
- 旧路径未提供兼容重定向；如已有外部链接，应在发布前评估兼容策略。

## 2026-07-18：项目文档基线核查与补全

### 任务目标

依据当前目录、源代码、依赖配置和可执行检查，建立统一项目文档；不把尚未运行验证的功能或规划内容记为已完成。

### 实现内容

- 创建统一文档索引、项目状态、开发日志、问题记录、技术决策和架构说明。
- 核查前端 React/Vite 目录、后端 FastAPI 目录、认证实现、数据库初始化逻辑和 CI 配置。
- 明确 AI 管家页面、知识库页面与真实 RAG/智能体流程尚未实现。

### 主要文件

- `docs/README.md`：统一文档的职责索引。
- `docs/PROJECT_STATUS.md`：当前功能状态、验证范围、下一步和风险。
- `docs/QUESTIONS.md`：记录本次形成的文档真实性约束结论。
- `docs/DECISIONS.md`：记录从现有代码核查得到的长期技术选择。
- `docs/ARCHITECTURE.md`：记录实际目录职责、认证数据流和未实现边界。

### 技术方案

以代码、依赖清单、CI 工作流和本地命令输出为证据来源。对已存在但未实际联调的功能采用“已实现、待集成验证”的表述；对只有路由或空页面的功能标记为“规划中”或“未实现”。

### 接口或数据变化

无。本次只新增项目文档，未修改 API、数据库结构或依赖。

### 验证情况

- 通过：使用 `backend/.venv/Scripts/python.exe -m py_compile` 编译 `main.py`、配置、数据库、依赖、路由、模型和认证服务模块。
- 通过：在 `frontend/` 执行 `pnpm build`（`tsc && vite build`）。
- 警告：Vite 报告主 JavaScript 包超过 500 kB；pnpm 读取用户级配置时出现权限警告，但构建退出码为 0。
- 未执行：数据库连接/建表、HTTP 集成测试、浏览器交互测试和认证自动化测试；本次未配置可验证的数据库服务。

### 遗留问题

- 认证流程需要连接真实 PostgreSQL 后完成端到端验证。
- 知识库、向量检索、智能体工作流及真实聊天回答仍待实现。
- 需校正 `frontend/docs/login.md` 与当前认证实现之间的历史描述差异。
