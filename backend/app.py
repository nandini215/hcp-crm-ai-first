import os

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

import crud
import models
from database import Base, engine, get_db
from graph import run_chat_agent
from schemas import (
    ChatRequest,
    ChatResponse,
    InteractionCreate,
    InteractionRead,
    InteractionUpdate,
)

load_dotenv()

# Creates tables on startup if they don't already exist. For a production
# rollout, replace this with Alembic migrations.
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="HCP CRM API",
    description="AI-first CRM backend for logging Healthcare Professional interactions.",
    version="1.0.0",
)

CORS_ORIGINS = os.getenv(
    "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in CORS_ORIGINS],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["health"])
def health_check():
    return {"status": "ok", "service": "hcp-crm-backend"}


# ---------------------------------------------------------------------------
# POST /chat — the AI Assistant entrypoint
# ---------------------------------------------------------------------------


@app.post("/chat", response_model=ChatResponse, tags=["chat"])
def chat(payload: ChatRequest, db: Session = Depends(get_db)):
    """
    Accepts a natural-language interaction note, runs it through the
    LangGraph agent (Groq tool-calling agent -> PostgreSQL write),
    and returns the assistant's reply plus the full structured interaction
    record for the frontend form to render.
    """
    try:
        result = run_chat_agent(
            db=db,
            user_message=payload.message,
            interaction_id=payload.interaction_id,
        )
    except Exception as exc:  # pragma: no cover - defensive guard for LLM/DB failures
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI Assistant failed to process the message: {exc}",
        ) from exc

    interaction = result.get("interaction")
    if interaction is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Interaction could not be persisted.",
        )

    return ChatResponse(
        reply=result.get("reply", ""),
        interaction=InteractionRead.model_validate(interaction),
    )


# ---------------------------------------------------------------------------
# Interaction CRUD endpoints
# ---------------------------------------------------------------------------


@app.post(
    "/interaction",
    response_model=InteractionRead,
    status_code=status.HTTP_201_CREATED,
    tags=["interactions"],
)
def create_interaction(payload: InteractionCreate, db: Session = Depends(get_db)):
    """Manually create an interaction record (bypassing the AI chat flow)."""
    data = payload.model_dump(exclude_unset=True)
    interaction = crud.create_interaction(db, data)
    return interaction


@app.put("/interaction/{interaction_id}", response_model=InteractionRead, tags=["interactions"])
def update_interaction(
    interaction_id: int, payload: InteractionUpdate, db: Session = Depends(get_db)
):
    """Partially update an existing interaction record."""
    data = payload.model_dump(exclude_unset=True)
    interaction = crud.update_interaction(db, interaction_id, data)
    if interaction is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Interaction {interaction_id} not found.",
        )
    return interaction


@app.get("/interaction/{interaction_id}", response_model=InteractionRead, tags=["interactions"])
def get_interaction(interaction_id: int, db: Session = Depends(get_db)):
    interaction = crud.get_interaction(db, interaction_id)
    if interaction is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Interaction {interaction_id} not found.",
        )
    return interaction


# ---------------------------------------------------------------------------
# HCP lookup
# ---------------------------------------------------------------------------


@app.get("/hcp/{name}", response_model=list[InteractionRead], tags=["hcp"])
def get_hcp_interactions(name: str, db: Session = Depends(get_db)):
    """
    Returns every logged interaction for a given HCP (case-insensitive,
    partial-name match), most recent first. Used to power HCP search/lookup
    in the frontend "HCP Name" field.
    """
    interactions = crud.get_interactions_by_hcp_name(db, name)
    if not interactions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No interactions found for HCP matching '{name}'.",
        )
    return interactions
