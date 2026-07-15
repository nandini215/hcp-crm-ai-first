# AI-First CRM — HCP Interaction Module

An AI-first CRM module for logging **Healthcare Professional (HCP) interactions**
purely through natural-language chat. A rep describes what happened in plain
English — *"Met Dr. Smith today, discussed Product X efficacy, shared the
brochure, positive sentiment, follow up in two weeks"* — and a LangGraph
agent, running on Groq, extracts the structured data and writes it straight
to PostgreSQL. There is no manual form entry: the **Interaction Details**
form is 100% read-only and is populated exclusively by the AI's output.

![Architecture](docs/architecture.png)

---

## Table of contents

- [Overview](#overview)
- [Features](#features)
- [Tech stack](#tech-stack)
- [Architecture](#architecture)
- [Folder structure](#folder-structure)
- [Installation](#installation)
- [Backend setup](#backend-setup)
- [Frontend setup](#frontend-setup)
- [Database setup](#database-setup)
- [Environment variables](#environment-variables)
- [Running the project](#running-the-project)
- [Running with Docker (optional)](#running-with-docker-optional)
- [API endpoints](#api-endpoints)
- [LangGraph workflow](#langgraph-workflow)
- [LangGraph tools](#langgraph-tools)
- [Screenshots](#screenshots)
- [Future improvements](#future-improvements)
- [License](#license)

---

## Overview

Most CRMs make reps fill out a structured form after every customer
interaction — tedious, and fields get skipped or the whole thing gets
skipped. This module inverts that: the rep just talks (or types) naturally,
and a tool-calling LLM agent does the structuring, using five purpose-built
tools to create, update, look up, and enrich interaction records in
PostgreSQL. The chat conversation and the structured record stay in sync
automatically, because the record can *only* change through the agent.

## Features

- **Conversational interaction logging** — no manual form fields; the rep
  only ever talks to the AI Assistant chat panel.
- **Read-only, AI-populated form** — `InteractionForm.jsx` renders every
  field `disabled`; the single Redux reducer that can change it
  (`setInteractionFromAI`) only fires after a successful `/chat` response.
- **Incremental editing across a conversation** — a follow-up message like
  *"also mention we discussed pricing"* updates only the fields it touches;
  everything else on the record is left untouched.
- **Non-destructive list merging** — materials shared, samples distributed,
  and AI-suggested follow-ups are merged as a de-duplicated union on update,
  not overwritten, so earlier turns in the conversation are never lost.
- **HCP history recall** — the agent can search prior interactions with the
  same HCP (case-insensitive, partial-name match) to inform how it logs a
  new one.
- **AI-suggested follow-ups** — the agent can proactively attach 1–3 next
  steps it inferred, kept distinct from follow-ups the rep explicitly stated.
- **Conversation audit trail** — every chat turn is persisted to
  `chat_messages`, linked to the interaction it helped populate.
- **Lenient natural-language parsing** — dates ("today", "tomorrow", ISO,
  or common formats) and times ("2:30 PM", "14:30", "noon") are all
  accepted; anything unparseable is simply left out of the update rather
  than failing the whole tool call.

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | React (Vite), Redux Toolkit, Material UI, Axios |
| Backend | FastAPI, SQLAlchemy, Pydantic |
| Database | PostgreSQL (JSONB columns for list fields) |
| AI orchestration | LangGraph (agent/tools loop) |
| LLM | Groq (tool-calling, `openai/gpt-oss-120b` by default) |

## Architecture

```
React UI  --dispatch-->  Redux Toolkit  --Axios POST /chat-->  FastAPI
                                                                    |
                                                            run_chat_agent()
                                                                    |
                                                             LangGraph graph
                                                          agent  <->  tools
                                                             |            |
                                                        Groq LLM     crud.py (merge logic)
                                                       (tool-calling)     |
                                                                     PostgreSQL
                                                                (interactions,
                                                                 chat_messages)
```

The LangGraph agent is a standard ReAct-style loop (see
[LangGraph workflow](#langgraph-workflow) below), not a single LLM call
parsing JSON — the model decides which of the five tools to call, in what
order, based on the running conversation state.

The FastAPI response returns **snake_case** keys (matching the SQLAlchemy
columns directly). `frontend/src/utils/caseMapper.js` is the single boundary
that translates this to **camelCase** before anything reaches Redux — every
component downstream only ever sees the camelCase shape.

## Folder structure

```
hcp-crm/
├── README.md                  # this file
├── LICENSE
├── .gitignore
├── docker-compose.yml          # optional — Postgres + backend + frontend
├── SUBMISSION_CHECKLIST.md
├── docs/
│   ├── architecture.png
│   └── screenshots/
├── backend/
│   ├── app.py                  # FastAPI app + all routes
│   ├── database.py             # Engine, SessionLocal, Base, get_db
│   ├── models.py                # SQLAlchemy models (Interaction, ChatMessage)
│   ├── schemas.py                # Pydantic request/response schemas
│   ├── crud.py                    # DB read/write + list-merge logic
│   ├── graph.py                    # LangGraph agent <-> tools loop
│   ├── tools.py                     # The 5 LangGraph tools
│   ├── llm.py                        # Groq client config
│   ├── requirements.txt
│   ├── .env.example
│   ├── Dockerfile
│   └── README.md                      # backend-specific details
└── frontend/
    ├── src/
    │   ├── app/store.js                # Redux store
    │   ├── redux/                       # interactionSlice, chatSlice
    │   ├── services/                     # axiosInstance, chatService
    │   ├── utils/caseMapper.js            # snake_case <-> camelCase boundary
    │   ├── theme/theme.js
    │   ├── components/                     # Header, InteractionForm, ChatPanel
    │   ├── pages/Home.jsx
    │   ├── App.jsx
    │   └── main.jsx
    ├── package.json
    ├── .env.example
    ├── Dockerfile
    └── README.md                            # frontend-specific details
```

## Installation

Prerequisites: **Python 3.11+**, **Node.js 18+**, **PostgreSQL 14+**, and a
[Groq API key](https://console.groq.com/keys).

```bash
git clone <your-repo-url>
cd hcp-crm
```

## Backend setup

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# edit .env: set DATABASE_URL and GROQ_API_KEY
```

## Frontend setup

```bash
cd frontend
npm install
cp .env.example .env
# edit .env if your backend isn't at http://localhost:8000
```

## Database setup

```bash
createdb hcp_crm
```

Tables (`interactions`, `chat_messages`) are auto-created on backend startup
via `Base.metadata.create_all()` — no separate migration step is needed for
this scope.

## Environment variables

**`backend/.env`** (see `backend/.env.example`):

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql://postgres:postgres@localhost:5432/hcp_crm` | PostgreSQL connection string |
| `GROQ_API_KEY` | *(required)* | API key from https://console.groq.com/keys |
| `MODEL_NAME` | `openai/gpt-oss-120b` | Groq model used for tool-calling |
| `CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | Allowed frontend origins, comma-separated |

**`frontend/.env`** (see `frontend/.env.example`):

| Variable | Default | Description |
|---|---|---|
| `VITE_API_BASE_URL` | `http://localhost:8000` | Backend base URL (no `/api/v1` prefix — routes are mounted at root) |

No API keys or secrets are hardcoded anywhere in the codebase — both are
read from environment variables, with `.env` gitignored and `.env.example`
committed as a template.

## Running the project

Backend:

```bash
cd backend
uvicorn app:app --reload --port 8000
```

Frontend (separate terminal):

```bash
cd frontend
npm run dev
```

- Frontend: http://localhost:5173
- Backend health check: http://localhost:8000
- Interactive API docs (Swagger UI): http://localhost:8000/docs

## Running with Docker (optional)

```bash
export GROQ_API_KEY=your_groq_api_key_here
docker compose up --build
```

This starts PostgreSQL, the FastAPI backend, and the Vite frontend together.
`GROQ_API_KEY` is read from your shell environment (or a root-level `.env`
file that `docker compose` picks up automatically) — it is never baked into
the compose file or any image.

## API endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/` | Health check |
| POST | `/chat` | Send a natural-language note; the LangGraph agent extracts and persists it |
| POST | `/interaction` | Manually create an interaction record (bypasses the AI chat flow) |
| PUT | `/interaction/{id}` | Partially update an existing interaction |
| GET | `/interaction/{id}` | Fetch a single interaction |
| GET | `/hcp/{name}` | List all interactions for a matching HCP name (case-insensitive, partial match) |

### `POST /chat` request

```json
{
  "message": "Today I met Dr Smith. Discussed Product X efficacy. Shared brochure. Positive sentiment. Follow up in two weeks.",
  "interaction_id": null
}
```

### `POST /chat` response

```json
{
  "reply": "Logged your meeting with Dr. Smith — positive sentiment recorded, follow-up noted for 2 weeks.",
  "interaction": {
    "id": 1,
    "hcp_name": "Dr. Smith",
    "interaction_type": "Meeting",
    "date": "2026-07-14",
    "time": null,
    "attendees": null,
    "topics_discussed": "Product X efficacy",
    "materials_shared": ["Brochure"],
    "samples_distributed": [],
    "sentiment": "positive",
    "outcomes": null,
    "follow_up_actions": "Follow up in two weeks",
    "ai_suggested_follow_ups": ["Schedule follow-up meeting in 2 weeks"],
    "created_at": "2026-07-14T10:00:00",
    "updated_at": "2026-07-14T10:00:00"
  }
}
```

## LangGraph workflow

The agent (`backend/graph.py`) is a 2-node LangGraph ReAct-style loop:

```
START -> agent -> (tools_condition) -> tools -> agent -> ... -> END
```

- **`agent` node** — calls the Groq LLM, bound with the 5 tools via
  `bind_tools()`, on the running message list.
- **`tools_condition`** (LangGraph built-in) — routes to the `tools` node
  whenever the model's response contains tool calls, and to `END` once the
  model replies with plain text and no further tool calls.
- **`tools` node** — a LangGraph `ToolNode` that executes whichever tools
  the model requested and appends their results back onto the message list
  before looping back to `agent`.

A **fresh graph is compiled per request** in `run_chat_agent()`. The
request-scoped SQLAlchemy session and a small `ctx` dict — tracking which
interaction id the current conversation turn is operating on — are captured
via closures in `tools.build_tools(db, ctx)`, so concurrent requests never
share state.

Each turn also injects a `[Conversation context]` note into the first
message, stating whether an interaction is already being tracked (and its
current field values, if so). The system prompt uses this to decide whether
to call `log_interaction` (nothing tracked yet) or `edit_interaction` (an
interaction is already in progress) — see `graph.py`'s `SYSTEM_PROMPT` for
the full instruction set, including the field-normalization rules
(`interaction_type` and `sentiment` enums, natural-language date parsing).

If the graph invocation fails or exhausts its recursion budget
(`recursion_limit=12`), `run_chat_agent()` falls back to logging the raw
rep message verbatim as an `"Unknown HCP"` record, so a rep's input is never
silently dropped even if the AI pipeline breaks.

## LangGraph tools

Five tools are exposed to the agent (`backend/tools.py`), each built fresh
per request via `build_tools(db, ctx)`:

| Tool | Purpose |
|---|---|
| **`log_interaction`** | Creates a brand-new interaction record. Used the first time an interaction is described in a conversation. `hcp_name` is required (falls back to `"Unknown HCP"` only if truly not given); every other field is optional and only filled when actually mentioned. |
| **`edit_interaction`** | Partially updates an existing record — only the fields passed are changed, everything else is left untouched. Used when an interaction is already being tracked and the rep adds, corrects, or appends details. Defaults to the currently-tracked interaction if no `interaction_id` is given. |
| **`get_interaction_details`** | Fetches the full current state of a record — lets the agent see what's already logged before deciding what still needs to be added via `edit_interaction`. |
| **`search_hcp_history`** | Case-insensitive, partial-name search of PostgreSQL for previously logged interactions with a given HCP — used to recall prior sentiment, topics, or outcomes for context before logging a new one. |
| **`suggest_follow_ups`** | Attaches 1–3 concrete, AI-generated follow-up suggestions to the record. Explicitly reserved for the AI's own reasoning about next steps that weren't explicitly stated by the rep — those go through `follow_up_actions` on `log_interaction`/`edit_interaction` instead. |

**Field normalization** (`tools.py`): `interaction_type` must be one of
`Meeting`, `Call`, `Email`, `Conference`, `Virtual Visit`; `sentiment` must
be one of `positive`, `neutral`, `negative`. Dates accept natural language
(`"today"`, `"tomorrow"`, `"yesterday"`) or common formats (ISO,
`MM/DD/YYYY`, `"July 14, 2026"`, etc.); times accept `"14:30"`, `"2:30 PM"`,
`"noon"`, `"midnight"`. Anything that can't be confidently parsed is left
out of the update rather than raising, so one malformed field never breaks
the whole tool call.

**List-field merge logic** (`backend/crud.py`): `materials_shared`,
`samples_distributed`, and `ai_suggested_follow_ups` are merged as a
de-duplicated, order-preserving union on every update — a later message
that only mentions one new item never erases what was logged earlier in the
same interaction. Scalar fields are only overwritten when the AI extracts a
genuinely non-empty value, so a partial follow-up message never blanks out
previously captured data.

## Screenshots

> Add screenshots to `docs/screenshots/` and reference them below. See
> `docs/screenshots/README.md` for the suggested set.

| | |
|---|---|
| Empty state | `docs/screenshots/01-empty-state.png` |
| Chat populating the form | `docs/screenshots/02-chat-populating-form.png` |
| AI-suggested follow-ups | `docs/screenshots/03-ai-suggested-followups.png` |
| HCP history recall | `docs/screenshots/04-hcp-history-recall.png` |
| API docs (Swagger UI) | `docs/screenshots/05-api-docs.png` |

## Future improvements

These are potential next steps, **not currently implemented**:

- Alembic migrations in place of `Base.metadata.create_all()` for schema
  changes beyond initial setup.
- Automated tests (e.g. pytest coverage of `crud.py`'s list-merge logic;
  React component tests for `ChatPanel`/`InteractionForm`).
- Authentication/authorization for multi-rep usage.
- Returning `chat_messages` history via the API (currently persisted for
  audit purposes but not exposed by any endpoint).
- Pagination on `GET /hcp/{name}` for HCPs with a long interaction history.

## License

[MIT](LICENSE)
