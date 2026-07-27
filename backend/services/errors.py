class DomainError(Exception):
    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


def not_found() -> DomainError:
    return DomainError(404, "RESOURCE_NOT_FOUND", "资源不存在或无权访问")


def stream_request_unrecoverable() -> DomainError:
    return DomainError(409, "STREAM_REQUEST_UNRECOVERABLE", "该流式请求缺少必需消息关联，请重新发送")


def stream_resume_unavailable() -> DomainError:
    return DomainError(409, "STREAM_RESUME_UNAVAILABLE", "当前暂不支持断线续流，请重新发送消息")


def immutable_agent() -> DomainError:
    return DomainError(409, "AGENT_IMMUTABLE", "内置 AI 管家不能修改或删除")


def default_agent_must_be_cleared() -> DomainError:
    return DomainError(409, "DEFAULT_AGENT_MUST_BE_CLEARED", "请先清空默认智能体，再删除该智能体")


def object_storage_unavailable() -> DomainError:
    return DomainError(503, "OBJECT_STORAGE_UNAVAILABLE", "头像存储服务暂不可用，请检查 MinIO 配置后重试")
