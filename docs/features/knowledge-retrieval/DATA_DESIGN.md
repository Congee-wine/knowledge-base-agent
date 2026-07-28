# 数据设计

现有 `document_versions`、`document_chunks` 和 `agent_knowledge_scopes` 将扩展版本化索引能力。

- 分块保存 token 范围、序号、文件页码、标题路径、段落序号与内容哈希。
- 向量记录关联分块、模型名、模型版本和向量维度；索引查询仅访问 current 且 ready 的版本。
- 索引任务记录阶段、重试次数、错误码和新旧版本关系。
- 需要新增/调整字段和索引时必须使用 Alembic 迁移；具体维度以实际 `bge-m3` 适配输出为准，禁止硬编码未验证数值。
