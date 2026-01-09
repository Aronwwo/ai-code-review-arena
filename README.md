# AI Code Review Arena 🏟️

A production-quality web application that provides multi-agent AI code review with debate and conversation capabilities. Upload your code, get it reviewed by multiple specialized AI agents (General, Security, Performance, Style), and watch them debate issues in cooperative or adversarial modes.

## Features

- 🤖 **Multi-Agent Code Review**: Specialized agents analyze your code from different perspectives
- 💬 **Agent Conversations**:
  - **Council Mode**: Agents cooperatively discuss and converge on recommendations
  - **Arena Mode**: Prosecutor vs Defender debate specific issues with a Moderator verdict
- 🔒 **Secure**: JWT authentication, rate limiting, input validation
- 🎨 **Clean UI**: Modern React interface with TailwindCSS and shadcn/ui
- 🔌 **Pluggable LLM Providers**: Groq, Gemini, Cloudflare Workers AI, Ollama, or Mock
- 💰 **Free-Tier Friendly**: Works with free API tiers or completely offline with Ollama
- 🐳 **Docker Ready**: Full Docker Compose setup for one-command deployment
- 📊 **Persistence**: SQLite (default) or PostgreSQL with Redis caching
- ✅ **Tested**: Comprehensive backend and frontend tests

## Quick Start (One Command)```bash# Install dependencies + seed admin + run migrationsnpm run setup# Start both frontend and backendnpm run dev```**Admin Credentials:** admin@local.test / Admin123!**URLs:**- Frontend: http://localhost:5173- Backend: http://localhost:8000- API Docs: http://localhost:8000/docs
## Quick Start (10 Minutes)

### Prerequisites

