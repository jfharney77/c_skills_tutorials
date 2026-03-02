# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Purpose

This repo is a sandbox for practicing Claude Code skills. Each versioned subdirectory (`V1/`, `V2/`, …) is a self-contained project built during a session.

## V1 — Research Paper Analyzer

### Running the app

```bash
cd V1
pip install -r requirements.txt          # first time only
uvicorn main:app --reload --port 8000
# then open http://localhost:8000
```

Requires [Ollama](https://ollama.com/) running locally with the model pulled:
```bash
ollama pull llama3:70b
```

To point at a non-default Ollama host: `export OLLAMA_HOST=http://host:11434`

### Architecture

Request flow: browser → FastAPI (`main.py`) → `document_loader.py` → `rag.py` + `llm_client.py` → Ollama

- **`main.py`** — two endpoints (`POST /load`, `POST /ask`) plus `GET /` serving the SPA. Holds a module-level `_state` dict (single-user; not thread-safe).
- **`document_loader.py`** — `load_document(source, source_type)` dispatches to URL/PDF/DOCX extractors. Add new formats here.
- **`rag.py`** — `build_index(text)` produces 500-word chunks with 50-word overlap; `retrieve(query, chunks)` scores by unique keyword overlap and returns top-5 in document order. Signatures are stable — swap bodies to upgrade to vector search.
- **`llm_client.py`** — `generate(prompt, system)` dispatches on `PROVIDER` ("ollama" or "claude"). Add a new `_*_generate()` function and a `PROVIDER` branch to swap models.
- **`static/index.html`** — single-file SPA (HTML + CSS + vanilla JS); no build step.

### Extensibility seams

| Goal | File | What to change |
|---|---|---|
| Swap LLM | `llm_client.py` | Change `PROVIDER`; implement `_claude_generate()` |
| Vector RAG | `rag.py` | Replace `build_index()` / `retrieve()` bodies |
| New input format | `document_loader.py` | Add branch in `load_document()` |
| New API endpoint | `main.py` | Add FastAPI route |
