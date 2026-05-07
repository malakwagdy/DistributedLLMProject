# Performance Monitoring with Separate Log Files

Logs CPU/GPU metrics and worker activities to organized log files.

## What It Does

- ✅ Checks CPU/GPU every 2 seconds (configurable)
- ✅ Saves metrics to separate CSV per worker in `logs/` folder
- ✅ Logs all worker activities to `logs/activity.log`
- ✅ Tracks which worker is working on which task
- ✅ No console spam - clean logs!

## Log Files Structure

```
logs/
├── worker-1_metrics.csv    # CPU/GPU metrics with timestamps
├── worker-2_metrics.csv
├── worker-3_metrics.csv
└── activity.log            # Worker activities (start, processing, completed)
```

## CSV Format (Metrics)

```csv
timestamp,worker_id,task_id,cpu_percent,gpu_percent
2026-05-07T01:00:00,worker-1,heartbeat,0.5,10.0
2026-05-07T01:00:05,worker-1,job_abc123,0.5,78.5
2026-05-07T01:00:10,worker-2,job_def456,0.5,65.3
```

## Activity Log Format

```
[2026-05-07 20:29:13] Worker 77d23d5309fe started
[2026-05-07 20:30:18] Worker 77d23d5309fe processing task 6fe1401a-a809-4a08-83ac-3ec5e8b096f6
[2026-05-07 20:30:21] Worker 77d23d5309fe completed task 6fe1401a-a809-4a08-83ac-3ec5e8b096f6
```

## Setup

### 1. Rebuild Workers
```bash
docker compose -f docker-compose.worker.yml up --build --scale worker=10
```

### 2. Metrics Saved Automatically
Logs are automatically mounted to host `logs/` folder. No need to copy from containers!

### 3. Analyze Results
```bash
python analyze_performance.py
```

## Analysis Output

```
============================================================
PER-NODE PERFORMANCE
============================================================
40cdb3e0f389: 83 tasks | CPU: 0.5% | GPU: 53.8%
5cbf60ed7a44: 83 tasks | CPU: 0.5% | GPU: 53.7%
77d23d5309fe: 83 tasks | CPU: 0.5% | GPU: 54.1%

============================================================
OVERALL AVERAGE
============================================================
CPU: 0.5% | GPU: 53.9%
============================================================
```

## Why is CPU Low?

CPU usage is low (0.5-2%) because:
- GPU does the heavy LLM inference work
- CPU only handles task coordination and I/O
- This is expected and normal behavior

GPU usage shows the actual workload (50-80% during tasks).

**Note for MacBook users**: Apple Silicon GPU cannot be detected by nvidia-smi, so GPU will show 0%.

## Files

- `worker/performance_monitor.py` - 25 lines
- `analyze_performance.py` - 55 lines
- Integration in `worker.py` - Activity logging
- `docker-compose.worker.yml` - Volume mount for logs

Simple and clean!
