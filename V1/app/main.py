"""
main.py — FastAPI application for the Research Paper Analyzer.
"""

import asyncio
import io
import logging
import logging.config
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import document_loader
from . import llm_client
from . import rag

# ── Logging setup ──────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ── App setup ──────────────────────────────────────────────────────────────────

app = FastAPI(title="Research Paper Analyzer")

STATIC_DIR = Path(__file__).parent.parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# ── Server-side state (single-user local app) ──────────────────────────────────
_state: dict = {"chunks": []}

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


# ── Pydantic models ────────────────────────────────────────────────────────────

class QARequest(BaseModel):
    question: str
    history: list[dict] = []


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    index_path = STATIC_DIR / "index.html"
    return HTMLResponse(content=index_path.read_text(encoding="utf-8"))


@app.post("/load")
async def load_document(
    url: str = Form(default=""),
    file: UploadFile = File(default=None),
):
    # ── 1. Determine source and extract text ───────────────────────────────────
    try:
        if url.strip():
            logger.info("Loading document from URL: %s", url.strip())
            text = document_loader.load_document(url.strip(), source_type="url")
        elif file is not None:
            filename = file.filename or ""
            logger.info("Loading document from file: %s", filename)
            content = await file.read()
            file_obj = io.BytesIO(content)
            if filename.lower().endswith(".pdf"):
                text = document_loader.load_document(file_obj, source_type="pdf")
            elif filename.lower().endswith(".docx"):
                text = document_loader.load_document(file_obj, source_type="docx")
            else:
                raise HTTPException(
                    status_code=400,
                    detail="Unsupported file type. Please upload a PDF or DOCX file.",
                )
        else:
            raise HTTPException(
                status_code=400,
                detail="Provide either a URL or a file upload.",
            )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to load document: {exc}") from exc

    word_count = len(text.split())
    logger.info("Document loaded: %d words", word_count)

    if not text.strip():
        raise HTTPException(status_code=400, detail="Document appears to be empty.")

    # ── 2. Build RAG index ─────────────────────────────────────────────────────
    logger.info("Building RAG index...")
    _state["chunks"] = rag.build_index(text)
    logger.info("RAG index built: %d chunks", len(_state["chunks"]))

    # ── 3. Generate summary from first 3000 words ──────────────────────────────
    first_3000 = " ".join(text.split()[:3000])
    prompt = SUMMARY_PROMPT_TEMPLATE.format(document_text=first_3000)

    logger.info("Requesting summary from LLM (this may take a while for large models)...")
    try:
        raw_response = await asyncio.to_thread(llm_client.generate, prompt, SUMMARY_SYSTEM)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"LLM error (is Ollama running?): {exc}",
        ) from exc

    # ── 4. Parse structured response ───────────────────────────────────────────
    title, authors, summary = _parse_summary_response(raw_response)

    return JSONResponse({"title": title, "authors": authors, "summary": summary})


@app.post("/ask")
async def ask_question(request: QARequest):
    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    if not _state["chunks"]:
        raise HTTPException(
            status_code=400,
            detail="No document loaded. Please load a document first.",
        )

    # ── 1. Retrieve relevant context ───────────────────────────────────────────
    logger.info("Retrieving context for question: %s", question)
    context = rag.retrieve(question, _state["chunks"])

    # ── 2. Format conversation history ────────────────────────────────────────
    history_lines = []
    for turn in request.history:
        q = turn.get("question", "").strip()
        a = turn.get("answer", "").strip()
        if q and a:
            history_lines.append(f"Q: {q}\nA: {a}")
    history_str = "\n\n".join(history_lines) if history_lines else "(none)"

    # ── 3. Generate answer ─────────────────────────────────────────────────────
    prompt = QA_PROMPT_TEMPLATE.format(
        context=context,
        history=history_str,
        question=question,
    )

    logger.info("Requesting answer from LLM...")
    try:
        answer = await asyncio.to_thread(llm_client.generate, prompt, QA_SYSTEM)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"LLM error (is Ollama running?): {exc}",
        ) from exc

    return JSONResponse({"answer": answer})


# ── Helpers ────────────────────────────────────────────────────────────────────

def _parse_summary_response(raw: str) -> tuple[str, str, str]:
    """
    Parse TITLE / AUTHORS / SUMMARY from the LLM response.
    Falls back gracefully if the format is malformed.
    """
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

    # Graceful fallback
    if not title and not summary:
        summary = raw.strip()
        title = "Untitled"
        authors = "Unknown"

    return title or "Untitled", authors or "Unknown", summary or raw.strip()
