from datetime import date as date_type
from datetime import datetime
from datetime import time as time_type
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class InteractionType(str, Enum):
    meeting = "Meeting"
    call = "Call"
    email = "Email"
    conference = "Conference"
    virtual_visit = "Virtual Visit"


class Sentiment(str, Enum):
    positive = "positive"
    neutral = "neutral"
    negative = "negative"


# ---------------------------------------------------------------------------
# Interaction schemas
# ---------------------------------------------------------------------------


class InteractionBase(BaseModel):
    """Shared, always-optional field set used across create/update/AI-merge."""

    hcp_name: Optional[str] = Field(default=None, examples=["Dr. Smith"])
    interaction_type: Optional[InteractionType] = InteractionType.meeting
    date: Optional[date_type] = None
    time: Optional[time_type] = None
    attendees: Optional[str] = None
    topics_discussed: Optional[str] = None
    materials_shared: Optional[List[str]] = Field(default_factory=list)
    samples_distributed: Optional[List[str]] = Field(default_factory=list)
    sentiment: Optional[Sentiment] = Sentiment.neutral
    outcomes: Optional[str] = None
    follow_up_actions: Optional[str] = None
    ai_suggested_follow_ups: Optional[List[str]] = Field(default_factory=list)


class InteractionCreate(InteractionBase):
    """Payload for POST /interaction — hcp_name is required for a manual log."""

    hcp_name: str


class InteractionUpdate(InteractionBase):
    """Payload for PUT /interaction/{id} — every field is optional (partial update)."""

    pass


class InteractionRead(InteractionBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Chat schemas
# ---------------------------------------------------------------------------


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, examples=[
        "Met Dr. Smith today, discussed Product X efficacy, shared brochure, "
        "positive sentiment, follow up in two weeks."
    ])
    interaction_id: Optional[int] = Field(
        default=None,
        description="If continuing an existing draft interaction, pass its id "
        "so the AI merges new details instead of creating a duplicate record.",
    )


class ChatResponse(BaseModel):
    reply: str
    interaction: InteractionRead


# ---------------------------------------------------------------------------
# Generic response wrappers
# ---------------------------------------------------------------------------


class MessageResponse(BaseModel):
    detail: str
