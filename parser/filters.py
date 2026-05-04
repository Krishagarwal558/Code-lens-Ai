"""File filtering helpers (kept separate so the policy is easy to tweak)."""
SKIP_SEGMENTS = (
    "/test", "tests/", "__pycache__", "/.venv", "site-packages",
    "/migrations/", "/build/", "/dist/",
)


def is_useful_python_path(path: str) -> bool:
    if not path.endswith(".py"):
        return False
    lower = path.lower()
    return not any(seg in lower for seg in SKIP_SEGMENTS)
