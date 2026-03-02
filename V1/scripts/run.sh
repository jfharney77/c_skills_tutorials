#!/usr/bin/env bash
set -e

# Always run from the V1 project root regardless of where script is called from
cd "$(dirname "$0")/.."

# Resolve the Windows host IP (WSL2 default gateway)
WINDOWS_IP=$(ip route show | grep default | awk '{print $3}')
export OLLAMA_HOST="http://${WINDOWS_IP}:11434"

echo "Windows host: ${WINDOWS_IP}"
echo "OLLAMA_HOST:  ${OLLAMA_HOST}"

# Verify Ollama is reachable
if ! curl -sf "${OLLAMA_HOST}/api/tags" > /dev/null; then
    echo ""
    echo "ERROR: Cannot reach Ollama at ${OLLAMA_HOST}"
    echo "Make sure Ollama is running on Windows with OLLAMA_HOST=0.0.0.0"
    exit 1
fi
echo "Ollama is reachable."

MODE=${1:-venv}

if [ "$MODE" = "uv" ]; then
    if ! command -v uv &>/dev/null; then
        echo "ERROR: uv is not installed. Run: pip install uv"
        exit 1
    fi
    echo "Using uv"
    uv sync
    echo ""
    echo "Starting app at http://localhost:8000"
    uv run uvicorn app.main:app --reload --port 8000
else
    echo "Using venv"
    if [ ! -d ".venv" ]; then
        echo "Creating virtual environment..."
        python3 -m venv .venv
    fi
    source .venv/bin/activate
    if ! python -c "import fastapi" &>/dev/null; then
        echo "Installing dependencies..."
        pip install -r requirements.txt
    fi
    echo ""
    echo "Starting app at http://localhost:8000"
    uvicorn app.main:app --reload --port 8000
fi
