"""Sync LangChain FAISS artifacts from S3-compatible storage (e.g. Cloudflare R2)."""

from __future__ import annotations

import json
import os
from pathlib import Path


def _r2_env_complete() -> bool:
    return all(
        os.getenv(k)
        for k in (
            "RAG_S3_ENDPOINT",
            "RAG_S3_ACCESS_KEY_ID",
            "RAG_S3_SECRET_ACCESS_KEY",
            "RAG_S3_BUCKET",
        )
    )


def _object_key(filename: str) -> str:
    prefix = os.getenv("RAG_S3_PREFIX", "rag").strip().strip("/")
    return f"{prefix}/{filename}" if prefix else filename


def sync_rag_artifacts(data_dir: Path) -> None:
    """
    If RAG_S3_* env vars are set, download manifest.json, index.faiss, and index.pkl
    when the remote version differs from the local cache (or files are missing).
    """
    if not _r2_env_complete():
        return

    import boto3
    from botocore.config import Config

    data_dir.mkdir(parents=True, exist_ok=True)
    endpoint = os.environ["RAG_S3_ENDPOINT"].rstrip("/")
    bucket = os.environ["RAG_S3_BUCKET"]

    client = boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=os.environ["RAG_S3_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["RAG_S3_SECRET_ACCESS_KEY"],
        region_name="auto",
        config=Config(signature_version="s3v4"),
    )

    manifest_key = _object_key("manifest.json")
    resp = client.get_object(Bucket=bucket, Key=manifest_key)
    manifest = json.loads(resp["Body"].read().decode("utf-8"))
    remote_version = str(manifest.get("version", ""))

    version_file = data_dir / ".version"
    if (
        version_file.exists()
        and version_file.read_text(encoding="utf-8").strip() == remote_version
        and (data_dir / "index.faiss").is_file()
        and (data_dir / "index.pkl").is_file()
    ):
        return

    for name in ("index.faiss", "index.pkl", "manifest.json"):
        client.download_file(bucket, _object_key(name), str(data_dir / name))

    version_file.write_text(remote_version, encoding="utf-8")
