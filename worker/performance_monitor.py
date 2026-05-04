"""
Simple Performance Monitor
Tracks CPU and GPU utilization for workers
"""
import psutil
import time
import os

try:
    import GPUtil
    GPU_AVAILABLE = True
except ImportError:
    GPU_AVAILABLE = False


def get_cpu_usage():
    """Get current CPU usage percentage"""
    return psutil.cpu_percent(interval=1)


def get_memory_usage():
    """Get current memory usage in MB and percentage"""
    mem = psutil.virtual_memory()
    return {
        "used_mb": mem.used / (1024 * 1024),
        "total_mb": mem.total / (1024 * 1024),
        "percent": mem.percent
    }


def get_gpu_usage():
    """Get GPU usage if available"""
    if not GPU_AVAILABLE:
        return None
    
    try:
        gpus = GPUtil.getGPUs()
        if not gpus:
            return None
        
        gpu_info = []
        for gpu in gpus:
            gpu_info.append({
                "id": gpu.id,
                "name": gpu.name,
                "load_percent": gpu.load * 100,
                "memory_used_mb": gpu.memoryUsed,
                "memory_total_mb": gpu.memoryTotal,
                "temperature": gpu.temperature
            })
        return gpu_info
    except Exception as e:
        print(f"GPU monitoring error: {e}")
        return None


def log_performance(worker_id):
    """Log current performance metrics"""
    cpu = get_cpu_usage()
    memory = get_memory_usage()
    gpu = get_gpu_usage()
    
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    
    print(f"[{timestamp}] Worker: {worker_id}")
    print(f"  CPU: {cpu:.1f}%")
    print(f"  Memory: {memory['used_mb']:.0f}/{memory['total_mb']:.0f} MB ({memory['percent']:.1f}%)")
    
    if gpu:
        for g in gpu:
            print(f"  GPU {g['id']} ({g['name']}): {g['load_percent']:.1f}% | "
                  f"Memory: {g['memory_used_mb']:.0f}/{g['memory_total_mb']:.0f} MB | "
                  f"Temp: {g['temperature']}°C")
    else:
        print(f"  GPU: Not available")
    
    print("-" * 60)
    
    return {
        "timestamp": timestamp,
        "worker_id": worker_id,
        "cpu_percent": cpu,
        "memory": memory,
        "gpu": gpu
    }


def store_metrics_to_redis(redis_client, worker_id, metrics):
    """Store performance metrics in Redis"""
    key = f"metrics:{worker_id}"
    redis_client.setex(key, 60, str(metrics))  # Store for 60 seconds
