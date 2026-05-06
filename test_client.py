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
        latency = time.time() - start_time
        return response.status_code, latency
    except Exception as e:
        return "Error", 0


async def run_load_test(total_requests):
    async with httpx.AsyncClient() as client:
        tasks = []
        print(f"Starting load test: {total_requests} concurrent requests...")
        start_period = time.time()

        for i in range(total_requests):
            tasks.append(send_request(client, i))

        results = await asyncio.gather(*tasks)

        total_time = time.time() - start_period
        successes = [r for r in results if r[0] == 200]
        latencies = [r[1] for r in results if r[1] > 0]

        print("\n--- Performance Report ---")
        print(f"Total Requests: {total_requests}")
        print(f"Successful: {len(successes)}")
        print(f"Failed: {total_requests - len(successes)}")
        print(f"Total Time: {total_time:.2f} seconds")
        print(f"Average Latency: {sum(latencies) / len(latencies):.2f}s" if latencies else "N/A")
        print(f"Throughput: {len(successes) / total_time:.2f} requests/sec")


if __name__ == "__main__":
    # for users in [100, 250, 500, 750, 1000]:
    asyncio.run(run_load_test(1000))