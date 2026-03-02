# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Purpose

This repo is a sandbox for practicing Claude Code skills. Each versioned subdirectory (`V1/`, `V2/`, …) is a self-contained project built during a session.

## V1 — Research Paper Analyzer

### Running the app

```bash
cd V1
./scripts/run.sh        # Linux/WSL — auto-detects Windows Ollama host, sets up venv
./scripts/run.sh uv     # same, but uses uv instead of venv
# then open http://localhost:8000
```

On Windows:
```powershell
# First, start Ollama with external access enabled:
$env:OLLAMA_HOST = "0.0.0.0"; ollama serve

# Then in a separate terminal:
.\scripts\run.ps1
```

Requires [Ollama](https://ollama.com/) with the model pulled:
```bash
ollama pull llama3:70b
```

### Architecture

Request flow: browser → FastAPI (`app/main.py`) → `app/document_loader.py` → `app/rag.py` + `app/llm_client.py` → Ollama

- **`app/main.py`** — two endpoints (`POST /load`, `POST /ask`) plus `GET /` serving the SPA. Holds a module-level `_state` dict (single-user; not thread-safe). LLM calls run via `asyncio.to_thread` to avoid blocking the event loop.
- **`app/document_loader.py`** — `load_document(source, source_type)` dispatches to URL/PDF/DOCX extractors. Add new formats here.
- **`app/rag.py`** — `build_index(text)` produces 500-word chunks with 50-word overlap; `retrieve(query, chunks)` scores by unique keyword overlap and returns top-5 in document order. Signatures are stable — swap bodies to upgrade to vector search.
- **`app/llm_client.py`** — `generate(prompt, system)` dispatches on `PROVIDER` ("ollama" or "claude"). Uses streaming to log token progress. Add a new `_*_generate()` function and a `PROVIDER` branch to swap models.
- **`static/index.html`** — single-file SPA (HTML + CSS + vanilla JS); no build step.
- **`scripts/run.sh`** — WSL2-aware launcher; detects Windows host IP, sets `OLLAMA_HOST`, creates venv or uses uv.
- **`scripts/run.ps1`** — Windows launcher; checks Python, creates venv, verifies Ollama, opens browser.

### Extensibility seams

| Goal | File | What to change |
|---|---|---|
| Swap LLM | `app/llm_client.py` | Change `PROVIDER`; implement `_claude_generate()` |
| Vector RAG | `app/rag.py` | Replace `build_index()` / `retrieve()` bodies |
| New input format | `app/document_loader.py` | Add branch in `load_document()` |
| New API endpoint | `app/main.py` | Add FastAPI route |
