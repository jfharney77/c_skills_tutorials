"""
state.py — TypedDict schemas for LangGraph graphs.
"""

from typing import TypedDict


class LoadState(TypedDict):
    source: str
    source_type: str          # "url" | "pdf" | "docx"
    file_bytes: bytes | None
    document_text: str
    chunks: list[dict]
    raw_response: str
    title: str
    authors: str
    summary: str
    error: str


class QAState(TypedDict):
    question: str
    history: list[dict]
    chunks: list[dict]
    context: str
    answer: str
    error: str
