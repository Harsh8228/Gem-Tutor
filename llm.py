import re
import json
from typing import Any, Dict, List, Optional

import requests

from config import OPENROUTER_URL, DEFAULT_MODEL, API_KEY
from students import load_student_profile, load_student_chat, save_student_profile


def call_openrouter(messages: List[Dict[str, str]], model: str = DEFAULT_MODEL, temperature: float = 0.5, max_tokens: Optional[int] = None) -> str:
    if not API_KEY:
        raise ValueError("OPENROUTER_API_KEY is not set in your environment.")
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:8501",
        "X-Title": "Gem Tutor",
    }
    payload = {"model": model, "messages": messages, "temperature": temperature}
    if max_tokens is not None:
        payload["max_tokens"] = max_tokens
    response = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=180)
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


def extract_json_block(text: str) -> dict:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    fence_match = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence_match:
        return json.loads(fence_match.group(1))
    generic_fence = re.search(r"```\s*(\{.*?\})\s*```", text, re.DOTALL)
    if generic_fence:
        return json.loads(generic_fence.group(1))
    brace_match = re.search(r"(\{.*\})", text, re.DOTALL)
    if brace_match:
        return json.loads(brace_match.group(1))
    raise ValueError("Could not parse JSON from model output.")


def build_compact_context(student_profile: Dict[str, Any], full_chat: List[Dict[str, Any]], latest_user_message: str, mode: str, pdf_context: str = "", lesson_plan: str = "") -> List[Dict[str, str]]:
    recent_messages = full_chat[-8:] if len(full_chat) > 8 else full_chat
    profile_summary = {
        "display_name": student_profile.get("display_name", ""),
        "personality": student_profile.get("personality", ""),
        "learning_habits": student_profile.get("learning_habits", ""),
        "study_level": student_profile.get("study_level", ""),
        "strengths": student_profile.get("strengths", []),
        "weaknesses": student_profile.get("weaknesses", []),
        "education_progress": student_profile.get("education_progress", ""),
        "recent_topics": student_profile.get("recent_topics", []),
    }
    system_prompt = f"""
You are a helpful educational tutor.

You are speaking with this student profile:
{json.dumps(profile_summary, ensure_ascii=False, indent=2)}

Operating mode: {mode}

Retrieved PDF context for this request:
{pdf_context if pdf_context else "No uploaded PDF context was provided."}

Lesson plan to follow, if provided:
{lesson_plan if lesson_plan else "No separate lesson plan was provided."}

Rules:
1. If mode is "chat", answer normally as a tutor.
2. If mode is "study_pack", produce a full study pack in JSON only.
3. Be tailored to the student profile.
4. Use the profile memory instead of relying on long chat history.
5. If PDF context is provided, ground the lesson in that information where relevant.
6. If the PDF context is insufficient, say so briefly inside the study material and continue with general tutoring knowledge.
"""
    if mode == "study_pack":
        system_prompt += """
For study_pack mode, return ONLY valid JSON with this exact structure:
{
  "title": "string",
  "learning_objectives": ["string", "string", "string"],
  "study_material_markdown": "string",
  "ascii_flow_diagram": "string",
  "quiz_questions": [
    {"question": "string", "answer": "string"}
  ]
}

Rules for study_pack:
- Write study_material_markdown like a warm, engaging human teacher is sitting with the student and explaining the topic step by step.
- Make the lesson feel alive: use friendly explanations, mini-stories, analogies, worked examples, check-in questions, quick recap boxes, and common mistake warnings.
- Avoid dry textbook paragraphs. Prefer short sections, direct address, and practical intuition.
- Do not use emojis anywhere. This content may be converted into a voice note, and emojis are read aloud awkwardly.
- Use Markdown headings and clear voice-friendly formatting.
- For lists, use numbered lists for main points: 1., 2., 3.
- For subpoints, use lettered lists: a., b., c.
- Do not use unordered bullet points such as hyphens or asterisks unless they are part of an equation or plain text example.
- The study_material_markdown should already feel polished and student-friendly.
- If PDF context is provided, weave it naturally into the lesson and do not contradict it.
- ascii_flow_diagram must be a clean plain-text ASCII flow diagram only.
- Do not use Mermaid, HTML, SVG, PNG, JavaScript, or image syntax.
- The ASCII diagram should work inside any Markdown viewer and should summarize the learning flow clearly.
- Use simple characters only, such as |, v, +, -, >, and boxes made with lines.
- quiz_questions should test understanding and include clear answers.
- Return JSON only. Do not include p5.js, JavaScript, HTML, or extra commentary.
"""
    msgs = [{"role": "system", "content": system_prompt.strip()}]
    for msg in recent_messages:
        if msg["role"] in ("user", "assistant"):
            msgs.append({"role": msg["role"], "content": msg["content"]})
    msgs.append({"role": "user", "content": latest_user_message})
    return msgs


