# 智问知识库问答智能体

一个支持多智能体管理、流式对话和私有知识库检索的 AI 智能体平台。

## 项目结构

```text
├── frontend/              React + TypeScript 前端应用
│   └── src/
│       ├── api/           HTTP 请求和认证接口封装
│       ├── features/      业务功能模块（chat / agents / knowledge）
│       ├── layouts/       应用布局组件
│       ├── lib/           工具函数和认证逻辑
│       ├── pages/         页面组件
│       ├── routes/        路由声明和守卫
│       ├── stores/        Zustand 状态管理
│       └── types/         TypeScript 类型定义
├── backend/               FastAPI 后端服务
│   ├── routers/           HTTP 路由声明
│   ├── schemas/           Pydantic 请求/响应模型
│   ├── services/          业务规则和用例编排
│   ├── repositories/      数据库访问逻辑
│   ├── retrieval/         文档分块与检索模型
│   ├── integrations/      第三方服务适配（DeepSeek、BGE-M3、Reranker、MinIO）
│   ├── workers/           RQ 异步任务队列（文档解析、Embedding、检索）
│   ├── migrations/        Alembic 数据库迁移
│   └── tests/             后端单元测试与集成测试
└── docs/                  项目文档
    ├── features/          功能设计文档
    ├── PROJECT_STATUS.md  项目当前状态
    ├── ARCHITECTURE.md    架构说明
    ├── DECISIONS.md       技术决策记录
    └── DEVELOPMENT_LOG.md 开发日志
```

## 技术栈

**前端**
- React 18 + TypeScript + Vite
- Ant Design 6 + Ant Design X（聊天组件）
- React Router + React Query + Zustand
- Tailwind CSS

**后端**
- FastAPI + Pydantic
- PostgreSQL + pgvector（向量检索）
- psycopg 连接池
- Alembic 迁移管理
- Argon2 密码哈希 + JWT 认证

**AI 与检索**
- LangGraph（智能体工作流编排）
- DeepSeek API（大语言模型）
- BGE-M3（多语言 Embedding）
- BGE-Reranker（交叉编码器重排）
- RRF 融合算法（向量 + 关键字混合检索）

**基础设施**
- Redis：RQ 任务队列消息中间件
- MinIO：S3 兼容对象存储
- RQ：异步任务队列（文档解析、Embedding、检索）
- Docker Compose：本地开发环境编排

## 已实现功能

### 用户认证
- 注册、登录、JWT 双 Token 认证（Access + Refresh）
- Refresh Token 滑动续期与会话级 Token 吊销
- 前端无感刷新与并发安全控制
- 路由守卫（登录回跳、匿名/受保护路由边界）

### 智能体管理
- 智能体 CRUD（创建、编辑、删除）
- 设为默认智能体、内置 AI 管家（不可修改删除）
- 智能体头像上传（MinIO 对象存储）
- 系统提示词 Markdown 编辑器
- 智能体知识范围绑定（资料树选择器）
- 编辑页实时对话预览

### 流式对话
- SSE 流式对话（正式会话 + 编辑预览双模式）
- 前端自研 SSE 解析器（分块传输、错误恢复）
- 多会话并行流式、生成中断与状态同步
- 乐观更新 + 本地/服务端消息合并
- Markdown 流式渲染、引用来源展示、消息复制
- 运行步骤可视化（检索状态、生成状态）
- 会话列表、历史消息加载

### 知识库管理
- 树形目录结构（创建文件夹、上传文件、重命名、移动、递归删除）
- 5 层嵌套限制、同名校验、账号隔离
- 支持 PDF、TXT、Markdown、DOCX 四种格式
- 异步文档处理流水线（上传 → 解析 → 分块 → Embedding → 索引）
- 文档版本管理与处理状态追踪
- 受认证文件预览（PDF Blob URL、DOCX 沙箱 iframe、TXT/Markdown 文本）

### RAG 检索增强生成
- 混合检索策略：向量检索 + 关键字检索 + RRF 融合排序
- BGE-M3 多语言 Embedding + BGE-Reranker 重排
- pgvector 余弦相似度检索
- 智能文档分块（标题检测 + 语义边界 + 180 字符重叠窗口）
- 文件级上下文限额与重排分数阈值筛选
- 检索可观测性（候选集、排序分数、选中原因持久化）

### LangGraph 智能体工作流
- 多节点条件编排：身份守卫 → 知识检查 → 请求分析 → 检索 → 证据评估 → 生成
- 动态路由策略（直接回答 / 知识库回答 / 目录查询）
- 模型信息隐藏守卫（身份、能力、内部配置问题由后端固定答复）
- 流式状态推送（分析中、检索中、生成中）

### 后端工程化
- 领域错误处理体系（DomainError + 错误码 + HTTP 状态码分离）
- psycopg 连接池与仓储模式
- RQ 异步任务队列（文档解析队列 + Embedding 队列 + 检索队列）
- Alembic 版本化数据库迁移（13 个迁移文件）
- 后端单元测试与集成测试（16 个测试文件）

### 前端工程化
- Feature-based 目录组织
- 路由按需加载（入口包 91 kB）
- 自定义 Hook 抽离业务逻辑
- TypeScript 严格类型约束
- 前端组件与工具测试（8 个测试文件）

## 本地启动

### 前端

```bash
cd frontend
pnpm install
pnpm dev
```

### 后端

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env  # 配置 PostgreSQL 连接等环境变量
fastapi dev main.py
```

### 基础设施

```bash
docker compose -f docker-compose.infrastructure.yml up -d
```

启动 Redis、MinIO、文档处理 Worker、Embedding Worker 和检索 Worker。

## 环境变量

复制 `backend/.env.example` 为 `backend/.env`，配置以下变量：

- `DATABASE_URL`：PostgreSQL 连接地址
- `AUTH_SECRET_KEY`：JWT 签名密钥（部署时使用随机强密钥）
- `DEEPSEEK_API_KEY`：DeepSeek 模型服务访问密钥
- `OBJECT_STORAGE_*`：MinIO 访问配置
- `REDIS_URL`：Redis 连接地址

不要提交真实的 `.env` 文件。

## 项目文档

详细文档位于 `docs/` 目录：

- [项目状态](docs/PROJECT_STATUS.md)：当前进度和下一步计划
- [架构说明](docs/ARCHITECTURE.md)：模块职责和数据流
- [技术决策](docs/DECISIONS.md)：重要选择和理由
- [开发日志](docs/DEVELOPMENT_LOG.md)：开发过程记录
- [功能设计](docs/features/)：重大功能的需求和设计文档
