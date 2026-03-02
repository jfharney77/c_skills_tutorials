"""
llm_client.py — Provider-agnostic LLM interface.

To swap providers, change PROVIDER and implement the corresponding _generate function.
Calling code uses only generate() and never touches provider-specific logic.
"""

import logging
import os
import ollama

logger = logging.getLogger(__name__)

# ── Configuration ──────────────────────────────────────────────────────────────
PROVIDER = "ollama"       # Change to "claude" to use Anthropic's API
OLLAMA_MODEL = "llama3:70b"
# Override with OLLAMA_HOST env var (e.g. "http://localhost:11434")
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")


# ── Public interface ───────────────────────────────────────────────────────────

def generate(prompt: str, system: str = "") -> str:
    """
    Send a prompt to the configured LLM and return the response text.

    Args:
        prompt: The user message / instruction.
        system: Optional system prompt that shapes model behavior.

    Returns:
        The model's response as a plain string.
    """
    if PROVIDER == "ollama":
        return _ollama_generate(prompt, system)
    elif PROVIDER == "claude":
        return _claude_generate(prompt, system)
    else:
        raise ValueError(f"Unknown PROVIDER: {PROVIDER!r}")


# ── Provider implementations ───────────────────────────────────────────────────

def _ollama_generate(prompt: str, system: str) -> str:
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    logger.info("Sending request to Ollama (%s) at %s", OLLAMA_MODEL, OLLAMA_HOST)
    client = ollama.Client(host=OLLAMA_HOST)

    tokens: list[str] = []
    token_count = 0
    for chunk in client.chat(model=OLLAMA_MODEL, messages=messages, stream=True):
        token = chunk["message"]["content"]
        tokens.append(token)
        token_count += 1
        if token_count % 50 == 0:
            logger.info("  ... %d tokens received so far", token_count)

    logger.info("Ollama response complete (%d tokens)", token_count)
    return "".join(tokens)


def _claude_generate(prompt: str, system: str) -> str:
    """Stub for Anthropic Claude API. Implement when PROVIDER = "claude"."""
    raise NotImplementedError(
        "Claude provider not yet implemented. "
        "Install anthropic, set your API key, and fill in this function."
    )
