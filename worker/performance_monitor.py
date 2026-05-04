"""Simple Performance Monitor"""
import psutil

def log_performance(worker_id):
    """Log CPU and memory usage"""
    cpu = psutil.cpu_percent(interval=0.1)
    mem = psutil.virtual_memory()
    
    print(f"[{worker_id}] CPU: {cpu:.1f}% | Memory: {mem.percent:.1f}%")
    
    return {"cpu": cpu, "memory": mem.percent}
