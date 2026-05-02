from __future__ import annotations

import json
import os
import pickle
import threading
from pathlib import Path

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

from artifact_sync import sync_rag_artifacts

_lock = threading.Lock()
_index: faiss.Index | None = None
_chunks: list[dict] | None = None
_model: SentenceTransformer | None = None


def _data_dir() -> Path:
    override = os.getenv("RAG_DATA_DIR")
    if override:
        return Path(override).expanduser().resolve()
    return Path(__file__).resolve().parent / "rag_data"


def _ensure_loaded() -> None:
    global _index, _chunks, _model
    with _lock:
        if _index is not None:
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
        model_name = os.getenv(
            "RAG_EMBED_MODEL",
            manifest.get("embedding_model", "sentence-transformers/all-MiniLM-L6-v2"),
        )
        expected = manifest.get("embedding_model")
        if expected and model_name != expected:
            print(
                f"Warning: RAG_EMBED_MODEL={model_name!r} differs from manifest {expected!r}; "
                "retrieval quality may suffer.",
            )

        _index = faiss.read_index(str(data_dir / "index.faiss"))
        with open(data_dir / "chunks.pkl", "rb") as f:
            _chunks = pickle.load(f)
        _model = SentenceTransformer(model_name)


def retrieve_context(query: str, top_k: int = 3) -> str:
    _ensure_loaded()
    assert _index is not None and _chunks is not None and _model is not None

    if not _chunks:
        return "No knowledge base available."

    q = _model.encode(
        [query],
        convert_to_numpy=True,
        normalize_embeddings=True,
    ).astype("float32")
    scores, indices = _index.search(q, top_k)

    lines: list[str] = []
    for rank, idx in enumerate(indices[0]):
        if idx < 0 or idx >= len(_chunks):
            continue
        score = float(scores[0][rank])
        row = _chunks[idx]
        text = str(row.get("text", ""))
        source = row.get("source", "")
        if source:
            lines.append(f"[score={score:.3f} source={source}] {text}")
        else:
            lines.append(f"[score={score:.3f}] {text}")

    if not lines:
        return "No relevant context found in knowledge base."
    return "\n".join(lines)
