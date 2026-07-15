"""
LangGraph agent wiring.

Graph shape:

    START -> agent -> (conditional) -> tools -> agent -> ... -> END

`agent` calls the Groq LLM (bound with the 5 tools from tools.py) with the
running message list. `tools_condition` routes to the `tools` node whenever
the model's response contains tool calls, and to END once the model replies
with plain text and no further tool calls. `tools` executes whichever tools
the model requested via a LangGraph `ToolNode` and appends their results back
onto the message list before looping back to `agent`.

A fresh graph + tool set is built per request (`run_chat_agent`) so that the
request-scoped DB session and the small `ctx` dict tracking the "current"
interaction id are safely isolated between concurrent requests.
"""

import json
from typing import Annotated, Any, Dict, List, Optional, TypedDict

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from sqlalchemy.orm import Session

import crud
from llm import get_llm
from tools import build_tools

SYSTEM_PROMPT = """You are the AI Assistant embedded in a pharmaceutical CRM used to \
log Healthcare Professional (HCP) interactions. The "Interaction Details" form on \
screen is 100% controlled by you — the rep never types into it directly. You control \
it exclusively through the five tools available to you: log_interaction, \
edit_interaction, get_interaction_details, search_hcp_history, and suggest_follow_ups.

For every message from the rep:
1. Check the [Conversation context] note. If no interaction is being tracked yet, \
call `log_interaction` with every field you can extract from the message. \
`hcp_name` is required — use "Unknown HCP" only if truly no name was given.
2. If an interaction IS already being tracked, call `edit_interaction` with ONLY the \
fields the new message actually adds or changes. Never re-send fields that weren't \
mentioned and never invent values.
3. You may call `search_hcp_history` first when it would help — e.g. an HCP name is \
mentioned and recalling past sentiment or topics would produce a better record.
4. After logging or editing, if you can identify 1-3 concrete next steps that were \
NOT explicitly stated as the rep's own follow-up actions, call `suggest_follow_ups` \
once with your own suggestions.
5. Always finish with a short, natural, one-to-two sentence reply confirming exactly \
what was logged or changed. Reply in plain conversational text only — never raw JSON \
— and never call a tool after you have already produced your final reply text.

Field rules:
- interaction_type must be one of: Meeting, Call, Email, Conference, Virtual Visit.
- sentiment must be one of: positive, neutral, negative (infer from tone if not stated).
- materials_shared covers brochures/leaflets/literature; samples_distributed covers \
physical drug samples handed to the HCP.
- Dates may be natural language ("today", "tomorrow") or ISO — the tools parse them.
- Never fabricate a name, date, or detail the rep didn't state or clearly imply.
"""


class ChatAgentState(TypedDict, total=False):
    messages: Annotated[List[Any], add_messages]
    interaction_id: Optional[int]


def _build_context_note(interaction_id: Optional[int], existing: Optional[Dict[str, Any]]) -> str:
    if interaction_id and existing:
        return (
            f"[Conversation context]: interaction_id={interaction_id} is already being "
            f"tracked. Current record: {json.dumps(existing, default=str)}. Use "
            "edit_interaction for any new details in this message, not log_interaction."
        )
    return (
        "[Conversation context]: no interaction is being tracked yet in this "
        "conversation. Use log_interaction to create one."
    )


def _build_graph(db: Session, ctx: Dict[str, Any]):
    tools = build_tools(db, ctx)
    llm_with_tools = get_llm().bind_tools(tools)

    def agent_node(state: ChatAgentState) -> Dict[str, Any]:
        response = llm_with_tools.invoke(state["messages"])
        return {"messages": [response]}

    tool_node = ToolNode(tools)

    builder = StateGraph(ChatAgentState)
    builder.add_node("agent", agent_node)
    builder.add_node("tools", tool_node)
    builder.add_edge(START, "agent")
    builder.add_conditional_edges("agent", tools_condition, {"tools": "tools", END: END})
    builder.add_edge("tools", "agent")
    return builder.compile()


def run_chat_agent(
    db: Session, user_message: str, interaction_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Entry point used by app.py's /chat endpoint.

    React -> Redux -> FastAPI -> [this function] -> Groq LLM (tool-calling) ->
    LangGraph ToolNode (PostgreSQL writes via crud.py) -> structured result
    returned back up the stack.
    """
    existing_dict: Optional[Dict[str, Any]] = None
    if interaction_id:
        existing = crud.get_interaction(db, interaction_id)
        if existing is not None:
            existing_dict = crud.orm_to_dict(existing)
        else:
            interaction_id = None  # stale/unknown id — start a fresh interaction

    ctx: Dict[str, Any] = {"interaction_id": interaction_id}
    graph = _build_graph(db, ctx)

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(
            content=f"{_build_context_note(interaction_id, existing_dict)}\n\n"
            f"Rep's message: {user_message}"
        ),
    ]

    try:
        result = graph.invoke(
            {"messages": messages, "interaction_id": interaction_id},
            config={"recursion_limit": 12},
        )
        final_messages = result.get("messages", [])
    except Exception:
        # Graph blew its recursion budget or the LLM call itself failed —
        # fall back to a plain log of the raw message rather than erroring out.
        final_messages = []

    reply = ""
    for msg in reversed(final_messages):
        if isinstance(msg, AIMessage) and (msg.content or "").strip():
            reply = msg.content.strip()
            break
    if not reply:
        reply = "Got it — I've updated the interaction record."

    final_interaction_id = ctx.get("interaction_id")
    interaction = crud.get_interaction(db, final_interaction_id) if final_interaction_id else None

    if interaction is None:
        # Safety net: the model never actually called a logging tool — log the
        # raw note verbatim so the rep never sees a silent no-op.
        interaction = crud.create_interaction(
            db, {"hcp_name": "Unknown HCP", "topics_discussed": user_message}
        )

    crud.create_chat_message(db, "user", user_message, interaction.id)
    crud.create_chat_message(db, "assistant", reply, interaction.id)

    return {"reply": reply, "interaction": interaction}
