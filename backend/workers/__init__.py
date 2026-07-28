"""RQ task package.

RQ 2.x resolves dotted task names through package attributes. Import the task
module here so queued names such as ``workers.tasks.process_document_ingestion``
remain resolvable inside both dedicated Worker containers.
"""

from . import tasks as tasks

__all__ = ["tasks"]
