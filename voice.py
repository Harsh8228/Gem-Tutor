import re
from pathlib import Path
from typing import List

try:
    from kokoro import KPipeline
    import soundfile as sf
    import numpy as np
    KOKORO_AVAILABLE = True
except Exception:
    KOKORO_AVAILABLE = False


def clean_markdown_for_tts(markdown_text: str) -> str:
    """Make Markdown study content easier for Kokoro to speak."""
    text = markdown_text
    text = re.sub(r"```.*?```", " ", text, flags=re.DOTALL)
    text = re.sub(r"<details>|</details>|<summary>|</summary>", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"^#{1,6}\s*", "", text, flags=re.MULTILINE)
    text = text.replace("---", " ")
    text = re.sub(r"[*_`>#|+\-]", " ", text)
    text = re.sub(r"\n{2,}", ". ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def split_text_for_tts(text: str, max_chars: int = 1200) -> List[str]:
    clean = re.sub(r"\s+", " ", text).strip()
    if not clean:
        return []
    sentences = re.split(r"(?<=[.!?])\s+", clean)
    chunks: List[str] = []
    current = ""
    for sentence in sentences:
        if len(current) + len(sentence) + 1 <= max_chars:
            current = f"{current} {sentence}".strip()
        else:
            if current:
                chunks.append(current)
            current = sentence
    if current:
        chunks.append(current)
    return chunks


def create_voice_lesson_audio(voice_text: str, wav_path: Path, lang_code: str = "b", voice: str = "bf_emma", speed: float = 0.92) -> bool:
    if not KOKORO_AVAILABLE or not voice_text.strip():
        return False
    try:
        pipeline = KPipeline(lang_code=lang_code)
        all_audio = []
        silence = np.zeros(int(24000 * 0.45), dtype=np.float32)
        for chunk in split_text_for_tts(voice_text):
            generator = pipeline(chunk, voice=voice, speed=speed)
            for _, _, audio in generator:
                all_audio.append(audio)
            all_audio.append(silence)
        if not all_audio:
            return False
        combined = np.concatenate(all_audio)
        sf.write(str(wav_path), combined, 24000)
        return True
    except Exception:
        return False
