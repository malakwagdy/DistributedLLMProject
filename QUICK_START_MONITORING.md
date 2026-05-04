# Quick Start

## 2 Steps

### 1. Rebuild Workers
```bash
docker compose -f docker-compose.worker.yml up --build --scale worker=10
```

### 2. Watch Logs
You'll see:
```
[worker-1] CPU: 45.2% | Memory: 25.0%
[worker-2] CPU: 12.5% | Memory: 18.8%
```

## Optional: Dashboard
```bash
python monitor_dashboard.py
```

## What Was Added
- `worker/performance_monitor.py` - 11 lines
- `monitor_dashboard.py` - 35 lines
- 1 line in `worker.py`

Done!
