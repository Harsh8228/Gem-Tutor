import time
import shutil
from pathlib import Path
from typing import Any, Dict, List

from config import BASE_DIR, slugify, load_json, save_json


def ensure_student_dirs(student_id: str) -> Path:
    student_dir = BASE_DIR / student_id
    student_dir.mkdir(parents=True, exist_ok=True)
    (student_dir / "packs").mkdir(exist_ok=True)
    return student_dir

def rename_student(student_id: str, new_display_name: str) -> None:
    profile = load_student_profile(student_id)
    profile["display_name"] = new_display_name.strip()
    save_student_profile(student_id, profile)

def student_profile_path(student_id: str) -> Path:
    return ensure_student_dirs(student_id) / "profile.json"


def student_chat_path(student_id: str) -> Path:
    return ensure_student_dirs(student_id) / "chat_history.json"


def list_students() -> List[Dict[str, str]]:
    students = []
    for path in BASE_DIR.iterdir():
        if path.is_dir():
            profile_path = path / "profile.json"
            if profile_path.exists():
                try:
                    profile = load_json(profile_path, {})
                    students.append({"student_id": path.name, "display_name": profile.get("display_name", path.name)})
                except Exception:
                    students.append({"student_id": path.name, "display_name": path.name})
    students.sort(key=lambda x: x["display_name"].lower())
    return students


def create_student(display_name: str) -> str:
    student_id = slugify(display_name)
    base_id = student_id
    idx = 1
    while (BASE_DIR / student_id).exists():
        idx += 1
        student_id = f"{base_id}-{idx}"

    profile = {
        "student_id": student_id,
        "display_name": display_name,
        "personality": "",
        "learning_habits": "",
        "study_level": "",
        "strengths": [],
        "weaknesses": [],
        "education_progress": "",
        "recent_topics": [],
        "last_updated": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    chat = [{"role": "assistant", "content": f"Hi {display_name}! Tell me what you want to study today.", "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"), "mode": "chat"}]

    save_json(student_profile_path(student_id), profile)
    save_json(student_chat_path(student_id), chat)
    return student_id


def delete_student(student_id: str) -> None:
    student_dir = BASE_DIR / student_id
    if student_dir.exists() and student_dir.is_dir():
        shutil.rmtree(student_dir)


def load_student_profile(student_id: str) -> Dict[str, Any]:
    return load_json(
        student_profile_path(student_id),
        {
            "student_id": student_id,
            "display_name": student_id,
            "personality": "",
            "learning_habits": "",
            "study_level": "",
            "strengths": [],
            "weaknesses": [],
            "education_progress": "",
            "recent_topics": [],
            "last_updated": "",
        },
    )


def save_student_profile(student_id: str, profile: Dict[str, Any]) -> None:
    profile["last_updated"] = time.strftime("%Y-%m-%d %H:%M:%S")
    save_json(student_profile_path(student_id), profile)


def load_student_chat(student_id: str) -> List[Dict[str, Any]]:
    return load_json(student_chat_path(student_id), [])


def save_student_chat(student_id: str, chat: List[Dict[str, Any]]) -> None:
    save_json(student_chat_path(student_id), chat)


def append_chat_message(student_id: str, role: str, content: str, mode: str) -> None:
    chat = load_student_chat(student_id)
    chat.append({"role": role, "content": content, "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"), "mode": mode})
    save_student_chat(student_id, chat)
