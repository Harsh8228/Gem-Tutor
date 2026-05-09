# Gem Tutor

Gem Tutor is an AI study tutor built with Streamlit. It helps students ask questions, generate study packs, use uploaded PDFs as learning context, and create optional voice lessons.

This project was built for the Gemma 4 Good Hackathon.

## Features

- AI tutor chat
- Student profile management
- PDF upload for study context
- Study pack generation
- Markdown study pack download
- Optional voice lesson generation
- Simple Streamlit interface

## Tech Stack

- Python
- Streamlit
- OpenRouter
- Gemma model
- PyMuPDF
- Kokoro TTS
- Local JSON storage

## Installation

Clone the repository:

```bash
git clone https://github.com/your-username/gem-tutor.git
cd gem-tutor

Install dependencies:

pip install -r requirements.txt
Environment Variable

Set your OpenRouter API key:

OPENROUTER_API_KEY=your_api_key_here
Run the App
streamlit run app.py
How to Use
Open the app in your browser.
Create or select a student profile.
Upload PDFs from the sidebar if you want PDF-based answers.
Ask questions in the chat box.
Turn on Study Pack to generate a full study pack.
Turn on Voice Lesson to create an audio version of the study pack.
Example Prompts
Explain photosynthesis in simple terms.
Create a study pack on Newton's Laws of Motion.
Make me 5 revision questions on fractions.
Project Structure
gem-tutor/
├── app.py
├── config.py
├── students.py
├── rag.py
├── llm.py
├── study_pack.py
├── requirements.txt
└── README.md
Author

Created by Harsh Vardhan.
