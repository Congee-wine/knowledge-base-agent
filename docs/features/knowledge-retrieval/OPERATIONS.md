# Retrieval Operations

## Runtime topology

- `embedding-worker` consumes only the `embedding` queue for document indexing.
- `retrieval-worker` consumes only the `retrieval` queue for query embedding and reranking.
- Both Workers share the model-cache volume, but online retrieval work must not wait behind document indexing tasks.

## Required startup

After changing the compose definition, start the dedicated worker from a terminal that has Docker Compose available:

```powershell
docker compose -f docker-compose.infrastructure.yml up -d --build retrieval-worker
```

## Failure semantics

- `no_match`: The retrieval service completed normally and found no usable source.
- `retrieval_failed`: The retrieval service, Redis queue, embedding model, or reranker failed or timed out. Do not report this as a missing document.

## CPU defaults

`RERANK_CANDIDATE_LIMIT=8` and `RETRIEVAL_QUERY_TIMEOUT_SECONDS=120` are conservative local-development defaults. Increase them only after measuring real query latency and relevance.
