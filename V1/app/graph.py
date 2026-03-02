"""
graph.py — LangGraph state machines for document loading and Q&A.

Load graph:  START → extract_text → build_index → summarize → END
QA graph:    START → retrieve → answer → END
"""

import io
import logging

from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, START, END

from .llm import llm
from . import document_loader, rag
from .state import LoadState, QAState

logger = logging.getLogger(__name__)

# ── Prompt templates ───────────────────────────────────────────────────────────

SUMMARY_SYSTEM = (
    "You are an expert research assistant. "
    "Extract structured metadata and summarize academic papers clearly."
)

SUMMARY_PROMPT_TEMPLATE = '''\
Below is the full text of a research paper. Respond with:

TITLE: <title>
AUTHORS: <comma-separated authors>
SUMMARY:
<Paragraph 1: problem and motivation>
<Paragraph 2: methods and approach>
<Paragraph 3: results and implications>

Paper text:
"""
{document_text}
"""'''

QA_SYSTEM = (
    "You are an expert research assistant. "
    "Answer questions using only the provided context. "
    "Say 'I don't know' if the answer is not in the context."
)

QA_PROMPT_TEMPLATE = '''\
Retrieved context:
"""
{context}
"""

Previous conversation:
{history}

Question: {question}
Answer:'''


# ── Load graph nodes ───────────────────────────────────────────────────────────

def extract_text_node(state: LoadState) -> LoadState:
    if state.get("error"):
        return state
    logger.info("extract_text_node: loading document (source_type=%s)", state["source_type"])
    try:
        if state["source_type"] == "url":
            text = document_loader.load_document(state["source"], source_type="url")
        else:
            file_obj = io.BytesIO(state["file_bytes"])
            text = document_loader.load_document(file_obj, source_type=state["source_type"])
        return {**state, "document_text": text}
    except Exception as exc:
        return {**state, "error": f"Failed to load document: {exc}"}


def build_index_node(state: LoadState) -> LoadState:
    if state.get("error"):
        return state
    logger.info("build_index_node: building RAG index")
    chunks = rag.build_index(state["document_text"])
    logger.info("build_index_node: %d chunks", len(chunks))
    return {**state, "chunks": chunks}


def summarize_node(state: LoadState) -> LoadState:
    if state.get("error"):
        return state
    logger.info("summarize_node: requesting summary from LLM")
    first_3000 = " ".join(state["document_text"].split()[:3000])
    prompt = SUMMARY_PROMPT_TEMPLATE.format(document_text=first_3000)
    try:
        response = llm.invoke([
            SystemMessage(content=SUMMARY_SYSTEM),
            HumanMessage(content=prompt),
        ])
        raw = response.content
    except Exception as exc:
        return {**state, "error": f"LLM error (is Ollama running?): {exc}"}
    title, authors, summary = _parse_summary_response(raw)
    logger.info("summarize_node: done (title=%r)", title)
    return {**state, "raw_response": raw, "title": title, "authors": authors, "summary": summary}


# ── QA graph nodes ─────────────────────────────────────────────────────────────

def retrieve_node(state: QAState) -> QAState:
    if state.get("error"):
        return state
    logger.info("retrieve_node: retrieving context for question")
    context = rag.retrieve(state["question"], state["chunks"])
    return {**state, "context": context}


def answer_node(state: QAState) -> QAState:
    if state.get("error"):
        return state
    logger.info("answer_node: requesting answer from LLM")
    history_lines = []
    for turn in state["history"]:
        q = turn.get("question", "").strip()
        a = turn.get("answer", "").strip()
        if q and a:
            history_lines.append(f"Q: {q}\nA: {a}")
    history_str = "\n\n".join(history_lines) if history_lines else "(none)"

    prompt = QA_PROMPT_TEMPLATE.format(
        context=state["context"],
        history=history_str,
        question=state["question"],
    )
    try:
        response = llm.invoke([
            SystemMessage(content=QA_SYSTEM),
            HumanMessage(content=prompt),
        ])
        return {**state, "answer": response.content}
    except Exception as exc:
        return {**state, "error": f"LLM error (is Ollama running?): {exc}"}


# ── Graph compilation ──────────────────────────────────────────────────────────

_load_builder = StateGraph(LoadState)
_load_builder.add_node("extract_text", extract_text_node)
_load_builder.add_node("build_index", build_index_node)
_load_builder.add_node("summarize", summarize_node)
_load_builder.add_edge(START, "extract_text")
_load_builder.add_edge("extract_text", "build_index")
_load_builder.add_edge("build_index", "summarize")
_load_builder.add_edge("summarize", END)
load_graph = _load_builder.compile()

_qa_builder = StateGraph(QAState)
_qa_builder.add_node("retrieve", retrieve_node)
_qa_builder.add_node("answer", answer_node)
_qa_builder.add_edge(START, "retrieve")
_qa_builder.add_edge("retrieve", "answer")
_qa_builder.add_edge("answer", END)
qa_graph = _qa_builder.compile()


# ── Helper ─────────────────────────────────────────────────────────────────────

def _parse_summary_response(raw: str) -> tuple[str, str, str]:
    title = ""
    authors = ""
    summary = ""
    lines = raw.strip().splitlines()
    mode = None
    summary_lines = []

    for line in lines:
        stripped = line.strip()
        upper = stripped.upper()

        if upper.startswith("TITLE:"):
            title = stripped[len("TITLE:"):].strip()
            mode = "title"
        elif upper.startswith("AUTHORS:"):
            authors = stripped[len("AUTHORS:"):].strip()
            mode = "authors"
        elif upper.startswith("SUMMARY:"):
            remainder = stripped[len("SUMMARY:"):].strip()
            if remainder:
                summary_lines.append(remainder)
            mode = "summary"
        elif mode == "summary":
            summary_lines.append(stripped)
        elif mode == "title" and not title:
            title = stripped
        elif mode == "authors" and not authors:
            authors = stripped

    summary = "\n\n".join(p for p in summary_lines if p)

    if not title and not summary:
        summary = raw.strip()
        title = "Untitled"
        authors = "Unknown"

    return title or "Untitled", authors or "Unknown", summary or raw.strip()
