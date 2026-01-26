# Instrukcja dla prowadzącego - AI Code Review Arena

## Autor
Aron Wwo

## Repozytorium GitHub
https://github.com/Aronwwo/ai-code-review-arena

## Co przesłać

### ⚠️ NIE przesyłaj tych folderów (zajmują >800MB):
- `frontend/node_modules/` - można zainstalować przez `npm install`
- `backend/venv/` - można zainstalować przez `pip install -r requirements.txt`
- `.git/` - można sklonować z GitHub
- `data/` - baza danych (generowana automatycznie)
- `Archiwum.zip` - za duży plik

### ✅ Przesyłane pliki (kod źródłowy):

```
ai-code-review-arena/
├── backend/
│   ├── app/
│   │   ├── api/          # Endpointy API
│   │   ├── models/       # Modele danych
│   │   ├── orchestrators/# Logika Arena/Council
│   │   ├── providers/    # Integracje LLM
│   │   └── utils/        # Narzędzia
│   ├── requirements.txt  # Zależności Python
│   └── tests/           # Testy
├── frontend/
│   ├── src/             # Kod React
│   ├── package.json     # Zależności Node
│   └── vite.config.ts   # Konfiguracja
├── README.md            # Dokumentacja
└── .gitignore          # Wykluczenia
```

## Jak uruchomić projekt (dla prowadzącego)

### 1. Backend
```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install fastapi "uvicorn[standard]" python-multipart sqlmodel alembic "python-jose[cryptography]" "passlib[bcrypt]" bcrypt python-dotenv pydantic pydantic-settings redis hiredis httpx aiohttp python-dateutil orjson pytest pytest-asyncio pytest-cov
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend: http://localhost:8000
API Docs: http://localhost:8000/docs

### 2. Frontend
```bash
cd frontend
npm install
npm run dev
```

Frontend: http://localhost:3000

## Archiwizacja projektu (bez zbędnych plików)

```bash
# Z katalogu głównego projektu
tar -czf projekt-aronwwo.tar.gz \
  --exclude='node_modules' \
  --exclude='venv' \
  --exclude='.git' \
  --exclude='data' \
  --exclude='*.db' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='Archiwum.zip' \
  --exclude='.pytest_cache' \
  .
```

Lub ZIP (Windows/Mac):
```bash
zip -r projekt-aronwwo.zip . \
  -x "*/node_modules/*" \
  -x "*/venv/*" \
  -x "*/.git/*" \
  -x "*/data/*" \
  -x "*.db" \
  -x "*/__pycache__/*" \
  -x "Archiwum.zip"
```

## Funkcjonalności projektu

1. **Arena Mode** - Porównanie dwóch losowych agentów AI
2. **Council Mode** - Zespół agentów dyskutujących o kodzie
3. **Review Mode** - Pojedynczy agent recenzujący kod
4. **System rankingowy ELO** dla agentów
5. **Wsparcie wielu LLM** (Groq, Gemini, Cloudflare, Ollama, Mock)
6. **Autentykacja JWT** z hashowaniem bcrypt
7. **Walidacja plików** i zabezpieczenia
8. **API REST** z dokumentacją Swagger

## Technologie

**Backend:**
- FastAPI + Uvicorn
- SQLModel (SQLAlchemy + Pydantic)
- SQLite
- JWT Authentication
- bcrypt

**Frontend:**
- React 18 + TypeScript
- Vite
- TanStack Query
- Tailwind CSS + Radix UI
- Monaco Editor

## Testowanie

```bash
# Backend
cd backend
source venv/bin/activate
pytest

# Frontend
cd frontend
npm test
```

## Struktura bazy danych

- **users** - użytkownicy z hashowanymi hasłami
- **projects** - projekty z plikami do review
- **reviews** - recenzje kodu
- **arena_sessions** - sesje porównań w trybie arena
- **team_ratings** - ranking ELO agentów
- **audit_logs** - logi bezpieczeństwa

## Kontakt
W razie pytań: sprawdzić README.md lub kod źródłowy
