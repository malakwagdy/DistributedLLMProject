# Quick Start

## 3 Steps

### 1. Rebuild Workers
```bash
docker compose -f docker-compose.worker.yml up --build --scale worker=10
```

### 2. Let It Run
Metrics are saved to `logs/` folder automatically. No console spam!

### 3. Analyze
```bash
# Logs are automatically mounted to host logs/ folder
python analyze_performance.py
```

## Output
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

## Log Files Structure
```
logs/
├── worker-1_metrics.csv    # CPU/GPU metrics with timestamps
├── worker-2_metrics.csv
├── worker-3_metrics.csv
└── activity.log            # Worker activities (start, processing, completed)
```

## Notes
- CPU usage is low (0.5-2%) because GPU does the LLM inference work
- GPU usage shows actual workload (50-80% during tasks)
- MacBook users: Apple Silicon GPU cannot be detected by nvidia-smi

Done!
