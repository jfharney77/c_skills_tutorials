"""
rag.py — Chunking and FAISS vector-search retrieval.

build_index() and retrieve() signatures are stable — the rest of the app
never needs to change if you swap the retrieval backend here.
"""

import logging
import os
import tomllib
from pathlib import Path
from typing import List, Dict

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

logger = logging.getLogger(__name__)

# ── Embeddings ─────────────────────────────────────────────────────────────────

_config_path = Path(__file__).parent.parent / "config.toml"
_config: dict = {}
if _config_path.exists():
    with open(_config_path, "rb") as _f:
        _config = tomllib.load(_f)

_provider = _config.get("llm", {}).get("provider", "ollama")

if _provider == "openai":
    from langchain_openai import OpenAIEmbeddings
    _embed_model = _config.get("openai", {}).get("embedding_model", "text-embedding-3-small")
    _embeddings = OpenAIEmbeddings(model=_embed_model)
else:
    from langchain_ollama import OllamaEmbeddings
    _embed_model = _config.get("ollama", {}).get("embedding_model", "nomic-embed-text")
    _base_url = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
    _embeddings = OllamaEmbeddings(model=_embed_model, base_url=_base_url)

logger.info("RAG embeddings: provider=%s model=%s", _provider, _embed_model)

# ── Vector store (module-level; replaced on each build_index call) ─────────────

_vector_store: FAISS | None = None


# ── Public interface ───────────────────────────────────────────────────────────

def build_index(text: str, chunk_size: int = 500, overlap: int = 50) -> List[Dict]:
    """
    Split text into overlapping word-based chunks, embed them, and build a
    FAISS index. Returns the chunk list (id + text) for use by retrieve().

    Args:
        text:       Full document text.
        chunk_size: Target number of words per chunk.
        overlap:    Number of words shared between consecutive chunks.

    Returns:
        List of chunk dicts sorted by id.
    """
    global _vector_store

    words = text.split()
    if not words:
        _vector_store = None
        return []

    chunks = []
    step = max(1, chunk_size - overlap)
    for i, start in enumerate(range(0, len(words), step)):
        chunk_words = words[start : start + chunk_size]
        chunks.append({"id": i, "text": " ".join(chunk_words)})
        if start + chunk_size >= len(words):
            break

    logger.info("Embedding %d chunks via %s (%s)...", len(chunks), _provider, _embed_model)
    docs = [Document(page_content=c["text"], metadata={"id": c["id"]}) for c in chunks]
    _vector_store = FAISS.from_documents(docs, _embeddings)
    logger.info("FAISS index built.")

    return chunks


def retrieve(query: str, chunks: List[Dict], top_k: int = 5) -> str:
    """
    Return the most relevant chunks for a query as a single joined string.

    Uses FAISS similarity search when an index is available, otherwise falls
    back to keyword overlap scoring.

    Args:
        query:  The user's question.
        chunks: Index produced by build_index().
        top_k:  Maximum number of chunks to return.

    Returns:
        Concatenated text of the top_k most relevant chunks, separated by "\\n\\n---\\n\\n".
    """
    if not chunks:
        return ""

    if _vector_store is not None:
        results = _vector_store.similarity_search(query, k=top_k)
        # Re-sort by original document order for coherent reading
        results.sort(key=lambda d: d.metadata["id"])
        return "\n\n---\n\n".join(d.page_content for d in results)

    # Fallback: keyword overlap scoring
    logger.warning("Vector store unavailable, falling back to keyword retrieval.")
    return _keyword_retrieve(query, chunks, top_k)


# ── Keyword retrieval fallback ─────────────────────────────────────────────────

def _keyword_retrieve(query: str, chunks: List[Dict], top_k: int) -> str:
    keywords = _extract_keywords(query)
    if not keywords:
        selected = chunks[:top_k]
    else:
        scored = []
        for chunk in chunks:
            chunk_lower = chunk["text"].lower()
            score = sum(1 for kw in keywords if kw in chunk_lower)
            scored.append((score, chunk["id"], chunk))
        scored.sort(key=lambda x: (-x[0], x[1]))
        top = scored[:top_k]
        top.sort(key=lambda x: x[1])
        selected = [item[2] for item in top]
    return "\n\n---\n\n".join(chunk["text"] for chunk in selected)


_STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "need", "dare", "ought",
    "used", "to", "of", "in", "on", "at", "by", "for", "with", "about",
    "against", "between", "into", "through", "during", "before", "after",
    "above", "below", "from", "up", "down", "out", "off", "over", "under",
    "again", "further", "then", "once", "and", "but", "or", "nor", "so",
    "yet", "both", "either", "neither", "not", "only", "own", "same",
    "than", "too", "very", "just", "that", "this", "these", "those",
    "i", "me", "my", "we", "our", "you", "your", "he", "she", "it",
    "his", "her", "its", "they", "their", "what", "which", "who",
    "how", "when", "where", "why", "all", "each", "every", "few",
    "more", "most", "other", "some", "such", "no", "if",
}


def _extract_keywords(text: str) -> List[str]:
    import re
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    seen: set = set()
    keywords = []
    for token in tokens:
        if token not in _STOPWORDS and token not in seen and len(token) > 1:
            seen.add(token)
            keywords.append(token)
    return keywords
