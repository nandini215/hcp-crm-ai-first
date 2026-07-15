from datetime import datetime

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    Time,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from database import Base


class Interaction(Base):
    """
    A single logged HCP interaction record.

    This table is the persisted, structured counterpart of the read-only
    "Interaction Details" form in the frontend. Rows are written exclusively
    by the AI agent pipeline (graph.py -> crud.py) or via the explicit
    REST endpoints exposed in app.py.
    """

    __tablename__ = "interactions"

    id = Column(Integer, primary_key=True, index=True)

    hcp_name = Column(String(255), index=True, nullable=False, default="")
    interaction_type = Column(String(50), nullable=False, default="Meeting")
    date = Column(Date, nullable=True)
    time = Column(Time, nullable=True)
    attendees = Column(String(500), nullable=True, default="")
    topics_discussed = Column(Text, nullable=True, default="")

    # Stored as JSONB arrays of strings, e.g. ["Product X Brochure"]
    materials_shared = Column(JSONB, nullable=False, default=list)
    samples_distributed = Column(JSONB, nullable=False, default=list)

    sentiment = Column(String(20), nullable=False, default="neutral")
    outcomes = Column(Text, nullable=True, default="")
    follow_up_actions = Column(Text, nullable=True, default="")
    ai_suggested_follow_ups = Column(JSONB, nullable=False, default=list)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    chat_messages = relationship(
        "ChatMessage", back_populates="interaction", cascade="all, delete-orphan"
    )


class ChatMessage(Base):
    """
    A single turn in the AI Assistant conversation, optionally linked to the
    interaction record it helped populate. Kept for audit / conversation
    history purposes.
    """

    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    interaction_id = Column(
        Integer, ForeignKey("interactions.id"), nullable=True, index=True
    )
    role = Column(String(20), nullable=False)  # "user" | "assistant"
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    interaction = relationship("Interaction", back_populates="chat_messages")
