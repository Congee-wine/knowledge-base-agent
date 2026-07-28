# 接口设计

## `GET /api/knowledge/files/{nodeId}/preview`

需要 Bearer 认证。

| 文件类型 | 成功响应 |
| --- | --- |
| TXT / Markdown | `application/json`：`kind: text`、`name`、`content`、`isMarkdown` |
| DOCX | `application/json`：`kind: html`、`name`、`html` |
| PDF | `application/pdf` 二进制流 |

错误：`404 RESOURCE_NOT_FOUND`（不存在或无权）、`409 DOCUMENT_NOT_READY`、`415 UNSUPPORTED_DOCUMENT_TYPE`、`422 DOCUMENT_PREVIEW_EMPTY`、`503 DOCUMENT_PREVIEW_UNAVAILABLE`。
