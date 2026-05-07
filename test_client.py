import asyncio
import httpx
import time


async def send_request(client, user_id):
    start_time = time.time()
    try:
        # We send the request to our Gateway (Load Balancer)
        response = await client.post(
            "http://localhost:8000/ask",
            params={"prompt": f"User {user_id}: What is distributed computing?"},
            timeout=120.0
        )
        status = response.status_code
        latency = time.time() - start_time
        body = {}
        try:
            body = response.json()
        except Exception:
            pass
        # Business-success only when 200 and has answer and no error
        if status == 200 and isinstance(body, dict) and "error" not in body and "answer" in body:
            return {"ok": True, "status": status, "latency": latency, "error_type": None}
        # 200 but backend error payload OR non-200
        err = body.get("error") if isinstance(body, dict) else f"http_{status}"
        return {"ok": False, "status": status, "latency": latency, "error_type": str(err), "body": body}
    except Exception as e:
        return {"ok": False, "status": None, "latency": 0, "error_type": type(e).__name__, "body": None}


async def run_load_test(total_requests):
    async with httpx.AsyncClient() as client:
        tasks = []
        print(f"Starting load test: {total_requests} concurrent requests...")
        start_period = time.time()

        for i in range(total_requests):
            tasks.append(send_request(client, i))

        results = await asyncio.gather(*tasks)
        total_time = time.time() - start_period

        successes = [r for r in results if r["ok"]]
        failures = [r for r in results if not r["ok"]]
        latencies = [r["latency"] for r in successes if r["latency"] > 0]
        from collections import Counter
        status_counts = Counter(r["status"] for r in results)
        error_counts = Counter(r["error_type"] for r in failures)
        print("\n--- Performance Report ---")
        print(f"Total Requests: {total_requests}")
        print(f"Successful (business): {len(successes)}")
        print(f"Failed: {len(failures)}")
        print(f"HTTP Status Counts: {dict(status_counts)}")
        print(f"Failure Types: {dict(error_counts)}")
        print(f"Total Time: {total_time:.2f} seconds")
        print(f"Average Latency: {sum(latencies) / len(latencies):.2f}s" if latencies else "N/A")
        print(f"Throughput: {len(successes) / total_time:.2f} requests/sec")


if __name__ == "__main__":
    # for users in [100, 250, 500, 750, 1000]:
    asyncio.run(run_load_test(200))