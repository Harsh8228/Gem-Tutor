import os
import re
import json
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv()

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "google/gemma-4-31b-it"
API_KEY = os.getenv("OPENROUTER_API_KEY", "")

BASE_DIR = Path("student_data")
BASE_DIR.mkdir(exist_ok=True)

GLOBAL_KB_DIR = BASE_DIR / "global_knowledge_base"
GLOBAL_KB_DIR.mkdir(parents=True, exist_ok=True)
GLOBAL_KB_INDEX_PATH = GLOBAL_KB_DIR / "rag_index.json"

PDF_CHUNK_SIZE = 1300
PDF_CHUNK_OVERLAP = 220
MAX_RAG_CHUNKS = 5


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-") or "student"


def safe_filename(text: str, fallback: str = "study-pack") -> str:
    value = slugify(text)
    return value if value else fallback


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def save_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def global_kb_dir() -> Path:
    GLOBAL_KB_DIR.mkdir(parents=True, exist_ok=True)
    return GLOBAL_KB_DIR


def global_kb_index_path() -> Path:
    global_kb_dir()
    return GLOBAL_KB_INDEX_PATH


def read_file_bytes(path_text: str) -> bytes:
    return Path(path_text).read_bytes()
