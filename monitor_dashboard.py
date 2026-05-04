"""
Simple Performance Dashboard
View CPU/GPU metrics for all workers in the network
"""
import redis
import time
import os
from datetime import datetime

# Connect to Redis
REDIS_URL = os.getenv("REDIS_URL", "redis://100.68.227.68:6379")
import urllib.parse
parsed = urllib.parse.urlparse(REDIS_URL)
r = redis.Redis(
    host=parsed.hostname,
    port=parsed.port or 6379,
    db=0,
    decode_responses=True
)

def clear_screen():
    """Clear terminal screen"""
    os.system('cls' if os.name == 'nt' else 'clear')

def get_all_workers():
    """Get list of all active workers"""
    workers = []
    for key in r.scan_iter("worker:*:heartbeat"):
        worker_id = key.split(":")[1]
        if worker_id not in workers:
            workers.append(worker_id)
    return sorted(workers)

def display_dashboard():
    """Display performance metrics for all workers"""
    clear_screen()
    print("=" * 80)
    print(f"DISTRIBUTED LLM PERFORMANCE DASHBOARD".center(80))
    print(f"Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}".center(80))
    print("=" * 80)
    print()
    
    workers = get_all_workers()
    
    if not workers:
        print("No active workers found.")
        return
    
    print(f"Active Workers: {len(workers)}")
    print("-" * 80)
    
    for worker_id in workers:
        # Check if worker is alive
        heartbeat = r.get(f"worker:{worker_id}:heartbeat")
        if not heartbeat:
            print(f"\n[{worker_id}] - OFFLINE")
            continue
        
        # Get metrics
        metrics_key = f"metrics:{worker_id}"
        metrics = r.get(metrics_key)
        
        # Get load
        load = r.get(f"worker:{worker_id}:load") or "0"
        
        print(f"\n[{worker_id}]")
        print(f"  Status: ONLINE | Current Load: {load} tasks")
        
        if metrics:
            # Metrics are stored as string, parse them
            try:
                # Simple display of stored metrics
                print(f"  Metrics: {metrics[:200]}...")  # Show first 200 chars
            except:
                print(f"  Metrics: Available")
        else:
            print(f"  Metrics: Not yet available")
    
    print("\n" + "=" * 80)
    print("Press Ctrl+C to exit")

def main():
    """Main monitoring loop"""
    print("Starting Performance Dashboard...")
    print("Connecting to Redis...")
    
    try:
        r.ping()
        print("Connected successfully!")
        time.sleep(1)
    except Exception as e:
        print(f"Error connecting to Redis: {e}")
        return
    
    try:
        while True:
            display_dashboard()
            time.sleep(2)  # Update every 2 seconds
    except KeyboardInterrupt:
        print("\n\nDashboard stopped.")

if __name__ == "__main__":
    main()
