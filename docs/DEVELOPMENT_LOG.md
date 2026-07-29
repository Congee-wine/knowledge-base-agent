# 开发日志

## 2026-07-28：阶段 4 embedding 基础设施与混合切分

### 任务目标

建立不阻塞文档解析的本地 `bge-m3` 向量化执行边界。

### 实现内容

- 新增独立 `embedding` 队列、Worker 入口、镜像与依赖清单。
- 增加版本化 embedding 任务迁移和文档索引状态。
- 实现保留页码、标题与段落定位的混合切分，以及解析完成后的 embedding 任务投递。

### 验证情况

- 混合切分、文档解析和预览相关单元测试共 13 项通过；Python 编译通过。
- 真实镜像构建、数据库迁移、模型下载和端到端验证尚未执行。

### 遗留问题

- 需要在本地 Docker 环境构建 embedding Worker、执行迁移并下载模型后继续实现向量写入和范围检索。

## 2026-07-28：知识库检索方案确认

### 任务目标

确认文本切分、`bge-m3` 向量化、检索和引用的阶段 4 实施边界。

### 实现内容

- 用户确认混合切分、独立 embedding Worker、Top 8 召回后最终最多 5 条、资料范围强制过滤、短引用和异步版本化索引。
- 创建 `docs/features/knowledge-retrieval/` 正式设计文档；本次未开始代码实现。

### 接口或数据变化

无实际接口或数据库变更；设计中的后续变更将通过 Alembic 和明确 API 契约实施。

### 验证情况

- 需求和设计方案已由用户确认。

### 遗留问题

- 按设计开始独立 embedding Worker、版本化向量索引与检索实现。

## 2026-07-28：文件预览浏览器验收

### 任务目标

确认已实现的受认证文件预览在真实浏览器中可用。

### 实现内容

- 用户验证 TXT、Markdown、PDF、DOCX 四种格式均可正常预览。
- Markdown 预览以安全渲染组件展示结构化内容；TXT 保持纯文本，PDF 使用浏览器原生阅读器，DOCX 展示受控 HTML。

### 主要文件

无新增代码修改；同步更新文件预览功能状态与下一阶段计划。

### 接口或数据变化

无。

### 验证情况

- 用户已完成浏览器端四种格式预览验收。

### 遗留问题

- 进入文本切分、`bge-m3` 向量化和知识库检索的需求确认与设计阶段。

## 2026-07-28：受认证文件预览

### 任务目标

为资料树中的 TXT、Markdown、PDF 与 DOCX 文件提供安全的浏览器内预览。

### 实现内容

- 增加按文件归属和处理状态校验的预览接口；私有对象存储地址不会返回给浏览器。
- TXT/Markdown 以 UTF-8 文本返回，PDF 以经认证请求获取的 Blob 在浏览器内展示。
- DOCX 复用 `python-docx` 读取段落、列表和表格；所有文档文字经 HTML 转义后放入固定安全标签，并在沙箱 iframe 内展示。
- Markdown 预览复用已有的安全渲染组件解析标题、表格、强调和代码块；TXT 保持纯文本展示。
- 资料树支持双击 ready 文件及右键“预览”进入同一预览页；未就绪或失败文件给出提示。

### 主要文件

- `backend/services/document_preview.py`：预览内容读取、状态判断和 DOCX 安全 HTML 转换。
- `backend/routers/knowledge.py`、`backend/repositories/knowledge.py`：受认证预览接口与按所有者查询。
- `frontend/src/pages/DocumentPreviewPage.tsx`：预览页及加载、错误和内容状态。
- `frontend/src/pages/KnowledgeBasePage.tsx`、`frontend/src/features/knowledge/components/KnowledgeItemGrid.tsx`：资料树入口。

### 技术方案

PDF 不使用预签名 URL，而是以 Bearer 认证请求获取 Blob URL，避免私有对象地址泄露。DOCX 不引入转换依赖；现有 `python-docx` 的结构化读取满足本期段落、列表和表格展示，并通过服务端转义与浏览器沙箱降低 HTML 执行风险。

### 接口或数据变化

- 新增 `GET /api/knowledge/files/{nodeId}/preview`。
- 无数据库迁移或数据结构变化。

### 验证情况

- 后端：`tests.test_document_preview`、`tests.test_document_worker_tasks`、`tests.test_document_validation` 共 14 项通过。
- 前端：TypeScript `tsc --noEmit` 通过；资料树双击测试通过。
- `pnpm build` 未通过：Vite 无法读取既有 `highlight.js` 依赖，报系统拒绝访问；TypeScript 阶段已完成，待修复本机依赖访问权限后重跑生产构建。
- 浏览器端四种格式验收尚未执行。

### 遗留问题

- 需要进行真实浏览器验收，重点检查 PDF、DOCX、跨账号访问与失败状态。
- 验收通过后再进入文本切分、`bge-m3` 向量化和检索。

## 2026-07-28：四种文档格式解析验收完成

### 任务目标

确认 PDF、TXT、Markdown、DOCX 的真实异步处理链路可用。

### 实现内容

- 用户完成四种允许格式的 Worker 解析验收。
- 阶段 3.2B 的上传、解析、处理状态和失败清理流程达到当前验收条件。

### 主要文件

无代码修改。

### 接口或数据变化

无。

### 验证情况

- 用户已验证：PDF、TXT、Markdown、DOCX 可完成真实解析。

### 遗留问题

- 下一阶段为受认证的文件预览；向量化与检索仍未实现。

## 2026-07-28：Worker 解析镜像依赖拆分

### 任务目标

解决重建文档 Worker 时因下载尚未使用的深度学习依赖而发生超时的问题。

### 实现内容

- 新增 `backend/requirements.worker.txt`，仅保留阶段 3.2B 的 PostgreSQL、MinIO、RQ、PDF 与 DOCX 解析依赖。
- `Dockerfile.worker` 改用轻量清单，并设置 pip 120 秒超时和 5 次重试。
- `FlagEmbedding` 与其 PyTorch/CUDA 依赖继续保留在主依赖清单，待向量化 Worker 实现时再引入镜像。

### 主要文件

- `backend/requirements.worker.txt`：文档解析 Worker 的最小运行依赖。
- `backend/Dockerfile.worker`：轻量依赖安装与网络重试配置。

### 接口或数据变化

无。

### 验证情况

- 已根据 Docker 构建日志确认失败发生在未使用的 PyTorch/CUDA 依赖下载阶段。
- 待在用户 Docker 环境中重新构建镜像验证。

### 遗留问题

- 向量化阶段需要单独扩展 Worker 镜像或为该镜像增加 Embedding 依赖。

## 2026-07-28：异步入库成功语义调整

### 任务目标

将“上传成功”定义为源文件已解析并成功加入知识库，而非仅完成对象存储写入。

### 实现内容

- 已完成处理的文件不显示成功标签，按普通资料样式展示。
- 处理中资料维持灰化外观和“处理中”文字，不显示额外图标。
- Worker 解析失败或队列投递失败时，清理资料树记录、关联数据和对象存储源文件；前端提示“文件处理失败，未加入知识库”。
- 移除失败文件重新处理接口和右键入口；用户可在修正源文件后重新上传。

### 主要文件

- `backend/workers/tasks.py`：解析失败后的递归资料与对象清理。
- `backend/services/knowledge.py`：队列投递失败后的上传回滚。
- `frontend/src/features/knowledge/components/KnowledgeItemGrid.tsx`：处理中和完成后的展示规则。
- `frontend/src/pages/KnowledgeBasePage.tsx`：识别待处理文件消失并提示失败。

### 接口或数据变化

- 移除 `POST /api/knowledge/files/{file_id}/reprocess`。
- 不新增数据库迁移。

### 验证情况

- 通过：后端 `unittest` 14 项、Python 编译检查、前端 `pnpm exec tsc --noEmit`、`git diff --check`。

### 遗留问题

- 仍需在真实 Redis/RQ、MinIO 环境中完成文件处理成功与失败清理的浏览器验收。

## 2026-07-28：资料处理中视觉状态调整

### 任务目标

让正在解析的资料以低饱和灰色展示，并使用明确的“处理中”标记。

### 实现内容

- `uploaded` 与 `processing` 都展示为“处理中”，避免用户看到内部队列术语。
- 处理中资料的文件图标、名称和大小统一使用灰色；状态行使用 AI 标记和蓝色“处理中”文本。

### 主要文件

- `frontend/src/features/knowledge/components/KnowledgeItemGrid.tsx`：根据处理状态增加视觉类名和标记。
- `frontend/src/style.css`：定义处理中资料的灰化与状态标记样式。

### 接口或数据变化

无。

### 验证情况

- 通过：前端 `pnpm exec tsc --noEmit`、`git diff --check`。

### 遗留问题

- 仍需浏览器端确认与设计参考图的实际视觉一致性。

## 2026-07-28：阶段 3.2B 异步解析与处理状态首轮实现

### 任务目标

将文本型资料投递到后台 Worker，并在资料树中显示临时处理状态；失败时不保留为知识库资料。

### 实现内容

- 上传成功后创建处理任务并投递至 `document-processing` RQ 队列。
- Worker 从私有对象存储读取源文件，提取 PDF、TXT、Markdown、DOCX 文本并写入 `document_chunks`。
- 处理状态按 `uploaded → processing → ready / failed` 更新；队列投递失败会保留文件并标记失败。
- 前端在存在待处理文件时每 3 秒刷新资料树；只有处理中显示临时标记，完成后显示为普通文件。

### 主要文件

- `backend/services/knowledge.py`：上传后的任务创建、投递和失败处理。
- `backend/workers/tasks.py`：Worker 文件读取、文本提取和状态收口。
- `backend/repositories/knowledge.py`：处理任务、状态和分块持久化。
- `frontend/src/pages/KnowledgeBasePage.tsx`：状态轮询与失败提示。

### 接口或数据变化

- 不新增数据库迁移；使用已存在的 `ingestion_jobs` 和 `document_chunks` 表。

### 验证情况

- 通过：后端 `unittest` 14 项（包含 TXT、PDF、DOCX 提取）、Python 编译检查、前端 `pnpm exec tsc --noEmit`、`git diff --check`。
- 未执行：真实 Redis/RQ Worker、MinIO 与四种格式的端到端处理；需在完整 Worker 环境中验证。

### 遗留问题

- 向量化、向量库写入、检索和文件预览仍未开始。

## 2026-07-27：流式聊天阶段收尾与知识库实施准备

### 任务目标

记录真实验收结果，停止未稳定的聊天续流改造，并为知识库异步文档处理确认运行环境和实施顺序。

### 实现内容

- 用户已完成直接 SSE 正常回答和停止生成的浏览器验收。
- Redis/RQ 聊天事件缓冲、后台聊天生成和断线续流未通过真实端到端验收，相关代码已撤回；不将其标记为完成。
- 为 Docker 文档 Worker 增加独立的本地环境文件覆盖：本机 API 继续用 `127.0.0.1` 访问 SSH 隧道，Worker 用 `host.docker.internal` 访问同一隧道。
- 已创建知识库阶段的当前执行计划，先完成资料树、上传与异步处理，再接入检索和 LangGraph。

### 主要文件

- `docker-compose.infrastructure.yml`：Worker 按顺序加载基础和 Worker 专用环境文件。
- `backend/.env.worker.example`：不含真实凭证的 Worker 配置模板。
- `docs/features/agent-knowledge-platform/IMPLEMENTATION_PLAN.md`：知识库阶段 3.0 至 3.5 的执行计划。
- `docs/features/agent-knowledge-platform/STREAMING_RUNTIME_PLAN.md`：标注聊天续流已延后。

### 技术方案

聊天继续采用已验收的直接 SSE。耗时的文档解析、切分和向量化由 Docker Linux RQ Worker 执行；聊天检索将在资料处理稳定后作为 LangGraph 的线性检索节点接入。

### 接口或数据变化

无业务接口或数据库结构变化。新增本地环境文件约定；该文件不提交版本库。

### 验证情况

- 用户完成正常直接 SSE 回答与停止生成的浏览器验收。
- Docker Worker 内执行数据库连通检查，返回 `database connection ok`。
- 本轮只更新文档和本地运行配置，未执行知识库业务实现测试。

### 遗留问题

- 知识库数据迁移、上传、解析、向量化、检索、引用与页面均未开始。
- 聊天断线续流保留为后续独立阶段，重新实施前必须完成真实端到端环境验证。

## 2026-07-27：编辑预览助手回复左对齐

### 任务目标

修复智能体编辑页右侧预览中，长助手回复继承欢迎态居中样式的问题。

### 实现内容

- 为共享 `ChatMessageList` 的 AI 气泡内容显式设置 `text-align: left`，避免父容器样式继承影响 Markdown 与普通回复。
- 保持欢迎态、用户消息右侧布局和正式聊天的现有结构不变。

### 主要文件

- `frontend/src/features/chat/components/ChatMessageList.tsx`：助手消息内容对齐规则。
- `frontend/src/features/chat/components/__tests__/ChatMessageList.test.tsx`：左对齐回归断言。

### 接口或数据变化

无。

### 验证情况

- 通过：组件测试 2 项通过。
- 通过：`pnpm exec tsc --noEmit`。
- 待执行：浏览器确认编辑预览的长 Markdown/普通助手回复均从左侧开始排版。

### 遗留问题

- 无代码级阻塞。

## 2026-07-27：生成中会话详情与新会话即时返回

### 任务目标

修复并发流式生成期间读取会话详情返回 500，以及新会话必须等待模型结束才能重新从侧边栏进入的问题。

### 实现内容

- `MessageResponse` 接受数据库已使用的 `generating` 消息状态；读取含生成中助手消息的会话详情不再触发 Pydantic 校验错误。
- 新会话收到 `message_start` 的真实会话 ID 后，立即写入当前智能体的 React Query 会话列表缓存；模型仍在生成时即可切换到其他会话，再从侧边栏返回。
- 新增会话服务测试，覆盖生成中助手消息的详情读取。

### 主要文件

- `backend/schemas/conversations.py`：会话详情消息状态契约。
- `backend/tests/test_conversations_service.py`：生成中消息详情回归测试。
- `frontend/src/pages/ChatPage.tsx`：首个流事件后的会话列表缓存更新。

### 技术方案

会话详情接口必须能返回持久化生命周期中的所有合法消息状态；前端不等待最终答案或列表重新请求，而是在服务端已经创建真实会话并返回 ID 的 `message_start` 时乐观写入列表缓存，随后仍由完成后的失效刷新校正标题和时间。

### 接口或数据变化

接口响应枚举增加已有状态 `generating`；无路由、数据库迁移或依赖变化。

### 验证情况

- 通过：后端 `.venv\\Scripts\\python.exe -m unittest tests.test_conversations_service`，6 项通过。
- 通过：前端 `pnpm test -- --run`，6 个测试文件、28 项测试通过。
- 通过：前端 `pnpm build`；首次沙箱构建因既有 `highlight.js` 读取权限失败，授权环境重试后通过。
- 待执行：浏览器验证两个会话同时生成、切换后返回生成中会话，以及新会话立即出现在侧边栏。

### 遗留问题

- 侧边栏尚未显示“生成中”视觉标记；会话即时可返回与流状态隔离不受影响。

## 2026-07-27：会话级并发流隔离

### 任务目标

支持同一智能体的不同会话并行生成，同时禁止同一会话同时存在两个生成请求，避免切换会话时取消旧流或让延迟事件污染当前页面。

### 实现内容

- `useStreamingChat` 从单一活动流重构为按会话 ID（新会话使用临时键）隔离的消息、请求状态、序号和 `AbortController` 映射。
- 切换历史会话只切换页面展示，不再停止或重置其他会话流；停止按钮只影响当前会话。
- 新会话在收到 `message_start` 的真实会话 ID 后，将本地流状态迁移到该会话键，后续事件继续更新原请求所属会话。
- 后端在锁定会话并写入消息前检查是否存在 `generating` 助手消息；存在时返回 `409 CONVERSATION_GENERATION_IN_PROGRESS`，不创建第二条消息对。

### 主要文件

- `frontend/src/features/chat/hooks/useStreamingChat.ts`：会话隔离的流状态、事件路由和取消控制。
- `frontend/src/pages/ChatPage.tsx`：按当前会话读取流状态，切换会话不再中止其他会话。
- `backend/repositories/conversations.py`：同会话生成中保护。
- `backend/services/errors.py`：稳定并发冲突错误码。
- `backend/tests/test_conversations_service.py`：同会话第二请求拒绝测试。

### 技术方案

前端以会话键而非当前页面选择项归属 SSE 事件，避免旧流在用户切换后写入新会话。后端使用既有会话行锁保护“检查生成中状态 + 预留消息序号 + 写入消息对”的临界区，从而允许不同会话并行，同时串行化同会话生成。

