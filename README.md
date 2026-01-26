# AI Code Review Arena

Arena porównująca różne modele AI w przeglądzie kodu. Użytkownicy mogą przesyłać kod, uzyskać recenzje od wielu agentów AI i ocenić jakość ich odpowiedzi.

## Wymagania

- Python 3.11+ (backend)
- Node.js 18+ (frontend)

## Instalacja i uruchomienie

### Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install fastapi "uvicorn[standard]" python-multipart sqlmodel alembic "python-jose[cryptography]" "passlib[bcrypt]" bcrypt python-dotenv pydantic pydantic-settings redis hiredis httpx aiohttp python-dateutil orjson pytest pytest-asyncio pytest-cov
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend będzie dostępny na: http://localhost:8000

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend będzie dostępny na: http://localhost:3000

## Funkcje

- **Arena Mode** - Porównanie dwóch losowych agentów AI
- **Council Mode** - Zespół agentów dyskutujących o kodzie
- **Review Mode** - Pojedynczy agent recenzujący kod
- System rankingowy ELO dla agentów
- Wsparcie dla wielu LLM providerów (Groq, Gemini, Cloudflare, Ollama)

## Technologie

**Backend:**
- FastAPI
- SQLModel (SQLAlchemy + Pydantic)
- SQLite (domyślnie) / PostgreSQL
- JWT Authentication
- Redis (cache)

**Frontend:**
- React + TypeScript
- Vite
- TanStack Query
- Tailwind CSS + Radix UI
- Monaco Editor

## Konfiguracja

Utwórz plik `.env` w katalogu `backend/` (opcjonalnie):

```env
# Database
DATABASE_URL=sqlite:///./data/code_review.db

# Security
JWT_SECRET_KEY=your_secret_key_here

# LLM Providers (opcjonalne)
GROQ_API_KEY=your_groq_key
GEMINI_API_KEY=your_gemini_key
CLOUDFLARE_API_TOKEN=your_cf_token
CLOUDFLARE_ACCOUNT_ID=your_cf_account_id
```

## API Dokumentacja

Po uruchomieniu backendu:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
