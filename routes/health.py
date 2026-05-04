"""Health + Ollama reachability check."""
from flask import Blueprint, jsonify
import requests

from config import Config

health_bp = Blueprint("health", __name__)


@health_bp.get("/health")
def health():
    ollama_ok = False
    model_present = False
    error = None
    try:
        r = requests.get(f"{Config.OLLAMA_URL}/api/tags", timeout=5)
        ollama_ok = r.ok
        if r.ok:
            tags = r.json().get("models", [])
            model_present = any(
                m.get("name", "").startswith(Config.OLLAMA_MODEL) for m in tags
            )
    except Exception as e:  # noqa: BLE001
        error = str(e)

    return jsonify(
        {
            "status": "ok",
            "ollama": {
                "url": Config.OLLAMA_URL,
                "reachable": ollama_ok,
                "model": Config.OLLAMA_MODEL,
                "model_present": model_present,
                "error": error,
            },
        }
    )
