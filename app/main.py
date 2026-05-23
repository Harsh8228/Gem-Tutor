import streamlit as st

from config import API_KEY, DEFAULT_MODEL, read_file_bytes
from students import list_students, create_student, delete_student, load_student_profile, load_student_chat, append_chat_message, rename_student
from rag import PYMUPDF_AVAILABLE, add_pdf_to_rag, delete_kb_document, load_rag_index, retrieve_relevant_pdf_context, format_rag_context
from llm import call_openrouter, extract_json_block, build_compact_context, build_lesson_plan_prompt, update_student_memory
from study_pack import remove_emojis, save_study_pack

st.set_page_config(page_title="Gem Tutor", page_icon="📘", layout="wide")

st.markdown(
    """
    <style>
    .main .block-container { padding-top: 5.2rem; padding-bottom: 11rem; }
    .small-note { opacity: 0.7; font-size: 0.9rem; }
    div[data-testid="stButton"] button[kind="secondary"] { border-radius: 999px; }
    div[data-testid="stButton"] button { min-height: 42px; }
    .st-key-bottom_pack_bar {
    position: fixed;
    left: 60%;
    transform: translateX(-50%);
    bottom: 0rem;
    z-index: 999998;

    width: min(760px, calc(100vw - 2rem));

    padding: 0.55rem 1.1rem 0.45rem 1.1rem;
    border: 1px solid rgba(128, 128, 128, 0.25);
    border-radius: 999px;
    background: rgba(255, 255, 255, 0.96);
    box-shadow: 0 8px 26px rgba(0, 0, 0, 0.12);
    backdrop-filter: blur(10px);
    }
    .st-key-bottom_pack_bar [data-testid="stHorizontalBlock"] {
    gap: 1.4rem;
    align-items: center;
    }

    .fixed-app-header {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    z-index: 999997;
    padding: 0.35rem 2rem 0.01rem 2rem;
    background: rgba(14, 17, 23, 0.96);
    border-bottom: 1px solid rgba(128, 128, 128, 0.25);
    backdrop-filter: blur(10px);

    display: flex;
    justify-content: center;
    align-items: center;
    }

    .fixed-app-header h1 {
        margin: 0;
        font-size: 2.5rem;
        font-weight: 750;
        line-height: 1.2;
        text-align: center;
    }

    .fixed-app-header .blue-g {
        color: #4285f4;
    }

    .st-key-bottom_pack_bar label {
        margin-bottom: 0 !important;
        font-weight: 600;
        white-space: nowrap;
    }

    .st-key-bottom_pack_bar [data-testid="stToggle"] {
        min-width: max-content;
    }
    @media (prefers-color-scheme: dark) {
        .st-key-bottom_pack_bar { background: rgba(20, 20, 20, 0.96); border: 1px solid rgba(255, 255, 255, 0.18); }
    }
    .st-key-bottom_pack_bar label { margin-bottom: 0 !important; font-weight: 600; white-space: nowrap; }
    .st-key-bottom_pack_bar [data-testid="stWidgetLabel"] { min-height: 0 !important; }
    .st-key-bottom_pack_bar div[data-testid="stToggle"] { margin-bottom: 0 !important; }
    div[data-testid="stChatInput"] { z-index: 999999; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="fixed-app-header">
        <h1><span class="blue-g">G</span>em Tutor</h1>
    </div>
    """,
    unsafe_allow_html=True,
)

if "selected_student_id" not in st.session_state:
    all_students = list_students()
    st.session_state.selected_student_id = all_students[0]["student_id"] if all_students else create_student("Student 1")
if "last_pack" not in st.session_state:
    st.session_state.last_pack = None
if "last_saved_files" not in st.session_state:
    st.session_state.last_saved_files = None
if "confirm_delete_student_id" not in st.session_state:
    st.session_state.confirm_delete_student_id = None

