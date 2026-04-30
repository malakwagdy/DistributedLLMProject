from collections import defaultdict
import asyncio
import json
import os
from typing import Any

from fastapi import FastAPI
import redis.asyncio as redis

app = FastAPI()
r = redis.from_url("redis://redis:6379/0", decode_responses=True)

HEARTBEAT_TIMEOUT_SECONDS = int(os.getenv("HEARTBEAT_TIMEOUT_SECONDS", "8"))
PROCESSING_STALE_SECONDS = int(os.getenv("PROCESSING_STALE_SECONDS", "45"))
MAX_ATTEMPTS = int(os.getenv("MAX_ATTEMPTS", "3"))
SCHEDULER_STRATEGY = os.getenv("SCHEDULER_STRATEGY", "least_connections")

_rr_index = 0


async def list_active_workers() -> list[str]:
    keys = await r.keys("worker:*:heartbeat")
    workers = []
    for key in keys:
        worker_id = key.split(":")[1]
        workers.append(worker_id)
    return sorted(workers)


async def worker_load(worker_id: str) -> int:
    value = await r.get(f"worker:{worker_id}:load")
    if not value:
        return 0
    return int(value)


async def choose_worker(workers: list[str], strategy: str) -> str:
    global _rr_index
    if not workers:
        raise RuntimeError("No workers available")

    if strategy == "round_robin":
        worker = workers[_rr_index % len(workers)]
        _rr_index += 1
        return worker

    if strategy == "load_aware":
        scored = []
        for wid in workers:
            load = await worker_load(wid)
            queue_depth = await r.llen(f"worker_queue:{wid}")
            scored.append((load + queue_depth, wid))
        scored.sort(key=lambda item: item[0])
        return scored[0][1]

    # Default: least connections
    loads = []
    for wid in workers:
        queue_depth = await r.llen(f"worker_queue:{wid}")
        loads.append((await worker_load(wid), queue_depth, wid))
    loads.sort(key=lambda item: (item[0], item[1]))
    return loads[0][2]


async def scheduler_loop() -> None:
    while True:
        try:
            popped = await r.brpop("incoming_tasks", timeout=2)
            if not popped:
                continue
            _, payload = popped
            task: dict[str, Any] = json.loads(payload)

            workers = await list_active_workers()
            if not workers:
                # No workers currently alive: push back and retry later.
                await r.rpush("incoming_tasks", json.dumps(task))
                await asyncio.sleep(1)
                continue

            strategy_raw = await r.get("scheduler:strategy")
            strategy = strategy_raw if strategy_raw else SCHEDULER_STRATEGY
            worker = await choose_worker(workers, strategy)
            task["assigned_worker"] = worker
            task["strategy"] = strategy

            await r.lpush(f"worker_queue:{worker}", json.dumps(task))
            print(f"[scheduler] scheduled job_id={task['job_id']} worker={worker} strategy={strategy}")
        except Exception as exc:  # noqa: BLE001
            print(f"[scheduler] error: {exc}")
            await asyncio.sleep(1)


async def recover_stale_processing_loop() -> None:
    while True:
        try:
            processing_keys = await r.keys("processing:*")
            grouped: dict[str, list[str]] = defaultdict(list)
            for meta_key in processing_keys:
                _, worker_id, job_id = meta_key.split(":")
                grouped[worker_id].append(job_id)

            for worker_id, jobs in grouped.items():
                alive = await r.exists(f"worker:{worker_id}:heartbeat")
                for job_id in jobs:
                    meta_raw = await r.get(f"processing:{worker_id}:{job_id}")
                    if not meta_raw:
                        continue
                    meta = json.loads(meta_raw)
                    started_at = float(meta.get("started_at", 0))
                    now = asyncio.get_running_loop().time()
                    stale = (now - started_at) > PROCESSING_STALE_SECONDS

                    if alive and not stale:
                        continue

                    payload = meta["task_payload"]
                    task = json.loads(payload)
                    task["attempts"] = int(task.get("attempts", 0)) + 1

                    await r.lrem(f"processing_queue:{worker_id}", 1, payload)
                    await r.delete(f"processing:{worker_id}:{job_id}")
                    await r.decr(f"worker:{worker_id}:load")

                    if task["attempts"] <= MAX_ATTEMPTS:
                        await r.lpush("incoming_tasks", json.dumps(task))
                        print(f"[recovery] requeued job_id={task['job_id']} from_worker={worker_id}")
                    else:
                        await r.setex(
                            f"result:{task['job_id']}",
                            300,
                            json.dumps({
                                "job_id": task["job_id"],
                                "error": "Task failed after retries",
                                "failed_worker": worker_id,
                            }),
                        )
        except Exception as exc:  # noqa: BLE001
            print(f"[recovery] error: {exc}")
        await asyncio.sleep(2)


@app.on_event("startup")
async def startup() -> None:
    await r.set("scheduler:strategy", SCHEDULER_STRATEGY)
    asyncio.create_task(scheduler_loop())
    asyncio.create_task(recover_stale_processing_loop())


@app.get("/health")
async def health() -> dict[str, Any]:
    workers = await list_active_workers()
    strategy_raw = await r.get("scheduler:strategy")
    strategy = strategy_raw if strategy_raw else SCHEDULER_STRATEGY
    loads = {wid: await worker_load(wid) for wid in workers}
    queued = {wid: await r.llen(f"worker_queue:{wid}") for wid in workers}
    return {
        "workers": workers,
        "strategy": strategy,
        "worker_loads": loads,
        "worker_queue_depth": queued,
        "incoming_queue_depth": await r.llen("incoming_tasks"),
    }


@app.post("/strategy/{strategy_name}")
async def set_strategy(strategy_name: str) -> dict[str, str]:
    allowed = {"round_robin", "least_connections", "load_aware"}
    if strategy_name not in allowed:
        return {"error": f"Invalid strategy. Allowed: {sorted(allowed)}"}
    await r.set("scheduler:strategy", strategy_name)
    return {"strategy": strategy_name}
