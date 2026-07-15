"""
LangGraph tool definitions.

Five tools are exposed to the agent's LLM (bound via `bind_tools`) and executed
through a LangGraph `ToolNode`:

    1. log_interaction        — create a brand-new interaction record
    2. edit_interaction       — partially update an existing record
    3. get_interaction_details— fetch the current state of a record
    4. search_hcp_history     — look up past interactions for a given HCP
    5. suggest_follow_ups     — attach AI-generated follow-up suggestions

Each request builds its own set of tool closures via `build_tools(db, ctx)`,
where `db` is the request-scoped SQLAlchemy session and `ctx` is a small
mutable dict used to track which interaction id the current conversation turn
is operating on (so the agent doesn't have to pass `interaction_id` on every
single call).
"""

import json
import re
from datetime import date, datetime, time, timedelta
from typing import Any, Dict, List, Optional

from langchain_core.tools import tool
from sqlalchemy.orm import Session

import crud

VALID_INTERACTION_TYPES = ["Meeting", "Call", "Email", "Conference", "Virtual Visit"]
VALID_SENTIMENTS = ["positive", "neutral", "negative"]


# ---------------------------------------------------------------------------
# Parsing helpers — lenient by design: anything that can't be confidently
# parsed is simply left out of the update rather than raising, so a single
# malformed field never breaks the whole tool call.
# ---------------------------------------------------------------------------


