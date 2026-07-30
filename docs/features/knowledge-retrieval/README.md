# 知识库检索

## 文档状态

已实现。混合检索、RRF 融合、Rerank 重排、检索可观测性均已跑通，待真实知识库语料端到端校准。

## 功能概述

对已处理文件进行智能分块（标题检测 + 语义边界 + 重叠窗口），由独立 Worker 使用 `BAAI/bge-m3` 向量化，聊天时按用户和智能体资料范围执行混合检索（向量 + 关键字 + RRF 融合 + Rerank 重排），产生可引用的上下文。

## 需求确认信息

- 确认日期：2026-07-28
- 确认依据：用户确认混合切分与推荐方案组合
- 当前版本：2.0
- 需求来源：用户（2026-07-29 确认检索质量升级）
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

- 前端：聊天消息引用区域已实现（可折叠编号资料列表、按资料去重、流式完成后展示）
- 后端：混合检索 Pipeline 已实现（向量召回 + 关键字召回 + RRF 融合 + BGE-Reranker 重排 + 分数阈值筛选 + 文件级上下文限额）
- 数据库：`20260728_0010`（Embedding 任务）、`20260728_0011`（消息引用持久化）、`20260729_0012`（检索可观测性）均已应用
- Worker：独立 embedding 队列和 retrieval 队列已启动；BGE-M3 和 BGE-Reranker 通过 RQ 远程调用
- 测试：分块、检索、Worker、流式协议单元测试已通过；真实知识库语料端到端校准待执行

## 已实现的检索流程

1. `embed_query()` 通过 RQ 远程获取查询向量
2. `search_agent_chunks()` 执行 pgvector 余弦相似度检索（Top 20）
3. `search_agent_chunks_by_keywords()` 执行关键字 ILIKE 检索（Top 20）
4. `_fuse_candidates()` 使用 RRF 融合算法合并两种候选
5. `rerank_query_candidates()` 通过 RQ 远程调用 BGE-Reranker 重排
6. `_select_context_sources()` 按重排分数阈值（0.30）和文件级限额（每文件最多 2 个片段，总计最多 5 个）筛选
7. `_record_retrieval_diagnostics()` 持久化候选集和选中原因到 `retrieval_runs` 表
