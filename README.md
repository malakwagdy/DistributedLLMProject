# Distributed LLM Cluster (Current Setup)

This is the currently used setup for the project:

- `gateway` receives `/ask` requests.
- `master` schedules tasks to worker-specific queues.
- `worker` runs against local Ollama (`phi3`).
- `worker_remote` runs against Kaggle Ollama over ngrok (`phi3:mini`).
- Redis stores queues, heartbeats, processing state, and results.

## Architecture Flow

1. Client calls `POST /ask` on gateway.
2. Gateway pushes task to `incoming_tasks`.
3. Master pops task and assigns it to `worker_queue:<worker_id>`.
4. Worker pulls with `BRPOPLPUSH` to `processing_queue:<worker_id>`.
5. Worker runs RAG + Ollama inference and writes `result:<job_id>`.
6. Gateway polls Redis and returns the result.
7. Master recovery loop requeues stale tasks if a worker dies.

## Prerequisites

- Docker + Docker Compose on local machine.
- Local Ollama running with `phi3` model.
- Kaggle notebook running `scripts/kaggle_ollama_ngrok_setup.py`.
- Local `.env` containing:
  - `REMOTE_OLLAMA_URL=https://<your-ngrok-url>`

## Run (Current)

```bash
docker compose down
docker compose up --build --force-recreate --scale worker=2 --scale worker_remote=2
```

## Scheduler Strategies

```bash
curl -X POST http://localhost:8001/strategy/round_robin
curl -X POST http://localhost:8001/strategy/least_connections
curl -X POST http://localhost:8001/strategy/load_aware
```

## Health Checks

```bash
curl http://localhost:8000/health
curl http://localhost:8001/health
```

## Quick Functional Test

```bash
curl -X POST "http://localhost:8000/ask?prompt=test"
```

## Load Test

```bash
python3 test_client.py
```

## Kaggle/ngrok Notes

- If remote requests fail, rerun Kaggle script and update `.env`.
- Verify tunnel from local machine before compose:

```bash
curl -i "$REMOTE_OLLAMA_URL/api/generate" \
  -H "Content-Type: application/json" \
  -d '{"model":"phi3:mini","prompt":"ping","stream":false}' \
  --max-time 30
```
