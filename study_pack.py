import re
import time
from typing import Any, Dict

from config import safe_filename
from students import ensure_student_dirs
from voice import clean_markdown_for_tts, create_voice_lesson_audio


def remove_emojis(text: str) -> str:
    emoji_pattern = re.compile(
        "["
        "\U0001F1E6-\U0001F1FF"
        "\U0001F300-\U0001F5FF"
        "\U0001F600-\U0001F64F"
        "\U0001F680-\U0001F6FF"
        "\U0001F700-\U0001F77F"
        "\U0001F780-\U0001F7FF"
        "\U0001F800-\U0001F8FF"
        "\U0001F900-\U0001F9FF"
        "\U0001FA00-\U0001FA6F"
        "\U0001FA70-\U0001FAFF"
        "\u2600-\u26FF"
        "\u2700-\u27BF"
        "]+",
        flags=re.UNICODE,
    )
    text = emoji_pattern.sub("", text)
    text = text.replace("✅", "").replace("❌", "").replace("✨", "")
    return text


def make_markdown_voice_friendly(markdown_text: str) -> str:
    text = remove_emojis(markdown_text)
    lines = text.splitlines()
    converted = []
    top_counter = 0
    sub_counter = 0
    in_code = False
    for raw_line in lines:
        stripped = raw_line.strip()
        if stripped.startswith("```"):
            in_code = not in_code
            converted.append(raw_line.rstrip())
            continue
        if in_code:
            converted.append(raw_line.rstrip())
            continue
        top_match = re.match(r"^[-*+]\s+(.+)$", raw_line)
        sub_match = re.match(r"^(\s{2,})[-*+]\s+(.+)$", raw_line)
        if sub_match:
            sub_counter += 1
            letter = chr(ord("a") + ((sub_counter - 1) % 26))
            converted.append(f"   {letter}. {sub_match.group(2).strip()}")
            continue
        if top_match:
            top_counter += 1
            sub_counter = 0
            converted.append(f"{top_counter}. {top_match.group(1).strip()}")
            continue
        if stripped == "" or stripped.startswith("#"):
            top_counter = 0
            sub_counter = 0
        converted.append(raw_line.rstrip())
    return "\n".join(converted).strip()


def normalize_ascii_diagram(diagram: str) -> str:
    if not diagram.strip():
        return "Start\n  |\n  v\nLearn the main idea\n  |\n  v\nPractise with examples\n  |\n  v\nCheck understanding"
    diagram = diagram.replace("```", "")
    lines = [line.rstrip() for line in diagram.splitlines()]
    return "\n".join(lines).strip()


def remove_flow_diagram_for_voice(markdown_text: str) -> str:
    pattern = r"\n---\n\n## Flow Diagram\n\n```text\n.*?\n```\n\n---\n"
    text = re.sub(pattern, "\n\n---\n", markdown_text, flags=re.DOTALL)
    fallback_pattern = r"\n## Flow Diagram\n.*?(?=\n---\n\n## |\n## |\Z)"
    text = re.sub(fallback_pattern, "\n", text, flags=re.DOTALL)
    return text.strip() + "\n"


def build_combined_markdown(pack: Dict[str, Any]) -> str:
    title = remove_emojis(pack.get("title", "Study Pack")).strip() or "Study Pack"
    objectives = "\n".join([f"{i}. {remove_emojis(str(obj)).strip()}" for i, obj in enumerate(pack.get("learning_objectives", []), start=1)])
    study_material = make_markdown_voice_friendly(pack.get("study_material_markdown", ""))
    ascii_diagram = normalize_ascii_diagram(remove_emojis(pack.get("ascii_flow_diagram", "")))
    quiz = "\n\n".join(
        [
            f"### Question {i}\n\nQuestion: {make_markdown_voice_friendly(qa.get('question', ''))}\n\nAnswer: {make_markdown_voice_friendly(qa.get('answer', ''))}"
            for i, qa in enumerate(pack.get("quiz_questions", []), start=1)
        ]
    )
    return f"""# {title}

A friendly lesson pack with clear explanations, an offline-safe ASCII flow diagram, quiz practice, and an optional matching voice note.

---

## Learning Objectives

{objectives}

---

## Study Material

{study_material}

---

## Flow Diagram

```text
{ascii_diagram}
```

---

## Quick Quiz

{quiz}

---

## Final Recap

1. Start with the main idea.
2. Follow the ASCII flow diagram from beginning to end.
3. Test yourself with the quiz.
4. Use the voice note, when generated, to listen to this study pack without the flow diagram section.
""".strip() + "\n"


def save_study_pack(student_id: str, topic_hint: str, pack: Dict[str, Any], create_voice_note: bool = False) -> Dict[str, str]:
    packs_dir = ensure_student_dirs(student_id) / "packs"
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    pack_name = f"{safe_filename(topic_hint)}-{timestamp}"
    pack_dir = packs_dir / pack_name
    pack_dir.mkdir(parents=True, exist_ok=True)
    md_path = pack_dir / "complete_study_pack.md"
    voice_audio_path = pack_dir / "voice_note.wav"
    combined_markdown = build_combined_markdown(pack)
    md_path.write_text(combined_markdown, encoding="utf-8")
    audio_created = False
    if create_voice_note:
        markdown_without_diagram = remove_flow_diagram_for_voice(combined_markdown)
        voice_text = clean_markdown_for_tts(markdown_without_diagram)
        audio_created = create_voice_lesson_audio(voice_text, voice_audio_path)
        if not audio_created and voice_audio_path.exists():
            voice_audio_path.unlink()
    return {"folder": str(pack_dir), "markdown": str(md_path), "voice_note": str(voice_audio_path) if audio_created else ""}
