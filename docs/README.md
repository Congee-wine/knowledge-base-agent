# 项目文档

本目录记录以当前代码和可复现检查结果为依据的项目状态。除非明确标注为"规划中"或"待确认"，内容均对应仓库内已存在的实现。

- [PROJECT_STATUS.md](PROJECT_STATUS.md)：当前阶段、已完成功能、进行中事项、下一步计划和已知风险。
- [ARCHITECTURE.md](ARCHITECTURE.md)：项目结构、模块职责、数据库设计、认证流程、RAG 检索流程、LangGraph 工作流和接口列表。
- [DEVELOPMENT_LOG.md](DEVELOPMENT_LOG.md)：按时间记录的开发过程。
- [DECISIONS.md](DECISIONS.md)：从现有代码归纳出的重要技术选择。
- [QUESTIONS.md](QUESTIONS.md)：对后续维护有长期价值的问题与结论。
- [features/agent-knowledge-platform/](features/agent-knowledge-platform/README.md)：首期 AI 管家、智能体、会话与知识库功能设计。
- [features/document-preview/](features/document-preview/README.md)：受认证文件预览功能设计。
- [features/knowledge-retrieval/](features/knowledge-retrieval/README.md)：文本切分、`bge-m3` 向量化与资料范围检索设计。
- [features/chat-stream-resumption/](features/chat-stream-resumption/README.md)：流式对话断线自动重连、事件回放与页面刷新恢复设计。

更新这些文档时，不记录 `.env` 中的真实值、令牌、密码、连接字符串或其他敏感信息。
