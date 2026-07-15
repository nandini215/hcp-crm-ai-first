from typing import Any, Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

import models

# Columns that hold list data — merged as a de-duplicated union rather than
# a straight overwrite, so previously logged materials/samples/suggestions
# aren't lost when a follow-up chat message only mentions new ones.
LIST_FIELDS = {"materials_shared", "samples_distributed", "ai_suggested_follow_ups"}

# All fields an Interaction may be created/updated with.
INTERACTION_FIELDS = {
    "hcp_name",
    "interaction_type",
    "date",
    "time",
    "attendees",
    "topics_discussed",
    "materials_shared",
    "samples_distributed",
    "sentiment",
    "outcomes",
    "follow_up_actions",
    "ai_suggested_follow_ups",
}


def _clean_payload(data: Dict[str, Any]) -> Dict[str, Any]:
    """Keep only known interaction columns, dropping unset/None-only noise."""
    return {k: v for k, v in data.items() if k in INTERACTION_FIELDS}


def create_interaction(db: Session, data: Dict[str, Any]) -> models.Interaction:
    payload = _clean_payload(data)
    interaction = models.Interaction(**payload)
    db.add(interaction)
    db.commit()
    db.refresh(interaction)
    return interaction


def get_interaction(db: Session, interaction_id: int) -> Optional[models.Interaction]:
    return (
        db.query(models.Interaction)
        .filter(models.Interaction.id == interaction_id)
        .first()
    )


def update_interaction(
    db: Session, interaction_id: int, data: Dict[str, Any]
) -> Optional[models.Interaction]:
    interaction = get_interaction(db, interaction_id)
    if interaction is None:
        return None

    payload = _clean_payload(data)
    for field, value in payload.items():
        if value is None:
            continue
        if field in LIST_FIELDS:
            existing_list = getattr(interaction, field) or []
            merged = list(dict.fromkeys([*existing_list, *value]))  # de-dup, order-preserving
            setattr(interaction, field, merged)
        else:
            # Skip empty-string overwrites so a blank AI extraction never
            # clobbers a previously captured value.
            if isinstance(value, str) and value.strip() == "":
                continue
            setattr(interaction, field, value)

    db.commit()
    db.refresh(interaction)
    return interaction


def delete_interaction(db: Session, interaction_id: int) -> bool:
    interaction = get_interaction(db, interaction_id)
    if interaction is None:
        return False
    db.delete(interaction)
    db.commit()
    return True


def get_interactions_by_hcp_name(
    db: Session, hcp_name: str, limit: int = 50
) -> List[models.Interaction]:
    """Case-insensitive partial match, most recent first."""
    return (
        db.query(models.Interaction)
        .filter(func.lower(models.Interaction.hcp_name).contains(hcp_name.lower()))
        .order_by(models.Interaction.created_at.desc())
        .limit(limit)
        .all()
    )


def orm_to_dict(interaction: models.Interaction) -> Dict[str, Any]:
    """Plain-dict snapshot of an Interaction row, used as merge context for the LLM."""
    if interaction is None:
        return {}
    return {
        "id": interaction.id,
        "hcp_name": interaction.hcp_name,
        "interaction_type": interaction.interaction_type,
        "date": interaction.date.isoformat() if interaction.date else None,
        "time": interaction.time.isoformat(timespec="minutes") if interaction.time else None,
        "attendees": interaction.attendees,
        "topics_discussed": interaction.topics_discussed,
        "materials_shared": interaction.materials_shared or [],
        "samples_distributed": interaction.samples_distributed or [],
        "sentiment": interaction.sentiment,
        "outcomes": interaction.outcomes,
        "follow_up_actions": interaction.follow_up_actions,
        "ai_suggested_follow_ups": interaction.ai_suggested_follow_ups or [],
    }


# ---------------------------------------------------------------------------
# Chat message persistence (conversation audit trail)
# ---------------------------------------------------------------------------


def create_chat_message(
    db: Session, role: str, content: str, interaction_id: Optional[int] = None
) -> models.ChatMessage:
    message = models.ChatMessage(
        role=role, content=content, interaction_id=interaction_id
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return message
