# Quick Start - Performance Monitoring

## 3 Simple Steps

### Step 1: Rebuild Workers
```bash
docker compose -f docker-compose.worker.yml up --build --scale worker=10
```

### Step 2: Watch the Logs
You'll see performance metrics in worker logs:
```
[2026-05-04 14:30:45] Worker: distributedllmproject-worker-1
  CPU: 45.2%
  Memory: 2048/8192 MB (25.0%)
  GPU: Not available
------------------------------------------------------------
```

### Step 3: View Dashboard (Optional)
```bash
python monitor_dashboard.py
```

## That's It!

Every worker now logs:
- ✅ CPU usage
- ✅ Memory usage  
- ✅ GPU usage (if available)
- ✅ Updates every 2 seconds

## What Was Added

1. **`worker/performance_monitor.py`** - Simple monitoring code
2. **`monitor_dashboard.py`** - View all workers at once
3. **Updated `worker/worker.py`** - Integrated monitoring
4. **Updated `worker/requirements.txt`** - Added psutil & gputil

## Code is Simple & Short

- `performance_monitor.py`: ~80 lines
- Integration in `worker.py`: 3 lines added
- Dashboard: ~100 lines

Easy to understand and modify!