def _parse_date(value: Optional[str]) -> Optional[date]:
    if not value or not isinstance(value, str):
        return None
    text = value.strip()
    lowered = text.lower()
    today = date.today()
    if lowered == "today":
        return today
    if lowered == "tomorrow":
        return today + timedelta(days=1)
    if lowered == "yesterday":
        return today - timedelta(days=1)
    try:
        return date.fromisoformat(text)
    except ValueError:
        pass
    for fmt in ("%m/%d/%Y", "%d/%m/%Y", "%m-%d-%Y", "%Y/%m/%d", "%B %d, %Y", "%b %d, %Y", "%d %B %Y", "%d %b %Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def _parse_time(value: Optional[str]) -> Optional[time]:
    if not value or not isinstance(value, str):
        return None
    text = value.strip().lower()
    if text == "noon":
        return time(12, 0)
    if text == "midnight":
        return time(0, 0)
    match = re.match(r"^(\d{1,2})(?::(\d{2}))?\s*(am|pm)$", text)
    if match:
        hour = int(match.group(1)) % 12
        minute = int(match.group(2) or 0)
        if match.group(3) == "pm":
            hour += 12
        return time(hour, minute)
    for fmt in ("%H:%M:%S", "%H:%M"):
        try:
            return datetime.strptime(text, fmt).time()
        except ValueError:
            continue
    return None


def _normalize_choice(value: Optional[str], valid: List[str]) -> Optional[str]:
    if not value or not isinstance(value, str):
        return None
    for option in valid:
        if option.lower() == value.strip().lower():
            return option
    return None


def _as_list(value: Any) -> Optional[List[str]]:
    if value is None:
        return None
    if isinstance(value, list):
        cleaned = [str(v).strip() for v in value if str(v).strip()]
        return cleaned
    if isinstance(value, str):
        parts = [p.strip() for p in value.split(",")]
        return [p for p in parts if p]
    return None


def _build_field_payload(
    hcp_name: Optional[str] = None,
    interaction_type: Optional[str] = None,
    date_: Optional[str] = None,
    time_: Optional[str] = None,
    attendees: Optional[str] = None,
    topics_discussed: Optional[str] = None,
    materials_shared: Optional[Any] = None,
    samples_distributed: Optional[Any] = None,
    sentiment: Optional[str] = None,
    outcomes: Optional[str] = None,
    follow_up_actions: Optional[str] = None,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {}

    if hcp_name and hcp_name.strip():
        payload["hcp_name"] = hcp_name.strip()

    interaction_type_norm = _normalize_choice(interaction_type, VALID_INTERACTION_TYPES)
    if interaction_type_norm:
        payload["interaction_type"] = interaction_type_norm

    parsed_date = _parse_date(date_)
    if parsed_date:
        payload["date"] = parsed_date

    parsed_time = _parse_time(time_)
    if parsed_time:
        payload["time"] = parsed_time

    if attendees and attendees.strip():
        payload["attendees"] = attendees.strip()

    if topics_discussed and topics_discussed.strip():
        payload["topics_discussed"] = topics_discussed.strip()

    materials = _as_list(materials_shared)
    if materials is not None:
        payload["materials_shared"] = materials

    samples = _as_list(samples_distributed)
    if samples is not None:
        payload["samples_distributed"] = samples

    sentiment_norm = _normalize_choice(sentiment, VALID_SENTIMENTS)
    if sentiment_norm:
        payload["sentiment"] = sentiment_norm

    if outcomes and outcomes.strip():
        payload["outcomes"] = outcomes.strip()

    if follow_up_actions and follow_up_actions.strip():
        payload["follow_up_actions"] = follow_up_actions.strip()

    return payload


def build_tools(db: Session, ctx: Dict[str, Any]) -> List[Any]:
    """Builds the 5 mandatory LangGraph tools, scoped to one request."""

    @tool
    def log_interaction(
        hcp_name: str,
        interaction_type: Optional[str] = None,
        date: Optional[str] = None,
        time: Optional[str] = None,
        attendees: Optional[str] = None,
        topics_discussed: Optional[str] = None,
        materials_shared: Optional[List[str]] = None,
        samples_distributed: Optional[List[str]] = None,
        sentiment: Optional[str] = None,
        outcomes: Optional[str] = None,
        follow_up_actions: Optional[str] = None,
    ) -> str:
        """Create a brand-new HCP interaction record in PostgreSQL. Use this the
        FIRST time an interaction is described in the conversation, i.e. when no
        interaction is currently being tracked. `hcp_name` is required — use
        "Unknown HCP" only if the user truly gave no name. Every other field is
        optional and should only be filled in when the user actually mentioned
        it. `date` accepts natural language such as "today" or an ISO date like
        "2026-07-14". `time` accepts "14:30" or "2:30 PM". `interaction_type`
        must be one of: Meeting, Call, Email, Conference, Virtual Visit.
        `sentiment` must be one of: positive, neutral, negative."""
        try:
            payload = _build_field_payload(
                hcp_name=hcp_name,
                interaction_type=interaction_type,
                date_=date,
                time_=time,
                attendees=attendees,
                topics_discussed=topics_discussed,
                materials_shared=materials_shared,
                samples_distributed=samples_distributed,
                sentiment=sentiment,
                outcomes=outcomes,
                follow_up_actions=follow_up_actions,
            )
            payload.setdefault("hcp_name", hcp_name.strip() if hcp_name and hcp_name.strip() else "Unknown HCP")
            interaction = crud.create_interaction(db, payload)
            ctx["interaction_id"] = interaction.id
            return json.dumps({"status": "logged", **crud.orm_to_dict(interaction)}, default=str)
        except Exception as exc:  # defensive — a tool failure must never crash the graph
            return json.dumps({"status": "error", "message": str(exc)})

    @tool
    def edit_interaction(
        interaction_id: Optional[int] = None,
        hcp_name: Optional[str] = None,
        interaction_type: Optional[str] = None,
        date: Optional[str] = None,
        time: Optional[str] = None,
        attendees: Optional[str] = None,
        topics_discussed: Optional[str] = None,
        materials_shared: Optional[List[str]] = None,
        samples_distributed: Optional[List[str]] = None,
        sentiment: Optional[str] = None,
        outcomes: Optional[str] = None,
        follow_up_actions: Optional[str] = None,
    ) -> str:
        """Partially update an EXISTING interaction record — only the fields you
        pass are changed, every other field on the record is left untouched.
        Use this when an interaction is already being tracked in this
        conversation and the user is adding, correcting, or appending details
        (e.g. "also mention we discussed pricing" or "actually make the
        sentiment positive"). If `interaction_id` is omitted, the interaction
        currently being tracked in this conversation is used automatically."""
        try:
            target_id = interaction_id or ctx.get("interaction_id")
            if not target_id:
                return json.dumps(
                    {"status": "error", "message": "No interaction is being tracked yet — call log_interaction first."}
                )
            payload = _build_field_payload(
                hcp_name=hcp_name,
                interaction_type=interaction_type,
                date_=date,
                time_=time,
                attendees=attendees,
                topics_discussed=topics_discussed,
                materials_shared=materials_shared,
                samples_distributed=samples_distributed,
                sentiment=sentiment,
                outcomes=outcomes,
                follow_up_actions=follow_up_actions,
            )
            interaction = crud.update_interaction(db, target_id, payload)
            if interaction is None:
                return json.dumps({"status": "error", "message": f"Interaction {target_id} not found."})
            ctx["interaction_id"] = interaction.id
            return json.dumps({"status": "updated", **crud.orm_to_dict(interaction)}, default=str)
        except Exception as exc:
            return json.dumps({"status": "error", "message": str(exc)})

    @tool
    def get_interaction_details(interaction_id: Optional[int] = None) -> str:
        """Fetch the full current state of an interaction record — useful to see
        what has already been logged before deciding what still needs to be
        added via edit_interaction. If `interaction_id` is omitted, the
        interaction currently being tracked in this conversation is used."""
        try:
            target_id = interaction_id or ctx.get("interaction_id")
            if not target_id:
                return json.dumps({"status": "error", "message": "No interaction is being tracked yet."})
            interaction = crud.get_interaction(db, target_id)
            if interaction is None:
                return json.dumps({"status": "error", "message": f"Interaction {target_id} not found."})
            return json.dumps({"status": "ok", **crud.orm_to_dict(interaction)}, default=str)
        except Exception as exc:
            return json.dumps({"status": "error", "message": str(exc)})

    @tool
    def search_hcp_history(hcp_name: str) -> str:
        """Search PostgreSQL for previously logged interactions with a given
        Healthcare Professional (case-insensitive, partial-name match). Use
        this to recall prior sentiment, topics, or outcomes for context before
        logging a new interaction with the same HCP."""
        try:
            interactions = crud.get_interactions_by_hcp_name(db, hcp_name, limit=5)
            if not interactions:
                return json.dumps({"status": "not_found", "message": f"No prior interactions found for '{hcp_name}'."})
            summaries = [
                {
                    "id": i.id,
                    "date": i.date.isoformat() if i.date else None,
                    "interaction_type": i.interaction_type,
                    "sentiment": i.sentiment,
                    "topics_discussed": i.topics_discussed,
                    "outcomes": i.outcomes,
                }
                for i in interactions
            ]
            return json.dumps({"status": "ok", "count": len(summaries), "interactions": summaries}, default=str)
        except Exception as exc:
            return json.dumps({"status": "error", "message": str(exc)})

    @tool
    def suggest_follow_ups(suggestions: List[str], interaction_id: Optional[int] = None) -> str:
        """Attach 1-3 concrete, AI-generated follow-up suggestions (your own
        reasoning about sensible next steps, e.g. "Send updated efficacy data
        in 2 weeks") to the interaction record so they surface in the CRM as
        one-click suggestions for the rep. Do not use this for follow-up
        actions the rep explicitly stated themselves — those belong in
        `follow_up_actions` via log_interaction/edit_interaction instead."""
        try:
            target_id = interaction_id or ctx.get("interaction_id")
            if not target_id:
                return json.dumps(
                    {"status": "error", "message": "No interaction is being tracked yet — call log_interaction first."}
                )
            clean = [s.strip() for s in (suggestions or []) if s and s.strip()][:3]
            if not clean:
                return json.dumps({"status": "error", "message": "No valid suggestions provided."})
            interaction = crud.update_interaction(db, target_id, {"ai_suggested_follow_ups": clean})
            if interaction is None:
                return json.dumps({"status": "error", "message": f"Interaction {target_id} not found."})
            return json.dumps(
                {"status": "ok", "ai_suggested_follow_ups": interaction.ai_suggested_follow_ups}, default=str
            )
        except Exception as exc:
            return json.dumps({"status": "error", "message": str(exc)})

    return [
        log_interaction,
        edit_interaction,
        get_interaction_details,
        search_hcp_history,
        suggest_follow_ups,
    ]
