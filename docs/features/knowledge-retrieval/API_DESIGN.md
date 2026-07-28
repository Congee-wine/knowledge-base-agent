# 接口设计

聊天现有接口后续扩展返回结构化 `citations`，每项包含：`documentId`、`fileName`、`pageNumber`（可空）、`sectionTitle`（可空）、`paragraphOrdinal`（可空）、`snippet` 和预览路由所需的文件 ID。

内部检索服务输入为用户 ID、智能体 ID、查询文本；输出最多 5 个已授权来源。服务内部固定执行当前用户、`ready` 文件和智能体资料范围过滤，调用方不得绕过。
