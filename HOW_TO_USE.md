# How to Use Performance Monitoring

## 1. Run Workers
```bash
docker compose -f docker-compose.worker.yml up --build --scale worker=10
```

## 2. Copy CSV
```bash
docker cp distributedllmproject-worker-1:/app/performance_metrics.csv .
```

## 3. Analyze
```bash
python analyze_performance.py
```

## Output
```
============================================================
PER-NODE PERFORMANCE
============================================================
worker-1: 327 tasks | CPU: 45.2% | GPU: 78.5%
worker-2: 315 tasks | CPU: 32.1% | No GPU

============================================================
OVERALL AVERAGE
============================================================
CPU: 38.7% | GPU: 26.2%
============================================================
```

Done!
