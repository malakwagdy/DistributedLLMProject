from fastapi import FastAPI
import redis.asyncio as redis
import uuid
import json
import asyncio

app = FastAPI()
r = redis.from_url("redis://redis:6379/0")


@app.post("/ask")
async def handle_request(prompt: str):
    job_id = str(uuid.uuid4())
    payload = json.dumps({"job_id": job_id, "prompt": prompt})

    # 1. Push to queue (Load Balancing: Workers pull when ready)
    await r.lpush("llm_tasks", payload)

    # 2. Polling for result (In a real system, use WebSockets, but this is fine for the project)
    while True:
        result = await r.get(f"result:{job_id}")
        if result:
            return json.loads(result)
        await asyncio.sleep(0.5)


@app.get("/health")
async def health_check():
    # Demonstrates monitoring of the cluster
    workers = await r.pubsub_channels("worker_heartbeat")
    return {"active_workers": len(workers)}