#!/usr/bin/env bash
set -e

# Always run from the V1 project root regardless of where script is called from
cd "$(dirname "$0")/.."

OUT=${1:-diagrams/workflows.md}

# Ensure venv exists and dependencies are installed
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi
source .venv/bin/activate
if ! python -c "import langgraph" &>/dev/null; then
    echo "Installing dependencies..."
    pip install -r requirements.txt
fi

echo "Generating Mermaid diagrams → ${OUT}"
python diagrams/diagrams.py > "${OUT}"
echo "Done. Output written to ${OUT}"
