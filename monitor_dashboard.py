"""Simple Dashboard - View all workers' CPU and Memory"""
import redis
import time
import os
import urllib.parse

REDIS_URL = os.getenv("REDIS_URL", "redis://100.68.227.68:6379")
parsed = urllib.parse.urlparse(REDIS_URL)
r = redis.Redis(host=parsed.hostname, port=parsed.port or 6379, db=0, decode_responses=True)

def show_workers():
    """Display all active workers"""
    print("\n" + "="*60)
    print("WORKER DASHBOARD")
    print("="*60)
    
    workers = []
    for key in r.scan_iter("worker:*:heartbeat"):
        worker_id = key.split(":")[1]
        if worker_id not in workers:
            workers.append(worker_id)
    
    if not workers:
        print("No workers found")
        return
    
    for worker_id in sorted(workers):
        load = r.get(f"worker:{worker_id}:load") or "0"
        print(f"{worker_id}: {load} tasks")
    
    print("="*60)

try:
    while True:
        show_workers()
        time.sleep(2)
except KeyboardInterrupt:
    print("\nStopped")
