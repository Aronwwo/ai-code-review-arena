# STATUS

## Works
- Council and Arena reviews with mock provider, including multi-round Council and moderator summary.
- Required review mode selection + backend validation.
- Arena voting + ELO + rankings with cache invalidation.
- Refusal handling (retry, sanitize, fallback) with tests.

## Run
- Backend dev: `npm run dev:backend`
- Frontend dev: `npm run dev:frontend`
- Lint: `npm run lint`
- Build: `npm run build`
- Backend tests: `backend/.venv311/bin/python -m pytest backend/tests -v`
- E2E (Playwright): `npm run test:e2e`
