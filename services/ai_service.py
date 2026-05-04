"""Ollama wrapper — strict JSON output, one call per file."""
import json
import logging
import re
from typing import Any
import requests

from config import Config

log = logging.getLogger(__name__)


class AIError(Exception):
    pass


SYSTEM_PROMPT = """You are a senior code analyst. You will receive a Python source file plus a pre-extracted AST context (functions, classes, imports).

You MUST respond with ONLY valid JSON matching this exact schema. No markdown, no prose, no code fences:

{
  "summary": "string",
  "functions": [
    {"name": "string", "purpose": "string", "steps": ["string"], "issues": ["string"]}
  ],
  "classes": [
    {"name": "string", "purpose": "string"}
  ],
  "issues": ["string"]
}

Rules:
- Use the provided AST as the ground truth for function/class names.
- Be concise, correct, and concrete. No greetings, no explanations outside JSON.
- If nothing exists for a section, return an empty array.
"""


def _build_user_prompt(filename: str, source: str, ast_ctx: dict, mode: str) -> str:
    style = (
        "Use beginner-friendly language. Avoid jargon."
        if mode == "beginner"
        else "Use precise technical language and step-level reasoning."
    )
    # Trim very long sources — AST already gives structure.
    src = source if len(source) <= 12_000 else source[:12_000] + "\n# ...truncated...\n"
    return (
        f"FILE: {filename}\nMODE: {mode}\nSTYLE: {style}\n\n"
        f"AST_CONTEXT:\n{json.dumps(ast_ctx, indent=2)}\n\n"
        f"SOURCE:\n```python\n{src}\n```\n\n"
        "Respond with ONLY the JSON object."
    )


_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


def _extract_json(text: str) -> dict:
    """Best-effort JSON extraction from a possibly-noisy LLM response."""
    if not text:
        raise AIError("empty AI response")

    cleaned = _FENCE_RE.sub("", text).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Find the largest {...} block.
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = cleaned[start : end + 1]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError as e:
            raise AIError(f"invalid JSON from model: {e}") from e
    raise AIError("no JSON object found in AI response")


def _normalize(obj: Any) -> dict:
    """Ensure response matches the contract; fill missing keys safely."""
    if not isinstance(obj, dict):
        raise AIError("AI response is not a JSON object")

    summary = obj.get("summary", "")
    if not isinstance(summary, str):
        summary = str(summary)

    def _str_list(v):
        if not isinstance(v, list):
            return []
        return [str(x) for x in v if x is not None]

    functions = []
    for f in obj.get("functions", []) or []:
        if not isinstance(f, dict):
            continue
        functions.append(
            {
                "name": str(f.get("name", "")),
                "purpose": str(f.get("purpose", "")),
                "steps": _str_list(f.get("steps")),
                "issues": _str_list(f.get("issues")),
            }
        )

    classes = []
    for c in obj.get("classes", []) or []:
        if not isinstance(c, dict):
            continue
        classes.append(
            {"name": str(c.get("name", "")), "purpose": str(c.get("purpose", ""))}
        )

    return {
        "summary": summary,
        "functions": functions,
        "classes": classes,
        "issues": _str_list(obj.get("issues")),
    }


def analyze_file(filename: str, source: str, ast_ctx: dict, mode: str = "advanced") -> dict:
    """Single Ollama call — returns strict JSON dict matching the contract."""
    payload = {
        "model": Config.OLLAMA_MODEL,
        "stream": False,
        "format": "json",  # Ollama-native JSON mode
        "options": {"temperature": 0.2},
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": _build_user_prompt(filename, source, ast_ctx, mode)},
        ],
    }

    try:
        r = requests.post(
            f"{Config.OLLAMA_URL}/api/chat",
            json=payload,
            timeout=Config.OLLAMA_TIMEOUT,
        )
    except requests.exceptions.ConnectionError as e:
        raise AIError(f"cannot reach Ollama at {Config.OLLAMA_URL}") from e
    except requests.exceptions.Timeout as e:
        raise AIError("Ollama request timed out") from e

    if r.status_code == 404:
        raise AIError(f"model '{Config.OLLAMA_MODEL}' not found on Ollama")
    if not r.ok:
        raise AIError(f"Ollama error {r.status_code}: {r.text[:200]}")

    try:
        body = r.json()
    except ValueError as e:
        raise AIError("Ollama returned non-JSON envelope") from e

    content = (body.get("message") or {}).get("content", "")
    parsed = _extract_json(content)
    return _normalize(parsed)
