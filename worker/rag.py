from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


KB_PATH = Path(__file__).parent / "knowledge_base.txt"

_documents = [line.strip() for line in KB_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]
_vectorizer = TfidfVectorizer(stop_words="english")
_doc_matrix = _vectorizer.fit_transform(_documents)


def retrieve_context(query: str, top_k: int = 3) -> str:
    if not _documents:
        return "No knowledge base available."
    query_vec = _vectorizer.transform([query])
    sims = cosine_similarity(query_vec, _doc_matrix).flatten()
    top_indices = sims.argsort()[::-1][:top_k]
    chunks = []
    for idx in top_indices:
        score = sims[idx]
        if score <= 0:
            continue
        chunks.append(f"[score={score:.3f}] {_documents[idx]}")
    return "\n".join(chunks) if chunks else "No relevant context found in knowledge base."
