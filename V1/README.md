# Research Paper Analyzer — V1

A locally-running web app that accepts a research paper (PDF, DOCX, or URL), sends it to **llama3:70b** via Ollama, and returns a structured summary with an interactive Q&A chain.

## Prerequisites

- Python 3.10+
- [Ollama](https://ollama.com/) with `llama3:70b` pulled

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
ollama pull llama3:70b
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
│   ├── document_loader.py  # URL / PDF / DOCX → plain text
│   ├── llm_client.py       # Ollama wrapper (provider-agnostic interface)
│   └── rag.py              # In-memory chunking + keyword retrieval
├── static/
│   └── index.html          # Single-page app (HTML + CSS + JS)
├── scripts/
│   ├── run.sh              # Linux/WSL start script (venv or uv, auto-detects Windows Ollama)
│   └── run.ps1             # Windows start script
├── requirements.txt
└── pyproject.toml          # uv-compatible dependency spec
```

## Extensibility

| What to change          | Where to look           |
|-------------------------|-------------------------|
| Swap LLM provider       | `llm_client.py` — change `PROVIDER` and implement the new `_*_generate()` function |
| Upgrade to vector RAG   | `rag.py` — replace `build_index()` and `retrieve()` bodies; signatures stay the same |
| Add new input formats   | `document_loader.py` — add a branch in `load_document()` |
| New API endpoints       | `main.py`               |

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
