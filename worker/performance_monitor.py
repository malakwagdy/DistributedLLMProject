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

# Configure psutil to use host /proc
PSUTIL_PROC_DIR = os.getenv("HOST_PROC", "/proc")

def log_performance(worker_id, task_id="idle"):
    """Log CPU and GPU to CSV file - reads host PC stats"""
    # Read host CPU by using host /proc
    try:
        # Create psutil with host proc path
        import psutil._pslinux as pslinux
        pslinux.PROCFS_PATH = PSUTIL_PROC_DIR
        cpu = psutil.cpu_percent(interval=0.1)
    except:
        cpu = psutil.cpu_percent(interval=0.1)
    
    gpu = 0
    if GPU_AVAILABLE:
        try:
            gpu = GPUtil.getGPUs()[0].load * 100
        except:
            pass
    
    # Append to CSV
    try:
        with open(CSV_FILE, 'a') as f:
            f.write(f"{datetime.now().isoformat()},{worker_id},{task_id},{cpu:.1f},{gpu:.1f}\n")
    except:
        pass
