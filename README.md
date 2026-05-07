# Distributed LLM Cluster

Distributed system for handling concurrent LLM requests using a queue-based architecture with:

- `gateway` (ingress + client-facing API)
- `master` (scheduler + recovery controller)
- `worker` / `worker_remote` (LLM inference + RAG retrieval)
- Redis (queues, heartbeats, processing state, results, cancellation markers)

This project targets the CSE354 distributed computing workflow: load balancing, task distribution, fault tolerance, and performance evaluation.

---

## 1) Project Structure

```text
distributedLLM/
├─ gateway/
│  ├─ main.py
│  ├─ Dockerfile
│  └─ requirements.txt
├─ master/
│  ├─ main.py
│  ├─ Dockerfile
│  └─ requirements.txt
├─ worker/
│  ├─ worker.py
│  ├─ rag.py
│  ├─ build_index.py
│  ├─ artifact_sync.py
│  ├─ knowledge_base.txt
│  ├─ kb_docs/
│  │  └─ .gitkeep
│  ├─ Dockerfile
│  └─ requirements.txt
├─ scripts/
│  └─ kaggle_ollama_ngrok_setup.py
├─ docker-compose.yml
├─ docker-compose.worker.yml
├─ test_client.py
├─ performance_metrics.csv
└─ README.md
```

---

## 2) High-Level Architecture

1. Client sends `POST /ask` to `gateway`.
2. `gateway` creates `job_id`, enqueues request into Redis `incoming_tasks`.
3. `master` scheduler pops from `incoming_tasks`, chooses worker by strategy, pushes to `worker_queue:<worker_id>`.
4. Worker atomically moves tasks from `worker_queue:<worker_id>` to `processing_queue:<worker_id>` using `BRPOPLPUSH`.
5. Worker retrieves RAG context, calls Ollama, writes `result:<job_id>`.
6. `gateway` polls `result:<job_id>` and returns response to client.
7. Recovery loop in `master` reclaims stale/unreachable in-flight jobs and requeues (bounded attempts).

---

## 3) Core Components

### Gateway (`gateway/main.py`)

- Accepts user prompts via `POST /ask`.
- Adds tasks to `incoming_tasks`.
- Polls for `result:<job_id>` until timeout.
- On timeout:
  - marks `cancel:<job_id>` with TTL
  - returns HTTP `504`.
- Exposes `GET /health` (active workers, strategy, pending queue depth).

### Master (`master/main.py`)

- Runs two background loops:
  - `scheduler_loop()` for assigning new tasks
  - `recover_stale_processing_loop()` for recovery and fault tolerance.
- Supports three strategies:
  - `round_robin`
  - `least_connections`
  - `load_aware`
- Exposes:
  - `GET /health`
  - `POST /strategy/{strategy_name}`.

### Worker (`worker/worker.py`)

- Sends heartbeat (`worker:<id>:heartbeat`) periodically.
- Pulls tasks from worker queue and tracks in processing queue.
- Checks `cancel:<job_id>` before expensive processing to drop canceled jobs early.
- Builds final prompt from:
  - user question
  - retrieved RAG context.
- Calls Ollama `/api/generate`.
- Writes final result (or error payload) to `result:<job_id>`.
- Maintains per-worker load safely (non-negative guard).

### RAG (`worker/rag.py`, `worker/build_index.py`, `worker/artifact_sync.py`)

- `build_index.py`: offline creation of FAISS index from KB documents.
- `rag.py`: loads FAISS index and retrieves top-k context for each query.
- `artifact_sync.py`: optional sync of RAG artifacts from S3-compatible storage (R2).

---

## 4) Redis Data Model

- `incoming_tasks` (list): unassigned requests.
- `worker_queue:<worker_id>` (list): assigned but not started tasks.
- `processing_queue:<worker_id>` (list): in-flight tasks.
- `processing:<worker_id>:<job_id>` (string/json): processing metadata (`task_payload`, `started_at`).
- `result:<job_id>` (string/json + TTL): final answer or error payload.
- `worker:<worker_id>:heartbeat` (string + TTL): liveness.
- `worker:<worker_id>:load` (int): current in-flight load.
- `scheduler:strategy` (string): current scheduling strategy.
- `cancel:<job_id>` (string + TTL): cancellation marker after gateway timeout.

---

## 5) Scheduling Strategies

Change strategy at runtime:

```bash
curl -X POST http://localhost:8001/strategy/round_robin
curl -X POST http://localhost:8001/strategy/least_connections
curl -X POST http://localhost:8001/strategy/load_aware
```

- **Round Robin**: cyclic assignment.
- **Least Connections**: prioritize worker with smallest current load.
- **Load-Aware**: prioritize by `load + queue_depth` to reduce backlog skew.

---

## 6) Fault Tolerance and Recovery

Implemented mechanisms:

- Worker heartbeat expiration indicates unreachable node.
- Recovery loop scans `processing:*`, reclaims stale/unreachable jobs.
- Requeues tasks while `attempts <= MAX_ATTEMPTS`.
- Writes terminal error result if retries are exhausted.
- Cancellation-aware scheduling:
  - master skips canceled jobs
  - worker drops canceled jobs before running inference.

---

## 7) Prerequisites

- Docker + Docker Compose
- Python 3.10+ for local scripts
- Running Redis endpoint reachable from containers
- Ollama endpoint(s):
  - local host Ollama, or
  - remote Ollama over ngrok/Kaggle

