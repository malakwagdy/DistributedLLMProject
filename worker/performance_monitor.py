"""Performance Monitor - CPU and GPU with CSV logging"""
import csv
import os
from datetime import datetime
import subprocess

LOGS_DIR = "/app/logs"
ACTIVITY_LOG = f"{LOGS_DIR}/activity.log"

# Create logs directory
os.makedirs(LOGS_DIR, exist_ok=True)

def read_host_cpu():
    """Read CPU usage from host /proc/stat"""
    try:
        with open("/host/proc/stat") as f:
            line = f.readline()
        fields = line.split()
        
        user = int(fields[1])
        nice = int(fields[2])
        system = int(fields[3])
        idle = int(fields[4])
        iowait = int(fields[5]) if len(fields) > 5 else 0
        irq = int(fields[6]) if len(fields) > 6 else 0
        softirq = int(fields[7]) if len(fields) > 7 else 0
        
        total = user + nice + system + idle + iowait + irq + softirq
        idle_total = idle + iowait
        cpu_percent = ((total - idle_total) / total * 100) if total > 0 else 0
        
        return cpu_percent
    except:
        return 0

def read_gpu():
    """Read GPU usage using nvidia-smi"""
    try:
        result = subprocess.run(
            ['nvidia-smi', '--query-gpu=utilization.gpu', '--format=csv,noheader,nounits'],
            capture_output=True,
            text=True,
            timeout=1
        )
        if result.returncode == 0:
            return float(result.stdout.strip())
    except:
        pass
    return 0

def log_performance(worker_id, task_id="idle", latency_seconds=None):
    """Log CPU, GPU, and latency to worker-specific CSV file"""
    cpu = read_host_cpu()
    gpu = read_gpu()
    
    # Worker-specific CSV file
    csv_file = f"{LOGS_DIR}/{worker_id}_metrics.csv"
    
    # Create CSV with headers if it doesn't exist
    file_exists = os.path.exists(csv_file)
    try:
        with open(csv_file, 'a') as f:
            if not file_exists:
                f.write("timestamp,worker_id,task_id,cpu_percent,gpu_percent,latency_seconds\n")
            latency_str = f"{latency_seconds:.2f}" if latency_seconds is not None else ""
            f.write(f"{datetime.now().isoformat()},{worker_id},{task_id},{cpu:.1f},{gpu:.1f},{latency_str}\n")
    except:
        pass

def log_activity(message):
    """Log worker activity to activity.log"""
    try:
        with open(ACTIVITY_LOG, 'a') as f:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"[{timestamp}] {message}\n")
    except:
        pass
