# RAGOncologyBooks

RAGProductionApp is a local Retrieval-Augmented Generation (RAG) app for studying PDF material.
It lets you:

- Ingest PDFs into a Qdrant vector store
- Ask questions grounded in retrieved chunks
- Generate Anki `.apkg` flashcard decks from retrieved content

## Tech Stack

- Python 3.11+
- FastAPI + Inngest (event-driven functions)
- Streamlit (UI)
- Qdrant (vector store)
- Sentence Transformers (embeddings)
- Groq OpenAI-compatible API (LLM)
- Genanki (Anki deck export)

## Project Structure

- `main.py` → Inngest functions (ingest, query, flashcards)
- `streamlit_app.py` → frontend UI
- `data_loader.py` → PDF loading/chunking/embedding helpers
- `vector_db.py` → Qdrant storage wrapper
- `custom_types.py` → pydantic result/data models
- `uploads/` → uploaded PDFs
- `qdrant_storage/` → local Qdrant data

## Prerequisites

- Python 3.11 or newer
- Running Qdrant instance (local or remote)
- Groq API key (or another OpenAI-compatible endpoint)
- Inngest dev server for local orchestration

## Environment Variables

Create a `.env` file in the repo root:

```env
GROQ_API_KEY=your_groq_api_key
# Optional if your Streamlit app needs a non-default Inngest API
INNGEST_API_BASE=http://127.0.0.1:8288/v1
```

## Installation

Using `uv`:

```bash
uv sync
```

Or with `pip`:

```bash
pip install -e .
```

## Run Locally

### 1) Start FastAPI app (Inngest handlers)

```bash
uv run uvicorn main:app --reload --port 8000
```

### 2) Start Inngest dev server

In a second terminal:

```bash
npx inngest-cli@latest dev -u http://127.0.0.1:8000/api/inngest
```

If your mounted endpoint differs, update the `-u` URL accordingly.

### 3) Start Streamlit UI

In a third terminal:

```bash
uv run streamlit run streamlit_app.py
```

## App Workflow

1. Upload one or more PDFs in the Streamlit app.
2. Wait for ingestion completion.
3. Ask a question to get a context-grounded answer.
4. Use flashcard generation to create an Anki `.apkg` deck.
5. Import the `.apkg` file into Anki.

## Notes

- Flashcard extraction currently expects model output in `Q: ...` / `A: ...` format.
- Generated decks are written to the project directory by default.
- If runs appear stuck in Streamlit, verify all 3 services are running: FastAPI, Inngest dev, Streamlit.

## Git / Repository Hygiene

Before pushing to GitHub, ignore large/private study data (for example books and local summaries) via `.gitignore`.

Example entries:

```gitignore
Oncology books from ESMO/
LEARNING_SUMMARY_*.md
uploads/
qdrant_storage/
quadrant_storage/
```

## Future Improvements

- Improve flashcard parsing robustness
- Add safe deck filename sanitization
- Add downloadable deck button in Streamlit
- Add tests for ingestion/query/flashcard flows
