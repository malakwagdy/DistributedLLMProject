"""
Offline RAG index build: load documents, chunk, embed, write FAISS + chunks.pkl + manifest.json.

Run from repo root or worker dir:
  python build_index.py
  python build_index.py --upload   # push rag_data/* to R2 (requires RAG_S3_* env)

Sources (in order):
  1) worker/kb_docs/*.txt — one file per document
  2) If no .txt files there: worker/knowledge_base.txt — each non-empty line is a mini-document
"""

from __future__ import annotations

import argparse
import json
import os
import pickle
import sys
from pathlib import Path

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer


DEFAULT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
WORKER_DIR = Path(__file__).resolve().parent
KB_DIR = WORKER_DIR / "kb_docs"
LEGACY_KB = WORKER_DIR / "knowledge_base.txt"
OUTPUT_DIR = WORKER_DIR / "rag_data"


def chunk_text(text: str, chunk_size: int = 700, overlap: int = 120) -> list[str]:
    text = text.strip()
    if not text:
        return []
    chunks: list[str] = []
    start = 0
    n = len(text)
    while start < n:
        end = min(start + chunk_size, n)
        piece = text[start:end].strip()
        if piece:
            chunks.append(piece)
        if end == n:
            break
        start = max(end - overlap, start + 1)
    return chunks


def load_documents() -> list[dict[str, str]]:
    docs: list[dict[str, str]] = []
    txt_files = sorted(KB_DIR.glob("*.txt"))
    if txt_files:
        for path in txt_files:
            raw = path.read_text(encoding="utf-8", errors="ignore").strip()
            if raw:
                docs.append({"source": path.name, "text": raw})
        return docs

    if LEGACY_KB.is_file():
        for i, line in enumerate(LEGACY_KB.read_text(encoding="utf-8").splitlines()):
            line = line.strip()
            if line:
                docs.append({"source": f"knowledge_base.txt#line{i + 1}", "text": line})
        return docs

    print(
        "No documents found. Add .txt files under kb_docs/ or keep knowledge_base.txt.",
        file=sys.stderr,
    )
    return []


def build_chunk_records(docs: list[dict[str, str]]) -> list[dict[str, str | int]]:
    records: list[dict[str, str | int]] = []
    for doc in docs:
        parts = chunk_text(doc["text"])
        if not parts:
            continue
        for i, piece in enumerate(parts):
            records.append(
                {
                    "text": piece,
                    "source": doc["source"],
                    "chunk_id": i,
                }
            )
    return records


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


def upload_artifacts(out_dir: Path) -> None:
    import boto3
    from botocore.config import Config

    if not _r2_env_complete():
        raise RuntimeError("RAG_S3_* environment variables are required for --upload")

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
    for name in ("manifest.json", "index.faiss", "chunks.pkl"):
        path = out_dir / name
        if not path.is_file():
            raise FileNotFoundError(path)
        client.upload_file(str(path), bucket, _object_key(name))
    prefix = os.getenv("RAG_S3_PREFIX", "rag").strip().strip("/")
    loc = f"{prefix}/" if prefix else ""
    print(f"Uploaded manifest + index + chunks to bucket={bucket!r} prefix={loc!r}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build FAISS RAG artifacts for workers.")
    parser.add_argument(
        "--model",
        default=os.getenv("RAG_EMBED_MODEL", DEFAULT_MODEL),
        help="Sentence-Transformers model id (must match worker at query time).",
    )
    parser.add_argument(
        "--version",
        default=os.getenv("RAG_INDEX_VERSION", "1"),
        help="Version string written to manifest (bump to force workers to re-download).",
    )
    parser.add_argument(
        "--upload",
        action="store_true",
        help="After build, upload rag_data/* to R2/S3 (requires RAG_S3_* env).",
    )
    args = parser.parse_args()

    docs = load_documents()
    if not docs:
        return 1

    records = build_chunk_records(docs)
    if not records:
        print("Chunking produced no segments.", file=sys.stderr)
        return 1

    texts = [str(r["text"]) for r in records]
    print(f"Embedding {len(texts)} chunks with {args.model} ...")
    model = SentenceTransformer(args.model)
    embeddings = model.encode(
        texts,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=True,
    ).astype("float32")

    d = embeddings.shape[1]
    index = faiss.IndexFlatIP(d)
    index.add(embeddings)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    index_path = OUTPUT_DIR / "index.faiss"
    chunks_path = OUTPUT_DIR / "chunks.pkl"
    manifest_path = OUTPUT_DIR / "manifest.json"

    faiss.write_index(index, str(index_path))
    with open(chunks_path, "wb") as f:
        pickle.dump(records, f)

    manifest = {
        "version": str(args.version),
        "embedding_model": args.model,
        "num_chunks": len(records),
        "index_file": "index.faiss",
        "chunks_file": "chunks.pkl",
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(f"Wrote {index_path}")
    print(f"Wrote {chunks_path}")
    print(f"Wrote {manifest_path}")

    if args.upload:
        upload_artifacts(OUTPUT_DIR)
    elif _r2_env_complete():
        print("Tip: set --upload to push artifacts to R2, or upload rag_data/ manually.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
