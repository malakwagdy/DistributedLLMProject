# Performance Monitoring

Simple CPU and GPU utilization monitoring for all workers in the distributed network.

## Features

- ✅ **CPU Usage**: Track CPU utilization percentage
- ✅ **Memory Usage**: Monitor RAM usage (MB and %)
- ✅ **GPU Usage**: Track GPU load, memory, and temperature (if available)
- ✅ **Real-time Logging**: Performance metrics logged every 2 seconds
- ✅ **Network-wide**: Monitor all workers across the network
- ✅ **Redis Storage**: Metrics stored in Redis for easy access

## How It Works

### Worker Side
Each worker automatically logs performance metrics every heartbeat (2 seconds):
- CPU percentage
- Memory usage (used/total MB and %)
- GPU info (if GPU available)
- Stores metrics in Redis with key: `metrics:{worker_id}`

### Dashboard
View all workers' performance in real-time:
```bash
python monitor_dashboard.py
```

## Setup

### 1. Install Dependencies
Already included in `worker/requirements.txt`:
- `psutil` - CPU and memory monitoring
- `gputil` - GPU monitoring (optional)

### 2. Rebuild Workers
```bash
docker compose -f docker-compose.worker.yml up --build --scale worker=10
```

### 3. View Dashboard
In a separate terminal:
```bash
python monitor_dashboard.py
```

## Example Output

```
================================================================================
                  DISTRIBUTED LLM PERFORMANCE DASHBOARD
                      Updated: 2026-05-04 14:30:45
================================================================================

Active Workers: 3
--------------------------------------------------------------------------------

[distributedllmproject-worker-1]
  Status: ONLINE | Current Load: 1 tasks
  CPU: 45.2%
  Memory: 2048/8192 MB (25.0%)
  GPU: Not available

[distributedllmproject-worker-2]
  Status: ONLINE | Current Load: 0 tasks
  CPU: 12.5%
  Memory: 1536/8192 MB (18.8%)
  GPU 0 (NVIDIA RTX 3080): 78.5% | Memory: 6144/10240 MB | Temp: 72°C

[distributedllmproject-worker-3]
  Status: ONLINE | Current Load: 2 tasks
  CPU: 67.8%
  Memory: 3072/8192 MB (37.5%)
  GPU: Not available

================================================================================
Press Ctrl+C to exit
```

## Files Added

- `worker/performance_monitor.py` - Core monitoring functions
- `monitor_dashboard.py` - Real-time dashboard viewer
- `PERFORMANCE_MONITORING.md` - This documentation

## Notes

- **CPU monitoring**: Works on all systems
- **GPU monitoring**: Requires NVIDIA GPU and drivers
  - If no GPU detected, shows "GPU: Not available"
- **Metrics refresh**: Every 2 seconds (same as heartbeat interval)
- **Metrics TTL**: Stored in Redis for 60 seconds

## Troubleshooting

### No workers showing up?
- Check workers are running: `docker ps`
- Verify Redis connection in `.env` file
- Check REDIS_URL in dashboard matches worker config

### GPU not detected?
- Normal if using CPU-only setup
- For GPU support, ensure NVIDIA drivers installed
- GPUtil only works with NVIDIA GPUs

## Future Enhancements

- Web-based dashboard (Flask/FastAPI)
- Historical metrics and graphs
- Alerts for high utilization
- Export metrics to CSV/JSON