with st.sidebar:
    st.header("Knowledge Base")
    st.caption("PDFs uploaded here are global and available to every student.")
    kb_action = st.selectbox("PDF options", options=["Upload PDF", "View uploaded PDFs"], index=0)

    if kb_action == "Upload PDF":
        uploaded_pdfs = st.file_uploader(
            "Upload lesson source PDFs",
            type=["pdf"],
            accept_multiple_files=True,
            help="Uploaded PDFs are saved once globally and used as a simple local RAG knowledge base for every student.",
        )
        if uploaded_pdfs and st.button("Add PDFs to RAG", use_container_width=True):
            if not PYMUPDF_AVAILABLE:
                st.error("PyMuPDF is not installed. Run: pip install pymupdf")
            else:
                added = []
                for uploaded_pdf in uploaded_pdfs:
                    file_name, chunk_count = add_pdf_to_rag(uploaded_pdf)
                    added.append(f"{file_name} ({chunk_count} chunks)")
                st.success("Added: " + ", ".join(added))
                st.rerun()
    else:
        kb_index = load_rag_index()
        docs = kb_index.get("documents", [])
        if not docs:
            st.info("No PDFs uploaded globally yet.")
        else:
            doc_labels = [f"{doc.get('file_name', 'PDF')} - {doc.get('chunk_count', 0)} chunks" for doc in docs]
            selected_doc_label = st.selectbox("Uploaded PDFs", doc_labels)
            selected_doc = docs[doc_labels.index(selected_doc_label)]
            st.caption(f"Uploaded: {selected_doc.get('uploaded_at', '')}")
            if st.button("Delete selected PDF", use_container_width=True):
                delete_kb_document(selected_doc.get("doc_id", ""))
                st.rerun()

    st.divider()
    st.header("Students")
    new_student_name = st.text_input("Create new student", placeholder="e.g. Harsh")
    if st.button("Add Student", use_container_width=True):
        if new_student_name.strip():
            st.session_state.selected_student_id = create_student(new_student_name.strip())
            st.session_state.last_pack = None
            st.session_state.last_saved_files = None
            st.rerun()

    st.divider()
    students = list_students()
    if students:
        student_labels = [s["display_name"] for s in students]
        student_map = {s["display_name"]: s["student_id"] for s in students}
        current_display = next((s["display_name"] for s in students if s["student_id"] == st.session_state.selected_student_id), student_labels[0])
        selected_display = st.radio("Switch student", options=student_labels, index=student_labels.index(current_display), label_visibility="collapsed")
        previous_student_id = st.session_state.selected_student_id
        st.session_state.selected_student_id = student_map[selected_display]
        if previous_student_id != st.session_state.selected_student_id:
            st.session_state.last_pack = None
            st.session_state.last_saved_files = None
            st.rerun()

    st.divider()
    profile = load_student_profile(st.session_state.selected_student_id)
    st.subheader("Rename Student")

    new_display_name = st.text_input(
        "Student name",
        value=profile.get("display_name", ""),
        key=f"rename_student_{st.session_state.selected_student_id}",
    )

    if st.button("Save student name", use_container_width=True):
        if new_display_name.strip():
            rename_student(st.session_state.selected_student_id, new_display_name.strip())
            st.success("Student name updated.")
            st.rerun()
        else:
            st.warning("Student name cannot be empty.")

    st.divider()
    
    st.subheader("Student Memory")
    st.write(f"**Name:** {profile.get('display_name', '')}")
    if profile.get("study_level"):
        st.write(f"**Level:** {profile['study_level']}")
    if profile.get("personality"):
        st.write(f"**Personality:** {profile['personality']}")
    if profile.get("learning_habits"):
        st.write(f"**Learning habits:** {profile['learning_habits']}")
    if profile.get("education_progress"):
        st.write(f"**Progress:** {profile['education_progress']}")

    st.divider()
    current_student_id = st.session_state.selected_student_id
    current_profile = load_student_profile(current_student_id)
    if st.session_state.confirm_delete_student_id == current_student_id:
        st.warning(f"Delete {current_profile.get('display_name', current_student_id)} permanently?")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Yes, delete", use_container_width=True):
                delete_student(current_student_id)
                st.session_state.confirm_delete_student_id = None
                remaining = list_students()
                st.session_state.selected_student_id = remaining[0]["student_id"] if remaining else create_student("Student 1")
                st.session_state.last_pack = None
                st.session_state.last_saved_files = None
                st.rerun()
        with c2:
            if st.button("Cancel", use_container_width=True):
                st.session_state.confirm_delete_student_id = None
                st.rerun()
    else:
        if st.button("Delete this student", use_container_width=True):
            st.session_state.confirm_delete_student_id = current_student_id
            st.rerun()

