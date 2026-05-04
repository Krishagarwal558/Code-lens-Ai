import os
from dotenv import load_dotenv

load_dotenv()


def _int(name, default):
    try:
        return int(os.getenv(name, default))
    except:
        return default


class Config:
    OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "phi")

    HOST = "0.0.0.0"
    PORT = 5000
    DEBUG = True

    CORS_ORIGINS = ["*"]

    GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")

    # 🔥 Reduce for speed
    MAX_FILE_BYTES = _int("MAX_FILE_BYTES", 150_000)
    MAX_FILES_PER_REPO = _int("MAX_FILES_PER_REPO", 5)