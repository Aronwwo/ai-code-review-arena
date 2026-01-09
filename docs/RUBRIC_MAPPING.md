# Rubric Mapping - AI Code Review Arena

This document maps each rubric requirement to the implementation and how to test it.

## A. One-Command Dev Setup

| Requirement | Implementation | How to Test |
|-------------|---------------|-------------|
| `npm run setup` installs deps, runs migrations, seeds admin | `scripts/setup.js` | Run `npm run setup` - should complete without errors |
| `npm run dev` starts frontend + backend | `scripts/dev.js` | Run `npm run dev` - both servers start |
| Print URLs on start | `scripts/dev.js` outputs URLs | Check console output |
| Detect package manager | `scripts/setup.js` checks for lock files | Auto-detected |

## B. Admin Account (Idempotent)

| Requirement | Implementation | How to Test |
|-------------|---------------|-------------|
| Email: admin@local.test | `backend/scripts/seed_admin.py` | Login with admin@local.test |
| Password: Admin123! | `backend/scripts/seed_admin.py` | Password works on login |
| Username: admin | `backend/scripts/seed_admin.py` | Check user profile |
| Idempotent creation | `seed_admin.py` checks if exists first | Run setup twice - no error |

## C. UI - Landing Page (Logged Out)

| Requirement | Implementation | How to Test |
|-------------|---------------|-------------|
| Dark SaaS style | `frontend/src/pages/Landing.tsx` + Tailwind dark mode | View landing page |
| Navbar: app name left, Login/Sign Up right | `frontend/src/pages/Landing.tsx` | Check header |
| Hero title + subtitle + 2 CTAs | Lines 35-75 of Landing.tsx | Visual inspection |
| Features: 2x3 cards with icons | Lines 77-149 of Landing.tsx | 6 feature cards visible |
| Hover/focus states | Tailwind `hover:` classes | Hover over cards |
| How it Works: 4 numbered cards | Lines 151-233 of Landing.tsx | 4 steps visible |
| Footer with API Docs link | Lines 235-245 of Landing.tsx | Link to /docs |

## D. UI - Dashboard (Logged In)

| Requirement | Implementation | How to Test |
|-------------|---------------|-------------|
| Sidebar layout | `frontend/src/components/DashboardLayout.tsx` | Login and view sidebar |
| Tabs navigation | Tabs in ProjectDetail.tsx, ReviewDetail.tsx | Click through tabs |
| Responsive | Tailwind responsive classes `md:` `lg:` | Resize browser |
| Clean spacing | Gap/padding utilities | Visual inspection |
| A11y focus rings | `focus:ring-2` classes | Tab through elements |

## E. AI - Local via Ollama

| Requirement | Implementation | How to Test |
|-------------|---------------|-------------|
| Ollama provider | `backend/app/providers/ollama.py` | Start Ollama, run review |
| Model discovery from /api/tags | `OllamaProvider.list_models()` | GET /api/ollama/models |
| TTL cache 60s | `backend/app/api/ollama.py` line 50 | Second request shows cached=true |
| Council mode (4 agents -> Moderator) | `backend/app/orchestrators/review.py` | Start review with all agents |
| Arena mode (Prosecutor vs Defender) | `backend/app/orchestrators/conversation.py` | Start debate on issue |
| Strict JSON schema | Pydantic models in `app/models/review.py` | Invalid JSON triggers repair |
| 1 repair attempt | `orchestrators/review.py` parse_with_repair | Check logs for retry |

## F. External Providers (Optional)

| Requirement | Implementation | How to Test |
|-------------|---------------|-------------|
| User-supplied API key | Settings page stores in localStorage | Add key in Settings |
| Multiple providers | OpenAI, Anthropic, Groq, Gemini, Cloudflare | Select provider in Settings |
| API keys encrypted at rest | Fernet encryption in providers | Keys stored encrypted |
| Test connection endpoint | POST /providers/{id}/test | Click "Test" in Settings |
| Fallback to Ollama/Mock | `ProviderRouter.get_provider()` | External fails -> uses fallback |

