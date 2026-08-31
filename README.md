# CLARA Backend

The CLARA backend is a FastAPI service for an AI-powered procurement assistant. It provides chat and conversation management, document ingestion and retrieval, approval workflows with audit history, inventory forecasting, and optional text-to-speech responses.

## Prerequisites

- Python 3.10 or later
- PostgreSQL database accessible through `DATABASE_URL`
- API credentials for the AI services you intend to use
- GNU Make, if you plan to use the Makefile targets

## Setup

1. Create and activate a virtual environment:

  ```powershell
  py -m venv .venv
  .\.venv\Scripts\Activate.ps1
  ```

2. Install the dependencies:

  ```powershell
  python -m pip install -r requirements.txt
  ```

3. Create your local environment file:

  ```powershell
  Copy-Item .env.example .env
  ```

4. Configure `.env`. The common settings are:

  ```dotenv
  DATABASE_URL=postgresql+psycopg2://user:password@localhost:5432/clara
  GOOGLE_API_KEY=your_google_api_key
  HF_TOKEN=your_hugging_face_token
  TAVILY_API_KEY=your_tavily_api_key
  PORT=8000
  ```

  `GOOGLE_API_KEY`, `HF_TOKEN`, and `TAVILY_API_KEY` enable the corresponding AI, embedding, and web-search features. See `.env.example` for optional Chroma Cloud, LlamaParse, text-to-speech, and embedding settings. Set `ENABLE_LANGSMITH_TRACING=true` only when tracing is needed.

5. Run the development server:

  ```powershell
  make dev
  ```

  Without Make:

  ```powershell
  python -m uvicorn app:app --host 0.0.0.0 --port 8000 --reload
  ```

The service is available at `http://localhost:8000`; interactive API documentation is at `http://localhost:8000/docs`.

## Make Targets

- `make install` installs the Python dependencies.
- `make env-check` verifies that `.env` exists.
- `make run` starts the application using the `PORT` environment variable, defaulting to `8000`.
- `make dev` starts Uvicorn with reload enabled on `PORT`, defaulting to `8000`.
- `make prod` starts Gunicorn with a Uvicorn worker for Linux deployments.
- `make lint` checks formatting with Black and lint rules with Ruff.
- `make clean` removes Python bytecode and cache directories.

## API Overview

All application routes, except `/health`, are prefixed with `/api/v1`.

- `GET /health` returns the service status.
- `/api/v1/chat` manages users, chats, messages, uploaded chat context, message feedback, pending actions, and audit logs.
- `/api/v1/documents` imports folders and manages knowledge-base document uploads.
- `/api/v1/inventory` exposes inventory forecasts, trends, and a summary of products needing attention.

Refer to the generated OpenAPI documentation at `/docs` for complete request and response schemas.

## Project Structure

- `app.py` configures FastAPI, CORS, environment loading, and the application entry point.
- `src/api/` contains route registration and versioned endpoint handlers.
- `src/core/agent_logic.py` builds the CLARA AI agent.
- `src/data_logic/` contains database, document retrieval, embedding, audit, and action-queue logic.
- `src/ml/` contains inventory forecasting and seed-data utilities.
- `src/models/` and `src/schema/` define database and API models.
- `src/tools/` provides the agent's procurement, negotiation, inventory, email, and search tools.

## Frontend Connection

The React client reads `REACT_APP_CHAT_ENDPOINT` as its backend base URL. For local development, configure its `.env` with:

```dotenv
REACT_APP_CHAT_ENDPOINT=http://localhost:8000
```

## Deployment

For a Render-style Linux deployment, use:

```text
Build command: pip install -r requirements.txt
Start command: gunicorn -w 1 -k uvicorn.workers.UvicornWorker app:app --bind 0.0.0.0:$PORT
```

Set `DATABASE_URL` and the service credentials required by the features you enable. Set `ENABLE_TTS=false` where loading the local speech model is undesirable.
