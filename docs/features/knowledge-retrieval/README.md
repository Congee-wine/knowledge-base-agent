# 知识库检索

## 文档状态

已确认，待实现。

## 功能概述

对已处理文件进行混合文本切分、由独立本地 Worker 使用 `BAAI/bge-m3` 向量化，并在聊天前按用户和智能体资料范围检索可引用的上下文。

## 需求确认信息

- 确认日期：2026-07-28
- 确认依据：用户确认混合切分与推荐方案组合
- 当前版本：1.0
- 需求来源：用户
- 最后确认人：用户

## 文档列表

- `REQUIREMENTS.md`：业务规则与范围
- `FRONTEND_DESIGN.md`：聊天引用展示设计
- `BACKEND_DESIGN.md`：Worker、切分与检索流程
- `API_DESIGN.md`：内部与前端接口契约
- `DATA_DESIGN.md`：版本化索引数据设计
- `ACCEPTANCE_CRITERIA.md`：验收标准
- `CHANGELOG.md`：变更记录

## 实现状态

- 前端：未开始
- 后端：未开始
- 数据库：待设计迁移
- Worker：待实现独立 embedding 队列
- 测试：未开始
