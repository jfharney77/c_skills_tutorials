"""
llm.py — LLM singleton. Provider and model configuration lives here.

Set [llm].provider in config.toml to "ollama" or "openai".
"""

import os
import tomllib
from pathlib import Path

# ── Load config ────────────────────────────────────────────────────────────────

_config_path = Path(__file__).parent.parent / "config.toml"
_config: dict = {}
if _config_path.exists():
    with open(_config_path, "rb") as _f:
        _config = tomllib.load(_f)

_provider = _config.get("llm", {}).get("provider", "ollama")

# ── Build singleton ────────────────────────────────────────────────────────────

if _provider == "openai":
    from langchain_openai import ChatOpenAI

    _model = _config.get("openai", {}).get("model", "gpt-4o-mini")
    llm = ChatOpenAI(model=_model)

else:  # default: ollama
    from langchain_ollama import ChatOllama

    _model = _config.get("ollama", {}).get("model", "llama3.1:8b")
    _base_url = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
    llm = ChatOllama(model=_model, base_url=_base_url)
