import redis
import json
import requests
import time
import os

# Connect to Redis
r = redis.Redis(host='redis', port=6379, db=0)
WORKER_ID = os.getenv("HOSTNAME")  # Docker gives each container a unique name


def process_with_llm(prompt):
    # ACTUAL LLM CALL to Ollama (running on host machine)
    # Note: 'host.docker.internal' refers to your actual PC from inside Docker
    url = "http://host.docker.internal:11434/api/generate"
    data = {"model": "phi3", "prompt": prompt, "stream": False}

    response = requests.post(url, json=data)
    return response.json().get("response", "Error processing")


print(f"Worker {WORKER_ID} started...")

while True:
    # Pull task from queue (Atomic operation ensures no two workers take the same task)
    _, task_data = r.brpop("llm_tasks")
    task = json.loads(task_data)

    print(f"Worker {WORKER_ID} processing task {task['job_id']}")

    # Simulate RAG (Retrieve dummy context)
    context = "Context: The project is for Ain Shams University."
    full_prompt = f"{context}\n\nUser Question: {task['prompt']}"

    # Actual LLM Inference
    answer = process_with_llm(full_prompt)

    # Store result back in Redis
    r.setex(f"result:{task['job_id']}", 60, json.dumps({"worker": WORKER_ID, "answer": answer}))