"""
main.py — FastAPI application for the Research Paper Analyzer.
"""

import asyncio
import logging
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .graph import load_graph, qa_graph

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
    if url.strip():
        logger.info("Loading document from URL: %s", url.strip())
        initial: dict = {
            "source": url.strip(),
            "source_type": "url",
            "file_bytes": None,
            "document_text": "",
            "chunks": [],
            "raw_response": "",
            "title": "",
            "authors": "",
            "summary": "",
            "error": "",
        }
    elif file is not None:
        filename = file.filename or ""
        logger.info("Loading document from file: %s", filename)
        if filename.lower().endswith(".pdf"):
            source_type = "pdf"
        elif filename.lower().endswith(".docx"):
            source_type = "docx"
        else:
            raise HTTPException(
                status_code=400,
                detail="Unsupported file type. Please upload a PDF or DOCX file.",
            )
        file_bytes = await file.read()
        initial = {
            "source": filename,
            "source_type": source_type,
            "file_bytes": file_bytes,
            "document_text": "",
            "chunks": [],
            "raw_response": "",
            "title": "",
            "authors": "",
            "summary": "",
            "error": "",
        }
    else:
        raise HTTPException(
            status_code=400,
            detail="Provide either a URL or a file upload.",
        )

    result = await asyncio.to_thread(load_graph.invoke, initial)

    if result.get("error"):
        status = 500 if "LLM error" in result["error"] else 400
        raise HTTPException(status_code=status, detail=result["error"])

    _state["chunks"] = result["chunks"]
    return JSONResponse({
        "title": result["title"],
        "authors": result["authors"],
        "summary": result["summary"],
    })


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

    initial: dict = {
        "question": question,
        "history": request.history,
        "chunks": _state["chunks"],
        "context": "",
        "answer": "",
        "error": "",
    }

    result = await asyncio.to_thread(qa_graph.invoke, initial)

    if result.get("error"):
        raise HTTPException(status_code=500, detail=result["error"])

    return JSONResponse({"answer": result["answer"]})
