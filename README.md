# CLARA Backend — AI Procurement Assistant

This repository contains the backend for CLARA, an AI-powered procurement assistant built with FastAPI and LangChain.

The service exposes REST APIs for:

- importing documents into a Chroma vector database
- running chat prompts against a LangChain agent

## Requirements

- Python 3.8+
- `requirements.txt` dependencies
- environment variables configured in `.env`

## Setup

1. Clone the repository and change into the project directory.

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Copy the example environment file:
   ```bash
   copy .env.example .env
   ```

4. Update `.env` with your API keys:
   - `GOOGLE_API_KEY`
   - `HF_TOKEN`
   - `TAVILY_API_KEY`
   - `NGROK_AUTH_TOKEN`

5. Start the app:
   ```bash
   make dev
   ```

   or to run without auto-reload:
   ```bash
   make run
   ```

## Makefile Targets

- `make install` — install Python dependencies
- `make env-check` — verify `.env` exists
- `make run` — start the FastAPI app via `python app.py`
- `make dev` — start the app with `uvicorn` and auto-reload
- `make lint` — run `black` and `ruff` if installed
- `make clean` — remove Python cache files

## Local API Usage

Start the backend, then use the Swagger docs at:

```text
http://127.0.0.1:1234/docs
```

### Document import endpoint

POST `/api/v1/documents/import`

Request body example:

```json
{
  "folder_directory": "C:/path/to/documents"
}
```

This endpoint processes documents from the provided folder path and stores them in the Chroma vector database.

### Chat endpoint

POST `/api/v1/chat/message`

Request body example:

```json
{
  "prompt": "Summarize the latest procurement request.",
  "history": [
    {"role": "user", "content": "Please read the uploaded files."}
  ]
}
```

Response example:

```json
{
  "response": "CLARA's generated answer text.",
  "audio": "<base64-audio-string>"
}
```

## Project Structure

- `app.py` — FastAPI application entrypoint
- `src/api/router.py` — API router configuration
- `src/api/v1/documents.py` — document ingest endpoint
- `src/api/v1/chat.py` — chat endpoint and agent invocation
- `src/core/agent_logic.py` — agent setup logic
- `src/data_logic/doc_processor.py` — PDF processing and retrieval setup
- `src/tools/tools_definition.py` — tool definitions for LangChain agent
- `src/addons/text_to_speech.py` — optional text-to-speech support

## Notes

- The backend uses FastAPI and Uvicorn on port `1234`.
- The app loads environment values via `python-dotenv`.
- If you do not need `streamlit` or `ngrok` behavior, those packages can remain installed but are not required for the core API.