### 接口或数据变化

- 新增 409 错误码：`CONVERSATION_GENERATION_IN_PROGRESS`。
- 不修改数据库结构、SSE 事件结构或依赖。

### 验证情况

- 通过：前端 `pnpm test -- --run`，6 个测试文件、28 项测试通过。
- 通过：前端 `pnpm build`；首次沙箱构建因既有 `highlight.js` 读取权限失败，授权环境重试后通过。
- 通过：后端 `.venv\\Scripts\\python.exe -m unittest tests.test_conversations_service`，5 项通过。
- 待执行：浏览器中同时向两个会话发送请求、切换查看、分别停止及同会话重复发送的人工验收。

### 遗留问题

- 会话列表尚未展示非当前会话“正在生成”的视觉状态；不影响流隔离和数据正确性，可在后续页面体验优化时补充。

## 2026-07-27：新会话消息顶部对齐与受控自动滚动

### 任务目标

修复新会话首条消息因组件内置倒序滚动而贴近输入区的问题，同时保留流式回复的底部跟随和回到底部操作。

### 实现内容

- 关闭 `Bubble.List` 的内置 `autoScroll`，使消息按正常文档流从顶部排列。
- 使用标准正向滚动位置计算：仅当用户距底部不超过 24px 时，新增或增量消息才自动滚到底部。
- 用户上滑阅读历史后停止自动跟随，并继续显示“回到底部”按钮。
- 修复切换会话时滚动节点尚未初始化便调用 `scrollTo` 的崩溃：仅在 `scrollBoxNativeElement` 已就绪后请求初始滚动。
- 新增组件测试，固定消息列表不再启用倒序自动滚动，且未就绪的滚动节点不会触发 `scrollTo`。

### 主要文件

- `frontend/src/features/chat/components/ChatMessageList.tsx`：受控滚动、底部状态判断与回到底部操作。
- `frontend/src/features/chat/components/__tests__/ChatMessageList.test.tsx`：验证消息列表采用正常滚动方向。

### 技术方案

保留 `Bubble.List` 的消息渲染、角色布局和公开 `scrollTo` 能力，但不采用其以 `column-reverse` 实现的内置自动滚动。页面根据用户是否停留在底部决定是否跟随，从而兼顾首条消息顶部对齐和流式生成体验。

### 接口或数据变化

无。未修改后端接口、数据库结构或依赖。

### 验证情况

- 通过：`frontend/` 下 `pnpm test -- --run src/features/chat/components/__tests__/ChatMessageList.test.tsx`，2 项组件回归测试通过。
- 通过：`frontend/` 下 `pnpm build`；首次沙箱构建因既有 `highlight.js` 读取权限失败，授权环境重试后通过。
- 待执行：浏览器确认新会话首条消息顶部对齐、长回复自动跟随、上滑后停止跟随及回到底部操作。

### 遗留问题

- 无代码级阻塞；滚动体验仍需浏览器人工验收。

## 2026-07-27：正式聊天自动跟随与回到底部

### 任务目标

让 AI 流式回复时使用 Ant Design X 的消息列表自动跟随能力，并在用户查看较早消息后提供明确、可访问的回到底部操作。

### 实现内容

- 正式聊天页的消息区域改由 Ant Design X `Bubble.List` 自身承担滚动，避免外层容器与组件内部滚动机制冲突。
- 保留 `autoScroll`；用户停留在底部时，流式新增内容会持续跟随。
- 用户向上浏览历史消息时，显示悬浮的图标按钮；点击后调用 `Bubble.List.scrollTo({ top: 'bottom', behavior: 'smooth' })` 平滑回到底部。
- 编辑页预览没有改变原有容器布局，避免本次局部修复影响其三栏工作台。

### 主要文件

- `frontend/src/features/chat/components/ChatMessageList.tsx`：消息列表滚动容器、滚动位置判断和回到底部控件。
- `frontend/src/pages/ChatPage.tsx`：正式聊天页将滚动职责交给消息列表。

### 技术方案

复用已安装的 `@ant-design/x` `Bubble.List` 及其公开的 `autoScroll`、`scrollTo` 能力，不新增依赖，也不自行维护 DOM 滚动计算。自动跟随仅在用户仍位于底部时生效，避免阅读历史记录时被新内容强制打断。

### 接口或数据变化

无。

### 验证情况

- 通过：`frontend/` 下执行 `pnpm test -- --run`，5 个测试文件、25 项测试通过。
- 通过：`frontend/` 下执行 `pnpm build`；首次沙箱构建无法读取既有 `highlight.js` 依赖，授权环境重试后通过。
- 待执行：浏览器端以长回复和流式增量确认自动跟随、上滑后的按钮显示及平滑回到底部效果。

### 遗留问题

- 不改变阶段 4 的真实模型流式浏览器联调范围；本次仅完成前端滚动容器和交互接入。

## 2026-07-27：复制操作改为悬浮提示

### 任务目标

使助手消息下方的复制操作保持紧凑，只在鼠标悬浮时显示文字说明。

### 实现内容

- 复制操作改为仅显示图标。
- 使用 Tooltip 在悬浮时显示“复制”，并保留无障碍标签与原有点击逻辑。

### 主要文件

- `frontend/src/features/chat/components/ChatMessageList.tsx`：复制操作的 Tooltip 展示。

### 技术方案

复用已安装的 Ant Design Tooltip，不新增依赖或自定义浮层逻辑。

### 接口或数据变化

无。

### 验证情况

- 待执行前端测试和构建。

### 遗留问题

- 待浏览器端确认 Tooltip 位置和触屏设备下的可发现性。

## 2026-07-27：区分助手消息样式并添加复制操作

### 任务目标

使助手回复与用户灰色消息气泡在视觉上清晰区分，并为助手回复提供复制能力。

### 实现内容

- 助手消息改为左对齐、透明、无内边距的内容区；用户消息继续使用右侧灰色填充气泡。
- 每条非空助手消息下方增加复制操作；复制成功或失败均提供反馈。
- 流式生成中的空助手消息不显示复制操作。

### 主要文件

- `frontend/src/features/chat/components/ChatMessageList.tsx`：助手气泡变体、样式和复制交互。

### 技术方案

使用 Ant Design X `Bubble` 的 `borderless` 变体和内容插槽样式，避免通过全局 CSS 覆盖组件内部结构；复制使用浏览器 Clipboard API。

### 接口或数据变化

无。

### 验证情况

- 待执行前端测试、构建和浏览器视觉验证。

### 遗留问题

- 需在阶段 4 人工验证长 Markdown、代码块和流式增量时复制操作的位置与可用性。

## 2026-07-27：使用 Sender 内置停止生成控件

### 任务目标

消除输入区生成状态中重复的停止操作，并保持已有的正式会话中断和预览本地取消逻辑。

### 实现内容

- 移除输入区 footer 中额外渲染的“停止生成”按钮。
- 将 Ant Design X `Sender` 在 `loading` 状态下内置的取消控件绑定到既有 `stream.stop()`。

### 主要文件

- `frontend/src/features/chat/components/ChatComposer.tsx`：使用 `Sender.onCancel` 复用框架的内置停止控件。

### 技术方案

保留框架组件在加载状态下原生呈现的方形中断图标，避免重复 UI；取消回调仍复用阶段 3 已实现的正式会话持久化和预览隔离逻辑。

### 接口或数据变化

无。

### 验证情况

- 待执行前端构建和浏览器验证。

### 遗留问题

- 仍需在阶段 4 验证真实流式生成时内置控件的视觉与中断行为。

## 2026-07-27：阶段 3 前端 SSE 状态机与停止生成

### 任务目标

让正式聊天和编辑页预览以一致的流式解析及请求控制方式工作，并为用户提供可停止的生成过程。

### 实现内容

- 新增增量 SSE 解析器，支持 `\n`/`\r\n`、同帧多行 `data:`、跨分块帧和流结束时未带空行的帧。
- Hook 为每条活动流保存 `AbortController`、运行模式、请求 ID 与正式助手消息 ID，并过滤模式不匹配的事件。
- 停止正式会话时标记本地消息为 `interrupted`，调用中断接口保存部分回答；停止预览时只取消本地请求。
- 聊天页切换智能体、切换会话或新建会话前停止活动流；编辑预览切换智能体和组件卸载时停止并重置预览。
- 输入区在生成时显示“停止生成”操作。

### 主要文件

- `frontend/src/features/chat/streaming/sseParser.ts`：增量 SSE 帧解析。
- `frontend/src/api/chat.ts`：解析器接入与中断接口客户端。
- `frontend/src/features/chat/hooks/useStreamingChat.ts`：活动流和停止逻辑。
- `frontend/src/features/chat/components/ChatComposer.tsx`、`pages/ChatPage.tsx`、`features/agents/components/AgentEditorPreview.tsx`：停止生成与页面清理接入。
- `frontend/src/features/chat/streaming/sseParser.test.ts`、`useStreamingChat.test.tsx`：解析和停止行为测试。

### 技术方案

以 `AbortController` 负责本地网络中止，以后端中断接口负责正式消息终态；两者缺一不可。预览没有持久化消息 ID，因此不调用正式中断接口。

### 接口或数据变化

无新增前端依赖或数据库变更；前端开始消费阶段 2B 新增的中断接口。

### 验证情况

- 通过：`pnpm test -- --run`，5 个测试文件、25 项测试。
- 通过：`pnpm build`。
- 未执行：真实浏览器和认证后的端到端流式中断联调。

### 遗留问题

- 尚未将状态更新彻底抽取为独立 reducer；当前 Hook 已具备活动流边界，后续可在不改变协议的前提下继续拆分。
- 阶段 4 需验证正式历史覆盖、本地预览隔离、停止按钮和 Markdown 流式展示。

## 2026-07-27：阶段 2B 后端运行生命周期与数据隔离

### 任务目标

让正式聊天使用受控历史上下文并具备可持久化的中断终态，同时保证编辑预览不写入正式业务数据。

### 实现内容

- 新增查询：仅返回当前用户消息之前、内容非空且 `generation_status='complete'` 的最近 10 条历史消息。
- 正式模型调用使用该历史；正在生成、失败、已中断和空内容消息不会进入 Prompt。
- `afterSequence > 0` 在两个流式入口处统一返回 `STREAM_RESUME_UNAVAILABLE`，不伪装支持续流。
- 新增正式助手消息中断接口；它验证消息属于当前用户且仍在生成中，保存客户端提供的已生成片段并标记为 `interrupted`。
- 预览服务继续只读取草稿请求和本地历史，不调用任何业务写入方法。

### 主要文件

- `backend/repositories/conversations.py`：有效历史查询和按用户中断消息更新。
- `backend/services/conversations.py`：历史组装与中断用例。
- `backend/routers/conversations.py`、`backend/routers/agents.py`：中断路由和续流拒绝。
- `backend/schemas/streaming.py`：中断请求结构。
- `backend/tests/test_streaming_protocol.py`：历史加载、续流拒绝和部分回答持久化测试。

### 技术方案

历史查询在插入当前消息后按其 `message_order` 截断，避免将本轮用户消息重复作为历史传给模型。中断请求由后续前端状态机传入当前累计文本，以保持中断回答可回显。

### 接口或数据变化

- 新增 `POST /api/conversations/messages/{assistantMessageId}:interrupt`。
- 请求体：`{ "content": "已生成的部分回答" }`，可省略并默认空字符串。
- 无数据库迁移或新增依赖。

### 验证情况

- 通过：会话服务和 SSE 协议测试共 10 项。
- 通过：相关 Python 模块 `py_compile`。
- 未执行：认证后的真实 HTTP 中断请求和浏览器端停止生成联调，留待阶段 3。

### 遗留问题

- 前端尚未调用中断接口，`AbortController`、取消后的本地状态同步和页面卸载清理属于阶段 3。
- Redis 断线续流仍明确不在当前范围。

## 2026-07-27：阶段 2A 双模式 SSE 契约

### 任务目标

使编辑预览和正式聊天共享流式事件基础设施，同时通过显式运行模式保持草稿预览与持久化会话的边界。

### 实现内容

- 所有预览和正式 SSE 事件均增加 `mode: "preview" | "conversation"`。
- 前端将 `message_start`、`message_end` 定义为按模式区分的联合类型：预览不读取数据库 ID，正式会话必须读取真实 ID。
- 预览流只更新本地临时消息，不创建会话状态或待确认的持久化消息对。
- 预览与正式服务在创建流响应前执行资源/权限校验；未知运行期异常转换为可消费的 `error` 事件。

### 主要文件

- `frontend/src/api/chat.ts`：双模式 SSE 事件验证。
- `frontend/src/features/chat/hooks/useStreamingChat.ts`：按模式更新预览或正式会话状态。
- `backend/routers/agents.py`、`backend/routers/conversations.py`：统一注入 SSE `mode`。
- `backend/services/agent_preview.py`、`backend/services/conversations.py`：前置校验并映射未知运行异常。
- `backend/tests/test_streaming_protocol.py`：覆盖两种模式的事件载荷和预览校验时机。

### 技术方案

使用 `mode` 作为可辨别字段，而不是通过是否存在 `conversationId` 或 `messageId` 猜测调用上下文。该方式使后续取消、重试和工具事件可以在同一协议下演进。

### 接口或数据变化

- 现有流式响应新增 `mode` 字段。
- 无数据库、迁移、路由路径或依赖变更。

### 验证情况

- 通过：前端 `pnpm test -- --run`，21 项测试。
- 通过：后端 `python -m unittest tests.test_streaming_protocol`，3 项测试。
- 通过：相关 Python 模块 `py_compile`。
- 通过：前端 `pnpm build`；沙箱内首次构建因既有 `highlight.js` 读取权限失败，获准在受限环境外复跑后成功。
- 未执行：真实浏览器端和认证后的端到端流式请求联调。

### 遗留问题

- 阶段 2B 仍需实现正式会话的完整历史加载、取消终态和续流未支持的标准错误。
- 阶段 2A 在浏览器端验证前保持“进行中”。

## 2026-07-27：重排未完成的流式聊天与编辑预览阶段

### 任务目标

基于已完成的阶段 0/1 和已确认的双运行上下文原则，修正后续流式实施顺序，避免编辑页预览继续被当作正式会话处理。

### 实现内容

- 未修改应用代码。
- 将未完成工作拆分为阶段 2A、2B、3、4、5：先定义预览/正式会话的 SSE 模式边界，再完成后端生命周期、前端状态机、页面联调和回归验收。
- 明确预览使用草稿配置与页面内存历史，正式聊天使用已保存配置与持久化会话；两者共享 Agent Runtime，不共享会话存储状态。

### 主要文件

- `docs/features/agent-knowledge-platform/STREAMING_RUNTIME_PLAN.md`：记录重排后的阶段目标、协议边界和验收条件。
- `docs/features/agent-knowledge-platform/CHANGELOG.md`：记录此次已确认的设计调整。
- `docs/PROJECT_STATUS.md`：同步当前阶段与预览链路尚未验收的真实状态。

### 技术方案

使用 `mode: "preview" | "conversation"` 作为 SSE 的可辨别字段。预览事件不携带持久化会话/消息 ID，正式事件必须携带这些 ID；前端据此执行不同的状态更新分支。

### 接口或数据变化

无实际接口、数据库或依赖变更。本次仅更新未完成阶段的设计与验收要求。

### 验证情况

- 已完成文档一致性检查：阶段 0/1 保持已完成，阶段 2A 仍未实现。
- 未执行代码测试或构建：本次没有修改代码。

### 遗留问题

- 需要在阶段 2A 实现并测试双模式 SSE 契约后，才能继续前端状态机与编辑预览联调。

## 2026-07-27：流式消息重复渲染修复

### 任务目标

修复流式聊天中同一对用户/助手消息被渲染两次的问题：前端在 `message_start` 拿到服务端真实消息 ID 后未替换本地临时 ID，导致数据库详情和本地流式消息同时存在于 `displayedMessages`。

### 实现内容