---

## 8) Environment Configuration

Create project-root `.env` (example template):

```env
# Core routing
REDIS_URL=redis://<redis-host>:6379
MASTER_URL=http://<master-host>:8001
REMOTE_OLLAMA_URL=https://<ngrok-domain>

# Optional RAG artifact sync from S3/R2
RAG_S3_ENDPOINT=https://<account>.r2.cloudflarestorage.com/
RAG_S3_BUCKET=<bucket>
RAG_S3_PREFIX=rag
RAG_S3_ACCESS_KEY_ID=<access-key-id>
RAG_S3_SECRET_ACCESS_KEY=<secret-access-key>
RAG_EMBED_MODEL=nomic-embed-text
```

> Do not commit real credentials into git.

---

## 9) Running the System

### Option A: Main compose stack

```bash
docker compose down
docker compose up --build --force-recreate --scale worker=2 --scale worker_remote=2
```

Exposed services:

- Gateway: `http://localhost:8000`
- Master: `http://localhost:8001`

### Option B: Worker-only compose (additional workers)

```bash
docker compose -f docker-compose.worker.yml up --build --scale worker=2
```

Use this when you want to add/scale workers independently.

---

## 10) API Endpoints

### Gateway

- `POST /ask?prompt=<text>`  
  Returns answer payload or timeout response.
- `GET /health`  
  Returns active worker count, pending incoming queue, and strategy.

### Master

- `GET /health`  
  Returns worker list, per-worker loads, queue depths, incoming queue depth.
- `POST /strategy/{strategy_name}`  
  Changes scheduler strategy.

---

## 11) RAG Workflow

### Build index locally

From `worker/`:

```bash
python3 build_index.py
```

Optional upload to R2/S3:

```bash
python3 build_index.py --upload
```

Input sources (priority order):

1. `worker/kb_docs/*.txt`
2. `worker/knowledge_base.txt` (line-based fallback)

Generated artifacts:

- `worker/rag_data/index.faiss`
- `worker/rag_data/index.pkl`
- `worker/rag_data/manifest.json`

At runtime, workers load FAISS through `rag.py`; optionally sync from remote artifacts via `artifact_sync.py`.

---

## 12) Testing

### A) Smoke test

```bash
curl -X POST "http://localhost:8000/ask?prompt=What is distributed computing?"
```

### B) Health checks

```bash
curl http://localhost:8000/health
curl http://localhost:8001/health
```

### C) Load test

```bash
python3 test_client.py
```

`test_client.py` reports:

- total requests
- business success vs failed
- HTTP status distribution
- failure type distribution
- average latency
- throughput

For coursework evaluation, run multiple loads (for example: `100`, `250`, `500`, `750`, `1000`) and archive output logs.

### D) Failure simulation (fault tolerance validation)

During load test, stop one worker:

```bash
docker stop <worker-container-name>
```

Then verify:

- master logs show reclaim/requeue
- requests continue via remaining workers
- final success/failure accounting is consistent.

---

## 13) Monitoring and Metrics

- Queue/load visibility: `GET /health` from gateway and master.
- Worker runtime logs include scheduling, cancellations, and errors.
- `performance_metrics.csv` can be collected/analyzed for resource observations.

Recommended for report quality:

- save metrics per run (strategy + concurrency + failure scenario)
- include charts for latency/throughput/success rate.

---

## 14) Troubleshooting

### `504 Timed out waiting for response`

- Check worker availability in `master /health`.
- Check Ollama endpoint reachability from worker container.
- Check queue buildup (`incoming_tasks`, `worker_queue:*`).

### Many failures with `status=None` in `test_client.py`

- Usually network/client-side exceptions.
- Verify gateway is up and reachable at `localhost:8000`.

### Remote Ollama errors over ngrok

- Recreate tunnel and update `REMOTE_OLLAMA_URL`.
- Validate manually:

```bash
curl -i "$REMOTE_OLLAMA_URL/api/generate" \
  -H "Content-Type: application/json" \
  -d '{"model":"smollm:135m","prompt":"ping","stream":false}' \
  --max-time 30
```

### RAG artifact mismatch or missing

- Rebuild with `python3 build_index.py`.
- Ensure `RAG_EMBED_MODEL` matches artifact manifest.
- If using remote artifacts, confirm all `RAG_S3_*` variables.

---

## 15) Known Limitations

- Single gateway instance is a potential single point of failure.
- Cancellation is cooperative (jobs may already be executing when timeout occurs).
- Reliability/performance claims should be backed by repeated benchmark runs and archived evidence.

---

## 16) Suggested Report Checklist (Coursework)

- Architecture diagram and data flow
- Strategy comparison (round robin vs least connections vs load-aware)
- Load test table (100 to 1000+ users)
- Fault-tolerance experiment (worker failure during run)
- Latency/throughput/resource utilization figures
- Limitations and future improvements
- Demo run instructions

---

## 17) Quick Command Reference

```bash
# Start stack
docker compose up --build --force-recreate --scale worker=2 --scale worker_remote=2

# Check health
curl http://localhost:8000/health
curl http://localhost:8001/health

# Change strategy
curl -X POST http://localhost:8001/strategy/load_aware

# Send one request
curl -X POST "http://localhost:8000/ask?prompt=test"

# Run load test
python3 test_client.py
```