- **Docker & Docker Compose** (recommended) OR
- **Python 3.11+** and **Node.js 18+** (for local development)
- **Ollama** (optional, for local LLM): [Download here](https://ollama.ai)

### Option 1: Docker Compose (Easiest)

```bash
# 1. Clone and navigate to the project
cd ai-code-review-arena

# 2. Copy environment configuration
cp .env.example .env

# 3. (Optional) Edit .env to add LLM API keys
# If you skip this, the app will use MockProvider for demo

# 4. Start all services
docker-compose up -d

# 5. Wait for services to be healthy (30 seconds)
docker-compose ps

# 6. Open your browser
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

That's it! The app is now running with:
- Frontend on port 3000
- Backend API on port 8000
- Redis on port 6379
- SQLite database in `backend/data/`

### Option 2: Local Development (Without Docker)

#### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy and configure environment
cp ../.env.example .env
# Edit .env as needed

# Initialize database
alembic upgrade head

# Run development server
uvicorn app.main:app --reload --port 8000
```

Backend will be available at http://localhost:8000

#### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Copy and configure environment
cp ../.env.example .env
# Make sure VITE_API_URL=http://localhost:8000

# Run development server
npm run dev
```

Frontend will be available at http://localhost:3000

#### Redis (Optional but Recommended)

```bash
# Install Redis (varies by OS)
# macOS: brew install redis
# Ubuntu: sudo apt-get install redis-server
# Windows: Use Docker or WSL

# Start Redis
redis-server

# Or use Docker:
docker run -d -p 6379:6379 redis:7-alpine
```

If you don't run Redis, the app will use in-memory caching (data lost on restart).

## LLM Provider Setup

The app supports multiple LLM providers. Configure at least one for full functionality:

### Mock Provider (Default - No Setup Required)

Perfect for testing and demos. Returns realistic but fake review data.

```env
DEFAULT_PROVIDER=mock
```

### Ollama (Local, Free, Private)

1. Install Ollama: https://ollama.ai
2. Pull a model: `ollama pull codellama` or `ollama pull llama3`
3. Configure:

```env
DEFAULT_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
DEFAULT_MODEL=codellama
```

### Groq (Fast, Free Tier)

1. Sign up at https://console.groq.com
2. Get API key
3. Configure:

```env
GROQ_API_KEY=your_api_key_here
DEFAULT_PROVIDER=groq
DEFAULT_MODEL=mixtral-8x7b-32768
```

### Google Gemini (Free Tier)

1. Get API key: https://makersuite.google.com/app/apikey
2. Configure:

```env
GEMINI_API_KEY=your_api_key_here
DEFAULT_PROVIDER=gemini
DEFAULT_MODEL=gemini-1.5-flash
```

### Cloudflare Workers AI

1. Get Cloudflare account and API token
2. Configure:

```env
CLOUDFLARE_API_TOKEN=your_token
CLOUDFLARE_ACCOUNT_ID=your_account_id
DEFAULT_PROVIDER=cloudflare
DEFAULT_MODEL=@cf/meta/llama-3-8b-instruct
```

## Usage Guide

### 1. Register and Login

- Navigate to http://localhost:3000
- Click "Sign Up" and create an account
- Login with your credentials

### 2. Create a Project

- Click "New Project"
- Enter project name and description
- Click "Create"

### 3. Add Code Files

- Click on your project
- Click "Add File"
- Paste code or upload a file
- Specify the programming language
- Click "Save"

### 4. Run a Code Review

- Click "Run Review"
- Select which agents to include:
  - **General**: Overall code quality and best practices
  - **Security**: Security vulnerabilities and risks
  - **Performance**: Performance issues and optimization opportunities
  - **Style**: Code style and formatting consistency
- Click "Start Review"
- Wait for the review to complete

### 5. View Issues

- Browse the issues list
- Filter by severity (info, warning, error)
- Filter by category (security, performance, style, etc.)
- Click on an issue to see details and suggestions

### 6. Launch Agent Conversations

#### Council Mode (Cooperative)

- Click "Start Council Discussion"
- Agents discuss the project/file/issue cooperatively
- Moderator summarizes consensus recommendations
- View the conversation transcript and summary

#### Arena Mode (Adversarial Debate)

- Click "Debate This Issue" on any issue
- Prosecutor argues why the issue is serious
- Defender argues it's acceptable in context
- Moderator renders a verdict
- Issue is updated with verdict (confirmed/severity/comment)

## Project Structure

```
ai-code-review-arena/
├── backend/                 # FastAPI backend
│   ├── app/
│   │   ├── main.py         # Application entry point
│   │   ├── config.py       # Configuration and settings
│   │   ├── models/         # SQLModel database models
│   │   ├── api/            # API endpoints
│   │   ├── services/       # Business logic
│   │   ├── providers/      # LLM provider implementations
│   │   ├── orchestrators/  # Review and conversation orchestration
│   │   └── utils/          # Utilities (auth, caching, etc.)
│   ├── tests/              # Pytest tests
│   ├── alembic/            # Database migrations
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/               # React frontend
│   ├── src/
│   │   ├── components/    # React components
│   │   ├── pages/         # Page components
│   │   ├── lib/           # Utilities and API client
│   │   ├── hooks/         # Custom React hooks
│   │   └── types/         # TypeScript types
│   ├── tests/             # Vitest tests
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml     # Docker orchestration
├── .env.example          # Environment template
├── README.md             # This file
└── DECISIONS.md          # Architecture decisions
```

## API Documentation

Interactive API documentation is available at:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Example API Usage

#### Register a User

```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "secure_password",
    "username": "coder123"
  }'
```

#### Login

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "secure_password"
  }'
# Returns: { "access_token": "...", "token_type": "bearer" }
```

#### Create a Project (Authenticated)

```bash
curl -X POST http://localhost:8000/projects \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -d '{
    "name": "My Web App",
    "description": "A React application"
  }'
```

#### Start a Review

```bash
curl -X POST http://localhost:8000/projects/1/reviews \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -d '{
    "agent_roles": ["general", "security", "performance"],
    "provider": "ollama",
    "model": "codellama"
  }'
```

## Testing

### Backend Tests

```bash
cd backend
pytest                          # Run all tests
pytest -v                       # Verbose output
pytest tests/test_auth.py      # Specific test file
pytest --cov=app               # With coverage report
```

