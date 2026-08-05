from __future__ import annotations

import json
from collections.abc import Iterator, Mapping
from functools import lru_cache

from config import STREAM_EVENT_RETENTION_SECONDS
from workers.queue import create_redis_connection


def publish(run_id: str, sequence: int, event: Mapping[str, object]) -> None:
    _redis().xadd(_key(run_id), {b"sequence": str(sequence), b"payload": json.dumps(event, ensure_ascii=False)})


def expire_after_terminal(run_id: str) -> None:
    _redis().expire(_key(run_id), STREAM_EVENT_RETENTION_SECONDS)


def subscribe(run_id: str, after_sequence: int) -> Iterator[dict[str, object]]:
    redis = _redis()
    key, cursor = _key(run_id), "0-0"
    for event_id, fields in redis.xrange(key):
        cursor = event_id.decode() if isinstance(event_id, bytes) else event_id
        event = _event(fields)
        if int(event["sequence"]) > after_sequence:
            yield event
            if _terminal(event): return
    while True:
        for _, events in redis.xread({key: cursor}, block=15_000, count=100):
            for event_id, fields in events:
                cursor = event_id.decode() if isinstance(event_id, bytes) else event_id
                event = _event(fields)
                if int(event["sequence"]) <= after_sequence: continue
                yield event
                if _terminal(event): return


def _key(run_id: str) -> str:
    return f"chat:stream:{run_id}"


def _event(fields: Mapping[bytes, bytes]) -> dict[str, object]:
    payload = fields[b"payload"]
    event = json.loads(payload.decode() if isinstance(payload, bytes) else str(payload))
    sequence = fields[b"sequence"]
    event["sequence"] = int(sequence)
    return event


def _terminal(event: Mapping[str, object]) -> bool:
    return event.get("type") in {"message_end", "error"}


@lru_cache(maxsize=1)
def _redis():
    return create_redis_connection()