- 将 `ChatStreamEvent` 从扁平可选字段改为可区分联合类型，`message_start` 的 `userMessageId`/`assistantMessageId` 变为必填。
- `useStreamingChat` 在 `message_start` 时将 `local-user-*`/`local-assistant-*` 替换为服务端真实 ID；`StreamState` 新增 `assistantMessageId` 用于后续 `answer_delta` 定位。
- `message_end` 不立即删除本地消息，而是将消息对记录到 `pendingPersistedPairs`，等待服务端详情确认后再清理。
- 新增 `acknowledgePersistedPair(requestId)` 方法，仅在 React Query 会话详情缓存中确认包含该对完成消息后移除本地副本。
- 新增 `mergeMessages` 纯函数：按 ID 合并服务端与本地消息，流式中的助手消息仅在 `sending === true` 或消息对尚处于 `pendingPersistedPairs` 时优先于服务端内容。
- `ChatPage` 使用 `mergeMessages` 替代直接拼接；`message_end` 后 `invalidateQueries` 触发后台刷新；详情确认完成后调用 `acknowledgePersistedPair` 清理本地消息。
- 每次发送流式请求前清空上一请求的真实消息 ID，避免新请求在收到自身 `message_start` 前失败时，把上一轮已完成助手消息误标记为失败。
- SSE 消费端在分发前校验事件类型、请求 ID、序号及各事件必填字段；`answer_delta.content` 允许空字符串，避免合法的空增量被误判为协议错误。
- `ChatPage` 的确认清理 effect 改为依赖具体状态和回调，避免依赖整个 hook 返回对象而增加无意义的重复执行。

### 主要文件

- `frontend/src/api/chat.ts`：`ChatStreamEvent` 改为联合类型，并增加 SSE 事件运行时结构校验。
- `frontend/src/api/__tests__/chat.test.ts`：2 项 SSE 协议校验测试，覆盖合法事件分发与缺失必填字段拒绝。
- `frontend/src/features/chat/hooks/useStreamingChat.ts`：真实 ID 替换、`pendingPersistedPairs`、`acknowledgePersistedPair`。
- `frontend/src/features/chat/utils/mergeMessages.ts`：新增按 ID 去重合并纯函数。
- `frontend/src/pages/ChatPage.tsx`：使用 `mergeMessages`、`invalidateQueries` 和 `acknowledgePersistedPair`。
- `frontend/src/features/chat/utils/__tests__/mergeMessages.test.ts`：9 项合并逻辑测试。
- `frontend/src/features/chat/hooks/__tests__/useStreamingChat.test.tsx`：7 项 hook 测试，覆盖新请求在 `message_start` 前失败时不污染上一轮消息状态。

### 技术方案

本地流式消息在服务端详情确认包含同一对完成消息前不删除。渲染时始终按真实消息 ID 去重；流式助手内容仅在发送进行中或尚未确认时优先显示，确认后由服务端数据接管。

### 接口或数据变化

无。后端、接口路径、数据库和迁移均未修改。

### 验证情况

- 通过：`pnpm test`，4 个测试文件共 19 项测试全部通过。
- 通过：`pnpm build`（tsc + vite build）。
- 未执行：浏览器人工联调；需验证新会话首条消息和已有会话续发两种场景下不出现重复消息。

### 遗留问题

- 浏览器端需人工验证：流式完成后消息不闪烁、不重复；详情查询失败时本地完成消息仍可见。
- 停止生成、Redis 断线续流不在本次修复范围。

## 2026-07-27：阶段 1 消息显示顺序修复

### 任务目标

消除用户消息与对应助手消息使用相同时间戳时，因 UUID 次序随机而出现助手消息显示在用户消息之前的问题。

### 实现内容

- 新增 `messages.message_order`，作为会话内唯一、连续的显示序号。
- Echo 和流式写入均在同一事务中锁定会话并为用户/助手消息连续分配序号。
- 历史消息查询改为按 `message_order` 排序；历史数据由迁移按旧的 `created_at, id` 顺序回填。

### 主要文件

- `backend/migrations/versions/20260727_0008_message_order.py`：新增字段、历史回填和会话内唯一约束。
- `backend/repositories/conversations.py`：分配序号并改用稳定排序。
- `backend/tests/test_conversations_repository.py`：覆盖相同会话内时间戳反转时的显示顺序。

### 接口或数据变化

- 数据库新增非空 `message_order`，并增加 `(conversation_id, message_order)` 唯一约束。
- 未新增或修改 HTTP 接口。

### 验证情况

- `py_compile` 通过。
- Alembic `upgrade head` 已应用至 `20260727_0008`。
- 仓储、服务、智能体/会话集成和认证集成测试分模块共 33 项通过。

### 遗留问题

- 以单个 120 秒超时运行全部后端测试会超时；四个模块分开运行均通过，后续应优化测试数据库连接和执行时长。

## 2026-07-27：阶段 1 验收修正

### 实现内容

- 将流式消息写入放在 PostgreSQL 保存点中；同一 `client_request_id` 的并发写入命中唯一约束时，回滚仅本次尝试并重读已创建的 user/assistant 消息对。
- 向已创建的草稿会话首次发送流式消息时，在同一事务中填充标题、设置 `is_draft=false` 并更新 `updated_at`。
- 流式终态更新限定为 `role='assistant' AND generation_status='generating'`，防止覆盖 user 消息、已完成消息或已中断消息。
- 旧流式记录缺少 `reply_to_message_id` 时，返回 `STREAM_REQUEST_UNRECOVERABLE` 而非构造不完整的消息对。

### 测试与验收

- 仓储层测试增加到 14 项，包含双连接同步起点的并发幂等测试、草稿激活、跨会话约束、状态更新保护和旧请求拒绝。
- 后端相关测试共 32 项通过。
- 未执行共享数据库的 `downgrade -1` 回滚验证，因为该操作会删除已存在的 `reply_to_message_id` 数据。

## 2026-07-27：阶段 1 独立验证更正

### 实际验证结果

- PostgreSQL `127.0.0.1:5432` 可连接，Alembic 当前版本为 `20260727_0007 (head)`。
- `py_compile` 通过；新增仓储层/服务层测试与现有集成测试共 27 项通过。
- 数据库实测确认：assistant 消息无法引用另一会话的 user 消息。

### 验收未通过项

- `start_stream_generation()` 先查询、后插入，未使用行锁、`ON CONFLICT` 恢复或唯一冲突重试。两个独立连接的竞态实测确认：同一 `client_request_id` 的第二个写入触发数据库唯一约束异常，不符合幂等性验收标准。
- 向已创建的 `is_draft=true` 会话首次发送流式消息时，代码未将其转为 `is_draft=false`、未更新标题和 `updated_at`。
- `_update_stream_status()` 仅按 `id` 更新消息，没有限定 `role='assistant'`。虽然当前服务层传入的是 assistant ID，但仓储层仍未独立保证“只更新正在生成的 assistant 消息”。
- 幂等查询对早期、`reply_to_message_id IS NULL` 的历史流式记录使用 `LEFT JOIN`，可能构造出空的 user 消息对象。需要明确把它们视为不可恢复的旧请求，而不是继续返回不完整的消息对。
- 新增测试没有覆盖跨会话约束、并发幂等性、流式开始时激活草稿会话和 `updated_at` 更新。
- 没有在共享环境中执行 `downgrade -1` 及再次 `upgrade head`：这会删除已存在的 `reply_to_message_id` 数据，不应将其写成已验证事实。

### 结论

不接受“阶段 1 已完成”的文档声明。上述项目修正并添加对应测试后，才可进入阶段 2。

## 2026-07-27：流式聊天修复阶段 1：消息仓储层事务与幂等性

### 任务目标

修复消息持久化的三个根本问题：`_append_echo_messages()` 被截断返回 `None` 导致上层解包崩溃、`finish_stream_generation()` 存在死代码和职责混乱、流式消息缺少用户-助手回复关联且幂等查询可能关联到错误的 user 消息。

### 实现内容

- 修复 `_append_echo_messages()`：补全 assistant 消息插入、会话标题更新和 `return` 语句，返回完整三元组。
- 删除 `finish_stream_generation()` 及其死代码，拆分为 `complete_stream_generation()`、`interrupt_stream_generation()`、`fail_stream_generation()` 三个职责清晰的方法，均通过 `RETURNING` 更新并抛出明确异常。
- 修改 `start_stream_generation()`：在同一事务中为 assistant 消息写入 `reply_to_message_id`，指向对应的 user 消息。
- 重写幂等查询 `_find_existing_stream_request()`：通过 `assistant.reply_to_message_id` 关联 user 消息，不再从整个 conversation 取最新 user 消息。
- 服务层适配：替换 `finish_stream_generation` 调用为 `complete_stream_generation` / `fail_stream_generation`；对 `generating` 状态的重复请求返回 `REQUEST_IN_PROGRESS` 错误，对 `failed` / `interrupted` 状态返回可重试错误。

### 主要文件

- `backend/repositories/conversations.py`：仓储层修复与重写。
- `backend/services/conversations.py`：服务层适配新仓储方法。
- `backend/migrations/versions/20260727_0007_message_reply_relation.py`：新增 `reply_to_message_id` 字段、索引、检查约束、唯一约束和外键。
- `backend/tests/test_conversations_repository.py`：9 项仓储层测试。
- `backend/tests/test_conversations_service.py`：4 项服务层测试。

### 技术方案

在 `messages` 表新增 `reply_to_message_id UUID NULL`，由 `assistant` 消息指向其回复的 `user` 消息。通过 `(id, conversation_id)` 唯一约束和复合外键保证 assistant 不能引用其他会话的消息。检查约束确保只有 `assistant` 角色可设置该字段。历史数据不回填，保持 `NULL`。

### 接口或数据变化

- 新增数据库迁移 `20260727_0007`，已在本地 PostgreSQL 执行 `alembic upgrade head`。
- 新增 `messages.reply_to_message_id` 字段、`ix_messages_reply_to_message_id` 索引、`uq_messages_id_conversation_id` 唯一约束、`ck_messages_reply_to_role` 检查约束、`fk_messages_reply_to_message_id` 和 `fk_messages_reply_conversation` 外键。
- 无新增 HTTP 接口。

### 验证情况

- 通过：`py_compile` 编译 `repositories/conversations.py`、`services/conversations.py`、迁移文件。
- 通过：Alembic `upgrade head` 和 `downgrade -1` / 再次 `upgrade head`。
- 通过：9 项仓储层测试（echo 三元组、流式开始写入 reply_to_message_id、complete/interrupt/fail 状态更新、幂等单次创建、幂等返回相同消息、不存在消息抛异常、检查约束拒绝 user 消息设置 reply_to_message_id）。
- 通过：4 项服务层测试（echo 不崩溃、已完成重复请求不调用模型、生成中返回 REQUEST_IN_PROGRESS、失败返回可重试错误）。
- 通过：9 项已有集成测试（智能体/会话）和 5 项已有认证集成测试，无回归。

### 遗留问题

- 前端 SSE 解析、停止生成、Redis 断线续流不在阶段 1 范围。
- `GENERATION_FAILED` 状态的重复请求当前返回可重试错误，后续阶段可改为自动重新生成。

## 2026-07-27：流式聊天修复阶段 0：测试基础与协议边界

### 任务目标

为后续 SSE 解析、事件去重、取消与聊天联调修复建立前端测试入口，同时纠正早期计划中与当前范围冲突的 Redis 续流描述。

### 实现内容

- 新增 Vitest、jsdom、React Testing Library 与 jest-dom 开发依赖。
- 新增 `pnpm test` 和 `pnpm test:watch` 脚本。
- 配置 jsdom 测试环境、DOM 断言和基础烟雾测试。

### 主要文件

- `frontend/vite.config.ts`：Vitest 测试环境。
- `frontend/src/test/setup.ts`：jest-dom 断言加载。
- `frontend/src/test/environment.test.tsx`：jsdom 和 Testing Library 烟雾测试。

### 接口或数据变化

无。

### 验证情况

- `pnpm test`：通过，1 个测试文件、1 个测试。
- `pnpm build`：通过。普通受限环境下无法读取现有 `highlight.js` 依赖，以提升权限重跑后构建成功。

### 遗留问题

阶段 1 将修复消息仓储层事务不完整与幂等性缺陷。

## 2026-07-25：确认智能体推理摘要展示策略

### 任务目标

确认真实模型问答、知识库检索和联网能力向用户展示过程的产品边界。

### 实现内容

- 确认展示简短、受控的模型推理摘要。
- 确认知识库检索、联网搜索和文件处理以独立执行步骤、状态和引用呈现，不展示完整原始思维链。
- 更新共享运行与预览设计、问题记录和技术决策。

### 接口或数据变化

无代码或 API 变更；后续运行结果会预留 `reasoningSummary` 与 `executionSteps`。

### 验证情况

- 设计确认阶段，无运行代码或测试变更。

## 2026-07-25：共享智能体运行与实时预览设计

### 任务目标

为编辑页右侧预览和正式聊天定义同一套真实模型运行链路，避免预览继续停留在静态展示或伪造回答。

### 实现内容

- 新增设计文档 `RUNTIME_PREVIEW_DESIGN.md`，定义共享运行服务、DeepSeek 适配、正式持久化聊天和无持久化预览的边界。
- 明确知识库、联网和对话上传分别依赖的后续能力与实施顺序。

### 接口或数据变化

- 规划新增 `POST /api/agents/{agentId}/preview/messages`；当前未修改代码、接口或数据库。

### 验证情况

- 设计阶段，无运行代码或测试变更。

## 2026-07-25：修复预设问题实时预览丢失条目

### 任务目标

修复编辑工作台中添加多个预设问题后，右侧预览只显示最后一个问题的状态同步错误。

### 实现内容

- 表单变更时不再将 `Form.List` 的局部 `changedValues` 直接覆盖预览草稿。
- 改为从表单实例读取完整当前值，再合并到预览草稿，确保所有预设问题都传给右侧欢迎组件。

### 主要文件

- `frontend/src/pages/AgentEditorPage.tsx`：完整表单值到预览草稿的同步。

### 技术方案

`Form.List` 的局部变更数据不能作为整个数组字段的权威值；使用 `form.getFieldsValue(true)` 获取当前表单快照，避免数组被最后一次变更截断。

### 接口或数据变化

无。

### 验证情况

- 待执行：TypeScript 检查和浏览器中连续填写多个预设问题的验证。

### 遗留问题

- 无代码级遗留问题。

## 2026-07-25：统一智能体配置展示与编辑预览

### 任务目标

修复编辑页、列表卡片、顶部标题和侧栏头像/名称来源不一致的问题；明确区分 AI 管家与自建智能体的欢迎区，并让 AI 管家的预设问题由数据库提供。

### 实现内容

- 新增共享头像组件，统一按 `avatarKey` 读取受保护头像 Blob；无头像或读取失败时回退到名称首字。
- 自建智能体聊天欢迎区和编辑页右侧预览复用同一头像欢迎组件；预览输入框复用聊天输入框主体，上传与联网入口随当前草稿配置变化。
- 编辑表单改为按变更字段合并预览草稿，避免单字段更新覆盖名称和头像；保存后立即更新智能体详情、列表和默认入口缓存。
- 内置 AI 管家继续使用既有欢迎区样式，删除前端硬编码预设问题；新增 Alembic 迁移写入内置 AI 管家的预设问题种子数据。

### 主要文件

- `frontend/src/features/agents/components/AgentAvatar.tsx`：共享受保护头像加载与回退展示。
- `frontend/src/features/agents/components/PersonalAgentWelcome.tsx`：自建智能体统一欢迎区。
- `frontend/src/features/agents/components/AgentEditorPreview.tsx`：编辑工作台的实时预览组合。
- `frontend/src/features/chat/components/ChatWelcome.tsx`、`ChatComposer.tsx`：区分内置/自建欢迎区并复用输入主体。
- `frontend/src/pages/AgentEditorPage.tsx`、`frontend/src/layouts/AppLayout.tsx`、`AgentCard.tsx`：消除各处独立头像与缓存状态。
- `backend/migrations/versions/20260725_0005_builtin_agent_preset_questions.py`：补齐内置 AI 管家预设问题数据。

### 技术方案

展示层只接收同一份 `ChatAgent` 配置，头像读取收敛为共享组件；表单草稿通过增量合并保持非表单字段。预览复用真实输入 UI，但因模型和消息工作流尚未接入，发送只给出明确提示，不伪造会话或回答。

### 接口或数据变化

- 无新增 HTTP API 或响应字段。
- 新增数据库数据迁移，向现有 `agent_preset_questions` 表插入内置 AI 管家问题；本地 PostgreSQL 已执行 `alembic upgrade head`。

### 验证情况

- 通过：在 `frontend/` 执行 `pnpm exec tsc --noEmit`。
- 通过：本地 PostgreSQL 已执行 `alembic upgrade head`，查询确认内置 AI 管家有 7 条预设问题。
- 待执行：浏览器端验证头像上传、保存后缓存同步、两类欢迎区和预览入口。

### 遗留问题

- 当前预览不能发送真实消息；需待模型、会话与工具能力接入后新增受控的预览会话接口。

## 2026-07-24：更正 UIW 单栏配置

### 任务目标

按 UIW 组件原生配置固定单栏编辑模式，避免将默认双栏布局误判为不可关闭。

### 实现内容

