# Research Paper Analyzer — V1

A locally-running web app that accepts a research paper (PDF, DOCX, or URL), sends it to a local LLM via Ollama, and returns a structured summary with an interactive Q&A chain.

## Prerequisites

- Python 3.10+
- [Ollama](https://ollama.com/) with a model pulled (default: `llama3.1:8b`)

## Quick Start

```bash
cd V1
./scripts/run.sh        # uses python venv (default)
./scripts/run.sh uv     # uses uv (requires uv installed)
```

Then open http://localhost:8000.

The script automatically:
- Detects the correct Ollama host (supports WSL2 → Windows)
- Creates a virtual environment and installs dependencies on first run
- Verifies Ollama is reachable before starting

### Running Ollama on Windows from WSL2

If Ollama is running on Windows, launch it with:

```powershell
# PowerShell on Windows
$env:OLLAMA_HOST = "0.0.0.0"
ollama serve
```

Then pull the model (first time only):

```powershell
ollama pull llama3.1:8b
```

`run.sh` will automatically point the app at the Windows host.

## Usage

1. **URL mode** — paste a link to a PDF or web page (e.g. `https://arxiv.org/pdf/1706.03762`)
2. **File upload** — select a `.pdf` or `.docx` file from your machine
3. Click **Analyze** — the app extracts text, builds a RAG index, and generates a structured summary
4. Ask questions in the Q&A section; each answer feeds into the conversation history

## Project Structure

```
V1/
├── app/                    # Python package
│   ├── main.py             # FastAPI app + API endpoints (/load, /ask)
│   ├── llm.py              # ChatOllama singleton (model config lives here)
│   ├── state.py            # TypedDict schemas for LangGraph graphs
│   ├── graph.py            # LangGraph graphs, prompt templates, node logic
│   ├── document_loader.py  # URL / PDF / DOCX → plain text
│   └── rag.py              # In-memory chunking + keyword retrieval
├── static/
│   └── index.html          # Single-page app (HTML + CSS + JS)
├── scripts/
│   ├── run.sh              # Linux/WSL start script (venv or uv, auto-detects Windows Ollama)
│   └── run.ps1             # Windows start script
├── config.toml             # Model selection (change [ollama].model here)
├── requirements.txt
└── pyproject.toml          # uv-compatible dependency spec
```

## Architecture

Request flow:
```
browser → FastAPI (main.py)
  → load_graph:  extract_text → build_index → summarize → (return)
  → qa_graph:    retrieve → answer → (return)
```

- **`app/main.py`** — thin FastAPI wrapper; builds initial state dicts and invokes graphs via `asyncio.to_thread`. Holds a module-level `_state` dict (single-user cache for chunks).
- **`app/llm.py`** — reads model from `config.toml` → `[ollama].model`; exports `llm = ChatOllama(...)` singleton.
- **`app/state.py`** — `LoadState` and `QAState` TypedDicts used by LangGraph.
- **`app/graph.py`** — two compiled LangGraph graphs plus prompt templates and response parsing. Each node short-circuits if a previous node set `error`.
- **`app/document_loader.py`** — `load_document(source, source_type)` dispatches to URL/PDF/DOCX extractors.
- **`app/rag.py`** — `build_index(text)` produces 500-word chunks with 50-word overlap; `retrieve(query, chunks)` scores by unique keyword overlap and returns top-5 in document order.

## Extensibility

| What to change        | Where to look                                                         |
|-----------------------|-----------------------------------------------------------------------|
| Swap model            | `config.toml` — change `[ollama].model`                              |
| Swap LLM provider     | `llm.py` — replace `ChatOllama` with another LangChain chat model    |
| Upgrade to vector RAG | `rag.py` — replace `build_index()` and `retrieve()` bodies           |
| Add new input formats | `document_loader.py` — add a branch in `load_document()`             |
| New API endpoints     | `main.py` + new nodes/graph in `graph.py`                            |

## API

### `POST /load`
| Field | Type          | Description                        |
|-------|---------------|------------------------------------|
| `url` | form string   | URL of a PDF or web page           |
| `file`| form file     | `.pdf` or `.docx` upload           |

Response: `{"title": str, "authors": str, "summary": str}`

### `POST /ask`
```json
{
  "question": "What dataset did the authors use?",
  "history": [{"question": "...", "answer": "..."}]
}
```
Response: `{"answer": str}`
