"""GitHub fetch + filter pipeline using the public REST API."""
import re
from typing import Optional
import requests

from config import Config

GITHUB_API = "https://api.github.com"


class GitHubError(Exception):
    def __init__(self, message: str, status: Optional[int] = None):
        super().__init__(message)
        self.status = status


_URL_RE = re.compile(
    r"^(?:https?://)?(?:www\.)?github\.com[:/]([^/]+)/([^/#?]+?)(?:\.git)?(?:[/#?].*)?$",
    re.IGNORECASE,
)


def parse_repo_url(url: str) -> tuple[str, str]:
    m = _URL_RE.match(url.strip())
    if not m:
        raise GitHubError("Invalid GitHub repository URL", status=400)
    return m.group(1), m.group(2)


def _headers() -> dict:
    h = {"Accept": "application/vnd.github+json", "User-Agent": "codelens-ai"}
    if Config.GITHUB_TOKEN:
        h["Authorization"] = f"Bearer {Config.GITHUB_TOKEN}"
    return h


def _get(url: str, **kw) -> requests.Response:
    r = requests.get(url, headers=_headers(), timeout=20, **kw)
    if r.status_code == 403 and "rate limit" in r.text.lower():
        raise GitHubError("GitHub rate limit exceeded", status=429)
    if r.status_code == 404:
        raise GitHubError("Repository or resource not found", status=404)
    if r.status_code == 401:
        raise GitHubError("GitHub authorization failed", status=401)
    if not r.ok:
        raise GitHubError(f"GitHub error {r.status_code}", status=r.status_code)
    return r


def _default_branch(owner: str, repo: str) -> str:
    r = _get(f"{GITHUB_API}/repos/{owner}/{repo}")
    return r.json().get("default_branch", "main")


def list_python_files(owner: str, repo: str) -> list[dict]:
    """Return up to MAX_FILES_PER_REPO .py files <= MAX_FILE_BYTES.

    Uses git tree (recursive) — single API call for the whole repo.
    """
    branch = _default_branch(owner, repo)
    r = _get(f"{GITHUB_API}/repos/{owner}/{repo}/git/trees/{branch}?recursive=1")
    data = r.json()
    if data.get("truncated"):
        # Still proceed — we only need a handful of files.
        pass

    py_files = []
    for node in data.get("tree", []):
        if node.get("type") != "blob":
            continue
        path = node.get("path", "")
        if not path.endswith(".py"):
            continue
        size = node.get("size", 0)
        if size > Config.MAX_FILE_BYTES:
            continue
        # Skip noisy paths
        lower = path.lower()
        if any(seg in lower for seg in ("/test", "tests/", "__pycache__", "/.venv", "site-packages")):
            continue
        py_files.append(
            {
                "path": path,
                "size": size,
                "download_url": f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}",
            }
        )

    # Prefer smaller, top-level files first for a useful overview.
    py_files.sort(key=lambda f: (f["path"].count("/"), f["size"]))
    return py_files[: Config.MAX_FILES_PER_REPO]


def fetch_file(raw_url: str) -> str:
    r = requests.get(raw_url, headers=_headers(), timeout=20)
    if not r.ok:
        raise GitHubError(f"Failed to fetch file ({r.status_code})", status=r.status_code)
    return r.text
