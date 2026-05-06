# Performance Monitoring with CSV Logging

Logs CPU and GPU metrics to CSV file instead of console spam.

## What It Does

- ✅ Checks CPU/GPU every 2 seconds (configurable)
- ✅ Saves to CSV file: `performance_metrics.csv`
- ✅ Tracks which worker is working on which task
- ✅ No console spam - clean logs!

## CSV Format

```csv
timestamp,worker_id,task_id,cpu_percent,gpu_percent
2026-05-07T01:00:00,worker-1,heartbeat,15.3,0
2026-05-07T01:00:05,worker-1,job_abc123,45.2,78.5
2026-05-07T01:00:10,worker-2,job_def456,32.1,65.3
```

## Setup

### 1. Rebuild Workers
```bash
docker compose -f docker-compose.worker.yml up --build --scale worker=10
```

### 2. Metrics Saved Automatically
CSV file is created at `/app/performance_metrics.csv` inside each worker container.

### 3. Analyze Results
```bash
# Copy CSV from container
docker cp distributedllmproject-worker-1:/app/performance_metrics.csv .

# Analyze
python analyze_performance.py
```

## Analysis Output

```
============================================================
PER-NODE PERFORMANCE
============================================================
worker-1
  Tasks: 327 | Avg CPU: 45.2% | Avg GPU: 78.5%
worker-2
  Tasks: 315 | Avg CPU: 32.1% | No GPU
worker-3
  Tasks: 340 | Avg CPU: 38.7% | No GPU

============================================================
OVERALL AVERAGE
============================================================
CPU: 38.7% | GPU: 26.2%
============================================================
```

## Files

- `worker/performance_monitor.py` - 50 lines
- `analyze_performance.py` - 50 lines
- Integration in `worker.py` - 3 lines

Simple and clean!
