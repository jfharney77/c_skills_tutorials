"""
rag.py — In-memory chunking and keyword-based retrieval.

To upgrade to ChromaDB or another vector store, replace the bodies of
build_index() and retrieve() while keeping their signatures identical.
"""

import re
from typing import List, Dict


# ── Public interface ───────────────────────────────────────────────────────────

def build_index(text: str, chunk_size: int = 500, overlap: int = 50) -> List[Dict]:
    """
    Split text into overlapping word-based chunks and return an index.

    Each chunk dict has:
        id    (int)  — original position for stable re-ordering
        text  (str)  — the chunk content

    Args:
        text:       Full document text.
        chunk_size: Target number of words per chunk.
        overlap:    Number of words shared between consecutive chunks.

    Returns:
        List of chunk dicts sorted by id.
    """
    words = text.split()
    if not words:
        return []

    chunks = []
    step = max(1, chunk_size - overlap)
    for i, start in enumerate(range(0, len(words), step)):
        chunk_words = words[start : start + chunk_size]
        chunks.append({"id": i, "text": " ".join(chunk_words)})
        if start + chunk_size >= len(words):
            break

    return chunks


def retrieve(query: str, chunks: List[Dict], top_k: int = 5) -> str:
    """
    Return the most relevant chunks for a query as a single joined string.

    Scoring: count of unique query keywords that appear in each chunk (case-insensitive).
    Ties are broken by original chunk order. Results are re-sorted by original id
    before joining so the returned context reads in document order.

    Args:
        query:  The user's question.
        chunks: Index produced by build_index().
        top_k:  Maximum number of chunks to return.

    Returns:
        Concatenated text of the top_k most relevant chunks, separated by "\\n\\n---\\n\\n".
    """
    if not chunks:
        return ""

    keywords = _extract_keywords(query)
    if not keywords:
        # Fall back to first top_k chunks if no keywords
        selected = chunks[:top_k]
    else:
        scored = []
        for chunk in chunks:
            chunk_lower = chunk["text"].lower()
            score = sum(1 for kw in keywords if kw in chunk_lower)
            scored.append((score, chunk["id"], chunk))

        scored.sort(key=lambda x: (-x[0], x[1]))
        top = scored[:top_k]
        # Re-sort by original document order for coherent reading
        top.sort(key=lambda x: x[1])
        selected = [item[2] for item in top]

    return "\n\n---\n\n".join(chunk["text"] for chunk in selected)


# ── Helpers ────────────────────────────────────────────────────────────────────

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
    """Lowercase alphanum tokens, remove stopwords, deduplicate."""
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    seen = set()
    keywords = []
    for token in tokens:
        if token not in _STOPWORDS and token not in seen and len(token) > 1:
            seen.add(token)
            keywords.append(token)
    return keywords
