# API 设计

## 1. 流式发送与恢复

`POST /api/conversations/messages:stream?agentId={agentId}&conversationId={conversationId?}`

请求体在现有字段基础上正式启用：

```json
{
  "requestId": "UUID",
  "content": "用户消息",
  "useKnowledgeBase": false,
  "afterSequence": 42
}
```

- `afterSequence: 0`：首次发送或从首事件订阅。
- `afterSequence > 0`：恢复同一 `requestId`，服务端回放序号大于该值的事件；不得创建消息或再次调用模型。

响应继续使用 `text/event-stream`。所有事件保留 `requestId`、`sequence`、`mode` 和 `type`。新增/扩展的终态必须可表达 `complete`、`failed`、`interrupted`、`timed_out`。

## 2. 会话详情恢复信息

会话详情中的生成中助手消息必须提供恢复所需的非敏感关联信息：`requestId`、`generationStatus` 与服务器已确认的 `lastSequence`。仅返回当前用户所属会话。

## 3. 错误约定

| 代码 | HTTP | 含义 | 前端行为 |
|---|---:|---|---|
| `STREAM_NOT_FOUND` | 404 | 不存在或无权访问任务 | 停止恢复，不泄露任务信息 |
| `STREAM_NOT_RECOVERABLE` | 409 | 缓存过期且无法安全继续 | 读取最终历史或展示失败 |
| `STREAM_ALREADY_FINISHED` | 200/SSE 终态 | 任务已结束 | 消费回放后停止 |
| `STREAM_TIMED_OUT` | SSE 终态 | 超过 5 分钟 | 停止重连并展示超时 |

不再返回现有的 `STREAM_RESUME_UNAVAILABLE`。
