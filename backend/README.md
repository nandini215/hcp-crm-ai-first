# HCP CRM — Backend

FastAPI + SQLAlchemy + PostgreSQL backend, with a LangGraph agent (Groq,
`openai/gpt-oss-120b` by default — see [Configuration](#configuration)) that
turns a free-form chat message into a structured Interaction record.

## Project structure

```
backend/
├── app.py            # FastAPI app + all routes
├── database.py        # Engine, SessionLocal, Base, get_db dependency
├── models.py          # SQLAlchemy ORM models (Interaction, ChatMessage)
├── schemas.py          # Pydantic request/response schemas
├── crud.py             # DB read/write + merge logic
├── graph.py             # LangGraph agent: agent <-> tools loop (tools_condition/ToolNode)
├── tools.py             # The 5 LangGraph tools bound to the agent
├── llm.py               # Groq client (openai/gpt-oss-120b default, see .env.example)
└── requirements.txt
```

## Setup

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# then edit .env: DATABASE_URL, GROQ_API_KEY
```

## Configuration

Environment variables (see `.env.example`):

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql://postgres:postgres@localhost:5432/hcp_crm` | PostgreSQL connection string |
| `GROQ_API_KEY` | — (required) | API key from https://console.groq.com/keys |
| `MODEL_NAME` | `openai/gpt-oss-120b` | Groq model used for tool-calling. `gemma2-9b-it` was the original choice but has since been deprecated by Groq; override this if you'd like a different model |
| `CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | Comma-separated list of allowed frontend origins |

Create the database (Postgres must be running):

```bash
createdb hcp_crm
```

Tables are auto-created on startup via `Base.metadata.create_all()` — no
Alembic migration step needed for this scope.

## Run

```bash
uvicorn app:app --reload --port 8000
```

API docs: http://localhost:8000/docs

## Endpoints

| Method | Path                    | Description                                            |
|--------|-------------------------|----------------------------------------------------------|
| POST   | `/chat`                 | Send a natural-language note; AI extracts + persists it |
| POST   | `/interaction`          | Manually create an interaction record                   |
| PUT    | `/interaction/{id}`     | Partially update an interaction                         |
| GET    | `/interaction/{id}`     | Fetch a single interaction                               |
| GET    | `/hcp/{name}`           | List all interactions for a matching HCP name            |

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

## LangGraph tools

Five tools are bound to the agent's LLM (`llm_with_tools = get_llm().bind_tools(tools)`
in `graph.py`) and executed through a LangGraph `ToolNode`. Each request builds
its own set of tool closures via `build_tools(db, ctx)`, where `db` is the
request-scoped SQLAlchemy session and `ctx` is a small mutable dict tracking
which interaction id the current conversation turn is operating on.

| Tool | Purpose |
|---|---|
| `log_interaction` | Creates a brand-new interaction record. Used the first time an interaction is described in the conversation, i.e. when nothing is currently being tracked. `hcp_name` is required (falls back to `"Unknown HCP"` only if truly not given); every other field is optional. |
| `edit_interaction` | Partially updates an existing record — only the fields passed are changed. Used when an interaction is already being tracked and the rep is adding, correcting, or appending details. Defaults to the interaction currently tracked in the conversation if no `interaction_id` is passed. |
| `get_interaction_details` | Fetches the full current state of a record — used by the agent to see what's already logged before deciding what still needs to be added. |
| `search_hcp_history` | Case-insensitive, partial-name search of PostgreSQL for previously logged interactions with a given HCP — used to recall prior sentiment/topics/outcomes for context before logging a new interaction. |
| `suggest_follow_ups` | Attaches 1–3 concrete, AI-generated follow-up suggestions to the interaction record. Explicitly reserved for the AI's own reasoning about next steps — follow-ups the rep stated themselves go through `follow_up_actions` on `log_interaction`/`edit_interaction` instead. |

Date/time parsing (`_parse_date`, `_parse_time` in `tools.py`) is lenient by
design: natural language like `"today"`/`"tomorrow"`, several date formats,
and `"2:30 PM"`-style times are all accepted, and anything unparseable is
simply left out of the update rather than raising — a single malformed field
never breaks the whole tool call.

## Design notes

- **graph.py** builds a 2-node LangGraph ReAct-style loop: `agent` (calls the
  Groq LLM, bound with the 5 tools via `bind_tools`) ↔ `tools` (a LangGraph
  `ToolNode` that executes whichever tools the model requested). LangGraph's
  built-in `tools_condition` routes back to `tools` whenever the model's
  response contains tool calls, and to `END` once it replies with plain text.
  A **fresh graph is compiled per request** in `run_chat_agent()` — the DB
  session and the small `ctx` dict (tracking which interaction id the current
  turn is operating on) are captured via closures in `build_tools(db, ctx)`,
  so concurrent requests never share state.
- **List fields** (`materials_shared`, `samples_distributed`,
  `ai_suggested_follow_ups`) are merged as a de-duplicated union on update,
  so a later chat message that only mentions a new sample doesn't erase
  materials logged earlier in the same interaction.
- **Scalar fields** are only overwritten when the AI actually extracts a
  non-empty value, so partial follow-up messages ("also, follow up in two
  weeks") don't blank out previously captured fields.
- Every `/chat` turn is written to `chat_messages` for an audit trail, even
  though it isn't returned by the API today.
