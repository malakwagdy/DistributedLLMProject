"""Simple Performance Monitor - CPU and GPU"""
import psutil

try:
    import GPUtil
    GPU_AVAILABLE = True
except:
    GPU_AVAILABLE = False

def log_performance(worker_id):
    """Log CPU and GPU usage"""
    cpu = psutil.cpu_percent(interval=0.1)
    
    # Get GPU info if available
    gpu_text = "No GPU"
    if GPU_AVAILABLE:
        try:
            gpus = GPUtil.getGPUs()
            if gpus:
                gpu = gpus[0]  # First GPU
                gpu_text = f"GPU: {gpu.load*100:.1f}%"
        except:
            pass
    
    print(f"[{worker_id}] CPU: {cpu:.1f}% | {gpu_text}")
    
    return {"cpu": cpu}
