"""
Offline RAG index build with LangChain: load docs, chunk, embed, and write FAISS artifacts.

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
import sys
from pathlib import Path

from langchain_community.document_loaders import TextLoader
from langchain_community.vectorstores import FAISS
from langchain_ollama import OllamaEmbeddings
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter


DEFAULT_MODEL = "nomic-embed-text"
WORKER_DIR = Path(__file__).resolve().parent
KB_DIR = WORKER_DIR / "kb_docs"
LEGACY_KB = WORKER_DIR / "knowledge_base.txt"
OUTPUT_DIR = WORKER_DIR / "rag_data"
ENV_KEYS = (
    "RAG_S3_ENDPOINT",
    "RAG_S3_ACCESS_KEY_ID",
    "RAG_S3_SECRET_ACCESS_KEY",
    "RAG_S3_BUCKET",
)


def _env_non_empty(key: str, default: str | None = None) -> str | None:
    value = os.getenv(key)
    if value is None:
        return default
    value = value.strip()
    return value if value else default


def _load_dotenv_if_present() -> None:
    # Direct python execution does not auto-load .env; compose usually does.
    for path in (WORKER_DIR.parent / ".env", WORKER_DIR / ".env"):
        if not path.is_file():
            continue
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[len("export ") :].strip()
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


def load_documents() -> list[Document]:
    docs: list[Document] = []
    txt_files = sorted(KB_DIR.glob("*.txt"))
    if txt_files:
        for path in txt_files:
            loaded = TextLoader(
                str(path),
                encoding="utf-8",
                autodetect_encoding=True,
            ).load()
            for doc in loaded:
                doc.metadata["source"] = path.name
                docs.append(doc)
        return docs

    if LEGACY_KB.is_file():
        for i, line in enumerate(LEGACY_KB.read_text(encoding="utf-8").splitlines()):
            line = line.strip()
            if line:
                docs.append(
                    Document(
                        page_content=line,
                        metadata={"source": f"knowledge_base.txt#line{i + 1}"},
                    )
                )
        return docs

    print(
        "No documents found. Add .txt files under kb_docs/ or keep knowledge_base.txt.",
        file=sys.stderr,
    )
    return []


def _r2_env_complete() -> bool:
    return all(_env_non_empty(k) for k in ENV_KEYS)


def _missing_r2_env() -> list[str]:
    return [key for key in ENV_KEYS if not _env_non_empty(key)]


def _object_key(filename: str) -> str:
    prefix = (_env_non_empty("RAG_S3_PREFIX", "rag") or "rag").strip().strip("/")
    return f"{prefix}/{filename}" if prefix else filename


def _ollama_base_url() -> str:
    raw = _env_non_empty("RAG_OLLAMA_URL")
    if not raw:
        raw = _env_non_empty("OLLAMA_URL", "http://host.docker.internal:11434")
    assert raw is not None
    # OLLAMA_URL in this repo is often set to /api/generate for chat.
    return raw.removesuffix("/api/generate").rstrip("/")


def upload_artifacts(out_dir: Path) -> None:
    import boto3
    from botocore.config import Config

    missing = _missing_r2_env()
    if missing:
        raise RuntimeError(
            "Missing required environment variables for --upload: "
            + ", ".join(missing)
        )

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
    for name in ("manifest.json", "index.faiss", "index.pkl"):
        path = out_dir / name
        if not path.is_file():
            raise FileNotFoundError(path)
        client.upload_file(str(path), bucket, _object_key(name))
    prefix = (_env_non_empty("RAG_S3_PREFIX", "rag") or "rag").strip().strip("/")
    loc = f"{prefix}/" if prefix else ""
    print(f"Uploaded manifest + index + chunks to bucket={bucket!r} prefix={loc!r}")


def main() -> int:
    _load_dotenv_if_present()

    parser = argparse.ArgumentParser(description="Build FAISS RAG artifacts for workers.")
    parser.add_argument(
        "--model",
        default=_env_non_empty("RAG_EMBED_MODEL", DEFAULT_MODEL),
        help="Ollama embedding model name (must match worker at query time).",
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

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=int(_env_non_empty("RAG_CHUNK_SIZE", "700") or "700"),
        chunk_overlap=int(_env_non_empty("RAG_CHUNK_OVERLAP", "120") or "120"),
    )
    chunks = splitter.split_documents(docs)
    if not chunks:
        print("Chunking produced no segments.", file=sys.stderr)
        return 1

    print(f"Embedding {len(chunks)} chunks with {args.model} ...")
    embeddings = OllamaEmbeddings(
        model=args.model,
        base_url=_ollama_base_url(),
    )
    vector_store = FAISS.from_documents(chunks, embeddings)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest_path = OUTPUT_DIR / "manifest.json"

    vector_store.save_local(str(OUTPUT_DIR))

    manifest = {
        "version": str(args.version),
        "embedding_model": args.model,
        "embedding_provider": "ollama",
        "num_chunks": len(chunks),
        "index_file": "index.faiss",
        "store_file": "index.pkl",
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(f"Wrote {OUTPUT_DIR / 'index.faiss'}")
    print(f"Wrote {OUTPUT_DIR / 'index.pkl'}")
    print(f"Wrote {manifest_path}")

    if args.upload:
        upload_artifacts(OUTPUT_DIR)
    elif _r2_env_complete():
        print("Tip: set --upload to push artifacts to R2, or upload rag_data/ manually.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
