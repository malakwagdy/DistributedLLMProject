"""
Kaggle setup using ngrok (usually simpler for demos).

Required env var:
- NGROK_AUTHTOKEN

Usage:
!python scripts/kaggle_ollama_ngrok_setup.py
"""

import json
import os
import subprocess
import time
import urllib.request
from kaggle_secrets import UserSecretsClient


def run(cmd: str) -> None:
    print(f"\n$ {cmd}")
    subprocess.check_call(cmd, shell=True)


def start(cmd: str, env: dict | None = None) -> subprocess.Popen:
    print(f"\n$ {cmd}")
    return subprocess.Popen(cmd, shell=True, env=env)


def main() -> None:
    user_secrets = UserSecretsClient()
    token = user_secrets.get_secret("NGROK_AUTHTOKEN")
    if not token:
        raise SystemExit("Missing NGROK_AUTHTOKEN environment variable.")

    run("apt-get update -y")
    run("apt-get install -y curl wget tar zstd ca-certificates")
    run("curl -fsSL https://ollama.com/install.sh | sh")

    # Allow tunneled requests through; default Ollama rejects external origins with 403.
    ollama_env = os.environ.copy()
    ollama_env["OLLAMA_HOST"] = "0.0.0.0:11434"
    ollama_env["OLLAMA_ORIGINS"] = "*"
    ollama_proc = start("ollama serve", env=ollama_env)
    time.sleep(6)
    if ollama_proc.poll() is not None:
        raise SystemExit("ollama serve failed to start.")

    run("ollama pull phi3:mini")

    run("wget -q https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-amd64.tgz")
    run("tar -xzf ngrok-v3-stable-linux-amd64.tgz")
    run(f"./ngrok config add-authtoken {token}")

    ngrok_proc = start("./ngrok http 11434")
    time.sleep(4)
    if ngrok_proc.poll() is not None:
        raise SystemExit("ngrok failed to start.")

    with urllib.request.urlopen("http://127.0.0.1:4040/api/tunnels", timeout=10) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    public_url = data["tunnels"][0]["public_url"]

    print("\nUse this in local .env as REMOTE_OLLAMA_URL:")
    print(public_url)
    print("\nKeep this process running while testing.\n")

    # Block forever so notebook cell stays alive
    ngrok_proc.wait()


if __name__ == "__main__":
    main()
