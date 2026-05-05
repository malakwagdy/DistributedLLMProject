from __future__ import annotations

import json
import os
import threading
from pathlib import Path

from langchain_community.vectorstores import FAISS
from langchain_ollama import OllamaEmbeddings

from artifact_sync import sync_rag_artifacts

_lock = threading.Lock()
_vector_store: FAISS | None = None


def _env_non_empty(key: str, default: str | None = None) -> str | None:
    value = os.getenv(key)
    if value is None:
        return default
    value = value.strip()
    return value if value else default


def _data_dir() -> Path:
    override = _env_non_empty("RAG_DATA_DIR")
    if override:
        return Path(override).expanduser().resolve()
    return Path(__file__).resolve().parent / "rag_data"


def _ollama_base_url() -> str:
    raw = _env_non_empty("RAG_OLLAMA_URL")
    if not raw:
        raw = _env_non_empty("OLLAMA_URL", "http://host.docker.internal:11434")
    assert raw is not None
    return raw.removesuffix("/api/generate").rstrip("/")


def _ensure_loaded() -> None:
    global _vector_store
    with _lock:
        if _vector_store is not None:
            return

        data_dir = _data_dir()
        data_dir.mkdir(parents=True, exist_ok=True)
        sync_rag_artifacts(data_dir)

        manifest_path = data_dir / "manifest.json"
        if not manifest_path.is_file():
            raise FileNotFoundError(
                "RAG artifacts missing. Build them with: python build_index.py "
                "(from the worker directory), or set RAG_S3_* so the worker can sync from R2."
            )

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        fallback_model = str(manifest.get("embedding_model", "nomic-embed-text")).strip() or "nomic-embed-text"
        model_name = _env_non_empty("RAG_EMBED_MODEL", fallback_model) or fallback_model
        expected = manifest.get("embedding_model")
        provider = str(manifest.get("embedding_provider", "")).strip()
        if provider and provider != "ollama":
            raise RuntimeError(
                "RAG artifact embedding provider mismatch. "
                f"Manifest has embedding_provider={provider!r}, but runtime uses Ollama embeddings. "
                "Rebuild and upload the index with the current pipeline."
            )
        if expected and model_name != expected:
            raise RuntimeError(
                "RAG embedding model mismatch between worker and FAISS index. "
                f"Runtime model={model_name!r}, manifest model={expected!r}. "
                "Rebuild/upload index with the same model (or set matching RAG_EMBED_MODEL), "
                "and bump RAG_INDEX_VERSION so workers re-sync artifacts."
            )

        embeddings = OllamaEmbeddings(
            model=model_name,
            base_url=_ollama_base_url(),
        )
        _vector_store = FAISS.load_local(
            str(data_dir),
            embeddings,
            allow_dangerous_deserialization=True,
        )


def retrieve_context(query: str, top_k: int = 3) -> str:
    _ensure_loaded()
    assert _vector_store is not None
    results = _vector_store.similarity_search_with_score(query, k=top_k)

    lines: list[str] = []
    for doc, score in results:
        text = doc.page_content.strip()
        source = str(doc.metadata.get("source", ""))
        if source:
            lines.append(f"[score={score:.3f} source={source}] {text}")
        else:
            lines.append(f"[score={score:.3f}] {text}")

    if not lines:
        return "No relevant context found in knowledge base."
    return "\n".join(lines)
