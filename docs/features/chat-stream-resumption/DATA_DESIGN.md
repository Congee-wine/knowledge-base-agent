# 数据设计

## 1. PostgreSQL 生成任务

新增 `stream_runs` 表或等价的独立持久化实体，避免将运行生命周期混入 `messages`：

| 字段 | 说明 |
|---|---|
| `id` | 主键 |
| `request_id` | 客户端幂等键，唯一 |
| `user_id` | 所属用户，用于权限校验 |
| `conversation_id` | 所属会话 |
| `assistant_message_id` | 对应助手消息，唯一 |
| `status` | `queued/generating/complete/failed/interrupted/timed_out` |
| `last_sequence` | 已发布最大事件序号 |
| `started_at/finished_at` | 生命周期审计 |
| `error_code/error_message` | 可诊断失败信息，不保存敏感配置 |

为 `request_id`、`assistant_message_id` 建唯一约束；为 `(user_id, status)` 建索引，支持刷新时发现可恢复任务。迁移需保留已有 `messages.client_request_id` 的幂等约束，不迁移或重写历史完成消息。

## 2. Redis Streams

- Key：`chat:stream:{stream_run_id}`。
- 每条记录：`sequence`、序列化事件载荷、写入时间。
- 生成中持续续期，终态写入后将整条 Stream 的 TTL 固定为 15 分钟。
- Redis 只保存可回放事件，不替代 PostgreSQL 中消息正文、引用和任务终态。

## 3. 生命周期一致性

先在数据库事务中创建任务与消息，再启动执行器。执行器发布事件后更新 `last_sequence`；终态以数据库状态为事实来源，Redis 终态事件用于客户端即时感知。缓存丢失时可凭数据库判定是否已完成，但不能凭空重建逐段事件。
