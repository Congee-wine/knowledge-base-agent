# 变更记录

## 2026-08-14

- 用户确认个人 Agent 未绑定资料范围时走普通模型回答，并必须明确提示当前未绑定知识库。
- 用户确认内置 AI 管家继续保留 `useKnowledgeBase` 全部资料库开关。
- 将“未绑定资料范围”和“已绑定但无 ready 索引资料”定义为不同路由分支。
- 实现 `check_knowledge_capability` 节点：个人 Agent 查询绑定范围，内置 AI 管家使用 `useKnowledgeBase` 全库开关；新增未绑定范围和关闭全库开关的回归测试。
