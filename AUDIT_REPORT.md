# AUDIT_REPORT

## Discovery

### Stack
- Frontend: React + TypeScript + Vite + Tailwind (frontend/)
- Backend: FastAPI + SQLModel (backend/)
- DB: SQLite (default `sqlite:///./data/code_review.db`), E2E uses `sqlite:///./data/e2e.db`

### Package managers and commands
- JS: `npm install`, `npm run dev:frontend`, `npm run lint`, `npm run build`, `npm run test:e2e`
- Python: `backend/.venv311/bin/pip install -r backend/requirements.txt`, `backend/.venv311/bin/python -m pytest backend/tests -v`

### Code map (key areas)
- Auth: `backend/app/api/auth.py`, `backend/app/utils/auth.py`
- Projects/files: `backend/app/api/projects.py`, `backend/app/api/files.py`
- Review orchestration: `backend/app/orchestrators/review.py`, `backend/app/orchestrators/conversation.py`
- Provider routing: `backend/app/providers/router.py` (source of truth), `backend/app/providers/mock.py`
- DB models: `backend/app/models/*.py` (review, arena, project, file, conversation)
- ELO/rankings: `backend/app/utils/elo.py`, `backend/app/api/arena.py`
- UI wizard/tabs: `frontend/src/components/ReviewConfigDialog.tsx`, `frontend/src/pages/ReviewDetail.tsx`

### Prompt source of truth
- `backend/app/orchestrators/conversation.py`
- `backend/app/providers/router.py`

## Evidence run
- Lint: `EVIDENCE/lint.log`
- Build: `EVIDENCE/build.log`
- Unit/Integration: `EVIDENCE/test.log`
- E2E (Playwright): `EVIDENCE/e2e.log` + `EVIDENCE/playwright/*`

## PASS/FAIL (Spec 1-10)

| # | Requirement | Status | Evidence |
| --- | --- | --- | --- |
| 1 | Login -> create project -> upload files to review | PASS | `EVIDENCE/e2e.log` |
| 2 | Mode selection required + backend validation | PASS | `EVIDENCE/e2e.log`, `EVIDENCE/test.log` |
| 3 | Council 4 roles, sequential rounds | PASS | `EVIDENCE/test.log` |
| 4 | Prompt+history, messages saved, moderator summary default | PASS | `EVIDENCE/test.log`, `EVIDENCE/e2e.log` |
| 5 | Moderator summary + JSON issues[] | PASS | `EVIDENCE/test.log` |
| 6 | Arena A/B config + parallel execution | PASS | `EVIDENCE/e2e.log`, `EVIDENCE/test.log` |
| 7 | Vote + ELO | PASS | `EVIDENCE/test.log`, `EVIDENCE/e2e.log` |
| 8 | Tabs: Issues / AI Discussions / Files | PASS | `EVIDENCE/e2e.log` |
| 9 | Arena rankings stats + filter + caching | PASS | `EVIDENCE/test.log`, `EVIDENCE/e2e.log` |
| 10 | Refusal handling + tests | PASS | `EVIDENCE/test.log` |

## Scores
- Frontend: 5/5
- Backend: 5/5
- Additional: 4/4