- 恢复 `@uiw/react-md-editor/nohighlight` 编辑器本体，设置受控 `preview="edit"` 作为编辑态。
- 编辑区只配置设计图要求的 Markdown 命令；不添加 `codeLive`，因此用户无法进入双栏模式。
- 自定义预览按钮只在 `edit` 和 `preview` 间切换，预览内容和编辑内容仍使用同一表单值。
- 为中栏的 `Form.Item`、表单控制容器和编辑器壳显式设置 `width: 100%`，修正其收缩为工具栏内容宽度后导致预览/帮助按钮被挤出的布局问题。
- 为自定义帮助和预览命令补充 `keyCommand`；UIW 工具栏会跳过缺少该字段的命令，因此这是按钮未渲染的直接原因。
- 将 Ant Design 自动生成的 `.ant-form-item-row` 纳入中栏的宽高 flex 链路；它是 `Form.Item` 的直接子元素，未拉伸会使编辑器只占用 row 的内容宽度并在右侧留下空白。
- 将 UIW 工具栏的两组命令从 `space-between` 改为左对齐；`extraCommands`（帮助、预览）应紧跟表格命令，而不是被推到工具栏最右侧。
- 标题工具使用 UIW 的 `group([heading1, …, heading6])`，而非单个 `heading` 命令；前者才会显示可选择 1–6 级的标题菜单。
- 覆盖标题菜单项的默认“包裹选区”执行逻辑，改为替换当前行已存在的 `#` 前缀，防止重复选择标题级别时不断叠加井号。

### 主要文件

- `frontend/src/features/agents/components/SystemPromptEditor.tsx`：UIW 单栏编辑器配置、工具栏命令和预览切换。
- `frontend/src/style.css`：UIW 编辑态和预览态的全高样式。
- `docs/DECISIONS.md`、`docs/features/agent-knowledge-platform/*`、`docs/PROJECT_STATUS.md`：更正技术方案。

### 技术方案

UIW 的 `preview="edit"` 原生将输入区宽度设为 100%、预览区宽度设为 0；预览时反向设置。通过只传入指定命令和自定义预览命令，避免默认的三种模式切换按钮暴露双栏模式。

### 接口或数据变化

无。

### 验证情况

- 通过：`pnpm exec tsc --noEmit`。
- 通过：`git diff --check`。
- 待执行：浏览器人工验证单栏宽度、文本选中、预览往返和保存回填。

### 遗留问题

- 上次 `pnpm build` 在本机命令超时前未完成，不作为通过记录。

## 2026-07-24：提示词编辑器单栏重构

### 任务目标

消除提示词编辑器默认双栏造成的右侧空白区域，使编辑和预览都在中栏同一编辑区域全宽显示。

### 实现内容

- 移除 `@uiw/react-md-editor` 的完整编辑器外壳，避免继续用 CSS 覆盖其输入/预览双栏布局。
- 新增原生受控 `textarea` 和自定义工具栏，所有 Markdown 插入操作直接更新既有 `systemPrompt` 表单值。
- 保留 `@uiw/react-md-editor` 的 Markdown 渲染组件；预览状态在同一内容容器中替换文本框，并可以切回编辑且不丢失内容。

### 主要文件

- `frontend/src/features/agents/components/SystemPromptEditor.tsx`：单栏编辑、Markdown 命令、帮助弹窗和同区预览。
- `frontend/src/style.css`：全宽全高编辑区和工具栏样式。
- `docs/DECISIONS.md`、`docs/features/agent-knowledge-platform/*`、`docs/PROJECT_STATUS.md`：更正技术方案与验证状态。

### 技术方案

`@uiw/react-md-editor` 的完整布局内置输入/预览两列，不适合设计图的单栏编辑体验。将编辑职责收回项目组件，依赖仅用于 Markdown 渲染，从布局上消除空白预览列。

### 接口或数据变化

无。继续使用 `systemPrompt` 字符串和既有 8000 字符限制。

### 验证情况

- 通过：`pnpm exec tsc --noEmit`。
- 待执行：浏览器人工验证单栏全宽、文本选中、工具栏插入、预览往返、保存后回填。

### 遗留问题

- 需要用户在当前浏览器页面刷新后进行视觉和交互复验；在未完成该验证前，不能标记为已验收。

## 2026-07-24：Markdown 编辑器交互与布局修正

### 任务目标

修正 Markdown 编辑器与设计图不一致的尺寸，以及文本选中、预览模式无法返回编辑的问题。

### 实现内容

- 切换到 `@uiw/react-md-editor/nohighlight` 并关闭高亮层，避免选中时文本层和高亮层重叠显示。
- 将预览改为受控状态切换：编辑时显示预览按钮，预览时显示返回编辑按钮，编辑内容始终保留在同一受控值中。
- 为编辑器增加全宽、全高 flex 容器，放大工具栏点击区域和图标，使中栏编辑区填满可用空间。

### 主要文件

- `frontend/src/features/agents/components/SystemPromptEditor.tsx`：无高亮编辑器、可逆预览切换。
- `frontend/src/style.css`：编辑器全高布局和工具栏尺寸。
- `docs/features/agent-knowledge-platform/CHANGELOG.md`、`docs/PROJECT_STATUS.md`：记录实现修正与待验证项。

### 技术方案

保留 Markdown 原始字符串为唯一表单值；预览只切换渲染视图，不改变内容。无高亮构建移除编辑层的语法高亮叠加，以保证浏览器原生选区稳定显示。

### 接口或数据变化

无。未修改依赖、接口、数据库或迁移。

### 验证情况

- 通过：`pnpm exec tsc --noEmit`。
- 未执行：浏览器人工验收；需验证选中文本、预览后返回编辑、编辑区全高以及工具栏尺寸。

### 遗留问题

- 无代码级阻塞；需依据浏览器截图继续进行像素级对比。

### 补充更正

- 浏览器截图确认首轮 flex 调整没有覆盖编辑器内部默认的输入区 `50%` 宽度。现已通过编辑/预览状态类显式控制输入区和预览区宽度，避免再次依赖库内部模式类；`pnpm exec tsc --noEmit` 已通过，仍待浏览器复验。
- 浏览器截图继续确认高度链未建立：工作台原先的 `height: 100%` 没有可靠视口基准，编辑器的百分比高度退化为内容高度。现将工作台设为 `100dvh`，内容网格和表单/编辑器容器按剩余高度拉伸；`pnpm exec tsc --noEmit` 已通过，仍待浏览器复验。
- DevTools 尺寸检查确认 textarea 实际仅为 `382 × 44`，且编辑态仍保留预览列。现将编辑器内容区扣除工具栏高度，强制 `.w-md-editor-area`、`.w-md-editor-text` 与 textarea 继承 100% 高度；编辑态隐藏预览列、预览态隐藏输入区。`pnpm exec tsc --noEmit` 已通过，仍待浏览器复验。

## 2026-07-24：完整 Markdown 提示词编辑器

### 任务目标

按用户确认的设计图，将智能体配置页中栏的普通系统提示词文本框替换为带完整 Markdown 工具栏和预览的编辑器。

### 实现内容

- 新增 `@uiw/react-md-editor@4.1.1`，使用其原生 Markdown 编辑、表格与预览命令。
- 新增 `SystemPromptEditor` 组件，提供加粗、斜体、标题、引用、无序列表、有序列表、代码、表格、帮助和预览。
- 帮助按钮改为站内中文 Markdown 语法弹窗；编辑值继续通过 Ant Design 表单保存为既有 `systemPrompt` 字符串，并限制为 8000 字符。
- 更新工作台样式，使编辑器占满中栏可用高度并保持设计图的浅色工具栏与无边框编辑区。

### 主要文件

- `frontend/src/features/agents/components/SystemPromptEditor.tsx`：Markdown 编辑器、工具栏与语法帮助弹窗。
- `frontend/src/pages/AgentEditorPage.tsx`：将 `systemPrompt` 表单控件替换为独立编辑器组件。
- `frontend/src/style.css`：工作台编辑器布局、工具栏和帮助弹窗样式。
- `frontend/package.json`、`frontend/pnpm-lock.yaml`：记录新增生产依赖。
- `docs/features/agent-knowledge-platform/*`、`docs/DECISIONS.md`、`docs/PROJECT_STATUS.md`：同步已确认需求、技术决策、状态和验收条件。

### 技术方案

采用基于 textarea 的 React Markdown 编辑器，而不引入完整代码编辑器内核；使用组件的受控 `value/onChange` 契约与 Ant Design `Form.Item` 集成，避免改变已有 API 和数据结构。

### 接口或数据变化

无。复用 `PATCH /api/agents/{agentId}` 的 `systemPrompt` 字段；未修改数据库或迁移。

### 验证情况

- 通过：`pnpm exec tsc --noEmit`。
- Vite 已输出成功的生产构建产物（未压缩主 JS 约 2.13 MB），但命令宿主在输出完成后超时回收；不能将该次执行记为完整通过。
- 未执行：浏览器人工验收、工具栏命令和保存回填的端到端测试。

### 遗留问题

- 新增编辑器使主包显著增大；后续应按路由懒加载编辑器并评估是否使用无高亮构建。
- 仍需在浏览器中验证各工具按钮、帮助弹窗、预览切换、8000 字符上限及保存后回填。

## 2026-07-24：智能体三栏搭建工作台

### 任务目标

将原有卡片式编辑表单调整为“配置 / 提示词 / 预览”三栏工作台，并明确当前能力与后续知识库、联网能力的边界。

### 实现内容

- 编辑页提供预设问题、欢迎语、描述、上传入口和联网入口的可保存配置。
- 系统提示词在中栏独立编辑；右栏随表单变化实时预览固定头像式欢迎页、预设问题和输入入口。
- 保留已有 `PATCH /api/agents/{id}` 契约；保存后以服务端返回值重新初始化表单和预览。
- 明确不实现嵌入网站与卡片式头像布局；绑定知识集区域仅说明后续依赖，不提供无后端支持的选择控件。
- 工作台路由隐藏应用级全局侧栏，仅保留工作台自身的配置栏，使三栏结构与确认原型一致。
- 预置问题调整为原型中的整行输入、红色删除圆钮、蓝色添加入口及说明文案；增加置灰的语音识别热词输入以明确其依赖未来语音能力。
- 左侧后续配置改为绑定知识集、上传入口、联网入口、登录要求和描述五个纵向区块；上传/联网使用“需要/不需要”单选，欢迎语、知识集和各入口均补充原型说明文案。
- 右侧预览将上传/联网入口改为清晰的文字按钮，随对应单选值即时显示或隐藏；实际文件上传和联网检索仍待后端能力接入。

### 主要文件

- `frontend/src/pages/AgentEditorPage.tsx`：三栏工作台、保存和实时预览。
- `frontend/src/style.css`：工作台布局与预览样式。
- `docs/features/agent-knowledge-platform/*`：同步需求、前端设计、接口与变更范围。

### 接口或数据变化

无新增接口或迁移；复用智能体更新接口。

### 验证情况

- 通过：`pnpm exec tsc --noEmit`。
- 未执行：浏览器视觉和交互人工验收；完整生产构建仍受本机依赖读取权限问题影响。

### 遗留问题

- 知识集绑定、实际文件上传/联网搜索、语音热词、公开访问和提示词助手等待各自后端能力与权限设计。

## 2026-07-24：智能体创建基础信息与私有头像

### 任务目标

将新建智能体调整为先填写基础信息，再进入完整配置页，并让用户上传的头像存入私有 MinIO。

### 实现内容

- 增加 `interaction_type` 数据列及文本/语音/数字人约束，首期创建固定为文本交互。
- 增加 multipart 基础创建接口、图片签名和大小校验、私有对象写入及经认证头像读取。
- 新增前端基础信息弹窗、客户端文件校验、创建后跳转编辑页和卡片头像 Blob 展示。
- 上传成功选择本地文件后，上传区域直接展示 object URL 图片预览与右上角选中标记；重新点击预览可替换头像。
- 创建确认按钮显式调用表单提交；未通过名称校验时给出提示，避免用户误以为点击没有响应。
- MinIO 认证失败时，头像创建接口改为返回 `503 OBJECT_STORAGE_UNAVAILABLE`，不再将底层 S3 异常堆栈暴露为未处理的 500。

### 接口或数据变化

- 新增 `POST /api/agents/bootstrap`、`GET /api/agents/{agentId}/avatar`。
- `agents` 新增 `interaction_type`，已本地执行 Alembic 升级。

### 验证情况

- 通过：Alembic `upgrade head`、前端 TypeScript `pnpm exec tsc --noEmit`、后端 `compileall`。
- 未执行：后端集成测试，当前虚拟环境未安装 pytest；完整 Vite 构建因本地 `highlight.js` 依赖读取权限被拒绝而未完成。

### 遗留问题

- 仍需在浏览器中实际验证头像上传、私有头像读取和创建后跳转。

## 2026-07-24：认证刷新中断误登出修复

### 任务目标

修复 Vite 热更新或网络中断刷新令牌时，前端错误清除本地会话并跳转登录页的问题。

### 实现内容

- 新增明确的认证拒绝判断：仅缺少刷新令牌，或服务端返回 401/403 时清除本地会话。
- 定时刷新和应用启动认证恢复遇到网络错误、请求取消或热更新中断时保留 token 与当前登录状态。
- 整页重载期间使用已保存的用户摘要作为路由守卫的临时身份，直到服务端明确拒绝凭证。

### 主要文件

- `frontend/src/lib/auth.ts`：认证拒绝类型、判断函数和用户摘要读取。
- `frontend/src/App.tsx`：启动恢复、定时刷新与路由守卫使用认证用户的策略。

### 技术方案

将“请求失败”与“凭证已失效”区分处理。前者可能由 HMR 重载、浏览器取消或临时网络问题引起，不能作为删除会话的依据；后者才触发登出。

### 接口或数据变化

无。继续使用既有认证接口和浏览器存储键。

### 验证情况

- 通过：`frontend/` 中 `pnpm build`。
- 未执行：浏览器中主动中断刷新请求的自动化测试；需在 Vite 开发服务器中人工验证 HMR 期间不会跳转登录页。

### 遗留问题

- 生产构建仍有超过 500 kB 的代码块警告，后续可按路由懒加载处理。

## 2026-07-24：智能体列表设计稿视觉还原

### 任务目标

根据用户提供的智能体列表设计稿，重构此前功能优先版本的页面视觉，不改变智能体、默认打开、删除或聊天跳转的既有规则。

### 实现内容

- 重构顶部横幅、分类栏、卡片网格、卡片标签和底部编辑信息，使布局密度与设计稿对齐。
- 调整左侧侧栏宽度和导航节奏，并补齐设计稿中的自动化任务展示项。
- 原设计插画和头像资源暂未提供；以可替换的本地 CSS 占位图形维持相同的空间结构和视觉层级。
- 根据后续视觉反馈，缩小横幅标题、说明、新建按钮和卡片内部字号；随后确认需要收紧的是顶部“新建智能体”横幅，将其高度从 144px 调整为 112px，列表卡片保持 158px。
- 补充可点击分类筛选：官方筛选只显示内置 AI 管家，现有会话智能体归入文本会话；数字人与语音筛选在尚无对应数据时展示空状态。网格改为不拉伸的最大 496px 卡片宽度，操作菜单使用横向省略号。
- 根据浏览器实际显示效果，将卡片网格最大宽度进一步收紧至 330px，并在分类栏与卡片网格之间增加 16px 间距，避免筛选标签紧贴卡片。

### 主要文件

- `frontend/src/pages/AgentListPage.tsx`：智能体列表页面的横幅、分类栏与网格结构。
- `frontend/src/features/agents/components/AgentCard.tsx`：卡片内容、标签、编辑信息和操作菜单布局。
- `frontend/src/layouts/AppLayout.tsx`、`frontend/src/style.css`：侧栏和页面级视觉规则。

### 技术方案

保留真实 API 列表、默认排序和操作菜单，仅替换展示组件与 CSS。头像与横幅插画隔离为视觉位，避免未来获取原 SVG 后牵连业务数据或路由逻辑。

### 接口或数据变化

无。未新增依赖、后端接口或数据库变更。

### 验证情况

- 通过：`frontend/` 中 `pnpm build`。
- 未执行：浏览器截图与设计稿的像素级人工比对；原设计插画和头像资源未提供。

### 遗留问题

- 后续取得原始 SVG 或头像资源后，需替换当前占位图形并完成最终视觉验收。

## 2026-07-24：智能体管理前后端联调

### 任务目标

实现个人智能体的列表、创建、编辑、默认打开、删除和聊天切换，并让内置 AI 管家可重新作为默认打开对象。

### 实现内容

