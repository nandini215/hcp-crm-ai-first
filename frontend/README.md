# HCP CRM — Frontend

React (Vite) + Redux Toolkit + Material UI + Axios frontend for the AI-first
Healthcare Professional CRM.

## Setup

```bash
npm install
npm run dev        # http://localhost:5173
```

Copy the example env file and set the backend URL (the FastAPI backend
mounts every route at the root — `/chat`, `/interaction`, `/hcp/{name}` —
there is **no** `/api/v1` prefix):

```bash
cp .env.example .env
```

```
VITE_API_BASE_URL=http://localhost:8000
```

## Key design rule

The **Interaction Details** form (`InteractionForm.jsx`) is 100% read-only.
Every field renders `disabled` and is driven exclusively by Redux state in
`redux/interactionSlice.js`. The only reducer that can change form data is
`setInteractionFromAI`, dispatched from `ChatPanel.jsx` after a successful
`POST /chat` response. There is no manual-edit path in the UI by design.

## Folder structure

```
src/
├── app/store.js              # Redux store
├── redux/
│   ├── interactionSlice.js   # Read-only form state (AI-populated only)
│   └── chatSlice.js          # Chat conversation state
├── services/
│   ├── axiosInstance.js
│   └── chatService.js        # POST /chat
├── utils/
│   └── caseMapper.js         # snake_case (API) <-> camelCase (Redux) boundary
├── theme/theme.js            # MUI theme, Inter font
├── components/
│   ├── Header.jsx
│   ├── InteractionForm.jsx   # Left panel
│   └── ChatPanel.jsx         # Right panel
├── pages/Home.jsx
├── App.jsx
└── main.jsx
```

## `/chat` response contract

FastAPI/Pydantic return **snake_case** keys, matching the SQLAlchemy model
columns directly:

```json
{
  "reply": "Logged your meeting with Dr. Smith. Positive sentiment recorded.",
  "interaction": {
    "id": 12,
    "hcp_name": "Dr. Smith",
    "interaction_type": "Meeting",
    "date": "2026-07-14",
    "time": "14:30:00",
    "attendees": "Dr. Smith",
    "topics_discussed": "Product X efficacy",
    "materials_shared": ["Product X Brochure"],
    "samples_distributed": [],
    "sentiment": "positive",
    "outcomes": "Agreed to review clinical data",
    "follow_up_actions": "",
    "ai_suggested_follow_ups": ["Schedule follow-up meeting in 2 weeks"]
  }
}
```

`services/chatService.js` passes the raw `interaction` object through
`utils/caseMapper.js` (`mapInteractionFromApi`) before it ever reaches Redux,
converting every key to camelCase and normalizing `"HH:MM:SS"` time strings
down to `"HH:MM"` for the native `<input type="time">` field. Every
component downstream (`interactionSlice`, `InteractionForm`) only ever sees
the camelCase shape — the snake_case ↔ camelCase boundary is isolated to
that one file.
