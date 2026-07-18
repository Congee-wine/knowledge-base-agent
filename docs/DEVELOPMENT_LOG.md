# 开发日志

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
