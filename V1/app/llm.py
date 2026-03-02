"""
llm.py — ChatOllama singleton. Model configuration lives here.
"""

import os
import tomllib
from pathlib import Path

from langchain_ollama import ChatOllama

# ── Configuration ──────────────────────────────────────────────────────────────

_config_path = Path(__file__).parent.parent / "config.toml"
if _config_path.exists():
    with open(_config_path, "rb") as _f:
        _config = tomllib.load(_f)
    _model = _config.get("ollama", {}).get("model", "llama3.1:8b")
else:
    _model = os.environ.get("OLLAMA_MODEL", "llama3.1:8b")

_base_url = os.environ.get("OLLAMA_HOST", "http://localhost:11434")

# ── Singleton ──────────────────────────────────────────────────────────────────

llm = ChatOllama(model=_model, base_url=_base_url)