student_id = st.session_state.selected_student_id
profile = load_student_profile(student_id)
chat_history = load_student_chat(student_id)
kb_index = load_rag_index()

st.subheader(f"Chat — {profile.get('display_name', student_id)}")
if kb_index.get("documents"):
    st.caption(f"PDF RAG enabled: {len(kb_index.get('documents', []))} global uploaded PDF(s) available to all students.")
else:
    st.caption("PDF RAG: no global PDFs uploaded yet. Upload PDFs from the sidebar to ground lessons in custom material for all students.")

with st.container():
    for msg in chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("mode") == "study_pack" and msg["role"] == "assistant":
                st.caption("Generated as study pack")

with st.container(key="bottom_pack_bar"):
    toggle_col1, toggle_col2 = st.columns(2)
    with toggle_col1:
        study_pack_mode = st.toggle("Study pack", value=st.session_state.get(f"pack_mode_{student_id}", False), key=f"pack_mode_{student_id}", help="Turn this on before sending a message to generate a complete study pack file.")
    with toggle_col2:
        voice_lesson_mode = st.toggle("Voice lesson with study pack", value=st.session_state.get(f"voice_mode_{student_id}", False), key=f"voice_mode_{student_id}", help="Turn this on with Study pack to create a Kokoro voice note from the final Markdown content.")

user_text = st.chat_input("Ask a question or request study material...", key=f"chat_input_{student_id}")
send = user_text is not None and user_text.strip() != ""

