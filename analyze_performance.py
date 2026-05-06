"""Analyze performance metrics from CSV"""
import csv
from collections import defaultdict

def analyze():
    worker_data = defaultdict(lambda: {"cpu": [], "gpu": [], "tasks": set()})
    
    with open("performance_metrics.csv") as f:
        for line in f:
            parts = line.strip().split(',')
            if len(parts) == 5:
                timestamp, worker, task, cpu, gpu = parts
                worker_data[worker]['cpu'].append(float(cpu))
                worker_data[worker]['gpu'].append(float(gpu))
                if task not in ["heartbeat", "idle"]:
                    worker_data[worker]['tasks'].add(task)
    
    print("\n" + "="*60)
    print("PER-NODE PERFORMANCE")
    print("="*60)
    
    all_cpu, all_gpu = [], []
    
    for worker in sorted(worker_data.keys()):
        data = worker_data[worker]
        avg_cpu = sum(data['cpu']) / len(data['cpu'])
        avg_gpu = sum(data['gpu']) / len(data['gpu'])
        
        all_cpu.extend(data['cpu'])
        all_gpu.extend(data['gpu'])
        
        gpu_text = f"GPU: {avg_gpu:.1f}%" if avg_gpu > 0 else "No GPU"
        print(f"{worker}: {len(data['tasks'])} tasks | CPU: {avg_cpu:.1f}% | {gpu_text}")
    
    print("\n" + "="*60)
    print("OVERALL AVERAGE")
    print("="*60)
    print(f"CPU: {sum(all_cpu)/len(all_cpu):.1f}% | GPU: {sum(all_gpu)/len(all_gpu):.1f}%")
    print("="*60 + "\n")

if __name__ == "__main__":
    analyze()
