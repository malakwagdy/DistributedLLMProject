# Performance Monitoring

Super simple CPU and GPU monitoring for all workers.

## What It Does

Logs CPU and GPU usage every 2 seconds:
```
[worker-1] CPU: 45.2% | GPU: 78.5%
[worker-2] CPU: 12.5% | No GPU
```

## Setup

### 1. Rebuild Workers
```bash
docker compose -f docker-compose.worker.yml up --build --scale worker=10
```

### 2. Done!
Watch the logs - you'll see CPU and GPU for each worker.

### 3. Optional Dashboard
```bash
python monitor_dashboard.py
```

## Files

- `worker/performance_monitor.py` - 23 lines
- `monitor_dashboard.py` - 35 lines  
- Integration in `worker.py` - 1 line added

That's it!