if send:
    if not API_KEY:
        st.error("OPENROUTER_API_KEY is not set in your environment.")
    else:
        mode = "study_pack" if study_pack_mode else "chat"
        user_text_clean = user_text.strip()
        append_chat_message(student_id, "user", user_text_clean, mode)
        with st.chat_message("user"):
            st.markdown(user_text_clean)
        try:
            chat_history = load_student_chat(student_id)
            profile = load_student_profile(student_id)
            if mode == "study_pack":
                with st.chat_message("assistant"):
                    status = st.status("Now retrieving information from PDFs...", expanded=True)
                    status.write("Searching the global uploaded PDFs for relevant context.")
                    retrieved_chunks = retrieve_relevant_pdf_context(user_text_clean)
                    pdf_context = format_rag_context(retrieved_chunks)
                    if retrieved_chunks:
                        status.write(f"Retrieved {len(retrieved_chunks)} relevant PDF chunk(s).")
                    else:
                        status.write("No matching PDF chunks found. The pack will use the student profile and general tutoring knowledge.")
                    status.update(label="Now making a lesson plan...", state="running", expanded=True)
                    lesson_plan = call_openrouter(build_lesson_plan_prompt(profile, user_text_clean, pdf_context), model=DEFAULT_MODEL, temperature=0.35, max_tokens=1200)
                    status.write("Lesson plan ready.")
                    status.update(label="Now generating the study pack...", state="running", expanded=True)
                    messages = build_compact_context(profile, chat_history, user_text_clean, mode, pdf_context=pdf_context, lesson_plan=lesson_plan)
                    raw_reply = call_openrouter(messages=messages, model=DEFAULT_MODEL, temperature=0.4, max_tokens=7000)
                    status.write("Study pack text generated.")
                    status.update(label="Now creating the Markdown study pack and voice note..." if voice_lesson_mode else "Now creating the Markdown study pack...", state="running", expanded=True)
                    pack = extract_json_block(raw_reply)
                    required_keys = {"title", "learning_objectives", "study_material_markdown", "ascii_flow_diagram", "quiz_questions"}
                    missing = required_keys - set(pack.keys())
                    if missing:
                        raise ValueError(f"Model output missing keys: {missing}")
                    saved_files = save_study_pack(student_id, user_text_clean[:40], pack, create_voice_note=voice_lesson_mode)
                    status.update(label="Study pack generated successfully.", state="complete", expanded=False)
                voice_line = "A voice note was also generated from the Markdown content, skipping the flow diagram." if saved_files.get("voice_note") else "Voice note was not generated because the Voice lesson toggle was off or Kokoro was unavailable."
                study_pack_message = f"## {remove_emojis(pack['title'])}\n\nGenerated a Markdown study pack with an ASCII flow diagram. {voice_line} Use the download buttons below."
                append_chat_message(student_id, "assistant", study_pack_message, mode)
                st.session_state.last_pack = pack
                st.session_state.last_saved_files = saved_files
            else:
                retrieved_chunks = retrieve_relevant_pdf_context(user_text_clean)
                pdf_context = format_rag_context(retrieved_chunks)
                messages = build_compact_context(profile, chat_history, user_text_clean, mode, pdf_context=pdf_context)
                with st.spinner("Thinking..."):
                    raw_reply = call_openrouter(messages=messages, model=DEFAULT_MODEL, temperature=0.6)
                append_chat_message(student_id, "assistant", raw_reply, mode)
            update_student_memory(student_id)
            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")

if st.session_state.last_pack and st.session_state.last_saved_files:
    pack = st.session_state.last_pack
    saved = st.session_state.last_saved_files
    st.divider()
    st.subheader("Latest Generated Study Pack")
    st.markdown(f"## {remove_emojis(pack['title'])}")
    st.markdown("### Learning Objectives")
    for i, obj in enumerate(pack["learning_objectives"], start=1):
        st.markdown(f"{i}. {remove_emojis(str(obj)).strip()}")
    st.success(f"Study pack saved in: `{saved['folder']}`")
    d1, d2 = st.columns(2)
    with d1:
        st.download_button("Download Markdown study pack", data=read_file_bytes(saved["markdown"]), file_name="complete_study_pack.md", mime="text/markdown", use_container_width=True)
    with d2:
        if saved.get("voice_note"):
            st.download_button("Download voice note", data=read_file_bytes(saved["voice_note"]), file_name="voice_note.wav", mime="audio/wav", use_container_width=True)
        else:
            st.button("Voice note unavailable", disabled=True, use_container_width=True)
            st.caption("Turn on the Voice lesson toggle before generating. If it was on, install kokoro, soundfile, numpy, and espeak-ng, then regenerate the pack.")
    with st.expander("Preview complete Markdown study pack"):
        st.markdown(read_file_bytes(saved["markdown"]).decode("utf-8"), unsafe_allow_html=True)
    with st.expander("Voice note"):
        if saved.get("voice_note"):
            st.audio(read_file_bytes(saved["voice_note"]), format="audio/wav")
        else:
            st.warning("Kokoro audio was not created. Install kokoro, soundfile, numpy, and espeak-ng, then regenerate the study pack.")
        st.caption("When the Voice lesson toggle is on, audio is generated from the Markdown study content while skipping the ASCII Flow Diagram section.")
    with st.expander("Preview quiz"):
        for i, qa in enumerate(pack["quiz_questions"], start=1):
            st.markdown(f"**Question {i}:** {remove_emojis(str(qa['question']))}")
            st.markdown(f"**Answer:** {remove_emojis(str(qa['answer']))}")
            st.divider()