- 新增智能体列表页、创建/编辑表单和指定智能体聊天路由；聊天页面复用既有会话与消息回显链路。
- 左侧“我的智能体”改为真实数据：默认项置顶，AI 管家与其他个人智能体按规则展示。
- 卡片三点菜单支持个人智能体设默认、编辑、删除；AI 管家仅支持恢复默认打开。
- 新增 `allow_network_access` 数据库字段、API 契约和聊天输入区显示逻辑；实际联网仍未调用外部服务。

### 主要文件

- `frontend/src/pages/AgentListPage.tsx`、`AgentEditorPage.tsx`：智能体管理页面与表单。
- `frontend/src/pages/ChatPage.tsx`、`layouts/AppLayout.tsx`：指定智能体聊天复用与动态侧栏。
- `frontend/src/api/agents.ts`、`frontend/src/features/agents/`：智能体 API、查询键、查询 Hook 与卡片组件。
- `backend/migrations/versions/20260724_0004_agent_network_access.py`：联网入口显示配置迁移。
- `backend/schemas/agents.py`、`repositories/agents.py`、`services/agents.py`：配置字段的读写与响应映射。

### 技术方案

默认智能体继续由服务端入口解析结果作为唯一事实来源。AI 管家“设为默认”调用清空个人默认配置的既有接口，从而保持数据库只保存个人默认智能体、为空即回退 AI 管家的既定模型。删除维持软删除，前端不暴露已删除智能体及其会话入口。

### 接口或数据变化

- 新增并已执行 Alembic 迁移 `20260724_0004`，为 `agents` 添加非空布尔字段 `allow_network_access`，已有记录默认 `false`。
- `POST/PATCH/GET /api/agents` 的请求或响应增加 `allowNetworkAccess`。
- 新增前端路由 `/app/chat/agents/:agentId`、`/app/agents/new`、`/app/agents/:agentId/edit`；未新增后端 HTTP 路由。

### 验证情况

- 通过：`backend/.venv/Scripts/python.exe -m unittest tests.test_agents_conversations_integration -v`，9 项真实 PostgreSQL 集成测试通过。
- 通过：`backend/.venv/Scripts/python.exe -m compileall -q .`。
- 通过：`frontend/` 中 `pnpm build`；首次沙箱内构建因既有依赖读取权限失败，在获批的受限环境外重跑后通过。
- 未执行：浏览器人工端到端检查与像素级原型比对。

### 遗留问题

- 联网按钮目前仅控制显示并提示“功能暂未支持”；DeepSeek、检索和 SSE 尚未接入。
- 生产构建仍有超过 500 kB 的代码块警告，后续可按路由懒加载处理。

## 2026-07-23：PostgreSQL 连接池优化

### 任务目标

定位并消除受保护 API 每次请求反复建立 PostgreSQL 连接造成的明显等待。

### 实现内容

- 新增 `psycopg_pool`，在 FastAPI 生命周期启动时创建共享连接池、关闭时释放。
- 保持 Repository 既有 `with get_connection()` 调用形态：现在它借用并归还池中连接，不再执行新的 TCP/数据库认证连接。
- 新增 `DATABASE_POOL_MIN_SIZE`、`DATABASE_POOL_MAX_SIZE` 配置，默认分别为 1、10，并校验最大值不小于最小值。
- 保留面向独立脚本和测试的延迟初始化兜底；Alembic 不接入 Web API 连接池。

### 主要文件

- `backend/database.py`：共享连接池生命周期和连接借还上下文。
- `backend/main.py`：FastAPI `lifespan` 初始化/关闭连接池。
- `backend/config.py`、`backend/.env.example`：连接池配置与校验。
- `backend/requirements.txt`：新增 `psycopg_pool` 依赖。

### 技术方案

数据库连接是昂贵资源，应在进程生命周期内复用而不是按 Repository 调用新建。池大小采用本地开发保守默认值，避免单进程占用过多 PostgreSQL 连接；迁移是短时管理任务，继续使用 Alembic 自己的 `NullPool`。

### 接口或数据变化

- 无 HTTP 接口、请求响应或数据库 schema 变化，无需 Alembic 迁移。
- 新增环境变量 `DATABASE_POOL_MIN_SIZE`、`DATABASE_POOL_MAX_SIZE`。

### 验证情况

- 直接测量：反复新建 PostgreSQL 连接平均约 605ms；连接池借还约 0.02ms；同一已连接会话的简单查询约 70–230ms。
- 通过：Python 静态编译。
- 通过：认证与智能体/会话真实 PostgreSQL 集成测试共 13 项，耗时约 73 秒。

### 遗留问题

- 连接池不减少 SQL 查询本身的往返或重复查询。若仍需优化，应先记录每个接口的 SQL 数量和耗时，再处理查询合并、索引或 PostgreSQL/容器网络延迟。

## 2026-07-23：聊天会话延迟创建与消息回显联调

### 任务目标

将“点击新会话即创建数据库记录”改为常见聊天产品的延迟创建方式，避免慢请求和无消息的历史记录。

### 实现内容

- 新会话按钮仅清空前端当前会话状态和输入内容，不再调用创建会话接口。
- 新增统一消息入口 `POST /api/conversations/messages`：无 `conversationId` 时在一个事务内创建会话、保存用户消息和阶段 2 回显助手消息；有 ID 时继续既有会话。
- 新增 Ant Design X `Bubble.List` 消息展示；首次发送成功后才选择响应会话并刷新右侧历史记录。
- 发送接口同时校验会话归属和请求中的智能体 ID，防止将其他智能体会话作为当前智能体继续写入。
- 发送采用乐观更新：立即展示用户消息和 Ant Design X 加载气泡；服务端响应后替换为真实消息，失败时恢复输入内容。
- 发送成功后直接更新 React Query 会话详情缓存，只后台刷新会话列表；避免首次发送或旧会话续聊时额外读取完整会话历史。
- 打开未缓存的历史会话时展示左右交错的消息骨架屏；首次发送与继续发送仍优先展示即时消息和加载气泡，不误显示历史加载状态。

### 主要文件

- `backend/schemas/conversations.py`、`backend/routers/conversations.py`：延迟发送请求模型和受保护接口。
- `backend/services/conversations.py`、`backend/repositories/conversations.py`：事务式首次发送及会话/智能体归属校验。
- `frontend/src/api/chat.ts`、`frontend/src/features/chat/hooks/useSendMessage.ts`：消息 API 和 React Query 写操作。
- `frontend/src/pages/AiManagerPage.tsx`、`frontend/src/features/chat/components/ChatMessageList.tsx`、`ChatComposer.tsx`：空白会话状态、消息渲染和发送联调。

### 技术方案

空白会话只存在于页面状态。首条消息提交时由后端在一个事务中完成创建和持久化，避免创建成功但消息失败的孤立会话。当前助手消息仍是阶段 2 回显；后续 SSE 模型接口沿用“首次发送时创建”的契约，不恢复点击即创建。

### 接口或数据变化

- 新增 `POST /api/conversations/messages`，请求包含 `agentId`、`content` 和可选 `conversationId`。
- 未新增数据库迁移；既有 `is_draft` 字段仅保留给兼容接口和历史数据。

### 验证情况

- 通过：新增的真实 PostgreSQL 集成测试，确认首次消息前列表为空，发送后创建会话并按用户、助手顺序保存消息；也确认不能使用另一智能体 ID 向既有会话写入。
- 通过：`pnpm exec tsc --noEmit`。
- 通过：原有 7 项完整智能体/会话集成套件（143 秒）；新增的跨智能体拒绝用例单独通过。

### 遗留问题

- 当前响应是一次性 JSON 回显，不是真实 SSE 或模型答案；模型接入后需在同一延迟创建语义下实现流式 token、取消和失败状态。

## 2026-07-23：AI 管家聊天页步骤 1 与组件库升级

### 任务目标

根据确认的 AI 管家原型实现欢迎态和历史记录的只读联调，并使用最新版 Ant Design X 构建聊天交互区域。

### 实现内容

- 将 Ant Design 升级至 6.5.1，新增 Ant Design X 2.8.0 与 Markdown 2.8.0；移除不兼容的 Pro Components，以原生 `Card` 保持认证页登录卡片。
- 新增聊天领域类型、API 模块和 React Query Hook，调用 `GET /api/chat/entry` 与 `GET /api/conversations`。
- 将空 `AiManagerPage` 拆分为欢迎区、输入区和历史记录抽屉；欢迎区使用 Ant Design X `Welcome`、`Prompts`，输入区使用 `Sender`。
- 实现 AI 管家“全部资料”默认选中、历史记录默认收起、推荐问题预填输入框，以及未实现入口的明确提示；不展示新建文档卡片。

### 主要文件

- `frontend/src/api/chat.ts`、`frontend/src/types/chat.ts`：聊天 API 契约与领域类型。
- `frontend/src/features/chat/`：聊天查询 Hook、欢迎区、输入区和历史记录抽屉组件。
- `frontend/src/pages/AiManagerPage.tsx`：页面组合、加载/失败状态和历史抽屉开关。
- `frontend/src/pages/AuthPage.tsx`：用 Ant Design 原生 `Card` 替代已移除的 ProCard。
- `frontend/package.json`、`frontend/pnpm-lock.yaml`：统一组件库版本。

### 技术方案

页面只组合状态，查询 Hook 管理服务器数据，API 模块统一添加 Bearer 令牌，展示组件不直接发 HTTP 请求。步骤 1 不提前调用创建会话或发送消息接口，所有尚未实现的按钮均显示清晰提示；步骤 2 再接入写操作。

### 接口或数据变化

- 前端开始消费既有 `GET /api/chat/entry` 与 `GET /api/conversations`。
- 未新增后端接口、数据库迁移或模型/RAG 调用。
- 前端依赖升级并移除 `@ant-design/pro-components`。

### 验证情况

- 通过：`pnpm exec tsc --noEmit`。
- 通过：提升权限后的 `pnpm build`，TypeScript 与 Vite 生产构建成功。
- 风险：普通沙箱构建无法读取 Markdown 的语法高亮依赖，但提升权限构建成功；这属于本机文件访问限制，不是代码或依赖兼容错误。

### 遗留问题

- 尚未实现创建会话、选中会话、读取历史消息和发送回显消息，属于聊天页步骤 2。
- 生产包超过 500 kB，后续通过路由级懒加载改善。

## 2026-07-23：阶段 2 消息写入与回显闭环

### 任务目标

在不接入模型、RAG 或 SSE 的前提下，验证聊天消息的持久化、会话所有权、标题更新和顺序读取链路。

### 实现内容

- 新增 `POST /api/conversations/{conversationId}/messages`，接收 1–4000 字符的非空消息，去除首尾空白后处理。
- 在同一 PostgreSQL 事务内验证会话归属和智能体活跃状态，写入 `user` 消息、明确标识为回显的 `assistant` 消息，并更新会话标题/时间。
- 首次未命名会话使用用户首条消息前 50 字作为标题；助手回显的创建时间紧随用户消息，保证现有读取排序稳定呈现“用户在前、助手在后”。
- 扩展集成测试，覆盖消息顺序、标题生成、空白输入拒绝和其他用户发送消息的越权拒绝。

### 主要文件

- `backend/schemas/conversations.py`：消息请求与回显响应模型、空白内容校验。
- `backend/repositories/conversations.py`：事务内消息写入、标题/时间更新和活跃会话查询。
- `backend/services/conversations.py`：消息用例编排和资源不存在映射。
- `backend/routers/conversations.py`：受保护的消息回显 HTTP 接口。
- `backend/tests/test_agents_conversations_integration.py`：消息持久化与越权集成测试。
- `docs/features/agent-knowledge-platform/API_DESIGN.md`：新增 API-007A 的阶段边界说明。

### 技术方案

回显接口与未来 SSE 模型接口并存：前者只验证数据持久化，不承担模型调用；后者仍按既有 API-008 设计在模型/RAG 阶段实现。两条消息和会话更新时间放在一个事务中，避免局部成功。通过不同的微秒级创建时间维持消息逻辑顺序，不引入额外且没有业务含义的排序字段。

### 接口或数据变化

- 新增 `POST /api/conversations/{conversationId}/messages`，成功响应为更新后的会话、用户消息和回显助手消息。
- 无数据库迁移；复用 `messages`、`conversations` 表。
- 未新增依赖；未实现模型调用、检索、SSE 或取消生成。

### 验证情况

- 通过：Python 静态编译。
- 通过：消息回显/顺序/空白校验与跨用户越权拒绝的真实 PostgreSQL 集成测试。
- 通过：完整智能体/会话集成测试共 5 项，以及既有认证集成测试 5 项。

### 遗留问题

- 回显助手消息不是 AI 回答，不能用于模型功能验收。
- 取消生成、流式 token、失败状态和引用持久化仍待阶段 4 的模型/RAG 工作流。

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

## 2026-07-23：单智能体草稿会话约束

### 任务目标

防止同一智能体因重复点击“新会话”产生多个无消息、无标题的空白会话。

### 实现内容

- 为 `conversations` 新增 `is_draft` 字段和按用户、智能体生效的部分唯一索引。
- 重复创建空白会话时复用已有草稿并返回 `200 OK`；首次创建返回 `201 Created`。
- 首条消息写入时将会话从草稿标记为非草稿，之后允许创建下一条新会话。
- 迁移保留每组现有空白会话中最新的一条为草稿，避免历史重复数据阻塞唯一索引创建。

### 主要文件

- `backend/migrations/versions/20260723_0003_single_draft_conversation.py`：字段、历史数据整理和唯一索引迁移。
- `backend/repositories/conversations.py`：草稿会话的原子创建/复用和首条消息状态转换。
- `backend/services/conversations.py`、`backend/routers/conversations.py`：复用结果及 HTTP 状态码。
- `backend/tests/test_agents_conversations_integration.py`：重复创建与首条消息后再创建的集成测试。

### 接口或数据变化

- 新增数据库迁移 `20260723_0003`，已执行 `alembic upgrade head`。
- `POST /api/conversations` 在复用既有草稿时返回 `200 OK`，响应结构不变。

### 验证情况

- 通过：Alembic 已升级至 `20260723_0003`。
- 通过：`backend/.venv/Scripts/python.exe -m unittest tests.test_agents_conversations_integration -v`，6 项通过。

### 遗留问题

- 前端消息发送和历史消息渲染仍待下一步接入；该步骤将使草稿会话转为普通会话。

## 2026-07-23：聊天会话创建与历史选择联调

### 任务目标

将 AI 管家页的“新会话”和右侧历史会话列表从静态提示改为真实 API 调用，同时不提前实现消息发送和消息列表展示。

### 实现内容

- 新增会话创建和会话详情读取 API 封装。
- 使用 React Query Mutation 创建会话，并在成功后失效、刷新当前智能体的会话列表缓存。
- 页面本地保存已选会话 ID；选择历史记录时读取会话详情，右侧列表显示选中状态。
- 新建会话期间禁用对应按钮并显示加载状态；创建或详情请求失败时显示可理解的错误提示。

### 主要文件

- `frontend/src/api/chat.ts`：创建和读取单个会话的 HTTP 请求。
- `frontend/src/types/chat.ts`：会话详情与消息响应类型。
- `frontend/src/features/chat/hooks/useCreateConversation.ts`：创建会话和列表缓存失效。
- `frontend/src/features/chat/hooks/useConversationDetail.ts`：选中会话详情查询。
- `frontend/src/features/chat/components/ConversationHistoryDrawer.tsx`：创建状态、选中样式和选择回调。
- `frontend/src/pages/AiManagerPage.tsx`：组合页面本地状态与会话 API 行为。

### 接口或数据变化

无新增后端接口或数据库迁移。前端开始调用既有 `POST /api/conversations` 与 `GET /api/conversations/{conversationId}`。

### 验证情况

- 通过：`pnpm exec tsc --noEmit`。
- 通过：`pnpm build`。
- 通过：`backend/.venv/Scripts/python.exe -m unittest tests.test_agents_conversations_integration -v`，5 项通过。

### 遗留问题

- 已读取的历史会话详情暂未渲染为消息列表；该展示与发送回显将作为下一步完成。

## 2026-07-23：认证刷新并发保护

### 任务目标

修复刷新令牌请求返回 401 时可能错误清除有效登录状态的问题。

### 实现内容

- 同一浏览器标签页内的多个刷新触发共用同一个进行中的请求，避免 refresh token 轮换产生竞争。
- 刷新失败时，如浏览器存储中的 refresh token 已被其他标签页更新，保留该更新后的会话而不是退出登录。
- 仅当 `/api/auth/me` 明确返回 401 时才尝试刷新；网络失败和服务端错误不再被误判为登录失效。

### 主要文件

- `frontend/src/lib/auth.ts`：刷新请求单飞控制和跨标签页 token 更新识别。
- `frontend/src/App.tsx`：限制自动刷新触发条件为认证 401。

### 接口或数据变化

无。继续使用既有 `POST /api/auth/refresh` 接口。

