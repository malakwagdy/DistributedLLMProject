"""Performance Monitor - CPU and GPU with CSV logging"""
import psutil
import csv
import os
from datetime import datetime

try:
    import GPUtil
    GPU_AVAILABLE = True
except:
    GPU_AVAILABLE = False

CSV_FILE = "/app/performance_metrics.csv"

def init_csv():
    """Create CSV file with headers if it doesn't exist"""
    if not os.path.exists(CSV_FILE):
        try:
            with open(CSV_FILE, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['timestamp', 'worker_id', 'task_id', 'cpu_percent', 'gpu_percent'])
        except:
            pass

def log_performance(worker_id, task_id="idle"):
    """Log CPU and GPU to CSV file"""
    cpu = psutil.cpu_percent(interval=0.1)
    gpu = 0
    
    if GPU_AVAILABLE:
        try:
            gpus = GPUtil.getGPUs()
            if gpus:
                gpu = gpus[0].load * 100
        except:
            pass
    
    # Save to CSV
    try:
        with open(CSV_FILE, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                datetime.now().isoformat(),
                worker_id,
                task_id,
                f"{cpu:.1f}",
                f"{gpu:.1f}"
            ])
    except:
        pass
    
    return {"cpu": cpu, "gpu": gpu}