def build_lesson_plan_prompt(student_profile: Dict[str, Any], latest_user_message: str, pdf_context: str) -> List[Dict[str, str]]:
    profile_summary = {
        "display_name": student_profile.get("display_name", ""),
        "study_level": student_profile.get("study_level", ""),
        "strengths": student_profile.get("strengths", []),
        "weaknesses": student_profile.get("weaknesses", []),
        "learning_habits": student_profile.get("learning_habits", ""),
    }
    system = """
You are planning an engaging study pack for a student.
Return a concise teaching plan only. Do not return JSON.
The plan should include:
1. the best teaching order,
2. what PDF facts to use if provided,
3. one analogy,
4. one worked example idea,
5. quiz focus areas,
6. how to make the voice lesson accessible for blind students.
"""
    user = f"""
Student profile:
{json.dumps(profile_summary, ensure_ascii=False, indent=2)}

Student request:
{latest_user_message}

Relevant PDF context:
{pdf_context}

Create the teaching plan.
"""
    return [{"role": "system", "content": system.strip()}, {"role": "user", "content": user.strip()}]


def build_profile_update_prompt(current_profile: Dict[str, Any], recent_chat: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    chat_text = "\n".join([f"{m['role'].upper()}: {m['content']}" for m in recent_chat[-10:]])
    system = """
You are updating a compact student memory profile for an educational app.

Return ONLY valid JSON with this exact structure:
{
  "personality": "string",
  "learning_habits": "string",
  "study_level": "string",
  "strengths": ["string"],
  "weaknesses": ["string"],
  "education_progress": "string",
  "recent_topics": ["string"]
}

Rules:
1. Be brief and cumulative.
2. Only include things reasonably supported by the chat.
3. Preserve useful long-term traits and progress.
4. Do not invent personal details.
"""
    user = f"""
Current student profile:
{json.dumps(current_profile, ensure_ascii=False, indent=2)}

Recent chat:
{chat_text}

Update the student profile memory.
"""
    return [{"role": "system", "content": system.strip()}, {"role": "user", "content": user.strip()}]


def update_student_memory(student_id: str) -> None:
    profile = load_student_profile(student_id)
    chat = load_student_chat(student_id)
    if len(chat) < 2:
        return
    try:
        messages = build_profile_update_prompt(profile, chat)
        raw = call_openrouter(messages, temperature=0.2, max_tokens=800)
        updated = extract_json_block(raw)
        profile["personality"] = updated.get("personality", profile.get("personality", ""))
        profile["learning_habits"] = updated.get("learning_habits", profile.get("learning_habits", ""))
        profile["study_level"] = updated.get("study_level", profile.get("study_level", ""))
        profile["strengths"] = updated.get("strengths", profile.get("strengths", []))
        profile["weaknesses"] = updated.get("weaknesses", profile.get("weaknesses", []))
        profile["education_progress"] = updated.get("education_progress", profile.get("education_progress", ""))
        profile["recent_topics"] = updated.get("recent_topics", profile.get("recent_topics", []))
        save_student_profile(student_id, profile)
    except Exception:
        pass