### 验证情况

- 通过：`pnpm exec tsc --noEmit`。
- 待验证：使用两个浏览器标签页同时接近过期令牌的人工刷新场景。

### 遗留问题

- 服务端明确拒绝当前 refresh token（过期、已退出或密钥变更）时，前端仍会安全退出，用户需要重新登录。

## 2026-07-23：AI 管家欢迎页视觉重做

### 任务目标

将此前功能导向的聊天欢迎页调整为与用户确认原型一致的页面结构，不改变既定的接口边界和按钮能力范围。

### 实现内容

- 重写 `AppLayout` 的侧栏视觉结构，保留真实导航和当前登录账户信息。
- 移除 AI 管家页的大型圆角容器和标题栏，改为纯白聊天画布与右上角文字操作。
- 将欢迎区调整为左对齐问候语和纵向编号预设问题；移除用户明确排除的“新建一个文档”卡片。
- 使用 Ant Design X `Sender` 保留可复用的 AI 输入能力，并将其调整为原型中的紧凑底部输入区。

### 主要文件

- `frontend/src/layouts/AppLayout.tsx`：应用级侧栏与账户区域布局。
- `frontend/src/pages/AiManagerPage.tsx`：聊天欢迎页的区域组合和历史抽屉状态。
- `frontend/src/features/chat/components/ChatWelcome.tsx`：问候语与纵向预设问题展示。
- `frontend/src/features/chat/components/ChatComposer.tsx`：输入区和已确认的能力入口展示规则。
- `frontend/src/style.css`：Ant Design X 输入组件的局部原型样式覆盖。

### 接口或数据变化

无。本次仅调整前端视觉和组件布局，既有聊天入口、会话列表接口保持不变。

### 验证情况

- 通过：`pnpm exec tsc --noEmit`。
- 通过：`pnpm build`（在允许读取依赖文件的环境中执行）。
- 警告：生产包仍超过 Vite 默认 500 kB 阈值；尚未进行浏览器像素级截图比对。

### 遗留问题

- 侧栏个人智能体列表待对应列表接口和创建功能完成后使用真实数据渲染。
- 新建会话、发送回显消息与历史消息展示仍待下一步前端接口联调。

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
## 2026-07-24：智能体入口配置默认值修正

### 任务目标

修正智能体完整配置页中上传文件和联网搜索入口在接口字段缺失时显示为未选择的问题。

### 实现内容

- 为上传文件和联网搜索配置增加前端初始化兜底：字段为 `undefined` 时默认选择“需要”。
- 为两个 Ant Design 表单字段声明 `initialValue=true`，使单选组件在字段未注册或接口值缺失时也能立即显示“需要”。
- 保持用户明确保存的 `false` 值不变，不会将“不需要”覆盖为“需要”。

### 主要文件

- `frontend/src/pages/AgentEditorPage.tsx`：将智能体接口数据转换为表单值，并处理历史/不完整响应字段。
- `docs/PROJECT_STATUS.md`：同步当前修正状态。

### 技术方案

使用空值合并运算符只处理缺失值，而不使用逻辑或运算符，避免错误改变有效的布尔值 `false`。

### 接口或数据变化

无。未修改后端接口、数据库结构或依赖。

### 验证情况

- 通过：在 `frontend/` 执行 `pnpm build`（`tsc && vite build`）。
- 警告：Vite 提示压缩后部分代码块超过 500 kB；首次沙箱构建无法读取本地 `highlight.js` 依赖文件，授权环境重跑后通过。
- 未执行：浏览器人工验证；需确认新建智能体与缺失配置字段的历史智能体均默认显示“需要”。

### 遗留问题

- 若后端持续返回缺失字段，应继续排查其实际响应和历史数据迁移状态；本次前端兜底可避免配置页出现未选择状态。

## 2026-07-24：智能体配置表单绑定更正

### 任务目标

修复上传文件与联网搜索单选项未显示当前值的问题，并消除相同模式对欢迎语控件的影响。

### 实现内容

- 将上传、联网和欢迎语帮助文字移动到 Ant Design `Form.Item` 的 `extra` 属性。
- 保证带 `name` 的表单项只有一个直接表单控件，使表单可向控件注入 `value` 和 `onChange`。
- 删除字段级重复 `initialValue` 及 Radio 的重复预览更新逻辑，统一由表单初始值和 `onValuesChange` 管理。

### 主要文件

- `frontend/src/pages/AgentEditorPage.tsx`：智能体编辑表单绑定和帮助文字布局。
- `docs/PROJECT_STATUS.md`：更正当前问题的根因和处理状态。

### 技术方案

使用 Ant Design `Form.Item.extra` 渲染说明内容，避免命名表单项包含多个直接子节点；默认值仍由 `toFormValues` 统一提供。

### 接口或数据变化

无。未修改后端接口、数据库结构或依赖。

### 验证情况

- 通过：在 `frontend/` 执行 `pnpm build`（`tsc && vite build`）。
- 警告：Vite 提示压缩后部分代码块超过 500 kB。
- 未执行：浏览器人工验证；需确认上传、联网单选分别默认勾选“需要”，并确认选择“不需要”后保存和预览同步正确。

### 遗留问题

- 无代码级阻塞；仍需完成浏览器人工验收。
# 2026-07-25：流式聊天前后端首次联调

### 任务目标

让正式聊天和智能体编辑预览都调用同一套 DeepSeek 流式运行能力，而不是继续使用回显或静态提示。

### 实现内容

- 前端新增 POST SSE 消费逻辑与 `useStreamingChat`，按 `requestId` 和递增 `sequence` 忽略重复事件。
- 正式聊天页改为实时追加模型 `answer_delta`；编辑页预览改为将当前草稿配置提交到预览流接口，消息仅保留在页面内存。
- 应用 `20260725_0006` 迁移，为正式消息增加请求幂等字段及 `generating` 状态。

### 主要文件

- `frontend/src/api/chat.ts`：流式请求与 SSE 帧解析。
- `frontend/src/features/chat/hooks/useStreamingChat.ts`：前端流式消息状态。
- `frontend/src/pages/ChatPage.tsx`：正式聊天入口接线。
- `frontend/src/features/agents/components/AgentEditorPreview.tsx`：草稿预览入口接线。

### 接口或数据变化

- 使用 `POST /api/conversations/messages:stream` 和 `POST /api/agents/{agentId}/preview/messages:stream`。
- 已执行 Alembic `20260725_0006`。

### 验证情况

- 后端相关模块 `py_compile` 通过。
- 前端 `pnpm build` 通过。
- 尚未完成浏览器真实模型请求、停止生成、断线续流与 Redis 缓冲验证。

### 遗留问题

- 阶段 A 仍为进行中，不应作为完整流式聊天能力验收。

# 2026-07-25：流式聊天渲染与工作流纠正

### 任务目标

纠正流式聊天加载态、Markdown 渲染与模型运行架构，使阶段 A 不再以直接 HTTP 调用替代智能体工作流边界。

### 实现内容

- 恢复生成中空助手消息的三点 loading，并展示 SSE `status` 文案。
- 助手气泡改用项目已安装的 `@ant-design/x-markdown`，支持流式 Markdown 安全渲染。
- DeepSeek 改由 LangChain `ChatOpenAI` 的 OpenAI 兼容适配调用；LangGraph 执行 `prepare_input -> model` 最小运行图。

### 接口或数据变化

- 不新增数据库迁移或 HTTP 路由。
- 新增生产依赖：`langchain-core`、`langchain-openai`、`langgraph`。

### 验证情况

- LangGraph 图编译通过。
- 使用已配置 DeepSeek 完成最小真实调用，返回 `runtime-ok`。
- 后端模块编译与应用导入通过；`http://127.0.0.1:8001/docs` 可访问。
- 前端 `pnpm build` 通过。

### 遗留问题

- 停止生成、Redis 续流、幂等回放和浏览器端人工验收未完成。
- 受控处理摘要、检索步骤和引用仍是后续阶段，当前不展示模型原始思维链。

# 2026-07-27：聊天生成过程组件调整

### 任务目标

将位置不当的“正在生成回答”文字替换为 Ant Design X 组件，并为未来知识库检索和联网等可审计运行步骤保留前端扩展边界。

### 实现内容

- 选择 Ant Design X `ThoughtChain`，并将其置于正在生成的助手消息内部，而非独立显示在消息列表上方。
- 新增 `ChatRunSummary`，使用受控步骤数据渲染运行过程；当前 SSE 协议只提供“正在生成回答”，因此不会虚构检索或联网节点。
- 定义运行步骤的加载、成功、失败和中止状态，以便后续 SSE 契约在真实接入知识库/联网工具后追加相应节点。
- 保持模型原始思维链不对用户展示；该组件仅用于展示可解释、可审计的执行摘要。

### 主要文件

- `frontend/src/features/chat/components/ChatRunSummary.tsx`：Ant Design X `ThoughtChain` 的受控运行摘要展示。
- `frontend/src/features/chat/components/ChatMessageList.tsx`：将生成态与对应助手消息绑定，移除列表上方的游离状态文案。
- `frontend/src/features/chat/components/__tests__/ChatMessageList.test.tsx`：验证生成态运行摘要位于助手消息中。
- `frontend/src/style.css`：运行摘要的紧凑视觉样式。

### 技术方案

采用 `ThoughtChain` 而不是 `Think`：聊天运行会随模型调用、知识库检索、网页搜索与引用整理逐步产生多个受控事件，链式节点可表达其顺序及完成状态。该方案只呈现后端明确产生的运行摘要，不暴露或模拟模型内部推理。

### 接口或数据变化

无。本次未改动 SSE 协议、后端接口、数据库迁移或依赖；后续新增检索/联网事件时，可在既有运行步骤模型中映射为真实节点。

### 验证情况

- 通过：在 `frontend/` 执行 `pnpm test -- ChatMessageList.test.tsx`，3 项测试通过。
- 通过：在 `frontend/` 执行 `pnpm build`（`tsc && vite build`）。
- 警告：Vite 报告压缩后主包超过 500 kB；现有依赖带来的警告，未因本次新增组件而解决。
- 未执行：浏览器端真实 SSE 流式视觉验收。

### 遗留问题

- 当前后端仅发送 `generating` 状态；知识库检索、联网搜索、引用整理等步骤需要在相应能力真正接入时扩展 SSE 事件并完成页面联调。

# 2026-07-27：生成中思考链闪烁样式调整

### 任务目标

将生成中思考链的蓝色 loading 圆圈替换为参考图中的轻量 `blink` 样式。

### 实现内容

- 生成中节点启用 Ant Design X `ThoughtChain` 的 `blink` 属性。
- 生成中节点改用中性提示图标，不再使用 `loading` 状态图标；标题在生成期间闪烁。
- 完成、失败和中止节点继续使用对应的状态图标，保证后续多步骤运行摘要可识别。

### 主要文件

- `frontend/src/features/chat/components/ChatRunSummary.tsx`：运行节点的 blink 与图标状态映射。
- `frontend/src/style.css`：进行中提示图标改为中性色。
- `frontend/src/features/chat/components/__tests__/ChatMessageList.test.tsx`：验证生成节点启用 blink 且不传递 loading 状态。

### 技术方案

保留 `ThoughtChain` 作为运行过程容器，仅针对进行中节点调整视觉语义。这样不会牺牲未来检索、联网与引用等多步骤状态的顺序和完成态表达。

### 接口或数据变化

无。

### 验证情况

- 通过：在 `frontend/` 执行 `pnpm test -- ChatMessageList.test.tsx`，3 项测试通过。
- 通过：在 `frontend/` 执行 `pnpm build`（`tsc && vite build`）。
- 警告：Vite 报告压缩后主包超过 500 kB。

### 遗留问题

- 仍需在浏览器实际流式回复中确认闪烁节奏与图标视觉效果。

## 2026-07-27：前端路由按需加载

### 任务目标

降低首次访问应用时的 JavaScript 体积，避免聊天渲染和 Markdown 编辑器依赖进入所有路由的首屏资源。

### 实现内容

- 使用 React `lazy` 将正式聊天页、智能体列表页和智能体编辑页改为路由级按需加载。
- 在现有 `BrowserRouter` 内增加统一的 `Suspense` 加载占位，保持认证守卫和应用布局职责不变。

### 主要文件

- `frontend/src/App.tsx`：定义延迟加载页面与路由加载状态，并保持现有路由契约。

### 技术方案

在路由入口执行代码分割，而不改变页面内部的查询、会话或表单逻辑。聊天 Markdown 渲染和编辑器依赖会随目标页面加载，从而降低登录后进入应用时的初始下载量。

### 接口或数据变化

无。

### 验证情况

- 通过：`frontend/` 执行 `pnpm test`，6 个测试文件、29 项测试全部通过。
- 通过：`frontend/` 执行 `pnpm build`，TypeScript 检查与生产构建通过。
- 构建产物：入口脚本为 91.41 kB（gzip 28.99 kB）；`chat` 分包仍为 683.83 kB，Vite 保留超过 500 kB 的警告。
- 未执行：浏览器端路由跳转人工验收；需在正式聊天与编辑页联调时一并确认首访加载占位和跳转体验。

### 遗留问题

- `chat` 分包仍超过 Vite 的 500 kB 警告阈值；后续可在聊天功能内部继续拆分，不影响当前流式聊天验收。
# 2026-07-27：Docker Worker 的 SSH 隧道数据库配置隔离

## 任务目标

让本机 API 与 Docker Worker 能通过同一条 SSH 隧道访问远程 PostgreSQL，同时不共用含义不同的 `127.0.0.1` 地址。

## 实现内容

- Worker Compose 服务按顺序加载 `backend/.env` 和 `backend/.env.worker`，后者只覆盖容器运行所需的数据库地址。
- 忽略本地 `backend/.env.worker`，并提供不含真实凭证的 `.env.worker.example`。

## 主要文件

- `docker-compose.infrastructure.yml`：为 Worker 增加专用环境文件。
- `backend/.env.worker.example`：Docker Worker 的安全配置模板。
- `.gitignore`：避免提交 Worker 的本地数据库凭证。

## 技术方案

本机 API 保持经 SSH 隧道访问 `127.0.0.1`；Docker Worker 使用 `host.docker.internal` 访问宿主机同一隧道。Redis 和 MinIO 继续使用 Compose 服务名。

## 接口或数据变化

无。

## 验证情况

- 已确认两个环境文件都配置了数据库地址，且 API 使用本机地址、Worker 使用 `host.docker.internal`。
- 待执行 Docker Worker 重建后的真实数据库连接验证。

## 遗留问题

- 当前 Worker 只处理文档队列；聊天保持直接 SSE，不恢复 Redis/RQ 续流实现。

## 2026-07-27：知识库阶段 3.0 Worker 最小闭环准备

### 任务目标

为后续文档处理建立受控依赖、配置和 Worker 连通探测，不开始资料树、上传、真实解析或 Embedding 业务。

### 实现内容

- 在 Worker 依赖清单中声明 PyMuPDF、`python-docx` 和 FlagEmbedding；未引入 OCR、云端 Embedding 或聊天续流依赖。
- 新增本地模型缓存、文件大小、处理超时和 Embedding 批处理大小配置，并为 Docker Worker 增加持久化模型缓存卷。
- 新增只读 `document-processing` 探测任务，验证 Worker 进程中的 PostgreSQL `SELECT 1` 与私有 MinIO Bucket 可访问；任务不创建业务数据、不上传对象且不加载模型。
- 增加任务的正常结果与缺失 Bucket 失败路径单元测试。

### 主要文件

- `backend/requirements.txt`：文档解析和本地 BGE 运行依赖声明。
- `backend/config.py`、`backend/.env.example`：非敏感运行配置及说明。
- `backend/workers/tasks.py`：只读 Worker 依赖探测。
- `backend/scripts/verify_infrastructure.py`：投递并校验新的文档 Worker 探测任务。
- `docker-compose.infrastructure.yml`：Worker 本地模型缓存卷。
- `backend/tests/test_document_worker_tasks.py`：Worker 探测任务单元测试。

### 技术方案

模型、解析和向量化仍保留在后续 Worker 阶段；本次先证明 Worker 能独立访问其必需基础设施，避免将容器网络、对象存储和模型问题混入同一故障链路。

### 接口或数据变化

无。未创建数据库迁移，也未新增 HTTP 接口。

### 验证情况

- 通过：`backend/.venv/Scripts/python.exe -m unittest tests.test_document_worker_tasks`，2 项测试通过。
- 通过：相关 Python 文件 `py_compile` 与 `git diff --check`。
- 未执行：Docker Worker 重新构建、真实队列消费和 PostgreSQL/MinIO 探测；当前终端未找到 Docker CLI。

### 遗留问题

