# 后端设计

## 模块职责

- `services/agent_runtime.py`：维护 LangGraph 状态、节点和条件边；映射白名单 SSE 事件。
- `services/agent_strategy.py`：仅识别资料目录查询与语义检索，不决定是否启用知识库。
- `services/retrieval.py`：提供范围绑定状态、ready 文档状态、目录查询和检索能力。
- `repositories/knowledge.py`：查询个人 Agent 是否绑定资料范围。
- `repositories/knowledge_retrieval.py`：查询授权范围内的 ready/current/已索引文档。

## 建议状态

现有 `knowledge_available` 应拆为语义明确的状态：

- `knowledge_enabled`：本请求是否允许使用知识库；个人 Agent 由是否绑定范围决定，AI 管家由 `useKnowledgeBase` 决定。
- `has_bound_scope`：个人 Agent 是否绑定至少一个范围节点；AI 管家不使用该字段作为全库模式前置条件。
- `has_ready_knowledge`：授权范围内是否存在 ready/current/已索引文档。
- `retrieval_failed`：检索执行是否异常。
- `sources`：已通过现有 rerank 阈值与上下文限制筛选的可靠来源。

## 节点与条件边

```text
START → guard_identity
guard_identity
  ├─ answer_public_profile → END
  └─ check_knowledge_capability
check_knowledge_capability
  ├─ direct_model_unbound_scope → generate_answer → END
  ├─ direct_model_knowledge_disabled → generate_answer → END
  ├─ knowledge_unavailable → END
  └─ analyze_request
analyze_request
  ├─ execute_document_catalog → END
  └─ execute_semantic_search → evaluate_evidence
evaluate_evidence
  ├─ retrieval_failed → END
  ├─ no_match → END
  └─ generate_answer → END
```

`direct_model_unbound_scope` 可为独立节点，或由能力检查节点写入状态后路由至生成节点；无论实现形式，都必须先产生可见的 `status` 事件，说明未绑定知识库。

## 数据访问

个人 Agent 的绑定状态必须单独查询 `agent_knowledge_scopes`，不能通过“是否存在 ready 文档”推断。ready 检查继续复用现有递归范围展开，并要求文档版本同时满足 current、处理完成和索引完成。

## 错误处理

- 目录查询异常与语义检索异常统一进入 `retrieval_failed` 终态，并记录可定位日志。
- 无 ready 文档与无可靠检索来源分别使用 `no_documents`、`no_match` 阶段。
- 直接模型分支不附带来源，且模型提示词不得声称已检索资料。
# 2026-08-14 调整：知识库概览路径

`agent_strategy` 将概览类问题标记为 `knowledge_overview`，与 `semantic_search` 区分。

```text
analyze_request
  ├─ knowledge_overview → execute_knowledge_operation → generate_answer → END
  └─ semantic_search    → execute_knowledge_operation → evaluate_evidence → generate_answer / no_match / retrieval_failed
```

- `retrieval.execute_knowledge_operation` 对概览从授权范围读取每份 ready 文档的首个已索引片段；查询本身仍由仓储层按用户和 Agent 范围隔离。
- `build_knowledge_overview_context` 负责限制每个片段为 500 字符，避免把完整资料传给模型。
- 概览专用提示词要求模型只根据文件名与片段生成“资料—主题—可回答问题”摘要；具体事实问答不改变原有检索和证据评估规则。
- `build_knowledge_overview_manifest` 在模型流式输出前写入后端生成的完整资料清单；该清单与 `sources` 事件共享同一个 `sources` 列表，保证引用与回答依据一致。
