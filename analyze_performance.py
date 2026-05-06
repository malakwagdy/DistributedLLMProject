"""Analyze performance metrics from CSV"""
import csv
from collections import defaultdict

CSV_FILE = "performance_metrics.csv"

def analyze():
    """Show per-node and overall averages"""
    
    worker_data = defaultdict(lambda: {"cpu": [], "gpu": [], "tasks": set()})
    
    try:
        with open(CSV_FILE, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                worker = row['worker_id']
                task = row['task_id']
                cpu = float(row['cpu_percent'])
                gpu = float(row['gpu_percent'])
                
                worker_data[worker]['cpu'].append(cpu)
                worker_data[worker]['gpu'].append(gpu)
                
                # Count unique tasks (not heartbeat)
                if task != "heartbeat" and task != "idle":
                    worker_data[worker]['tasks'].add(task)
        
        print("\n" + "="*60)
        print("PER-NODE PERFORMANCE")
        print("="*60)
        
        all_cpu = []
        all_gpu = []
        
        for worker in sorted(worker_data.keys()):
            data = worker_data[worker]
            avg_cpu = sum(data['cpu']) / len(data['cpu'])
            avg_gpu = sum(data['gpu']) / len(data['gpu'])
            task_count = len(data['tasks'])
            
            all_cpu.extend(data['cpu'])
            all_gpu.extend(data['gpu'])
            
            gpu_text = f"Avg GPU: {avg_gpu:.1f}%" if avg_gpu > 0 else "No GPU"
            print(f"{worker}")
            print(f"  Tasks: {task_count} | Avg CPU: {avg_cpu:.1f}% | {gpu_text}")
        
        print("\n" + "="*60)
        print("OVERALL AVERAGE")
        print("="*60)
        overall_cpu = sum(all_cpu) / len(all_cpu) if all_cpu else 0
        overall_gpu = sum(all_gpu) / len(all_gpu) if all_gpu else 0
        print(f"CPU: {overall_cpu:.1f}% | GPU: {overall_gpu:.1f}%")
        print("="*60 + "\n")
        
    except FileNotFoundError:
        print(f"Error: {CSV_FILE} not found")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    analyze()