- 需在具备 Docker CLI 的环境中重建 Worker 后运行 `backend/scripts/verify_infrastructure.py`，再决定阶段 3.0 是否完成。

## 2026-07-27：知识库阶段 3.1 资料树与数据模型

### 任务目标

建立私有资料树、文件处理持久化模型和资料范围的数据边界；不接入真实文件上传、异步处理或检索。

### 实现内容

- 新增 Alembic `20260727_0009`，定义 `knowledge_nodes`、`document_versions`、`ingestion_jobs`、`document_chunks` 和 `agent_knowledge_scopes`，包含状态、版本、分块序号和资料范围唯一约束。
- 新增资料树 Repository、Service、Schema 与 Router，提供当前用户资料树读取和文件夹创建。
- 文件作为父节点、越权父节点和同级重名均由 Service 拒绝；内置 AI 管家资料范围不持久化为共享关联记录。
- 新增失败文件重新处理的路由边界，当前明确返回“文档处理尚未开放”，不伪装为已投递任务。

### 主要文件

- `backend/migrations/versions/20260727_0009_knowledge_foundation.py`：知识库阶段 3.1 表、约束与索引。
- `backend/repositories/knowledge.py`：资料树与范围查询。
- `backend/services/knowledge.py`：资料树业务规则。
- `backend/schemas/knowledge.py`、`backend/routers/knowledge.py`：资料树 HTTP 契约。
- `backend/tests/test_knowledge_service.py`：资料树组合和非法父节点/同名规则测试。

### 技术方案

资料树以邻接表表示，后续范围递归由查询展开，因此新建到已选文件夹的子节点可自动进入范围。根节点与子节点分别使用部分唯一索引，避免 PostgreSQL `NULL` 唯一性语义放过根目录同名。

### 接口或数据变化

- 新增 `GET /api/knowledge/nodes`、`POST /api/knowledge/nodes`。
- 增加 `POST /api/knowledge/files/{fileId}/reprocess` 的未开放边界；当前返回 `DOCUMENT_PROCESSING_UNAVAILABLE`。
- 数据库迁移尚未实际应用。

### 验证情况

- 通过：`tests.test_knowledge_service` 与既有 Worker 任务测试共 5 项通过。
- 通过：Python 编译、Alembic `upgrade head --sql` 离线 SQL 生成、`git diff --check`。
- 未执行：真实数据库迁移、资料树 API 集成、跨用户数据库权限测试和 Docker Worker 验收；按本轮指示未将其作为当前完成条件。

### 遗留问题

- 阶段 3.2 负责接入上传、对象存储、任务创建和真实失败重试；阶段 3.3 才会写入分块与向量。

## 2026-07-27：知识库阶段 3.2 根目录前端原型

### 任务目标

根据用户提供的两张原型图，先完成知识库根目录的视觉布局和基础前端交互。

### 实现内容

- 新增独立知识库页面及路由级懒加载入口，替代原空白页面。
- 实现文档管理横幅、根目录路径工具栏、搜索、网格/列表切换与资料卡片布局。
- 文件和文件夹卡片在悬停或选中时显示左上角多选框。
- 实现“新建”Office 文档/文件夹菜单及“上传”文件/文件夹菜单，匹配原型信息架构。
- 当前使用本地展示样例，页面明确说明尚待后端资料树接入；未创建模拟上传或模拟文件记录。

### 主要文件

- `frontend/src/pages/KnowledgeBasePage.tsx`：页面级组合、局部视图与选择状态。
- `frontend/src/features/knowledge/components/KnowledgeItemGrid.tsx`：资料卡片与悬停多选展示。
- `frontend/src/features/knowledge/components/KnowledgeActionMenus.tsx`：新建和上传菜单。
- `frontend/src/features/knowledge/types.ts`：展示项目类型。
- `frontend/src/style.css`：知识库页面的原型视觉样式。
- `frontend/src/App.tsx`：知识库页面的路由级懒加载。

### 接口或数据变化

无。未调用、修改或新增后端上传接口；当前展示数据只用于前端视觉搭建。

### 验证情况

- 通过：`pnpm build` 的 TypeScript 编译阶段。
- 未通过：Vite 打包阶段读取既有 `highlight.js` 语言文件时出现系统“拒绝访问”，与本次页面源代码无直接错误关联。
- 未执行：浏览器像素级人工验收，待用户确认页面视觉后继续调整。

### 遗留问题

- 阶段 3.2 后续需接入真实资料树、创建文件夹、上传、对象存储和处理状态；当前菜单仅展示，不应作为功能完成标记。

## 2026-07-28：知识库多选批量操作前端交互

### 任务目标

补齐资料卡片多选后的批量操作界面，匹配用户提供的移动、删除和取消选择原型。

### 实现内容

- 资料卡片被选中后显示蓝色选中态，并在摘要栏显示已选数量。
- 增加“移动”“删除”“取消”操作；移动使用目标文件夹选择弹窗，删除要求二次确认。
- 在本地展示样例中实现移动和删除结果，方便验证交互状态；操作完成后清空选择。

### 主要文件

- `frontend/src/pages/KnowledgeBasePage.tsx`：多选状态、批量移动/删除和目标文件夹弹窗。
- `frontend/src/features/knowledge/types.ts`：展示样例的父节点字段。
- `frontend/src/style.css`：批量操作栏、选中态和移动弹窗样式。

### 接口或数据变化

无。当前没有资料移动或删除后端接口，本地操作不持久化。

### 验证情况

- 通过：`pnpm exec tsc --noEmit`。
- 通过：`git diff --check`。

### 遗留问题

- 资料树 API 接入后，需要以服务端返回结果替换展示样例，并为批量移动、删除和权限失败增加统一错误处理。

## 2026-07-28：知识库资料右键菜单

### 任务目标

实现文件夹和文件的右键操作菜单，并让菜单项可由资料配置控制。

### 实现内容

- 新增可配置的资料动作类型；未配置时，文件夹和文件按各自默认动作集渲染。
- 右键资料项时选中该项并在鼠标位置显示上下文菜单。
- 菜单不包含有效期、共享管理；内置文件夹展示样例配置为仅显示“打开”。
- 重命名使用输入弹窗；移动和删除复用本地展示数据操作；预览、编辑、下载明确提示待服务端能力。

### 主要文件

- `frontend/src/features/knowledge/components/KnowledgeContextMenu.tsx`：动作配置到右键菜单的映射与渲染。
- `frontend/src/features/knowledge/components/KnowledgeItemGrid.tsx`：资料项右键事件。
- `frontend/src/features/knowledge/types.ts`：资料动作参数类型。
- `frontend/src/pages/KnowledgeBasePage.tsx`：右键菜单状态和本地交互处理。

### 接口或数据变化

无。动作参数目前仅用于本地展示样例，尚未定义后端授权字段或移动、删除、下载接口。

### 验证情况

- 通过：`pnpm exec tsc --noEmit`。
- 通过：`git diff --check`。

### 遗留问题

- 后续接入资料树 API 时，菜单动作必须基于服务端返回的权限，不得信任前端 `actions` 参数。

### 补充：菜单元数据展示规则

- 快捷键仅在资料项 `shortcuts` 明确提供对应动作时显示；默认动作不附带快捷键。
- 所有者从资料项 `ownerName` 读取；本地展示样例使用当前登录账号，内置资料不传该字段且不显示所有者。

## 2026-07-28：对象存储阻塞状态更正

### 任务目标

更正项目状态中已失效的 MinIO 凭据阻塞记录，避免后续开发计划基于过期信息判断。

### 实现内容

- 删除“后端对象存储凭据不一致导致头像上传被拒绝”的当前阻塞项。
- 记录用户已验证头像上传正常；知识库资料文件上传及 Worker 处理仍未实现，需在阶段 3.2 独立验证。

### 主要文件

- `docs/PROJECT_STATUS.md`：维护当前阻塞项和最近更新时间。
- `docs/DEVELOPMENT_LOG.md`：保留本次状态更正的依据和范围。

### 技术方案

以已验证的实际运行结果替换过期阻塞记录，同时区分已经恢复的头像对象存储链路与尚未实施的知识库文件处理链路，避免扩大验证结论。

### 接口或数据变化

无。

### 验证情况

- 用户已验证：头像上传正常。
- 未执行：知识库资料文件上传、对象存储写入和 Worker 处理验证；相关功能尚未实现。

### 遗留问题

- 阶段 3.2 实施后，需要对知识库文件上传与异步处理链路执行独立集成验收。

## 2026-07-28：知识库阶段 3.1 资料树管理启动

### 任务目标

将重命名、移动和递归永久删除纳入首期资料树管理，并开始以服务端权限和数据一致性规则替代前端展示样例操作。

### 实现内容

- 用户确认删除文件夹递归删除全部后代，并先清理资料范围、分块、处理任务和版本等数据库关联，再删除对象存储原文件。
- 新增资料树节点更新与删除 API 骨架；移动拒绝自身/后代目标，同级名称冲突由服务端拒绝。
- 对象清理失败记录服务端异常日志，数据库删除不回滚；待上传阶段建立可重试清理机制。

### 主要文件

- `backend/routers/knowledge.py`：资料树更新和删除接口。
- `backend/services/knowledge.py`：资料树业务校验及对象清理协调。
- `backend/repositories/knowledge.py`：递归子树关联清理与持久化操作。
- `backend/schemas/knowledge.py`：更新请求结构。

### 接口或数据变化

- 新增 `PATCH /api/knowledge/nodes/{nodeId}` 与 `DELETE /api/knowledge/nodes/{nodeId}`。
- 未新增数据库表；使用既有阶段 3.1 迁移中的资料树、版本、任务、分块与资料范围表。

### 验证情况

- 通过：后端相关模块 `py_compile`、既有知识库服务单元测试（3 项）及 `git diff --check`。
- 未执行：真实数据库迁移、递归删除集成测试、对象存储清理测试和前端联调。

### 遗留问题

- 仍需补齐前端真实资料树查询与操作调用，并在应用迁移后进行端到端验证。

## 2026-07-28：资料树页面真实数据联调

### 任务目标

将知识库页面的本地展示样例替换为受认证的服务端资料树，并将首期目录操作接入真实 API。

### 实现内容

- 新增资料树 API 客户端与 React Query 缓存键。
- 页面改为读取服务端资料树，支持当前目录浏览、返回上级、刷新和空/加载/失败状态。
- 新建文件夹、重命名、移动、右键删除和批量删除均调用真实接口；删除确认明确提示递归且不可恢复。
- 上传相关菜单仍未调用上传接口，保持阶段 3.2 待实现状态。

### 主要文件

- `frontend/src/api/knowledge.ts`：资料树 HTTP 请求。
- `frontend/src/features/knowledge/knowledgeKeys.ts`：资料树缓存键。
- `frontend/src/pages/KnowledgeBasePage.tsx`：真实资料树页面状态与目录操作。
- `frontend/src/features/knowledge/components/KnowledgeActionMenus.tsx`：新建文件夹入口。

### 接口或数据变化

前端开始消费 `GET/POST/PATCH/DELETE /api/knowledge/nodes`；未新增数据库迁移。

### 验证情况

- 通过：`pnpm exec tsc --noEmit`、`git diff --check`。
- 未执行：真实数据库迁移、浏览器端到端验证和递归删除集成测试。

### 遗留问题

- 迁移应用后需验证资料树账号隔离、循环移动拒绝、同级重名和递归删除关联清理。

## 2026-07-28：知识库迁移应用与加载异常修复

### 任务目标

处理知识库页面首次读取资料树时的服务端 500 错误。

### 实现内容

- 根据 ASGI 堆栈确认当前 PostgreSQL 停留在 `20260727_0008`，缺少 `knowledge_nodes` 表。
- 执行 Alembic 升级，将当前数据库升级到 `20260727_0009 (head)`，创建资料树及其关联表。

### 主要文件

- `backend/migrations/versions/20260727_0009_knowledge_foundation.py`：本次实际应用的既有知识库基础迁移，未修改。

### 接口或数据变化

- 数据库新增既有迁移定义的 `knowledge_nodes`、`document_versions`、`ingestion_jobs`、`document_chunks`、`agent_knowledge_scopes` 表及相关索引。

### 验证情况

- 通过：`alembic current` 确认版本为 `20260727_0009 (head)`。
- 通过：知识库服务单元测试 3 项、相关模块 Python 编译和 `git diff --check`。
- 待执行：浏览器刷新后的资料树读取与目录操作端到端验证。

### 遗留问题

- 当前数据库为空资料树是正常初始状态；请在页面创建文件夹以验证真实读取和写入链路。

## 2026-07-28：资料树历史导航与面包屑

### 任务目标

让资料树工具栏的后退、前进、上一层级和路径展示具备真实导航行为。

### 实现内容

- 进入目录时记录页面级目录历史；后退和前进按历史栈切换目录。
- 上一级返回当前目录的父节点；根目录时禁用。
- 面包屑显示“根目录 / 子目录 …”，每一级均可点击跳转。
- 仅存在可用目标时高亮导航按钮；不可用按钮保持禁用样式。

### 主要文件

- `frontend/src/pages/KnowledgeBasePage.tsx`：目录历史栈、路径计算与导航事件。
- `frontend/src/style.css`：可用/禁用按钮和可点击面包屑样式。

### 接口或数据变化

无；仅使用已加载的资料树数据进行本地目录导航。

### 验证情况

- 通过：`pnpm exec tsc --noEmit`、`git diff --check`。
- 待执行：浏览器人工验证后退、前进、上一级和面包屑跳转。

### 遗留问题

无新增阻塞项。

## 2026-07-28：资料树五层深度限制

### 任务目标

限制个人知识库目录嵌套深度，控制递归操作与后续检索范围展开的复杂度。

### 实现内容

- 确认根目录下为第 1 层，最多允许 5 层文件夹。
- 创建第 6 层，或移动后使任一后代超过第 5 层时，服务端返回 `KNOWLEDGE_DEPTH_LIMIT_EXCEEDED`。

### 主要文件

- `backend/repositories/knowledge.py`：节点深度与子树高度查询。
- `backend/services/knowledge.py`：创建和移动校验。
- `backend/tests/test_knowledge_service.py`：深度超限测试。

### 接口或数据变化

资料树创建/移动可能返回 `409 KNOWLEDGE_DEPTH_LIMIT_EXCEEDED`；无数据库迁移。

### 验证情况

- 通过：知识库服务单元测试 4 项、相关 Python 模块编译、`git diff --check`。

### 遗留问题

- 前端接近上限的提示可后续补充；服务端已作为最终限制。

## 2026-07-28：知识库阶段 3.1 浏览器验收完成

### 任务目标

确认资料树管理在真实浏览器与当前 PostgreSQL 环境中达到阶段 3.1 验收条件。

### 实现内容

- 用户已完成资料树创建、双击进入、历史导航、面包屑跳转、重命名、移动、递归删除、五层限制和账号隔离的浏览器验收。
- 项目当前目标转入阶段 3.2A：上传入口与四种允许格式的前后端限制。

### 主要文件

- `docs/PROJECT_STATUS.md`：将当前阶段更新为 3.2A。
- `docs/features/agent-knowledge-platform/README.md`：修正阶段 3.1 实现与验收状态。

### 接口或数据变化

无。

### 验证情况

- 用户已验证：阶段 3.1 资料树全流程浏览器验收完成。

### 遗留问题

- 阶段 3.2A 尚未实现上传接口和前后端格式限制。

## 2026-07-28：知识库阶段 3.2A 格式校验基础

### 任务目标

为仅允许 PDF、TXT、Markdown、DOCX 的上传规则建立服务端最终校验边界。

### 实现内容

- 新增支持格式校验：扩展名、声明 MIME、空文件与内容特征联合判断。
- PDF 必须具有 `%PDF-` 文件头；DOCX 必须是含 Word 主文档的 OpenXML ZIP；TXT/Markdown 必须能以 UTF-8 解码。
- 不支持格式统一返回 `415 UNSUPPORTED_DOCUMENT_TYPE`。

### 主要文件

- `backend/services/document_validation.py`：纯文档格式校验逻辑。
- `backend/services/errors.py`：统一不支持格式错误。
- `backend/tests/test_document_validation.py`：允许与拒绝场景测试。

### 接口或数据变化

新增错误契约 `UNSUPPORTED_DOCUMENT_TYPE`；上传 HTTP 接口将在 3.2A 后续步骤接入该校验。

### 验证情况

- 通过：文档校验与资料树服务单元测试共 6 项、Python 编译、`git diff --check`。

### 遗留问题

- 尚未实现上传接口、前端选择器限制、文件夹上传、对象存储写入与处理任务投递。

## 2026-07-28：阶段 3.2A 单文件上传入口

### 任务目标

将四种允许格式的前后端校验接入真实单文件上传链路。

