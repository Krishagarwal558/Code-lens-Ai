"""Analysis endpoints — raw code and GitHub repo ingestion."""

import logging
from flask import Blueprint, request, jsonify

from services.github_service import (
    GitHubError,
    parse_repo_url,
    list_python_files,
    fetch_file,
)
from services.ai_service import analyze_file, AIError
from parser.python_parser import parse_python
from config import Config

log = logging.getLogger(__name__)
analyze_bp = Blueprint("analyze", __name__)


# 🔹 Helper: analyze one file
def _analyze_one(filename: str, source: str, mode: str) -> dict:
    ast_ctx = parse_python(source)

    try:
        ai = analyze_file(filename, source, ast_ctx, mode=mode)

    except AIError as e:
        log.warning(f"AI failed for {filename}: {e}")

        ai = {
            "summary": f"AI analysis unavailable: {e}",
            "functions": [
                {
                    "name": f["name"],
                    "purpose": "",
                    "steps": [],
                    "issues": [],
                }
                for f in ast_ctx["functions"]
            ],
            "classes": [
                {
                    "name": c["name"],
                    "purpose": "",
                }
                for c in ast_ctx["classes"]
            ],
            "issues": [],
        }

    return {
        "file": filename,
        "ast": ast_ctx,
        "analysis": ai,
    }


# 🔹 Analyze raw code
@analyze_bp.post("/analyze/code")
def analyze_code():
    data = request.get_json(silent=True) or {}

    code = data.get("code", "")
    filename = data.get("filename") or "snippet.py"
    mode = data.get("mode", "advanced")

    if not isinstance(code, str) or not code.strip():
        return jsonify({"error": "empty_code"}), 400

    if len(code.encode("utf-8")) > Config.MAX_FILE_BYTES:
        return jsonify({
            "error": "file_too_large",
            "limit": Config.MAX_FILE_BYTES
        }), 413

    result = _analyze_one(filename, code, mode)

    return jsonify({
        "files": [result],
        "count": 1
    })


# 🔹 Analyze GitHub repo
@analyze_bp.post("/analyze/github")
def analyze_github():
    data = request.get_json(silent=True) or {}

    url = (data.get("url") or "").strip()
    mode = data.get("mode", "advanced")

    if not url:
        return jsonify({"error": "missing_url"}), 400

    try:
        owner, repo = parse_repo_url(url)
        files_meta = list_python_files(owner, repo)

    except GitHubError as e:
        return jsonify({
            "error": "github_error",
            "detail": str(e)
        }), e.status or 500

    if not files_meta:
        return jsonify({
            "files": [],
            "count": 0,
            "message": "No Python files found."
        })

    results = []
    skipped = []

    for meta in files_meta:
        print(f"🔍 Processing: {meta['path']}")

        try:
            source = fetch_file(meta["download_url"])

        except GitHubError as e:
            skipped.append({
                "file": meta["path"],
                "reason": str(e)
            })
            continue

        try:
            analyzed = _analyze_one(meta["path"], source, mode)
            results.append(analyzed)

        except Exception as e:
            log.exception(f"Failed analyzing {meta['path']}")
            skipped.append({
                "file": meta["path"],
                "reason": f"analysis_failed: {e}"
            })

    return jsonify({
        "owner": owner,
        "repo": repo,
        "files": results,
        "skipped": skipped,
        "count": len(results),
    })