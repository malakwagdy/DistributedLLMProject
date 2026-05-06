# Quick Start

## 3 Steps

### 1. Rebuild Workers
```bash
docker compose -f docker-compose.worker.yml up --build --scale worker=10
```

### 2. Let It Run
Metrics are saved to CSV automatically. No console spam!

### 3. Analyze
```bash
# Copy CSV from container
docker cp distributedllmproject-worker-1:/app/performance_metrics.csv .

# Show per-node and overall averages
python analyze_performance.py
```

## Output
```
============================================================
PER-NODE PERFORMANCE
============================================================
worker-1
  Tasks: 327 | Avg CPU: 45.2% | Avg GPU: 78.5%
worker-2
  Tasks: 315 | Avg CPU: 32.1% | No GPU

============================================================
OVERALL AVERAGE
============================================================
CPU: 38.7% | GPU: 26.2%
============================================================
```

Done!
