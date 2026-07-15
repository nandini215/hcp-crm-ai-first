# Submission Checklist

## Repository

- [x] Frontend and backend in one GitHub repository
- [x] Root `README.md` — overview, features, tech stack, architecture,
      folder structure, installation, backend/frontend/database setup,
      environment variables, running instructions, API endpoints,
      LangGraph workflow, all 5 LangGraph tools, screenshot placeholders,
      future improvements
- [x] `backend/README.md` — backend-specific setup, endpoint reference, tools
- [x] `frontend/README.md` — frontend-specific setup, folder structure,
      response-contract mapping
- [x] `LICENSE`
- [x] `.gitignore` (Python, Node, env files, build/dist output, editor/OS files)
- [x] `docker-compose.yml` (optional convenience path — Postgres + backend +
      frontend, no hardcoded secrets)
- [x] `docs/architecture.png`
- [x] `docs/screenshots/` folder (screenshots to be added before final submit)
- [x] No `node_modules/`, `venv/`, `__pycache__/`, `.env`, `dist/`, or `build/`
      committed
- [x] No hardcoded API keys or secrets anywhere in source — `GROQ_API_KEY`
      and `DATABASE_URL` are read from environment variables, with
      `.env.example` committed as a template on both sides

## Before you push

- [ ] Run `pip install -r backend/requirements.txt` and
      `uvicorn app:app --reload` from a clean clone to confirm the backend
      boots
- [ ] Run `npm install && npm run dev` from a clean clone to confirm the
      frontend boots and reaches the backend
- [ ] Add real screenshots to `docs/screenshots/` (see that folder's README
      for the suggested set) and update the Screenshots table in the root
      README if you rename any files
- [ ] Double-check `backend/.env` and `frontend/.env` are **not** staged
      (`git status` should not list them — `.gitignore` already excludes them)
- [ ] Fill in your actual GitHub repo URL in the root README's
      `git clone <your-repo-url>` line

## Demo video (10–15 minutes)

- [ ] Frontend walkthrough — show the read-only form + AI Assistant chat panel
- [ ] Demo all 5 LangGraph tools working: `log_interaction`,
      `edit_interaction`, `get_interaction_details`, `search_hcp_history`,
      `suggest_follow_ups`
- [ ] Simple explanation of the code and project structure
- [ ] Brief summary of your understanding of the task

## Final submission

- [ ] GitHub repository link
- [ ] Demo video link
- [ ] Both submitted via the assignment's Google Form
