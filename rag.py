import re
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

from config import PDF_CHUNK_SIZE, PDF_CHUNK_OVERLAP, MAX_RAG_CHUNKS, safe_filename, global_kb_dir, global_kb_index_path, load_json, save_json

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except Exception:
    PYMUPDF_AVAILABLE = False


def clean_text(text: str) -> str:
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_text_from_pdf(pdf_path: Path) -> str:
    if not PYMUPDF_AVAILABLE:
        raise RuntimeError("PyMuPDF is not installed. Install it with: pip install pymupdf")
    doc = fitz.open(str(pdf_path))
    parts = []
    for page_num, page in enumerate(doc, start=1):
        page_text = page.get_text("text")
        if page_text.strip():
            parts.append(f"\n\n[Page {page_num}]\n{page_text}")
    doc.close()
    return clean_text("\n".join(parts))


def chunk_text(text: str, chunk_size: int = PDF_CHUNK_SIZE, overlap: int = PDF_CHUNK_OVERLAP) -> List[str]:
    text = clean_text(text)
    if not text:
        return []
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(text):
            break
        start = max(0, end - overlap)
    return chunks


def load_rag_index() -> Dict[str, Any]:
    return load_json(global_kb_index_path(), {"documents": []})


def save_rag_index(index: Dict[str, Any]) -> None:
    save_json(global_kb_index_path(), index)


def add_pdf_to_rag(uploaded_file) -> Tuple[str, int]:
    kb_dir = global_kb_dir()
    safe_name = safe_filename(Path(uploaded_file.name).stem, fallback="uploaded-pdf")
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    pdf_path = kb_dir / f"{safe_name}-{timestamp}.pdf"
    pdf_path.write_bytes(uploaded_file.getbuffer())

    extracted_text = extract_text_from_pdf(pdf_path)
    chunks = chunk_text(extracted_text)

    doc_entry = {
        "doc_id": f"{safe_name}-{timestamp}",
        "file_name": uploaded_file.name,
        "saved_path": str(pdf_path),
        "uploaded_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "chunk_count": len(chunks),
        "chunks": [{"chunk_id": f"{safe_name}-{timestamp}-{i}", "text": chunk} for i, chunk in enumerate(chunks, start=1)],
    }
    index = load_rag_index()
    index.setdefault("documents", []).append(doc_entry)
    save_rag_index(index)
    return uploaded_file.name, len(chunks)


def delete_kb_document(doc_id: str) -> None:
    index = load_rag_index()
    kept_docs = []
    for doc in index.get("documents", []):
        if doc.get("doc_id") == doc_id:
            saved_path = Path(doc.get("saved_path", ""))
            if saved_path.exists():
                saved_path.unlink()
        else:
            kept_docs.append(doc)
    index["documents"] = kept_docs
    save_rag_index(index)


def tokenize(text: str) -> List[str]:
    return [t for t in re.findall(r"[a-zA-Z0-9]+", text.lower()) if len(t) > 2]


def retrieve_relevant_pdf_context(query: str, top_k: int = MAX_RAG_CHUNKS) -> List[Dict[str, Any]]:
    index = load_rag_index()
    query_terms = tokenize(query)
    if not query_terms:
        return []
    query_term_set = set(query_terms)
    scored_chunks = []
    for doc in index.get("documents", []):
        for chunk in doc.get("chunks", []):
            text = chunk.get("text", "")
            chunk_terms = tokenize(text)
            if not chunk_terms:
                continue
            overlap = query_term_set.intersection(set(chunk_terms))
            if not overlap:
                continue
            tf_boost = sum(chunk_terms.count(term) for term in overlap)
            score = len(overlap) * 2.0 + tf_boost * 0.25
            scored_chunks.append({"score": score, "file_name": doc.get("file_name", "Unknown PDF"), "doc_id": doc.get("doc_id", ""), "chunk_id": chunk.get("chunk_id", ""), "text": text})
    scored_chunks.sort(key=lambda item: item["score"], reverse=True)
    return scored_chunks[:top_k]


def format_rag_context(chunks: List[Dict[str, Any]]) -> str:
    if not chunks:
        return "No relevant PDF context was retrieved."
    blocks = []
    for i, chunk in enumerate(chunks, start=1):
        blocks.append(
            f"[PDF Context {i}]\n"
            f"Source file: {chunk.get('file_name', 'Unknown PDF')}\n"
            f"Chunk id: {chunk.get('chunk_id', '')}\n"
            f"Content:\n{chunk.get('text', '')}"
        )
    return "\n\n---\n\n".join(blocks)
