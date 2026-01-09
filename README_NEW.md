# AI Code Review Arena 🏟️

A professional web application providing multi-agent AI code review with debate capabilities. Upload code, get comprehensive reviews from specialized AI agents (General, Security, Performance, Style), and watch them debate issues in Council or Arena mode.

**100% Free & Local** - Powered by Ollama for complete privacy and zero API costs.

## ✨ Features

### 🤖 Multi-Agent Code Review
- **4 Specialized Agents**: General (best practices), Security (vulnerabilities), Performance (optimization), Style (formatting)
- **Moderator Agent**: Summarizes discussions and renders verdicts
- **Customizable Models**: Choose different Ollama models for each agent

### 💬 Agent Conversations
- **Council Mode**: Agents cooperatively discuss and converge on recommendations
- **Arena Mode**: Prosecutor vs Defender debate with Moderator verdict
- **Real-time Transcripts**: View full conversation history

### 🎨 Professional UI/UX
- **Modern Design**: Built with React 18 + TypeScript + Tailwind CSS + shadcn/ui
- **Dark Mode**: Persistent theme toggle (default: dark)
- **Responsive**: Mobile-first design, works on all devices
- **Loading States**: Skeleton loaders and spinners
- **Empty States**: Helpful guidance when no data
- **Toast Notifications**: Real-time feedback for all actions

### 🔒 Security & Privacy
- **100% Local**: All AI processing with Ollama (or use Mock provider for testing)
- **JWT Authentication**: Secure token-based auth with bcrypt password hashing
- **Input Validation**: Pydantic (backend) + Zod (frontend)
- **CORS Protection**: Configurable allowlist
- **File Upload Security**: Extension allowlist, size limits, sanitization

### ⚡ Performance
- **TTL Caching**: 60s cache for Ollama model discovery
- **React Query**: Optimistic updates, auto-refetch
- **Code Splitting**: Fast initial load
- **Syntax Highlighting**: Fast code display with react-syntax-highlighter

## 🚀 Quick Start (Local Development)

### Prerequisites

