from fastapi import FastAPI, HTTPException
import redis.asyncio as redis
import uuid
import json
import asyncio
import os

app = FastAPI()
r = redis.from_url(os.getenv("REDIS_URL", "redis://redis:6379/0"), decode_responses=True)
REQUEST_TIMEOUT_SECONDS = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "120"))


@app.post("/ask")
async def handle_request(prompt: str):
    job_id = str(uuid.uuid4())
    payload = json.dumps(
        {
            "job_id": job_id,
            "prompt": prompt,
            "created_at": asyncio.get_running_loop().time(),
            "attempts": 0,
        }
    )

    # Gateway role (Load Balancer ingress): receives and forwards to master queue.
    await r.lpush("incoming_tasks", payload)

    deadline = asyncio.get_running_loop().time() + REQUEST_TIMEOUT_SECONDS
    while asyncio.get_running_loop().time() < deadline:
        result = await r.get(f"result:{job_id}")
        if result:
            return json.loads(result)
        await asyncio.sleep(0.5)

    print(
        f"[gateway] timeout job_id={job_id} "
        f"waited_seconds={REQUEST_TIMEOUT_SECONDS} action=cancel_marked"
    )
    await r.setex(f"cancel:{job_id}", 300, "1")
    raise HTTPException(status_code=504, detail="Timed out waiting for response")


@app.get("/health")
async def health_check():
    worker_keys = await r.keys("worker:*:heartbeat")
    strategy = await r.get("scheduler:strategy")
    pending = await r.llen("incoming_tasks")
    return {
        "active_workers": len(worker_keys),
        "pending_incoming_tasks": pending,
        "scheduler_strategy": strategy if strategy else "least_connections",
    }
