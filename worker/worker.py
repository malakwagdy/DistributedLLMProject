import redis
import json
import requests
import time
import os
import threading

from rag import retrieve_context
from performance_monitor import log_performance, log_activity

# r = redis.Redis(host="redis", port=6379, db=0, decode_responses=True)
import urllib.parse

_redis_url = os.getenv("REDIS_URL", "redis://redis:6379")
_parsed = urllib.parse.urlparse(_redis_url)
r = redis.Redis(
    host=_parsed.hostname,
    port=_parsed.port or 6379,
    db=0,
    decode_responses=True
)
print(f"REDIS_URL = {os.getenv('REDIS_URL', 'NOT SET')}")
WORKER_ID = os.getenv("HOSTNAME", "worker-unknown")
HEARTBEAT_INTERVAL_SECONDS = int(os.getenv("HEARTBEAT_INTERVAL_SECONDS", "2"))
HEARTBEAT_TTL_SECONDS = int(os.getenv("HEARTBEAT_TTL_SECONDS", "8"))
RESULT_TTL_SECONDS = int(os.getenv("RESULT_TTL_SECONDS", "300"))


def process_with_llm(prompt):
    # Each worker can target a different endpoint to simulate/enable GPU cluster routing.
    url = os.getenv("OLLAMA_URL", "http://host.docker.internal:11434") + "/api/generate"
    model = os.getenv("OLLAMA_MODEL", "smollm:135m")
    data = {"model": model, "prompt": prompt, "stream": False}
    response = requests.post(url, json=data, timeout=120)
    return response.json().get("response", "Error processing")


def heartbeat_loop():
    while True:
        r.setex(f"worker:{WORKER_ID}:heartbeat", HEARTBEAT_TTL_SECONDS, str(time.time()))
        r.set(f"worker:{WORKER_ID}:endpoint", os.getenv("OLLAMA_URL", "http://host.docker.internal:11434"))
        log_performance(WORKER_ID, "heartbeat")  # Log to CSV every 2 seconds
        time.sleep(HEARTBEAT_INTERVAL_SECONDS)


def process_one_task(task_payload):
    task = json.loads(task_payload)
    job_id = task["job_id"]
    print(f"Worker {WORKER_ID} processing task {job_id}")
    log_activity(f"Worker {WORKER_ID} processing task {job_id}")
    
    # Log CPU/GPU for this task
    log_performance(WORKER_ID, job_id)

    context = retrieve_context(task["prompt"], top_k=3)
    full_prompt = (
        "Use the following retrieved context when answering.\n\n"
        f"{context}\n\n"
        f"User Question: {task['prompt']}"
    )

    answer = process_with_llm(full_prompt)
    
    log_activity(f"Worker {WORKER_ID} completed task {job_id}")
    
    r.setex(
        f"result:{job_id}",
        RESULT_TTL_SECONDS,
        json.dumps({"worker": WORKER_ID, "answer": answer, "job_id": job_id}),
    )


print(f"Worker {WORKER_ID} started...")
log_activity(f"Worker {WORKER_ID} started")
threading.Thread(target=heartbeat_loop, daemon=True).start()
r.set(f"worker:{WORKER_ID}:load", 0)

while True:
    source_queue = f"worker_queue:{WORKER_ID}"
    processing_queue = f"processing_queue:{WORKER_ID}"

    task_payload = r.brpoplpush(source_queue, processing_queue, timeout=5)
    if not task_payload:
        continue

    task = json.loads(task_payload)
    job_id = task["job_id"]
    r.incr(f"worker:{WORKER_ID}:load")
    r.set(
        f"processing:{WORKER_ID}:{job_id}",
        json.dumps({"task_payload": task_payload, "started_at": time.monotonic()}),
    )

    try:
        process_one_task(task_payload)
    except Exception as exc:  # noqa: BLE001
        print(f"Worker {WORKER_ID} failed job_id={job_id} error={exc}")
        log_activity(f"Worker {WORKER_ID} FAILED task {job_id}: {exc}")
        r.setex(
            f"result:{job_id}",
            RESULT_TTL_SECONDS,
            json.dumps({"worker": WORKER_ID, "job_id": job_id, "error": str(exc)}),
        )
    finally:
        r.lrem(processing_queue, 1, task_payload)
        r.delete(f"processing:{WORKER_ID}:{job_id}")
        r.decr(f"worker:{WORKER_ID}:load")
