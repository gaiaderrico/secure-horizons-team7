"""Tiny LLM client (stdlib only) shared by prepare/, claims and narrator.

Pick the backend with MIRAGE_LLM:
  none       (default) no LLM. Every caller has a deterministic fallback, so nothing breaks offline.
  ollama     local model, e.g. qwen2.5:7b          (MIRAGE_OLLAMA_URL, MIRAGE_OLLAMA_MODEL)
  anthropic  Claude API, key in ANTHROPIC_API_KEY  (MIRAGE_ANTHROPIC_MODEL)

The LLM never runs in guard.py. Callers must treat its output as untrusted: parse it, validate it,
and fall back to the deterministic path if anything is off.
"""
from __future__ import annotations

import json
import os
import re
import urllib.request

TIMEOUT = float(os.environ.get("MIRAGE_LLM_TIMEOUT", "60"))


class LLMUnavailable(Exception):
    pass


def backend() -> str:
    return os.environ.get("MIRAGE_LLM", "none").lower()


def enabled() -> bool:
    return backend() in ("ollama", "anthropic")


def _post(url: str, payload: dict, headers: dict) -> dict:
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return json.loads(resp.read())
    except Exception as e:  # network, HTTP error, bad JSON: all mean "no LLM right now"
        raise LLMUnavailable(str(e)) from e


def complete(prompt: str, system: str = "", max_tokens: int = 1200) -> str:
    """Return the model's text answer. Raises LLMUnavailable if disabled or failing."""
    b = backend()
    if b == "ollama":
        url = os.environ.get("MIRAGE_OLLAMA_URL", "http://localhost:11434") + "/api/chat"
        out = _post(url, {
            "model": os.environ.get("MIRAGE_OLLAMA_MODEL", "qwen2.5:7b"),
            "stream": False,
            "options": {"temperature": 0.2},
            "messages": ([{"role": "system", "content": system}] if system else [])
            + [{"role": "user", "content": prompt}],
        }, {"Content-Type": "application/json"})
        return out["message"]["content"]
    if b == "anthropic":
        key = os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise LLMUnavailable("ANTHROPIC_API_KEY not set")
        out = _post("https://api.anthropic.com/v1/messages", {
            "model": os.environ.get("MIRAGE_ANTHROPIC_MODEL", "claude-sonnet-5-5"),
            "max_tokens": max_tokens,
            "system": system,
            "messages": [{"role": "user", "content": prompt}],
        }, {"Content-Type": "application/json", "x-api-key": key, "anthropic-version": "2023-06-01"})
        return "".join(block.get("text", "") for block in out.get("content", []))
    raise LLMUnavailable("MIRAGE_LLM is 'none'")


def complete_json(prompt: str, system: str = "", max_tokens: int = 1200):
    """Ask for JSON and parse the first JSON object/array in the answer. Raises LLMUnavailable."""
    text = complete(prompt, system, max_tokens)
    m = re.search(r"(\{.*\}|\[.*\])", text, re.S)
    if not m:
        raise LLMUnavailable("no JSON in answer")
    try:
        return json.loads(m.group(1))
    except json.JSONDecodeError as e:
        raise LLMUnavailable(f"bad JSON: {e}") from e
