# 软小筑 AI 管家

一个持续迭代的 AI 智能体平台，支持多智能体管理、会话聊天和知识库功能。

## 项目结构

```text
├── frontend/              React + TypeScript 前端应用
│   └── src/
│       ├── api/           HTTP 请求和认证接口封装
│       ├── features/      业务功能模块
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
│   ├── integrations/      第三方服务适配（MinIO、Redis）
│   ├── workers/           RQ 文档处理队列
│   ├── migrations/        Alembic 数据库迁移
│   └── scripts/           工具脚本
└── docs/                  项目文档
    ├── features/          功能设计文档
    ├── PROJECT_STATUS.md  项目当前状态
    ├── ARCHITECTURE.md    架构说明
    ├── DECISIONS.md       技术决策记录
    └── DEVELOPMENT_LOG.md 开发日志
```

## 技术栈

**前端**
- React 18 + TypeScript
- Vite 构建
- Ant Design 6 + Ant Design X
- React Router + React Query + Zustand
- Tailwind CSS

**后端**
- FastAPI + Pydantic
- PostgreSQL + pgvector
- psycopg 连接池
- Alembic 迁移管理
- Argon2 密码哈希 + JWT 认证

**基础设施**
- Redis：缓存和消息队列
- MinIO：S3 兼容对象存储
- RQ：异步任务队列
- Docker Compose：本地开发环境

## 已实现功能

- **用户认证**：注册、登录、令牌刷新、登出、会话管理
- **智能体管理**：创建、编辑、删除、设为默认、内置 AI 管家
- **会话管理**：创建会话、会话列表、消息持久化
- **聊天骨架**：SSE 流式消息、生成状态展示、停止生成

## 当前进行中

- 知识库数据模型和资料树 API
- 流式聊天的完整联调验收
- Docker Worker 文档处理基础设施

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

### 基础设施（可选）

```bash
docker compose -f docker-compose.infrastructure.yml up -d
```

启动 Redis、MinIO 和 RQ Worker。

## 环境变量

复制 `backend/.env.example` 为 `backend/.env`，配置以下变量：

- `DATABASE_URL`：PostgreSQL 连接地址
- `AUTH_SECRET_KEY`：JWT 签名密钥（部署时使用随机强密钥）
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