### Frontend Tests

```bash
cd frontend
npm test                       # Run all tests
npm run test:ui               # Interactive test UI
npm run test:coverage         # With coverage report
```

## Development

### Backend Development

```bash
cd backend

# Install development dependencies
pip install -r requirements-dev.txt

# Format code
black app tests

# Lint code
ruff check app tests

# Type checking
mypy app

# Create a new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1
```

### Frontend Development

```bash
cd frontend

# Format code
npm run format

# Lint code
npm run lint

# Type checking
npm run type-check

# Build for production
npm run build

# Preview production build
npm run preview
```

## Troubleshooting

### "Connection refused" errors

**Problem**: Backend can't connect to Redis or database.

**Solutions**:
- Ensure Redis is running: `docker-compose ps` or `redis-cli ping`
- Check `.env` file has correct connection URLs
- For Docker: use service names (e.g., `redis://redis:6379`)
- For local: use localhost (e.g., `redis://localhost:6379`)

### "Module not found" errors in backend

**Problem**: Python dependencies not installed.

**Solution**:
```bash
cd backend
pip install -r requirements.txt
```

### Frontend build errors

**Problem**: Node modules not installed or outdated.

**Solution**:
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
```

### Ollama connection errors

**Problem**: Backend can't reach Ollama.

**Solutions**:
- Ensure Ollama is running: `ollama list`
- Check `OLLAMA_BASE_URL` in `.env`
- On Docker: use `http://host.docker.internal:11434`
- On local: use `http://localhost:11434`
- Pull a model: `ollama pull codellama`

### Database migration errors

**Problem**: Database schema out of sync.

**Solution**:
```bash
cd backend
# Reset database (WARNING: deletes all data)
rm data/code_review.db
alembic upgrade head
```

### Port already in use

**Problem**: Port 8000 or 3000 is occupied.

**Solution**:
```bash
# Find and kill process on port
# Linux/Mac:
lsof -ti:8000 | xargs kill -9
# Windows:
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# Or change ports in docker-compose.yml or .env
```

## Production Deployment

### Security Checklist

- [ ] Change `JWT_SECRET_KEY` to a strong random value
- [ ] Set `ENVIRONMENT=production`
- [ ] Set `DEBUG=false`
- [ ] Use PostgreSQL instead of SQLite
- [ ] Enable HTTPS/TLS
- [ ] Set strong database passwords
- [ ] Configure CORS_ORIGINS to your domain only
- [ ] Enable rate limiting
- [ ] Review and rotate API keys
- [ ] Set up monitoring and logging
- [ ] Configure backups

### Environment Variables for Production

```env
ENVIRONMENT=production
DEBUG=false
DATABASE_URL=postgresql://user:password@db-host:5432/dbname
REDIS_URL=redis://redis-host:6379/0
JWT_SECRET_KEY=<generate-with-openssl-rand-hex-32>
CORS_ORIGINS=https://yourdomain.com
```

### Docker Production Build

```bash
# Build production images
docker-compose -f docker-compose.prod.yml build

# Run in production mode
docker-compose -f docker-compose.prod.yml up -d

# View logs
docker-compose -f docker-compose.prod.yml logs -f
```

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Run linters and tests
6. Submit a pull request

## License

MIT License - see LICENSE file for details

## Support

- **Issues**: Report bugs or request features via GitHub Issues
- **Discussions**: Ask questions in GitHub Discussions
- **Documentation**: See `DECISIONS.md` for architecture decisions

## Credits

Built with:
- [FastAPI](https://fastapi.tiangolo.com/)
- [React](https://react.dev/)
- [SQLModel](https://sqlmodel.tiangolo.com/)
- [TailwindCSS](https://tailwindcss.com/)
- [shadcn/ui](https://ui.shadcn.com/)
- [TanStack Query](https://tanstack.com/query)

---

**Ready to get started?** Run `docker-compose up -d` and visit http://localhost:3000 🚀