### 实现内容

- 新增受认证的 `POST /api/knowledge/files`，在对象存储写入前检查文件大小、名称、MIME 与内容特征。
- 成功上传后写入私有对象存储，创建资料树文件节点及初始 `uploaded` 文件版本；数据库写入失败时尝试删除已写对象。
- 上传菜单显示仅支持 PDF、TXT、Markdown、DOCX；浏览器文件选择器与客户端扩展名校验拒绝其他格式。

### 主要文件

- `backend/routers/knowledge.py`：文件上传接口。
- `backend/services/knowledge.py`：上传业务编排与失败清理。
- `backend/repositories/knowledge.py`：文件节点与初始版本持久化。
- `frontend/src/api/knowledge.ts`：上传 API 客户端。
- `frontend/src/features/knowledge/components/KnowledgeActionMenus.tsx`：支持格式提示及上传入口。
- `frontend/src/pages/KnowledgeBasePage.tsx`：受限文件选择与上传状态。

### 接口或数据变化

- 新增 `POST /api/knowledge/files`，使用 `multipart/form-data` 的 `file` 与可选 `parentId`。

### 验证情况

- 通过：前端 `pnpm exec tsc --noEmit`、后端上传相关模块 Python 编译、`git diff --check`。
- 未执行：真实 MinIO 写入与浏览器上传端到端验证；待当前环境实际上传四种允许格式和一个非法格式后确认。

### 遗留问题

- 文件夹上传、RQ 任务投递、解析、状态推进和预览尚未实现。

## 2026-07-28：阶段 3.2A 文件夹选择与层级上传

### 任务目标

支持从知识库页面选择文件夹，并保留包含文件的目录层级上传四种允许格式。

### 实现内容

- 上传菜单的“文件夹”调用浏览器目录选择器；按文件的相对路径逐级创建资料树目录并上传文件。
- 文件夹内只要含有不支持格式，前端在开始网络写入前整体拒绝。
- 浏览器目录选择 API 不提供空目录信息，因此本期只创建包含允许文件的目录层级；空目录不会被上传。

### 主要文件

- `frontend/src/features/knowledge/components/KnowledgeActionMenus.tsx`：文件与文件夹上传入口。
- `frontend/src/pages/KnowledgeBasePage.tsx`：目录选择、相对路径展开、目录创建和逐文件上传。

### 接口或数据变化

无新增后端接口；复用既有创建文件夹与单文件上传 API。

### 验证情况

- 通过：`pnpm exec tsc --noEmit`、`git diff --check`。
- 未执行：包含嵌套目录、非法格式和 MinIO 实际写入的浏览器端到端验证。

### 遗留问题

- 当前批量上传发生网络或服务端错误时可能已有部分文件成功，页面会刷新资料树提示用户检查结果；后续可增加逐文件结果列表和重试。

## 2026-07-28：上传文件名称与类型图标修正

### 任务目标

修正上传后文件标题携带路径前缀及所有文件使用同一图标的问题。

### 实现内容

- 上传服务将传入文件名规范化为路径最后一段，避免目录相对路径出现在资料树文件标题中。
- 资料树响应新增当前文件版本的 MIME 类型与大小。
- 前端按 MIME 与扩展名映射 PDF、Word 和文本/Markdown 图标，不再将所有文件降级为同一图标。

### 主要文件

- `backend/repositories/knowledge.py`：查询当前版本 MIME 与大小。
- `backend/schemas/knowledge.py`、`backend/services/knowledge.py`：返回文件元数据并规范化名称。
- `frontend/src/api/knowledge.ts`、`frontend/src/pages/KnowledgeBasePage.tsx`：消费 MIME 并选择图标类型。

### 接口或数据变化

资料树文件节点新增可空的 `mimeType`、`byteSize`；文件夹保持为空。

### 验证情况

- 通过：前端 `pnpm exec tsc --noEmit`、后端 Python 编译、`git diff --check`。

### 遗留问题

- 需在浏览器刷新资料树后验证既有 PDF 与 DOCX 的图标；旧文件若没有版本 MIME，需要在后续处理阶段补齐或按扩展名回退。

## 2026-07-28：删除目录后的上传上下文修复

### 任务目标

防止删除当前目录或其祖先后，页面仍以已删除目录作为上传父节点。

### 实现内容

- 资料树刷新后检测当前目录是否仍存在；不存在时自动返回根目录并重置目录历史与选中状态。
- HTTP 客户端现读取统一错误响应的 `message` 字段；文件夹上传失败时展示服务端具体原因。

### 主要文件

- `frontend/src/pages/KnowledgeBasePage.tsx`：失效目录恢复与上传错误展示。
- `frontend/src/api/http.ts`：统一错误消息解析。

### 接口或数据变化

无。

### 验证情况

- 通过：`pnpm exec tsc --noEmit`、`git diff --check`。

### 遗留问题

- 仍需浏览器复测“删除当前文件夹后重新上传同名文件夹”的完整流程。

## 2026-07-28：上传无效文档提示修正

### 任务目标

区分“不支持的文件格式”与“扩展名允许但文件为空或内容无效”的上传失败原因。

### 实现内容

- 空文件、无效 PDF 文件头或无效 DOCX OpenXML 结构返回 `422 EMPTY_OR_INVALID_DOCUMENT`。
- 不支持扩展名继续返回 `415 UNSUPPORTED_DOCUMENT_TYPE`。
- 单文件上传界面展示后端具体错误信息。

### 主要文件

- `backend/services/document_validation.py`：校验错误分类。
- `backend/services/errors.py`：无效文档错误定义。
- `frontend/src/pages/KnowledgeBasePage.tsx`：上传失败提示。

### 接口或数据变化

新增错误契约 `EMPTY_OR_INVALID_DOCUMENT`。

### 验证情况

- 通过：文档校验单元测试 3 项、Python 编译、`git diff --check`。

### 遗留问题

- 仍需浏览器上传 0 KB DOCX，确认界面显示新的明确提示。

## 2026-07-28：知识库检索链路接入

### 任务目标

将独立 embedding Worker 产出的向量接入受资料范围约束的聊天检索，并向用户展示可追溯引用。

### 实现内容

- 新增检索服务：查询向量仅召回当前用户、当前智能体资料范围内、当前且索引完成的文档分块；先取 Top 8，再向模型提供最多 5 条。
- 聊天运行时先检索，再将资料上下文作为独立系统消息传入模型；检索异常时降级为普通回答。
- 新增 SSE `sources` 事件、消息引用展示和引用持久化字段迁移。
- embedding Worker 已由用户构建并启动，日志确认其监听 `embedding` 队列。

### 主要文件

- `backend/services/retrieval.py`：检索编排与模型上下文构造。
- `backend/repositories/knowledge.py`：受范围约束的 pgvector 查询。
- `backend/services/conversations.py`：检索、流式来源事件和引用保存。
- `frontend/src/features/chat/components/ChatMessageList.tsx`：文件名、定位与原文片段展示。
- `backend/migrations/versions/20260728_0011_message_citations.py`：持久化助手消息引用。

### 接口或数据变化

- 新增聊天 SSE `sources` 事件。
- `MessageResponse` 新增 `citations`。
- 新增迁移 `20260728_0011`，需要执行 Alembic 升级。

### 验证情况

- 通过：Python 编译、切分/Worker/流式协议单元测试 15 项、前端 TypeScript 检查、`git diff --check`。
- 未执行：真实文档上传后的模型下载、向量写入、范围召回和浏览器引用验收，等待迁移与运行环境验证。

### 遗留问题

- 当前智能体资料范围的配置界面尚未接入；未配置范围时严格过滤会返回空结果。

## 2026-07-28：阶段 3.2A 上传验收完成

### 任务目标

确认四种允许格式的单文件与文件夹上传、限制和资料树写入达到当前验收要求。

### 实现内容

- 用户已验证单文件和文件夹上传基本正常。
- 阶段目标转入异步解析、处理状态、失败重试和预览。

### 主要文件

- `docs/PROJECT_STATUS.md`：当前阶段更新为 3.2B。

### 接口或数据变化

无。

### 验证情况

- 用户已验证：上传文件与文件夹基本正常。

### 遗留问题

- 文件尚未投递 Worker，仍停留在 `uploaded` 状态，不能参与检索或提供内容预览。

## 2026-07-29：智能体知识集绑定选择器视觉重构

### 任务目标

将智能体编辑页“请选择知识集”的简易勾选列表替换为资料浏览器式选择弹窗，并明确不在该入口提供新建和上传操作。

### 实现内容

- 新增只读知识集选择弹窗，使用现有受认证资料树读取接口加载资料。
- 支持根目录/子目录浏览、后退、前进、上一级、面包屑、当前目录搜索和文件夹或文件的多选。
- 取消操作保留已保存的范围；只有点击“确定”才更新编辑页中的待保存范围，仍由既有智能体保存流程提交。
- 弹窗不显示新建、上传、删除、移动等资料管理入口，避免在绑定场景中扩大操作范围。

### 主要文件

- `frontend/src/features/knowledge/components/KnowledgeScopeSelectorModal.tsx`：资料树浏览与多选交互组件。
- `frontend/src/pages/AgentEditorPage.tsx`：接入选择组件并保留既有资料范围保存接口。
- `frontend/src/style.css`：选择弹窗的工具栏、网格资料卡和底部操作样式。
- `docs/PROJECT_STATUS.md`、`docs/ARCHITECTURE.md`：同步当前状态和模块职责。

### 技术方案

将资料浏览选择抽为知识库 feature 下的独立展示组件，而不是把导航、搜索和选择状态继续堆积在智能体页面。组件仅读取资料树，资料的创建、上传与维护仍留在知识库管理页，保持权限和职责边界清晰。

### 接口或数据变化

无新增接口、数据库或依赖；复用 `GET /api/knowledge/nodes` 及既有智能体资料范围读取/保存接口。

### 验证情况

- 通过：`pnpm exec tsc --noEmit`。
- 通过：`pnpm test -- --run src/features/knowledge/components/KnowledgeItemGrid.test.tsx`（1 项）。
- 通过：`git diff --check`。
- 未通过：`pnpm build` 的 TypeScript 阶段通过，但 Vite 在读取项目既有 `highlight.js` 依赖文件时遭遇 Windows `EPERM/拒绝访问`；该依赖位于 Markdown 编辑器的现有构建链路，非本次选择器引入。
- 待执行：浏览器人工验证弹窗的视觉、目录导航、选择取消和保存后的资料范围。

### 遗留问题

- 搜索当前按所在目录过滤；若后续需要跨目录全局搜索，应单独确定结果定位与导航规则。

## 2026-07-29：知识集选择卡片对齐修正

### 任务目标

修正知识集绑定弹窗中资料卡片被垂直置于内容区域中央的问题。

### 实现内容

- 将资料画布改为从工具栏下方起始排列，消除工具栏与第一行资料卡之间的非预期大面积空白。
- 移除卡片按钮不对称的上下内边距，使文件图标与名称在卡片可点击区内严格上下居中。

### 主要文件

- `frontend/src/style.css`：知识集选择器画布与资料卡片的对齐样式。

### 技术方案

资料画布使用水平居中、垂直顶部对齐；卡片内部仍使用 Flex 居中，复现资料浏览器从顶部开始排列的视觉节奏。

### 接口或数据变化

无。

### 验证情况

- 待执行：浏览器人工确认第一行卡片紧邻工具栏显示，且卡片图标与名称上下居中。

### 遗留问题

- 无新增问题。

## 2026-07-29：知识集绑定弹窗视口居中修正

### 任务目标

修正整个知识集绑定弹窗使用默认顶部定位、在内容较高时贴近浏览器底部的问题。

### 实现内容

- 为知识集绑定弹窗启用 Ant Design 的 `centered` 定位，使整个弹窗在可视区域上下居中显示。

### 主要文件

- `frontend/src/features/knowledge/components/KnowledgeScopeSelectorModal.tsx`：绑定弹窗的视口定位。

### 技术方案

使用组件库内置的居中定位，而非通过额外的固定偏移量覆盖样式，以便弹窗高度随不同分辨率自适应。

### 接口或数据变化

无。

### 验证情况

- 待执行：浏览器人工确认整个弹窗上下居中且不贴近底部。

### 遗留问题

- 无新增问题。

## 2026-07-29：复用知识库导航与搜索工具栏

### 任务目标

消除知识集绑定弹窗对知识库页导航、面包屑和搜索栏结构与样式的重复实现。

### 实现内容

- 抽取 `KnowledgeNavigationToolbar` 共享组件，统一后退、前进、上一级、面包屑与搜索输入框的 DOM 结构和样式。
- 知识库管理页改为使用共享组件，原有目录历史、刷新、上传和视图切换逻辑保持在页面层。
- 知识集绑定弹窗改为使用同一共享组件，仅保留自己的只读资料树与选择状态。

### 主要文件

- `frontend/src/features/knowledge/components/KnowledgeNavigationToolbar.tsx`：共享工具栏组件。
- `frontend/src/pages/KnowledgeBasePage.tsx`：使用共享工具栏替换页面内重复 JSX。
- `frontend/src/features/knowledge/components/KnowledgeScopeSelectorModal.tsx`：使用共享工具栏替换弹窗内重复 JSX。
- `docs/ARCHITECTURE.md`：同步共享组件职责。

### 技术方案

共享组件只负责展示和触发导航事件；目录历史栈与当前目录仍由各自使用场景持有，避免将资料管理页与智能体编辑页的状态强行耦合。

### 接口或数据变化

无。

### 验证情况

- 通过：`pnpm exec tsc --noEmit`、`git diff --check`。
- 待执行：浏览器人工确认两个入口的工具栏一致性。

### 遗留问题

- 无新增问题。

## 2026-07-29：收紧知识集选择器标题间距

### 任务目标

缩短绑定知识集标题与共享导航搜索栏之间的纵向空白。

### 实现内容

- 缩小弹窗标题区的下内边距及内容区的上内边距，使共享搜索栏整体上移 16px。

### 主要文件

- `frontend/src/style.css`：仅调整知识集选择器弹窗的局部间距。

### 技术方案

不修改共享导航组件及知识库管理页样式，仅通过绑定弹窗容器的间距控制保持复用边界。

### 接口或数据变化

无。

### 验证情况

- 待执行：浏览器人工确认标题与搜索栏间距。

### 遗留问题

- 无新增问题。

## 2026-07-29：修正知识集资料图标尺寸

### 任务目标

恢复知识集选择器中资料类型图标应有的卡片尺寸。

### 实现内容

- 将文件名截断样式从宽泛的 `span` 选择器改为专用名称类，避免覆盖 Ant Design 图标容器的字体大小。
- 文件、PDF、Word 和文件夹图标恢复使用选择器既定的 47px 尺寸。

### 主要文件

- `frontend/src/features/knowledge/components/KnowledgeScopeSelectorModal.tsx`：为资料名称增加专用样式类。
- `frontend/src/style.css`：限定文本截断样式的作用范围。

### 技术方案

图标与文件名使用独立语义类，防止第三方组件内部同样使用的 `span` 元素被误匹配。

### 接口或数据变化

无。

### 验证情况

- 待执行：浏览器确认资料类型图标以卡片尺寸显示。

### 遗留问题

- 无新增问题。

## 2026-07-29：显示智能体已绑定资料范围

### 任务目标

让用户在智能体编辑页无需打开选择器，即可确认当前智能体是否绑定了资料以及文件、文件夹的数量。

### 实现内容

- 新增资料范围字段组件，读取现有资料树并按当前资料范围 ID 分别统计文件与文件夹。
- 已绑定时以与确认参考图一致的浅色标签显示“已绑定 N 篇资料，M 个文件夹”。
- 点击标签重新打开选择器；点击 × 清空本次待保存的资料范围。无绑定时保留“请选择知识集”入口。

### 主要文件

- `frontend/src/features/agents/components/AgentKnowledgeScopeField.tsx`：资料范围统计与展示交互。
- `frontend/src/pages/AgentEditorPage.tsx`：将资料范围字段接入编辑表单的待保存状态。
- `frontend/src/style.css`：已绑定状态标签样式。
- `docs/PROJECT_STATUS.md`、`docs/ARCHITECTURE.md`：同步功能状态和组件职责。

### 技术方案

统计逻辑位于智能体 feature 的展示组件内，仅读取既有资料树并以选择的节点 ID 精确分类；资料范围写入仍由编辑页已有保存流程统一处理。

### 接口或数据变化

无新增接口、数据库或依赖；复用既有资料树读取与智能体资料范围保存接口。

### 验证情况

- 通过：`pnpm exec tsc --noEmit`、`git diff --check`。
- 待执行：浏览器确认文件/文件夹计数及清空后保存行为。

### 遗留问题

- 无新增问题。
