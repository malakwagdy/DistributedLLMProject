"""Performance Monitor - CPU and GPU with CSV logging"""
import psutil
import csv
from datetime import datetime

try:
    import GPUtil
    GPU_AVAILABLE = True
except:
    GPU_AVAILABLE = False

CSV_FILE = "/app/performance_metrics.csv"

def log_performance(worker_id, task_id="idle"):
    """Log CPU and GPU to CSV file"""
    cpu = psutil.cpu_percent(interval=0.1)
    gpu = 0
    
    if GPU_AVAILABLE:
        try:
            gpu = GPUtil.getGPUs()[0].load * 100
        except:
            pass
    
    # Append to CSV (creates file if needed)
    try:
        with open(CSV_FILE, 'a') as f:
            f.write(f"{datetime.now().isoformat()},{worker_id},{task_id},{cpu:.1f},{gpu:.1f}\n")
    except:
        pass