## G. Backend Quality

| Requirement | Implementation | How to Test |
|-------------|---------------|-------------|
| Business logic + edge cases | `backend/app/api/*.py` | Run pytest |
| GET/POST/PUT/DELETE | All CRUD operations | API docs at /docs |
| Correct HTTP status codes | 200/201/204/400/401/403/404/409 | Check response codes |
| DB integration (ORM) | SQLModel in `app/models/` | No raw SQL anywhere |
| Security (authz) | JWT + ownership checks | Access other user's project -> 403 |
| Performance + caching | Redis/in-memory cache | Check cache headers |
| Indexes on user_id/project_id/created_at | Alembic migration | Check DB schema |

## H. Frontend Quality

| Requirement | Implementation | How to Test |
|-------------|---------------|-------------|
| Intuitive UI | Clean design patterns | User testing |
| Responsive | Tailwind breakpoints | Resize browser |
| Forms + validation | React Hook Form + Zod | Submit invalid form |
| Dynamic updates (React Query) | useQuery/useMutation everywhere | Data updates after mutation |
| Toasts | Sonner toast library | Perform actions |
| Loading/empty states | Skeleton components, EmptyState | Slow network / no data |
| Backend data rendering | All pages fetch from API | Check network tab |
| Refresh after mutations | invalidateQueries calls | Create item -> list updates |

## I. Security

| Requirement | Implementation | How to Test |
|-------------|---------------|-------------|
| bcrypt hashing | `app/utils/auth.py` passlib | Check password storage |
| JWT auth | `app/utils/auth.py` python-jose | Check tokens |
| Ownership checks | API endpoints check user_id | Access other's resource |
| ORM only (no raw SQL) | SQLModel everywhere | Grep for "execute(" |
| Input validation | Pydantic models | Send malformed data |
| XSS safe (no dangerouslySetInnerHTML) | None in codebase | Grep for "dangerously" |
| Upload security | File validation in api/files.py | Upload .exe -> rejected |

## J. Performance

| Requirement | Implementation | How to Test |
|-------------|---------------|-------------|
| In-memory TTL cache: Ollama models | `app/utils/cache.py` | Check cached=true in response |
| In-memory TTL cache: provider responses | Same cache system | Second request faster |
| DB indexes | SQLModel index=True | Check DB schema |
| Pagination | skip/limit on list endpoints | Large dataset |

## K. Documentation

| Requirement | Implementation | How to Test |
|-------------|---------------|-------------|
| README: setup/dev/test commands | README.md Quick Start section | Follow instructions |
| README: troubleshooting | README.md Troubleshooting section | Common issues covered |
| RUBRIC_MAPPING.md | This file | Present |

---

## Testing Commands

```bash
# Setup
npm run setup

# Development
npm run dev

# Backend tests
cd backend && venv/Scripts/pytest tests/ -v

# Smoke test (with servers running)
cd backend && venv/Scripts/python -c "
import httpx
BASE = 'http://localhost:8000'
r = httpx.post(f'{BASE}/auth/login', json={'email': 'admin@local.test', 'password': 'Admin123!'})
print('Login:', 'OK' if r.status_code == 200 else 'FAIL')
"
```

## File Locations

| Feature | Primary Files |
|---------|--------------|
| Root scripts | `package.json`, `scripts/setup.js`, `scripts/dev.js` |
| Admin seed | `backend/scripts/seed_admin.py` |
| Landing page | `frontend/src/pages/Landing.tsx` |
| Dashboard | `frontend/src/components/DashboardLayout.tsx` |
| Ollama provider | `backend/app/providers/ollama.py` |
| Cache | `backend/app/utils/cache.py` |
| Review orchestration | `backend/app/orchestrators/review.py` |
| Mock provider | `backend/app/providers/mock.py` |
| Auth | `backend/app/utils/auth.py`, `backend/app/api/auth.py` |
| API endpoints | `backend/app/api/*.py` |
