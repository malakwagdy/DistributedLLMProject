"""Performance Monitor - CPU and GPU with CSV logging"""
import csv
import os
from datetime import datetime
import time

try:
    import GPUtil
    GPU_AVAILABLE = True
except:
    GPU_AVAILABLE = False

CSV_FILE = "/app/performance_metrics.csv"
HOST_PROC = "/host/proc"

# Store previous CPU values for calculation
_prev_cpu_times = None

def read_host_cpu():
    """Read CPU usage from host /proc/stat"""
    global _prev_cpu_times
    
    try:
        with open(f"{HOST_PROC}/stat") as f:
            line = f.readline()
        
        # Parse: cpu  user nice system idle iowait irq softirq
        fields = line.split()
        user = int(fields[1])
        nice = int(fields[2])
        system = int(fields[3])
        idle = int(fields[4])
        iowait = int(fields[5]) if len(fields) > 5 else 0
        
        total = user + nice + system + idle + iowait
        work = user + nice + system
        
        if _prev_cpu_times:
            prev_total, prev_work = _prev_cpu_times
            total_diff = total - prev_total
            work_diff = work - prev_work
            cpu_percent = (work_diff / total_diff * 100) if total_diff > 0 else 0
        else:
            cpu_percent = 0
        
        _prev_cpu_times = (total, work)
        return cpu_percent
    except:
        return 0

def log_performance(worker_id, task_id="idle"):
    """Log CPU and GPU to CSV file - reads host PC stats"""
    cpu = read_host_cpu()
    
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
