from __future__ import annotations

from datetime import datetime, timezone
from platform import system


def run_infrastructure_probe() -> dict[str, str]:
    """Return a small result that proves an RQ worker executed this task."""
    return {
        "message": "Worker 已运行",
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "execution_platform": system(),
    }
