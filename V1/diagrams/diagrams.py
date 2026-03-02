"""
diagrams.py — Generate Mermaid diagrams for the LangGraph workflows.

Prints Mermaid source for both compiled graphs to stdout.
Redirect to a .md file to embed in documentation.

Usage (from V1/):
    python diagrams/diagrams.py
    python diagrams/diagrams.py > diagrams/workflows.md
"""

import sys
from pathlib import Path

# Make the app package importable when run directly from V1/ or from this file's directory
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.graph import load_graph, qa_graph


def mermaid_block(title: str, graph) -> str:
    diagram = graph.get_graph().draw_mermaid()
    return f"## {title}\n\n```mermaid\n{diagram}```\n"


def main() -> None:
    print(mermaid_block("Load Graph (extract_text → build_index → summarize)", load_graph))
    print(mermaid_block("QA Graph (retrieve → answer)", qa_graph))


if __name__ == "__main__":
    main()
