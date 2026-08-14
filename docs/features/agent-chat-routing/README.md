# Agent 问答路由

## 文档状态

待验证。

## 功能概述

明确 LangGraph 在普通问答、个人 Agent 资料范围和内置 AI 管家“全部资料库”开关下的路由规则，避免将“未绑定资料”错误当作“资料尚未完成索引”。

## 需求确认信息

- 确认日期：2026-08-14
- 确认依据：用户确认个人 Agent 未绑定资料范围时走普通模型回答，并明确告知未绑定知识库；内置 AI 管家继续通过 `useKnowledgeBase` 使用当前用户的全部资料库。
- 当前版本：1.0
- 需求来源：LangGraph 工作流审查
- 最后确认人：用户

## 文档列表

- `REQUIREMENTS.md`：路由规则与边界。
- `BACKEND_DESIGN.md`：LangGraph 节点、状态与服务职责。
- `API_DESIGN.md`：现有流式接口的事件语义。
- `ACCEPTANCE_CRITERIA.md`：验收与测试场景。
- `CHANGELOG.md`：需求变更记录。

本功能不涉及数据库结构、缓存结构或其他持久化方案变化。

## 实现状态

- 前端：无需修改事件类型；复用现有 `generating` 运行步骤展示后端文案，浏览器联调待验证。
- 后端：已实现；工作流已区分未绑定范围与绑定后无 ready 文件。
- 数据库：不涉及迁移；复用现有 Agent 范围绑定与文档索引状态数据。
- 接口联调：待验证。
- 测试：后端路由与流式协议回归测试通过；完整后端测试集在 60 秒执行窗口内超时，未获得最终结果。

## 相关全局文档

- `docs/PROJECT_STATUS.md`
- `docs/ARCHITECTURE.md`
- `docs/DECISIONS.md`
- `docs/QUESTIONS.md`
