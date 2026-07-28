class DomainError(Exception):
    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


def document_queue_unavailable() -> DomainError:
    return DomainError(503, "DOCUMENT_QUEUE_UNAVAILABLE", "文档已保存，但处理队列暂不可用；请稍后重试处理")


def document_not_failed() -> DomainError:
    return DomainError(409, "DOCUMENT_NOT_FAILED", "仅处理失败的文档可以重试")


def not_found() -> DomainError:
    return DomainError(404, "RESOURCE_NOT_FOUND", "资源不存在或无权访问")


def stream_request_unrecoverable() -> DomainError:
    return DomainError(409, "STREAM_REQUEST_UNRECOVERABLE", "该流式请求缺少必需消息关联，请重新发送")


def stream_resume_unavailable() -> DomainError:
    return DomainError(409, "STREAM_RESUME_UNAVAILABLE", "当前暂不支持断线续流，请重新发送消息")


def conversation_generation_in_progress() -> DomainError:
    return DomainError(409, "CONVERSATION_GENERATION_IN_PROGRESS", "该会话正在生成回答，请先停止或等待完成")


def immutable_agent() -> DomainError:
    return DomainError(409, "AGENT_IMMUTABLE", "内置 AI 管家不能修改或删除")


def default_agent_must_be_cleared() -> DomainError:
    return DomainError(409, "DEFAULT_AGENT_MUST_BE_CLEARED", "请先清空默认智能体，再删除该智能体")


def object_storage_unavailable() -> DomainError:
    return DomainError(503, "OBJECT_STORAGE_UNAVAILABLE", "头像存储服务暂不可用，请检查 MinIO 配置后重试")


def invalid_parent_node() -> DomainError:
    return DomainError(409, "INVALID_PARENT_NODE", "父节点必须是当前用户拥有的文件夹")


def knowledge_name_conflict(message: str) -> DomainError:
    return DomainError(409, "KNOWLEDGE_NODE_NAME_CONFLICT", message)


def invalid_knowledge_move() -> DomainError:
    return DomainError(409, "INVALID_KNOWLEDGE_MOVE", "不能将资料移动到自身或其子文件夹中")


def knowledge_depth_limit_exceeded() -> DomainError:
    return DomainError(409, "KNOWLEDGE_DEPTH_LIMIT_EXCEEDED", "文件夹最多支持 5 层嵌套")


def unsupported_document_type() -> DomainError:
    return DomainError(415, "UNSUPPORTED_DOCUMENT_TYPE", "当前仅支持 PDF、TXT、Markdown、DOCX 文档")


def file_too_large() -> DomainError:
    return DomainError(413, "FILE_TOO_LARGE", "文件大小超过允许限制")


def empty_or_invalid_document() -> DomainError:
    return DomainError(422, "EMPTY_OR_INVALID_DOCUMENT", "文件为空，或 PDF/DOCX 文件内容无效")


def invalid_knowledge_update() -> DomainError:
    return DomainError(422, "INVALID_KNOWLEDGE_UPDATE", "重命名或移动必须且只能指定一项")


def processing_unavailable() -> DomainError:
    return DomainError(501, "DOCUMENT_PROCESSING_UNAVAILABLE", "文档处理任务将在上传阶段开放")