- **Python 3.10+** ([Download](https://python.org))
- **Node.js 18+** ([Download](https://nodejs.org))
- **Ollama** (optional, for local LLMs) ([Download](https://ollama.ai))

### 1. Clone & Setup

```bash
# Clone repository
cd ai-code-review-arena

# Create .env file (if not exists)
cp .env.example .env
```

### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (macOS/Linux)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Start backend server
uvicorn app.main:app --reload --port 8000
```

**Backend will run on http://localhost:8000**
- API Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/health

### 3. Frontend Setup

Open a new terminal:

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

**Frontend will run on http://localhost:3000**

### 4. (Optional) Install Ollama Models

If you want to use real local LLMs instead of the Mock provider:

```bash
# Install Ollama from https://ollama.ai

# Pull a code-focused model
ollama pull codellama

# Or pull other models
ollama pull llama3
ollama pull mistral
ollama pull qwen2.5-coder

# Verify Ollama is running
curl http://localhost:11434/api/tags
```

## 📖 Usage Guide

### 1. Register & Login

1. Open http://localhost:3000
2. Click "Sign Up" and create an account
   - Email: your@email.com
   - Username: your choice (min 3 chars)
   - Password: min 8 characters
3. Login with your credentials

### 2. Create a Project

1. Click "New Project" button
2. Enter project name and description
3. Click "Create Project"

### 3. Add Code Files

1. Click on your project
2. Go to "Files" tab
3. Click "Add File"
4. **Option A**: Upload a file (supports .py, .js, .ts, .java, .cpp, .go, .rs, etc.)
5. **Option B**: Paste code directly
6. Click "Add File"

### 4. Run a Code Review

1. Click "Run Review" button
2. Review will start with all 4 agents (General, Security, Performance, Style)
3. Wait for completion (uses Mock provider by default)
4. View results in "Reviews" tab

### 5. View Issues & Recommendations

1. Click on a completed review
2. See issues by severity (low, medium, high, critical)
3. Filter by category (security, performance, style, bug, maintainability)
4. Read detailed recommendations

### 6. Configure AI Models (Settings)

1. Go to Settings (user menu → Settings)
2. See available Ollama models
3. Assign models to each agent:
   - General Agent → codellama
   - Security Agent → codellama
   - Performance Agent → codellama
   - Style Agent → codellama
   - Moderator → codellama
4. Click "Save Settings"
5. Settings stored in browser localStorage

## 🏗️ Project Structure

```
ai-code-review-arena/
├── backend/                    # FastAPI backend
│   ├── app/
│   │   ├── main.py            # Application entry point
│   │   ├── config.py          # Settings (Pydantic)
│   │   ├── database.py        # SQLModel engine
│   │   ├── models/            # SQLModel database models
│   │   ├── api/               # API endpoints
│   │   │   ├── auth.py        # /auth/register, /auth/login, /auth/me
│   │   │   ├── projects.py    # /projects CRUD
│   │   │   ├── files.py       # /projects/{id}/files
│   │   │   ├── reviews.py     # /projects/{id}/reviews
│   │   │   ├── ollama.py      # /api/ollama/models (NEW!)
│   │   │   └── conversations.py
│   │   ├── services/          # Business logic
│   │   ├── providers/         # LLM providers (Ollama, Mock, Groq, Gemini, etc.)
│   │   │   └── ollama.py      # Ollama integration with list_models()
│   │   ├── orchestrators/     # Review orchestration (Council/Arena)
│   │   └── utils/
│   │       ├── auth.py        # JWT helpers
│   │       └── cache.py       # TTL cache manager
│   ├── alembic/               # Database migrations
│   ├── requirements.txt
│   └── data/                  # SQLite database (auto-created)
│
├── frontend/                  # React frontend
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx            # Routing
│   │   ├── components/
│   │   │   ├── ui/            # shadcn/ui components
│   │   │   ├── Layout.tsx
│   │   │   ├── DashboardLayout.tsx  # Sidebar + Header
│   │   │   ├── CodeViewer.tsx       # Syntax highlighting (NEW!)
│   │   │   └── EmptyState.tsx       # Reusable empty states (NEW!)
│   │   ├── pages/
│   │   │   ├── Landing.tsx          # Public landing page (NEW!)
│   │   │   ├── Login.tsx            # Updated UI
│   │   │   ├── Register.tsx         # Updated UI
│   │   │   ├── Projects.tsx         # Dialog + Skeleton + EmptyState
│   │   │   ├── ProjectDetail.tsx    # Tabs + Dialogs + CodeViewer
│   │   │   ├── ReviewDetail.tsx
│   │   │   └── Settings.tsx         # Model selection (NEW!)
│   │   ├── contexts/
│   │   │   ├── AuthContext.tsx
│   │   │   └── ThemeContext.tsx     # Dark mode (NEW!)
│   │   ├── lib/
│   │   │   ├── api.ts         # Axios instance
│   │   │   └── utils.ts       # cn() helper
│   │   └── types/
│   ├── components.json        # shadcn/ui config (NEW!)
│   └── package.json
│
├── docker-compose.yml         # Docker setup (optional)
├── .env.example               # Environment template
└── README.md                  # This file
```

## 🔧 Configuration

### Environment Variables

**Backend** (`.env` in root or `backend/` directory):

```env
# Database
DATABASE_URL=sqlite:///./data/code_review.db

# Redis (optional - falls back to in-memory cache)
REDIS_URL=redis://localhost:6379/0

# JWT
JWT_SECRET_KEY=your_secret_key_change_in_production
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# CORS
CORS_ORIGINS=http://localhost:3000,http://localhost:5173

# LLM Providers
OLLAMA_BASE_URL=http://localhost:11434
DEFAULT_PROVIDER=mock
DEFAULT_MODEL=codellama

# Cache
CACHE_TTL_SECONDS=60

# Environment
ENVIRONMENT=development
DEBUG=true
```

**Frontend** (`frontend/.env`):

```env
VITE_API_URL=http://localhost:8000
```

### LLM Provider Configuration

**Mock Provider (Default - No Setup Required)**

Perfect for testing and development. Returns realistic but fake review data.

```env
DEFAULT_PROVIDER=mock
```

**Ollama (Local, Free, Private)**

1. Install Ollama: https://ollama.ai
2. Pull models: `ollama pull codellama`
3. Configure:

```env
DEFAULT_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
DEFAULT_MODEL=codellama
```

**Other Providers (Optional)**

- Groq (fast, free tier)
- Google Gemini (free tier)
- Cloudflare Workers AI

See original README for full provider setup.

## 🎯 Key Features Implementation

### ✅ Frontend (shadcn/ui + Professional Look)

- [x] **Landing Page** (`/src/pages/Landing.tsx`)
  - Hero with title + description + CTAs
  - Features grid (2x3 cards with icons)
  - "How It Works" (4 steps)
  - Footer with API Docs link

- [x] **Dashboard Layout** (`/src/components/DashboardLayout.tsx`)
  - Sidebar navigation (Projects, Settings)
  - User dropdown menu
  - Dark mode toggle
  - Mobile hamburger menu

- [x] **Auth Pages** (Login, Register)
  - Full-screen layout with header
  - Form validation (Zod)
  - Loading states

- [x] **Components** (shadcn/ui)
  - Button, Card, Input, Label, Textarea
  - Dialog, Tabs, Select, Separator
  - Skeleton, Badge, Table, DropdownMenu
  - Toaster (sonner)

- [x] **Theme Provider**
  - Dark/Light modes
  - localStorage persistence
  - Default: dark

- [x] **Code Viewer** (`/src/components/CodeViewer.tsx`)
  - Syntax highlighting (react-syntax-highlighter)
  - Copy to clipboard
  - Line numbers
  - Highlight specific lines

- [x] **Empty States** (`/src/components/EmptyState.tsx`)
  - Reusable component
  - Icon + Title + Description + CTA

- [x] **Loading States**
  - Skeleton loaders (Projects, ProjectDetail)
  - Spinners for buttons

- [x] **Settings Page** (`/src/pages/Settings.tsx`)
  - Fetch Ollama models via `/api/ollama/models`
  - Model selection per agent (dropdown)
  - Save to localStorage
  - TTL cache indicator

### ✅ Backend (Ollama + TTL Cache)

- [x] **Ollama Endpoint** (`/app/api/ollama.py`)
  - `GET /api/ollama/models` - lists models with 60s TTL cache
  - `GET /api/ollama/health` - checks Ollama availability
  - Requires authentication
  - Clear error messages (503 when Ollama unavailable)

- [x] **Ollama Provider** (`/app/providers/ollama.py`)
  - `list_models()` method - fetches from `/api/tags`
  - Removes duplicates, sorts

- [x] **Cache Manager** (`/app/utils/cache.py`)
  - Redis or in-memory fallback
  - TTL support (60s for models)
  - Thread-safe

### ✅ Security

- [x] **Authentication**: JWT + bcrypt (passlib)
- [x] **Validation**: Pydantic (backend) + Zod (frontend)
- [x] **SQL Injection**: SQLAlchemy ORM (no raw SQL)
- [x] **XSS**: React auto-escaping
- [x] **CORS**: Configurable allowlist
- [x] **File Upload**:
  - Extension allowlist
  - Size limits (1MB/file, 50 files, 25MB total)
  - Filename sanitization

### ✅ UX Excellence

- [x] **Loading States**: Skeleton, spinners
- [x] **Empty States**: Helpful CTAs
- [x] **Error Handling**: Toast notifications, inline errors
- [x] **Optimistic Updates**: React Query invalidation
- [x] **Responsive Design**: Mobile-first
- [x] **Accessibility**: ARIA labels, focus rings

## 🧪 Testing

### Backend

```bash
cd backend
pytest                  # Run all tests
pytest -v               # Verbose output
pytest --cov=app        # With coverage
```

### Frontend

```bash
cd frontend
npm test                # Run all tests
npm run test:ui         # Interactive test UI
npm run test:coverage   # With coverage
```

## 🐛 Troubleshooting

### "Ollama is not available"

**Problem**: Settings page shows "Ollama not available"

**Solution**:
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# If not, start Ollama
ollama serve

# Or install from https://ollama.ai
```

### Port Already in Use

**Problem**: Port 8000 or 3000 is occupied

**Solution (Windows)**:
```bash
# Find process on port 8000
netstat -ano | findstr :8000

# Kill process (replace PID)
taskkill /PID <PID> /F
```

**Solution (macOS/Linux)**:
```bash
# Find and kill process on port 8000
lsof -ti:8000 | xargs kill -9
```

### Frontend Build Errors

**Problem**: Module not found errors

**Solution**:
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
```

### Database Migration Errors

**Problem**: Database schema out of sync

**Solution**:
```bash
cd backend
# WARNING: Deletes all data
rm -rf data/code_review.db
alembic upgrade head
```

## 📚 API Documentation

Interactive API documentation available at:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Key Endpoints

**Auth**
- `POST /auth/register` → 201 {user, token}
- `POST /auth/login` → 200 {access_token, user}
- `GET /auth/me` (protected) → 200 {user}

**Projects**
- `GET /projects` (protected) → 200 {projects: [...]}
- `POST /projects` (protected) → 201 {project}
- `GET /projects/{id}` (protected) → 200 {project, files, reviews}

**Files**
- `POST /projects/{id}/files` (protected) → 201 {file}
- `GET /projects/{id}/files` (protected) → 200 {files: [...]}

**Reviews**
- `POST /projects/{id}/reviews` (protected) → 201 {review}
- `GET /reviews/{id}` (protected) → 200 {review, issues, conversation}

**Ollama (NEW!)**
- `GET /api/ollama/models` (protected) → 200 {models: [...], cached: bool}
- `GET /api/ollama/health` (protected) → 200 {status, ollama_url, available}

## 🚢 Production Deployment

### Security Checklist

- [ ] Change `JWT_SECRET_KEY` to strong random value (`openssl rand -hex 32`)
- [ ] Set `ENVIRONMENT=production`
- [ ] Set `DEBUG=false`
- [ ] Use PostgreSQL instead of SQLite
- [ ] Enable HTTPS/TLS
- [ ] Configure CORS to your domain only
- [ ] Review and rotate API keys
- [ ] Set up monitoring and logging
- [ ] Configure backups

### Docker Deployment (Optional)

```bash
# Build and run with Docker Compose
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

## 🤝 Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Run linters (`npm run lint`, `black app`, `ruff check app`)
6. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details

## 🙏 Credits

Built with:
- [FastAPI](https://fastapi.tiangolo.com/)
- [React](https://react.dev/)
- [shadcn/ui](https://ui.shadcn.com/)
- [TailwindCSS](https://tailwindcss.com/)
- [TanStack Query](https://tanstack.com/query)
- [Ollama](https://ollama.ai/)

---

**Ready to start?** Follow the Quick Start guide and visit http://localhost:3000 🚀
