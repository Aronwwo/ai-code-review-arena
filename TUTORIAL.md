# 📚 AI Code Review Arena - Kompletny Tutorial Techniczny

## Spis Treści

1. [Wprowadzenie](#wprowadzenie)
2. [Architektura Systemu](#architektura-systemu)
3. [Stack Technologiczny](#stack-technologiczny)
4. [Struktura Projektu](#struktura-projektu)
5. [Backend - Szczegółowy Opis](#backend---szczegółowy-opis)
6. [Frontend - Szczegółowy Opis](#frontend---szczegółowy-opis)
7. [Tryby Review - Council vs Arena](#tryby-review---council-vs-arena)
8. [Integracje z LLM](#integracje-z-llm)
9. [Baza Danych](#baza-danych)
10. [Bezpieczeństwo](#bezpieczeństwo)
11. [Deployment](#deployment)
12. [Rozwój i Rozszerzenia](#rozwój-i-rozszerzenia)

---

## Wprowadzenie

### Co to jest AI Code Review Arena?

**AI Code Review Arena** to zaawansowana aplikacja webowa do automatycznego przeglądania kodu przy użyciu wielu agentów AI (Large Language Models). Aplikacja pozwala programistom na:

- **Przeanalizowanie kodu** przez specjalistyczne agenty AI (Security, Performance, Style, General)
- **Dwoma trybami pracy**:
  - **Council Mode**: Agenci współpracują i wspólnie tworzą raport
  - **Arena Mode**: Dwa zespoły agentów debatują nad kodem, moderator wydaje werdykt
- **Integrację z wieloma providerami LLM**: Ollama (lokalne), Gemini, Groq, OpenAI, Anthropic, Cloudflare
- **Real-time monitoring** postępu review przez WebSocket
- **Historię i statystyki** wszystkich przeglądów

### Założenia Projektu

Projekt został zaprojektowany z myślą o:

1. **Modularności** - łatwe dodawanie nowych providerów LLM
2. **Skalowalności** - asynchroniczne przetwarzanie, obsługa wielu review jednocześnie
3. **Niezawodności** - retry logic, timeout handling, graceful error handling
4. **Użyteczności** - intuicyjny interfejs, real-time feedback, szczegółowe raporty
5. **Bezpieczeństwie** - JWT auth, CSRF protection, rate limiting

---

## Architektura Systemu

### Ogólny Przegląd

Aplikacja składa się z trzech głównych warstw:

```
┌─────────────────────────────────────────────────────────────┐
│                    FRONTEND (React)                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │  Pages   │  │Components│  │ Contexts │  │   Hooks  │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└─────────────────────────────────────────────────────────────┘
                          │ HTTP/WebSocket
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                  BACKEND (FastAPI)                           │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │   API    │  │Orchestr. │  │Providers │  │  Utils   │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│              PERSISTENCE LAYER                               │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                 │
│  │ SQLite   │  │  Redis   │  │   LLM    │                 │
│  │ (or PG)  │  │ (Cache)  │  │  APIs    │                 │
│  └──────────┘  └──────────┘  └──────────┘                 │
└─────────────────────────────────────────────────────────────┘
```

### Przepływ Danych

#### Przepływ Review (Council Mode):

```
1. User → Frontend: Kliknięcie "Nowy Review"
   ↓
2. Frontend → Backend: POST /projects/{id}/reviews
   Body: {agent_roles: ["general", "security"], provider: "ollama", ...}
   ↓
3. Backend: Tworzy Review(status="pending") w bazie
   ↓
4. Backend: Uruchamia ReviewOrchestrator (BackgroundTask)
   ↓
5. ReviewOrchestrator:
   a) Pobiera pliki z projektu
   b) Dla każdego agenta (sekwencyjnie, z opóźnieniem 5s):
      - Buduje prompt (system + user message)
      - Wywołuje LLM przez ProviderRouter
      - Parsuje JSON response
      - Zapisuje ReviewAgent do bazy
   c) Wywołuje moderatora:
      - Moderator syntetyzuje odpowiedzi agentów
      - Generuje końcowy raport (JSON)
      - Zapisuje do Review.summary
   d) Aktualizuje Review(status="completed")
   ↓
6. Backend → Frontend: WebSocket event "review_completed"
   ↓
7. Frontend: Refetch danych, aktualizuje UI
```

#### Przepływ Arena Mode:

```
1. User → Frontend: Konfiguruje Team A i Team B
   ↓
2. Frontend → Backend: POST /arena/sessions
   Body: {team_a_config: {...}, team_b_config: {...}}
   ↓
3. Backend: Tworzy ArenaSession
   ↓
4. Backend: Uruchamia ArenaOrchestrator
   a) Uruchamia Team A (wszyscy agenci równolegle)
   b) Uruchamia Team B (wszyscy agenci równolegle)
   c) Generuje podsumowania zespołów
   d) Aktualizuje ArenaSession(status="completed")
   ↓
5. Frontend: Wyświetla wyniki Arena
```

---

## Stack Technologiczny

### Backend

#### **FastAPI 0.109.0**
- **Co to jest**: Nowoczesny, szybki framework webowy dla Python 3.10+
- **Dlaczego**: 
  - Automatyczna dokumentacja API (Swagger/OpenAPI)
  - Walidacja danych przez Pydantic
  - Async/await natywnie wspierane
  - Wysoka wydajność (porównywalna z Node.js)
- **Użycie w projekcie**: Wszystkie endpointy REST, WebSocket, middleware

#### **SQLModel 0.0.14**
- **Co to jest**: Biblioteka łącząca SQLAlchemy (ORM) i Pydantic (walidacja)
- **Dlaczego**: 
  - Jeden model dla bazy danych i API
  - Automatyczna walidacja i serializacja
  - Type hints dla lepszego IDE support
- **Użycie w projekcie**: Wszystkie modele bazy danych (User, Project, Review, Issue, etc.)

#### **Alembic 1.13.1**
- **Co to jest**: Narzędzie do zarządzania migracjami bazy danych
- **Dlaczego**: 
  - Wersjonowanie zmian w schemacie bazy
  - Bezpieczne aktualizacje struktury tabel
- **Użycie w projekcie**: Migracje w `backend/alembic/versions/`

#### **Uvicorn 0.27.0**
- **Co to jest**: ASGI server (HTTP/WebSocket)
- **Dlaczego**: 
  - Szybki, oparty na uvloop
  - Auto-reload w development
  - Obsługa WebSocket natywnie
- **Użycie w projekcie**: Serwer uruchamiający FastAPI

#### **Pydantic 2.5.3**
- **Co to jest**: Biblioteka do walidacji danych przez type hints
- **Dlaczego**: 
  - Automatyczna walidacja requestów/response
  - Type safety
  - Error messages w języku naturalnym
- **Użycie w projekcie**: Wszystkie request/response schemas, konfiguracja (Settings)

#### **Python-JOSE 3.3.0**
- **Co to jest**: Biblioteka do JWT (JSON Web Tokens)
- **Dlaczego**: 
  - Bezpieczna autentykacja bezstanowa
  - Tokeny access i refresh
- **Użycie w projekcie**: Generowanie i walidacja tokenów JWT

#### **Passlib + bcrypt**
- **Co to jest**: Biblioteki do haszowania haseł
- **Dlaczego**: 
  - Bezpieczne przechowywanie haseł (bcrypt)
  - Sprawdzanie haseł bez znajomości oryginału
- **Użycie w projekcie**: Haszowanie haseł przy rejestracji/logowaniu

#### **httpx 0.26.0**
- **Co to jest**: Async HTTP client (następca requests)
- **Dlaczego**: 
  - Async/await support
  - Wysoka wydajność
  - Obsługa retry logic
- **Użycie w projekcie**: Wszystkie wywołania do LLM APIs (Gemini, Groq, OpenAI, etc.)

#### **Redis 5.0.1**
- **Co to jest**: In-memory data store (opcjonalnie)
- **Dlaczego**: 
  - Cache odpowiedzi LLM (oszczędność kosztów)
  - Rate limiting (zliczanie requestów per IP)
- **Użycie w projekcie**: Cache i rate limiting (fallback do in-memory jeśli Redis nie dostępny)

#### **Python-dotenv**
- **Co to jest**: Ładowanie zmiennych środowiskowych z pliku .env
- **Dlaczego**: 
  - Łatwa konfiguracja bez commitu secretów
  - Wsparcie dla różnych środowisk (dev/prod)
- **Użycie w projekcie**: Ładowanie kluczy API, DATABASE_URL, etc.

### Frontend

#### **React 18.2.0**
- **Co to jest**: Biblioteka JavaScript do budowania interfejsów użytkownika
- **Dlaczego**: 
  - Komponentowa architektura
  - Virtual DOM dla wydajności
  - Duża społeczność i ekosystem
- **Użycie w projekcie**: Cały interfejs użytkownika

#### **TypeScript 5.3.3**
- **Co to jest**: JavaScript z type checking
- **Dlaczego**: 
  - Type safety - wykrywanie błędów przed runtime
  - Lepsze IDE support (autocomplete, refactoring)
  - Dokumentacja kodu przez typy
- **Użycie w projekcie**: Wszystkie pliki .tsx i .ts

#### **Vite 5.0.11**
- **Co to jest**: Build tool i dev server (alternatywa dla Webpack)
- **Dlaczego**: 
  - Szybkie hot module replacement (HMR)
  - Szybki build dzięki ES modules
  - Out-of-the-box TypeScript support
- **Użycie w projekcie**: Dev server i build process

#### **React Router 6.21.1**
- **Co to jest**: Routing dla React (single-page application)
- **Dlaczego**: 
  - Nawigacja między stronami bez przeładowania
  - Protected routes (autentykacja)
  - URL-based routing
- **Użycie w projekcie**: Nawigacja (`/login`, `/projects`, `/reviews/:id`, etc.)

#### **TanStack Query (React Query) 5.17.9**
- **Co to jest**: Biblioteka do zarządzania stanem serwera (cache, fetching, mutations)
- **Dlaczego**: 
  - Automatyczny cache i refetch
  - Loading states, error handling
  - Optimistic updates
  - Background refetching
- **Użycie w projekcie**: Wszystkie requesty do API (`useQuery`, `useMutation`)

#### **Axios 1.13.2**
- **Co to jest**: HTTP client dla JavaScript
- **Dlaczego**: 
  - Interceptory (automatyczne dodawanie tokenów, error handling)
  - Request/response transformation
  - Cancel requests
- **Użycie w projekcie**: Wszystkie API calls (wrapped przez React Query)

#### **React Hook Form 7.49.3**
- **Co to jest**: Biblioteka do zarządzania formularzami
- **Dlaczego**: 
  - Mniej re-renderów (uncontrolled components)
  - Integracja z Zod (walidacja)
  - Proste API
- **Użycie w projekcie**: Formularze (login, register, review config)

#### **Zod 3.22.4**
- **Co to jest**: Schema validation dla TypeScript
- **Dlaczego**: 
  - Type-safe walidacja
  - Type inference (automatyczne generowanie typów z schematów)
  - Integracja z React Hook Form
- **Użycie w projekcie**: Walidacja formularzy i API responses

#### **Tailwind CSS 3.4.1**
- **Co to jest**: Utility-first CSS framework
- **Dlaczego**: 
  - Szybkie stylowanie bez pisania CSS
  - Responsywność out-of-the-box
  - Customizable (theme configuration)
- **Użycie w projekcie**: Wszystkie style w aplikacji

#### **Radix UI**
- **Co to jest**: Biblioteka accessible (WCAG) komponentów UI
- **Dlaczego**: 
  - Accessibility out-of-the-box (keyboard navigation, screen readers)
  - Headless (tylko logika, style przez Tailwind)
  - Wysokiej jakości komponenty
- **Użycie w projekcie**: Dialog, Dropdown, Select, Tabs, Toast, etc.

#### **Monaco Editor 4.7.0**
- **Co to jest**: Code editor (ten sam co VS Code)
- **Dlaczego**: 
  - Syntax highlighting dla wielu języków
  - Auto-completion
  - Błędy i warnings
  - Minimap, line numbers
- **Użycie w projekcie**: Edytor kodu w `CodeEditor.tsx`

#### **Lucide React 0.309.0**
- **Co to jest**: Biblioteka ikon (fork Feather Icons)
- **Dlaczego**: 
  - Duża kolekcja ikon
  - Tree-shakeable (tylko używane ikony w bundle)
  - TypeScript support
- **Użycie w projekcie**: Ikony w całej aplikacji

### Narzędzia Deweloperskie

#### **Black 23.12.1**
- Code formatter dla Python
- Automatyczne formatowanie zgodne z PEP 8

#### **Ruff 0.1.11**
- Szybki linter dla Python (alternatywa dla Flake8, isort)
- Sprawdza jakość kodu, importy, etc.

#### **MyPy 1.8.0**
- Static type checker dla Python
- Sprawdza type hints w kodzie

#### **ESLint 8.56.0**
- Linter dla JavaScript/TypeScript
- Sprawdza błędy, best practices

#### **Prettier 3.1.1**
- Code formatter dla JavaScript/TypeScript/CSS
- Automatyczne formatowanie zgodne z konwencjami

#### **Pytest 7.4.4**
- Framework testowy dla Python
- Używany do testów backendu

#### **Vitest 1.2.0**
- Framework testowy dla Vite/React
- Używany do testów frontendu

#### **Playwright 1.48.2**
- End-to-end testing framework
- Automatyzacja przeglądarki, testy integracyjne

---

## Struktura Projektu

### Ogólna Struktura

```
ai-code-review-arena-main/
├── backend/                    # Backend (FastAPI)
│   ├── app/
│   │   ├── api/                # Endpointy REST
│   │   │   ├── auth.py         # Autentykacja (login, register, refresh)
│   │   │   ├── projects.py     # CRUD projektów
│   │   │   ├── files.py        # Operacje na plikach
│   │   │   ├── reviews.py      # Review endpoints
│   │   │   ├── conversations.py # Council/Arena conversations
│   │   │   ├── arena.py        # Arena sessions
│   │   │   ├── providers.py    # LLM providers info
│   │   │   ├── ollama.py       # Ollama-specific endpoints
│   │   │   ├── websocket.py    # WebSocket dla real-time updates
│   │   │   ├── audit.py        # Audit logs (admin only)
│   │   │   └── rankings.py     # Rankings based on reviews
│   │   ├── models/             # Modele bazy danych (SQLModel)
│   │   │   ├── user.py         # User model
│   │   │   ├── project.py      # Project model
│   │   │   ├── file.py         # File model
│   │   │   ├── review.py       # Review, ReviewAgent, Issue models
│   │   │   ├── arena.py        # ArenaSession, ArenaTeam models
│   │   │   └── conversation.py # Conversation, Message models
│   │   ├── orchestrators/      # Logika biznesowa
│   │   │   ├── review.py       # ReviewOrchestrator (Council mode)
│   │   │   ├── arena.py        # ArenaOrchestrator (Arena mode)
│   │   │   └── conversation.py # ConversationOrchestrator
│   │   ├── providers/          # Integracje z LLM APIs
│   │   │   ├── base.py         # LLMProvider base class
│   │   │   ├── router.py       # ProviderRouter (routing logic)
│   │   │   ├── mock.py         # MockProvider (testy)
│   │   │   ├── ollama.py       # OllamaProvider
│   │   │   ├── gemini.py       # GeminiProvider
│   │   │   ├── groq.py         # GroqProvider
│   │   │   ├── openai.py       # OpenAIProvider
│   │   │   ├── anthropic.py    # AnthropicProvider
│   │   │   ├── cloudflare.py   # CloudflareProvider
│   │   │   └── custom.py       # CustomProvider (user-defined)
│   │   ├── utils/              # Pomocnicze narzędzia
│   │   │   ├── auth.py         # JWT helpers
│   │   │   ├── rate_limit.py   # Rate limiting
│   │   │   ├── cache.py        # Caching logic
│   │   │   └── elo.py          # ELO ranking algorithm
│   │   ├── config.py           # Ustawienia (Pydantic Settings)
│   │   ├── database.py         # Database setup (SQLModel engine)
│   │   └── main.py             # FastAPI app, middleware, routing
│   ├── alembic/                # Migracje bazy danych
│   │   └── versions/           # Historia migracji
│   ├── tests/                  # Testy jednostkowe i integracyjne
│   ├── scripts/                # Skrypty pomocnicze
│   │   ├── create_admin.py     # Tworzenie konta admina
│   │   └── seed_admin.py       # Seed danych testowych
│   ├── data/                   # Baza danych SQLite (gitignored)
│   ├── requirements.txt        # Zależności Python
│   └── Dockerfile              # Docker image dla backendu
│
├── frontend/                   # Frontend (React + TypeScript)
│   ├── src/
│   │   ├── components/         # Komponenty React
│   │   │   ├── ui/             # Podstawowe komponenty UI (Radix UI)
│   │   │   ├── CodeEditor.tsx  # Monaco editor wrapper
│   │   │   ├── CodeViewer.tsx  # Syntax highlighter dla kodu
│   │   │   ├── ReviewConfigDialog.tsx # Dialog konfiguracji review
│   │   │   ├── ArenaSetupDialog.tsx   # Dialog konfiguracji Arena
│   │   │   └── ConversationView.tsx   # Wyświetlanie konwersacji
│   │   ├── pages/              # Strony aplikacji (routes)
│   │   │   ├── Landing.tsx     # Strona główna (publiczna)
│   │   │   ├── Login.tsx       # Logowanie
│   │   │   ├── Register.tsx    # Rejestracja
│   │   │   ├── Projects.tsx    # Lista projektów
│   │   │   ├── ProjectDetail.tsx # Szczegóły projektu
│   │   │   ├── ReviewDetail.tsx  # Szczegóły review
│   │   │   ├── ArenaDetail.tsx   # Szczegóły Arena session
│   │   │   ├── Rankings.tsx      # Rankingi agentów
│   │   │   └── Settings.tsx      # Ustawienia użytkownika
│   │   ├── contexts/           # React Context (globalny stan)
│   │   │   ├── AuthContext.tsx  # Stan autentykacji
│   │   │   └── ThemeContext.tsx # Stan motywu (light/dark)
│   │   ├── hooks/              # Custom React hooks
│   │   │   └── useReviewWebSocket.ts # WebSocket hook
│   │   ├── lib/                # Pomocnicze biblioteki
│   │   │   ├── api.ts          # Axios instance, API helpers
│   │   │   ├── providers.ts    # Helper dla LLM providers
│   │   │   └── validation.ts   # Zod schemas
│   │   ├── types/              # TypeScript type definitions
│   │   ├── App.tsx             # Główny komponent (routing)
│   │   └── main.tsx            # Entry point
│   ├── package.json            # Zależności Node.js
│   ├── tailwind.config.js      # Konfiguracja Tailwind
│   ├── vite.config.ts          # Konfiguracja Vite
│   └── Dockerfile              # Docker image dla frontendu
│
├── docker-compose.yml          # Docker Compose (backend, frontend, Redis)
├── playwright.config.ts        # Konfiguracja Playwright (E2E tests)
├── package.json                # Root package.json (scripts)
└── README.md                   # Podstawowa dokumentacja
```

---

## Backend - Szczegółowy Opis

### 1. Konfiguracja (`config.py`)

Plik `config.py` używa **Pydantic Settings** do zarządzania ustawieniami aplikacji.

**Źródła konfiguracji** (w kolejności priorytetu):
1. Zmienne środowiskowe (`export DATABASE_URL=...`)
2. Plik `.env` (w root projektu)
3. Wartości domyślne (zdefiniowane w kodzie)

**Główne ustawienia**:
- `database_url`: URL bazy danych (SQLite lub PostgreSQL)
- `jwt_secret_key`: Secret key do podpisu tokenów JWT
- `jwt_access_token_expire_minutes`: Czas ważności tokenu (domyślnie 60 min)
- `cors_origins`: Lista dozwolonych domen (CORS)
- `rate_limit_per_minute`: Limit requestów na minutę (domyślnie 60)
- `groq_api_key`, `gemini_api_key`, etc.: Klucze API dla LLM providers

**Przykład użycia**:
```python
from app.config import settings

print(settings.database_url)  # sqlite:///./data/code_review.db
print(settings.jwt_secret_key)  # Wczytane z .env lub wartość domyślna
```

### 2. Baza Danych (`database.py`)

Plik `database.py` konfiguruje **SQLModel engine** i tworzy tabele w bazie.

**Główne komponenty**:
- `engine`: SQLAlchemy engine (połączenie z bazą)
- `Session`: Context manager dla sesji bazy danych
- `create_db_and_tables()`: Funkcja tworząca tabele (wywoływana przy starcie)

**Wsparcie dla różnych baz**:
- **SQLite**: Domyślne dla development (`sqlite:///./data/code_review.db`)
- **PostgreSQL**: Dla production (`postgresql://user:pass@localhost/db`)

**Migracje Alembic**:
- Migracje w `backend/alembic/versions/`
- Uruchamianie: `alembic upgrade head`

### 3. Modele (`models/`)

Wszystkie modele używają **SQLModel** (SQLAlchemy + Pydantic).

#### **User** (`models/user.py`)
```python
class User(SQLModel, table=True):
    id: int | None
    email: str (unique)
    username: str
    hashed_password: str
    is_active: bool
    is_superuser: bool
```

#### **Project** (`models/project.py`)
```python
class Project(SQLModel, table=True):
    id: int | None
    name: str
    description: str | None
    owner_id: int (FK → User)
    files: list[File] (relationship)
    reviews: list[Review] (relationship)
```

#### **File** (`models/file.py`)
```python
class File(SQLModel, table=True):
    id: int | None
    project_id: int (FK → Project)
    name: str
    content: str
    language: str | None (auto-detected)
    content_hash: str (SHA-256, do deduplikacji)
```

#### **Review** (`models/review.py`)
```python
class Review(SQLModel, table=True):
    id: int | None
    project_id: int (FK → Project)
    status: str ("pending" | "running" | "completed" | "failed")
    review_mode: str ("council" | "arena")
    summary: str | None (końcowy raport moderatora)
    agents: list[ReviewAgent] (relationship)
    issues: list[Issue] (relationship)

class ReviewAgent(SQLModel, table=True):
    id: int | None
    review_id: int (FK → Review)
    role: str ("general" | "security" | "performance" | "style")
    provider: str ("ollama" | "gemini" | "groq" | ...)
    model: str ("qwen2.5-coder:0.5b", "gemini-1.5-flash", ...)
    raw_output: str | None (surowa odpowiedź LLM)
    parsed_successfully: bool
    timed_out: bool

class Issue(SQLModel, table=True):
    id: int | None
    review_id: int (FK → Review)
    severity: str ("info" | "warning" | "error")
    category: str ("security" | "performance" | "style" | ...)
    title: str
    description: str
    file_name: str | None
    line_start: int | None
    line_end: int | None
    code_snippet: str | None
    suggested_fix: str | None
```

### 4. API Endpoints (`api/`)

#### **Autentykacja** (`api/auth.py`)

**POST `/auth/register`**
- Rejestracja nowego użytkownika
- Body: `{email, password, username}`
- Walidacja: hasło min 8 znaków, wielka litera, cyfra
- Response: User object (bez hasła)

**POST `/auth/login`**
- Logowanie
- Body: `{email, password}`
- Response: Ustawia cookies (`access_token`, `refresh_token`, `csrf_token`)

**POST `/auth/refresh`**
- Odświeżanie tokenu access
- Cookies: `refresh_token`
- Response: Nowy `access_token` w cookie

**GET `/auth/me`**
- Pobranie danych bieżącego użytkownika
- Auth required (JWT token w cookie lub header)

#### **Projekty** (`api/projects.py`)

**GET `/projects`**
- Lista projektów użytkownika
- Paginacja: `?page=1&page_size=20`

**POST `/projects`**
- Utworzenie nowego projektu
- Body: `{name, description?}`

**GET `/projects/{id}`**
- Szczegóły projektu (z plikami)

**PUT `/projects/{id}`**
- Aktualizacja projektu

**DELETE `/projects/{id}`**
- Usunięcie projektu (z plikami)

#### **Pliki** (`api/files.py`)

**POST `/projects/{id}/files`**
- Dodanie pliku do projektu
- Body: `{name, content}`
- Walidacja: max 10MB, max 100 plików/projekt

**GET `/projects/{id}/files`**
- Lista plików w projekcie

**DELETE `/files/{id}`**
- Usunięcie pliku

#### **Reviews** (`api/reviews.py`)

**POST `/projects/{id}/reviews`**
- Uruchomienie review (Council mode)
- Body:
  ```json
  {
    "review_mode": "council",
    "agent_roles": ["general", "security"],
    "agent_configs": {
      "general": {
        "provider": "ollama",
        "model": "qwen2.5-coder:0.5b",
        "temperature": 0.2,
        "max_tokens": 4096,
        "timeout_seconds": 180
      }
    },
    "moderator_config": {...},
    "api_keys": {"ollama": null, "gemini": "..."}
  }
  ```
- Response: `{review_id}`
- Uruchamia `ReviewOrchestrator` w BackgroundTask

**GET `/reviews/{id}`**
- Szczegóły review (status, summary, agents, issues)

**GET `/reviews/{id}/agents`**
- Lista agentów i ich odpowiedzi

**GET `/reviews/{id}/issues`**
- Lista znalezionych problemów (z paginacją)

#### **Arena** (`api/arena.py`)

**POST `/arena/sessions`**
- Uruchomienie Arena session
- Body:
  ```json
  {
    "project_id": 1,
    "team_a_config": {
      "name": "Team Security",
      "agents": [
        {"role": "security", "provider": "ollama", "model": "..."}
      ]
    },
    "team_b_config": {...}
  }
  ```
- Uruchamia `ArenaOrchestrator`

**GET `/arena/sessions/{id}`**
- Szczegóły Arena session (team summaries, status)

#### **WebSocket** (`api/websocket.py`)

**WS `/ws/reviews/{review_id}`**
- Real-time updates dla review
- Events:
  - `agent_started`: Agent zaczął analizę
  - `agent_completed`: Agent zakończył
  - `review_completed`: Review zakończony

### 5. Orchestratory (`orchestrators/`)

#### **ReviewOrchestrator** (`orchestrators/review.py`)

**Rola**: Zarządza całym procesem Council mode review.

**Główna metoda**:
```python
async def conduct_review(
    self,
    review_id: int,
    agent_configs: dict[str, AgentConfig],
    moderator_config: dict
) -> Review
```

**Przepływ**:
1. **Pobranie danych**: Review, Project, Files z bazy
2. **Uruchomienie agentów** (sekwencyjnie, z opóźnieniem 5s):
   - Dla każdego agenta:
     - Buduje prompt (system + user message z kodem)
     - Wywołuje LLM przez `ProviderRouter`
     - Parsuje JSON response
     - Zapisuje `ReviewAgent` do bazy
   - Obsługa timeoutów i błędów (429, connection errors)
3. **Moderator syntetyzuje**:
   - Zbiera wszystkie odpowiedzi agentów
   - Generuje końcowy raport (JSON z issues i summary)
   - Zapisuje do `Review.summary`
4. **Zakończenie**: `Review.status = "completed"`

**Prompt engineering**:
- **System prompt**: Definiuje rolę agenta ("Jesteś ekspertem bezpieczeństwa...")
- **User prompt**: Zawiera kod do analizy + instrukcje formatowania (JSON)
- **Moderator prompt**: Instrukcje syntezy (TYLKO formatowanie odpowiedzi, nie generowanie własnej analizy)

**Obsługa błędów**:
- Timeout: Agent oznaczany jako `timed_out = True`
- 429 Rate Limit: Retry z exponential backoff (w providerze)
- Parsing error: `parsed_successfully = False`, `raw_output` zapisane
- Jeśli żaden agent nie odpowiedział: Moderator NIE jest wywoływany, zwracany jest fallback summary

#### **ArenaOrchestrator** (`orchestrators/arena.py`)

**Rola**: Zarządza Arena mode (debata dwóch zespołów).

**Główna metoda**:
```python
async def run_arena_session(
    self,
    session_id: int,
    team_a_config: dict,
    team_b_config: dict
) -> ArenaSession
```

**Przepływ**:
1. **Uruchomienie Team A** (wszyscy agenci równolegle):
   - Każdy agent analizuje kod niezależnie
   - Zapisuje `ArenaTeamAnalysis`
2. **Uruchomienie Team B** (wszyscy agenci równolegle):
   - Analogicznie
3. **Generowanie podsumowań zespołów**:
   - Podsumowanie Team A (na podstawie analiz agentów)
   - Podsumowanie Team B (na podstawie analiz agentów)
   - Zapisuje do `ArenaSession.team_a_summary`, `team_b_summary`
4. **Zakończenie**: `ArenaSession.status = "completed"`

**Różnice vs Council**:
- Dwa zespoły zamiast jednego moderatora
- Agenty pracują równolegle (nie sekwencyjnie)
- Brak moderatora syntetyzującego (tylko podsumowania zespołów)

### 6. Providers (`providers/`)

#### **LLMProvider Base Class** (`providers/base.py`)

Abstrakcyjna klasa bazowa dla wszystkich providerów:

```python
class LLMProvider(ABC):
    @abstractmethod
    async def generate(
        self,
        messages: list[LLMMessage],
        model: str,
        temperature: float = 0.0,
        max_tokens: int = 4096
    ) -> str:
        """Generate response from LLM."""
```

**LLMMessage**:
```python
class LLMMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str
```

#### **ProviderRouter** (`providers/router.py`)

**Rola**: Routing do odpowiedniego providera z fallback logic.

**Główne metody**:
```python
async def generate(
    self,
    provider_name: str,
    model: str,
    messages: list[LLMMessage],
    custom_provider: CustomProviderConfig | None = None
) -> str
```

**Logika routingu**:
1. Jeśli `custom_provider`: Używa `CustomProvider`
2. W przeciwnym razie: Wybiera provider z `self.providers[provider_name]`
3. Wywołuje `provider.generate(...)`
4. Obsługa błędów: Refusal detection, truncation, etc.

**Cache**: Odpowiedzi LLM są cache'owane (Redis lub in-memory) na 24h, aby oszczędzić koszty i przyspieszyć powtórne zapytania.

#### **OllamaProvider** (`providers/ollama.py`)

**Komunikacja**: HTTP POST do `http://localhost:11434/api/generate`

**Specjalne funkcje**:
- Sprawdzanie dostępności Ollama (`/api/tags`)
- Weryfikacja modelu (czy jest dostępny lokalnie)
- Obsługa pustych odpowiedzi
- Timeout handling

**Przykład request**:
```json
POST http://localhost:11434/api/generate
{
  "model": "qwen2.5-coder:0.5b",
  "prompt": "...",
  "stream": false,
  "options": {
    "temperature": 0.0,
    "num_predict": 4096
  }
}
```

#### **GeminiProvider** (`providers/gemini.py`)

**Komunikacja**: HTTP POST do `https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent`

**Specjalne funkcje**:
- **Retry logic**: Exponential backoff dla 429 errors (3 próby: 5s, 10s, 20s)
- **Free tier detection**: Automatyczne fallback do `gemini-1.5-flash` jeśli model nie jest dostępny
- **API key**: Z `settings.gemini_api_key` lub `api_keys` dict

**Przykład request**:
```json
POST https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=...
{
  "contents": [
    {
      "parts": [
        {"text": "..."}
      ]
    }
  ],
  "generationConfig": {
    "temperature": 0.0,
    "maxOutputTokens": 4096
  }
}
```

#### **MockProvider** (`providers/mock.py`)

**Rola**: Provider do testów - nie wymaga API key, generuje przykładowe odpowiedzi.

**Użycie**: Testy, development bez LLM API, demo.

---

## Frontend - Szczegółowy Opis

### 1. Architektura

Frontend używa **architektury komponentowej** z React, z podziałem na:

- **Pages**: Strony aplikacji (routes) - `pages/`
- **Components**: Reużywalne komponenty UI - `components/`
- **Contexts**: Globalny stan (autentykacja, motyw) - `contexts/`
- **Hooks**: Custom React hooks - `hooks/`
- **Lib**: Pomocnicze biblioteki (API, walidacja) - `lib/`

### 2. Routing (`App.tsx`)

**React Router** definiuje następujące trasy:

```
/                    → Landing (publiczna)
/login               → Login
/register            → Register
/dashboard           → Projects (protected)
/projects            → Projects (protected)
/projects/:id        → ProjectDetail (protected)
/reviews/:id         → ReviewDetail (protected)
/arena/:id           → ArenaDetail (protected)
/rankings            → Rankings (protected)
/settings            → Settings (protected)
```

**Protected Routes**: Wymagają autentykacji - przekierowanie do `/login` jeśli niezalogowany.

**Lazy Loading**: Strony są ładowane lazy (`React.lazy()`) dla code splitting.

### 3. State Management

#### **TanStack Query** (React Query)

**Użycie**: Wszystkie dane z API są zarządzane przez React Query.

**Przykład**:
```typescript
// Pobieranie projektu
const { data: project, isLoading } = useQuery({
  queryKey: ['projects', id],
  queryFn: () => api.get(`/projects/${id}`)
});

// Utworzenie review
const createReviewMutation = useMutation({
  mutationFn: (config: ReviewConfig) => 
    api.post(`/projects/${id}/reviews`, config),
  onSuccess: () => {
    queryClient.invalidateQueries(['projects', id]);
    toast.success('Review uruchomiony!');
  }
});
```

**Korzyści**:
- Automatyczny cache
- Background refetching
- Loading/error states
- Optimistic updates

#### **React Context** (AuthContext, ThemeContext)

**AuthContext**: Zarządza stanem autentykacji (user, tokens, login/logout).

**ThemeContext**: Zarządza motywem (light/dark mode).

### 4. Komponenty

#### **CodeEditor** (`components/CodeEditor.tsx`)

**Biblioteka**: Monaco Editor (VS Code editor)

**Funkcje**:
- Syntax highlighting (auto-detect z rozszerzenia pliku)
- Line numbers, minimap
- Read-only mode (dla przeglądania)
- Edycja (dla dodawania plików)

**Props**:
```typescript
interface CodeEditorProps {
  value: string;
  onChange?: (value: string) => void;
  language?: string;
  readOnly?: boolean;
}
```

#### **CodeViewer** (`components/CodeViewer.tsx`)

**Biblioteka**: React Syntax Highlighter

**Użycie**: Wyświetlanie fragmentów kodu w odpowiedziach agentów (code snippets, suggested fixes).

**Funkcje**:
- Syntax highlighting dla wielu języków
- Line highlighting (pokazanie zakresu linii problemu)
- Copy button

#### **ReviewConfigDialog** (`components/ReviewConfigDialog.tsx`)

**Rola**: Dialog konfiguracji review przed uruchomieniem.

**Konfiguracja**:
- Wybór agentów (general, security, performance, style) - checkboxy
- Provider i model dla każdego agenta
- Provider i model dla moderatora
- Timeout i max_tokens dla agentów i moderatora
- API keys (opcjonalnie)

**Walidacja**: React Hook Form + Zod

#### **ReviewDetail** (`pages/ReviewDetail.tsx`)

**Rola**: Wyświetlanie szczegółów review po zakończeniu.

**Sekcje**:
1. **Moderator Report**: 
   - Parsowanie JSON summary na czytelny tekst
   - Lista issues z filtrowaniem po severity
   - Overall quality rating
2. **Agent Responses**:
   - Lista wszystkich agentów z ich odpowiedziami
   - Rozwijane sekcje (`<details>`) dla pełnych odpowiedzi
   - Error handling (pokazywanie błędów agentów)
3. **Issues List**:
   - Tabela z wszystkimi znalezionymi problemami
   - Filtrowanie, sortowanie
   - Linki do plików i linii

**Real-time Updates**: WebSocket hook (`useReviewWebSocket`) dla aktualizacji statusu.

#### **ArenaDetail** (`pages/ArenaDetail.tsx`)

**Rola**: Wyświetlanie wyników Arena session.

**Sekcje**:
1. **Team A Summary**: Podsumowanie analizy Team A
2. **Team B Summary**: Podsumowanie analizy Team B
3. **Team A Agents**: Lista agentów i ich analiz
4. **Team B Agents**: Lista agentów i ich analiz

### 5. API Integration (`lib/api.ts`)

**Axios Instance**:
```typescript
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  withCredentials: true, // Cookies dla JWT
  headers: {
    'Content-Type': 'application/json'
  }
});
```

**Interceptors**:
- **Request**: Automatyczne dodawanie CSRF tokenu z cookie do headerów
- **Response**: Error handling (401 → logout, 429 → retry message)

**Helper functions**:
- `api.get()`, `api.post()`, `api.put()`, `api.delete()`
- Type-safe z TypeScript generics

### 6. Walidacja (`lib/validation.ts`)

**Zod Schemas** dla formularzy:

```typescript
const loginSchema = z.object({
  email: z.string().email(),
  password: z.string().min(8)
});

const reviewConfigSchema = z.object({
  agent_roles: z.array(z.string()),
  agent_configs: z.record(z.any()),
  // ...
});
```

**Integracja z React Hook Form**:
```typescript
const form = useForm({
  resolver: zodResolver(loginSchema),
  defaultValues: {...}
});
```

---

## Tryby Review - Council vs Arena

### Council Mode

**Cel**: Współpraca wielu agentów w celu stworzenia wspólnego raportu.

**Przepływ**:
1. User wybiera agentów (general, security, performance, style)
2. Każdy agent analizuje kod **niezależnie** (sekwencyjnie, z opóźnieniem 5s)
3. Moderator **syntetyzuje** wszystkie odpowiedzi w jeden raport:
   - Zbiera wszystkie issues od agentów
   - Usuwa duplikaty
   - Tworzy podsumowanie
   - Ocenia ogólną jakość kodu

**Moderator Prompt**:
```
Jesteś Moderatorem przeglądu kodu. Twoim zadaniem jest TYLKO 
sformatować odpowiedzi od agentów-ekspertów w czytelny raport.

KRYTYCZNE ZASADY:
- TYLKO formatowanie odpowiedzi - NIE generuj własnej analizy
- Jeśli NIE MA odpowiedzi od agentów → zwróć fallback
- Opieraj się TYLKO na odpowiedziach od agentów
```

**Wynik**: Jeden wspólny raport z issues i summary.

### Arena Mode

**Cel**: Debata dwóch zespołów agentów nad kodem.

**Przepływ**:
1. User konfiguruje **Team A** i **Team B** (każdy z własnymi agentami)
2. **Team A** analizuje kod (wszyscy agenci równolegle)
3. **Team B** analizuje kod (wszyscy agenci równolegle)
4. Generowane są **podsumowania zespołów** (nie ma moderatora)

**Podsumowanie zespołu**:
- Zbiera wszystkie analizy agentów z zespołu
- Tworzy podsumowanie (plain text, nie JSON):
  - "Najważniejsze problemy"
  - "Ogólna jakość kodu"
  - "Rekomendacja"

**Wynik**: Dwa niezależne podsumowania - user może porównać perspektywy.

**Użycie**: Gdy chcesz zobaczyć różne punkty widzenia (np. Team Security vs Team Performance).

---

## Integracje z LLM

### Architektura Providerów

Wszystkie providery implementują interfejs `LLMProvider`:

```python
class LLMProvider(ABC):
    @abstractmethod
    async def generate(
        self,
        messages: list[LLMMessage],
        model: str,
        temperature: float = 0.0,
        max_tokens: int = 4096
    ) -> str:
        pass
```

### Ollama (Lokalne)

**URL**: `http://localhost:11434`

**Wymagania**: Zainstalowany Ollama + pobrany model (np. `qwen2.5-coder:0.5b`)

**Zalety**:
- Darmowe (brak limitów)
- Prywatne (kod nie opuszcza komputera)
- Szybkie (lokalne przetwarzanie)

**Wady**:
- Wymaga GPU/lokalnych zasobów
- Ograniczone możliwości (mniejsze modele)

**Użycie**:
```python
provider = OllamaProvider()
response = await provider.generate(
    messages=[...],
    model="qwen2.5-coder:0.5b",
    temperature=0.0,
    max_tokens=4096
)
```

### Gemini (Google AI)

**URL**: `https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent`

**API Key**: Z Google AI Studio (free tier)

**Modele free tier**:
- `gemini-1.5-flash`
- `gemini-1.5-flash-latest`

**Specjalne funkcje**:
- Retry logic dla 429 errors (exponential backoff)
- Automatyczny fallback do `gemini-1.5-flash` jeśli model nie dostępny

**Rate limits** (free tier):
- 60 requests/minute
- Delay między requestami: min 5s (sekwencyjne uruchamianie agentów)

### Groq

**URL**: `https://api.groq.com/openai/v1/chat/completions`

**API Key**: Z Groq Console

**Zalety**:
- Bardzo szybkie (GPU acceleration)
- Darmowy tier (generous limits)

### OpenAI

**URL**: `https://api.openai.com/v1/chat/completions`

**Modele**: `gpt-4`, `gpt-3.5-turbo`

**Wymaga**: Płatny API key

### Custom Provider

**Rola**: Użytkownik może dodać własnego providera (dowolne API).

**Konfiguracja** (w Settings):
```json
{
  "id": "my-custom-provider",
  "name": "My Custom LLM",
  "base_url": "https://api.example.com/v1/chat",
  "api_key": "...",
  "header_name": "Authorization",
  "header_prefix": "Bearer "
}
```

**Implementacja**: `CustomProvider` używa `httpx` do generycznego POST requesta.

---

## Baza Danych

### Schemat

```
User
├── id (PK)
├── email (unique)
├── username
├── hashed_password
├── is_active
└── is_superuser

Project
├── id (PK)
├── name
├── description
├── owner_id (FK → User.id)
├── created_at
└── updated_at

File
├── id (PK)
├── project_id (FK → Project.id)
├── name
├── content
├── language
├── content_hash (SHA-256)
└── size_bytes

Review
├── id (PK)
├── project_id (FK → Project.id)
├── status ("pending" | "running" | "completed" | "failed")
├── review_mode ("council" | "arena")
├── summary (JSON raport moderatora)
├── created_by (FK → User.id)
├── created_at
└── completed_at

ReviewAgent
├── id (PK)
├── review_id (FK → Review.id)
├── role ("general" | "security" | "performance" | "style")
├── provider ("ollama" | "gemini" | ...)
├── model ("qwen2.5-coder:0.5b", ...)
├── raw_output (JSON string)
├── parsed_successfully (bool)
├── timed_out (bool)
└── timeout_seconds

Issue
├── id (PK)
├── review_id (FK → Review.id)
├── file_id (FK → File.id, nullable)
├── severity ("info" | "warning" | "error")
├── category ("security" | "performance" | ...)
├── title
├── description
├── file_name
├── line_start
├── line_end
├── code_snippet
├── suggested_fix
└── status ("open" | "confirmed" | "dismissed" | "resolved")

ArenaSession
├── id (PK)
├── project_id (FK → Project.id)
├── status ("pending" | "running" | "completed")
├── team_a_summary
├── team_b_summary
└── created_at

ArenaTeamAnalysis
├── id (PK)
├── session_id (FK → ArenaSession.id)
├── team ("a" | "b")
├── agent_role
├── provider
├── model
├── analysis (JSON)
└── created_at
```

### Relacje

- `User` → `Project` (1:N) - jeden użytkownik może mieć wiele projektów
- `Project` → `File` (1:N) - jeden projekt może mieć wiele plików
- `Project` → `Review` (1:N) - jeden projekt może mieć wiele review
- `Review` → `ReviewAgent` (1:N) - jeden review może mieć wielu agentów
- `Review` → `Issue` (1:N) - jeden review może mieć wiele issues
- `File` → `Issue` (1:N) - jeden plik może mieć wiele issues

### Indeksy

- `User.email` (unique index)
- `Project.owner_id` (index)
- `File.project_id` (index)
- `Review.project_id` (index)
- `Review.status` (index)
- `ReviewAgent.review_id` (index)
- `Issue.review_id` (index)
- `Issue.severity` (index)

---

## Bezpieczeństwo

### Autentykacja (JWT)

**Flow**:
1. User loguje się (`POST /auth/login`) z `email` i `password`
2. Backend sprawdza hasło (bcrypt)
3. Backend generuje dwa tokeny:
   - `access_token` (ważny 60 min) - w cookie `access_token` (httpOnly)
   - `refresh_token` (ważny 7 dni) - w cookie `refresh_token` (httpOnly)
4. Backend generuje `csrf_token` - w cookie `csrf_token` (dostępny dla JS)
5. Frontend automatycznie wysyła `csrf_token` w headerze `X-CSRF-Token` dla POST/PUT/DELETE

**Token JWT zawiera**:
```json
{
  "sub": "user_id",
  "email": "user@example.com",
  "exp": 1234567890
}
```

**Refresh token**:
- Używany do odświeżania `access_token` (`POST /auth/refresh`)
- Przechowywany w httpOnly cookie (nie dostępny dla JS)

### CSRF Protection

**Mechanizm**:
- CSRF token generowany przy logowaniu
- Przechowywany w cookie `csrf_token` (dostępny dla JS)
- Frontend automatycznie dodaje `X-CSRF-Token` header do POST/PUT/DELETE
- Backend sprawdza zgodność tokenu z cookie i headerem

**Middleware** (`main.py`):
```python
if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
    csrf_header = request.headers.get("X-CSRF-Token")
    csrf_cookie = request.cookies.get("csrf_token")
    if csrf_header != csrf_cookie:
        return JSONResponse(status_code=403, ...)
```

### Rate Limiting

**Implementacja**: `app/utils/rate_limit.py`

**Mechanizm**:
- Zliczanie requestów per IP w oknie czasowym (1 minuta)
- Limit: 60 requestów/minutę per IP
- Storage: Redis (jeśli dostępny) lub in-memory dict (fallback)

**Response**:
- `429 Too Many Requests` jeśli limit przekroczony
- Header `Retry-After` wskazuje kiedy można spróbować ponownie

**Wyłączenia**:
- `/health`, `/docs`, `/openapi.json` - bez rate limiting
- `OPTIONS` requests (CORS preflight)

### Autoryzacja

**Mechanizm**: Sprawdzanie właściciela zasobu przed dostępem.

**Przykład** (`api/deps.py`):
```python
def get_project(project_id: int, current_user: User) -> Project:
    project = session.get(Project, project_id)
    if project.owner_id != current_user.id:
        raise HTTPException(403, "Access denied")
    return project
```

**Admin Only**: Endpointy `/audit/*` wymagają `is_superuser = True`.

### Hasła

**Hashowanie**: bcrypt (salt rounds = 12)

**Walidacja** (przy rejestracji):
- Min 8 znaków
- Wielka litera
- Cyfra
- (Opcjonalnie) znak specjalny

**Przechowywanie**: Tylko hash w bazie, nigdy plaintext.

### CORS

**Konfiguracja**: Custom middleware w `main.py`

**Allowed Origins** (development):
- `http://localhost:3000`
- `http://localhost:5173` (Vite)
- Itd.

**Credentials**: `Access-Control-Allow-Credentials: true` (dla cookies).

---

## Deployment

### Docker Compose

**Plik**: `docker-compose.yml`

**Serwisy**:
1. **backend**: FastAPI (port 8000)
2. **frontend**: Vite dev server (port 3000) lub nginx (production build)
3. **redis**: Cache i rate limiting (port 6379)
4. **db**: PostgreSQL (opcjonalnie, domyślnie SQLite)

**Uruchomienie**:
```bash
docker-compose up -d
```

**Environment variables** (w `.env`):
```env
DATABASE_URL=sqlite:///./data/code_review.db
REDIS_URL=redis://redis:6379/0
JWT_SECRET_KEY=change_this_in_production
GEMINI_API_KEY=...
GROQ_API_KEY=...
```

### Dockerfiles

#### Backend (`backend/Dockerfile`)
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### Frontend (`frontend/Dockerfile`)
```dockerfile
# Development
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

# Production (multi-stage)
FROM node:18-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/nginx.conf
CMD ["nginx", "-g", "daemon off;"]
```

### Production Checklist

1. **Environment variables**:
   - `ENVIRONMENT=production`
   - `JWT_SECRET_KEY` (losowy, bezpieczny)
   - `DATABASE_URL` (PostgreSQL, nie SQLite)
   - `CORS_ORIGINS` (tylko twoja domena)

2. **Database**:
   - PostgreSQL dla production (nie SQLite)
   - Backup strategy
   - Migracje Alembic przed startem

3. **Security**:
   - HTTPS (nginx reverse proxy z Let's Encrypt)
   - Rate limiting włączony
   - Debug mode wyłączony (`DEBUG=false`)

4. **Monitoring**:
   - Logging (structured logs, np. JSON)
   - Error tracking (Sentry, Rollbar)
   - Health checks (`/health` endpoint)

5. **Performance**:
   - Redis dla cache (nie in-memory)
   - CDN dla frontendu (statyczne pliki)
   - Load balancer (jeśli wiele instancji backendu)

---

## Rozwój i Rozszerzenia

### Dodawanie Nowego Providera LLM

**Krok 1**: Utwórz plik `backend/app/providers/nowy_provider.py`:

```python
from app.providers.base import LLMProvider, LLMMessage
import httpx

class NowyProvider(LLMProvider):
    def __init__(self):
        self.base_url = "https://api.example.com"
    
    async def generate(
        self,
        messages: list[LLMMessage],
        model: str,
        temperature: float = 0.0,
        max_tokens: int = 4096,
        api_key: str | None = None
    ) -> str:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/chat",
                json={
                    "model": model,
                    "messages": [{"role": m.role, "content": m.content} for m in messages],
                    "temperature": temperature,
                    "max_tokens": max_tokens
                },
                headers={"Authorization": f"Bearer {api_key}"}
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
```

**Krok 2**: Zarejestruj w `ProviderRouter` (`providers/router.py`):

```python
from app.providers.nowy_provider import NowyProvider

def __init__(self):
    self.providers = {
        # ... istniejące
        "nowy_provider": NowyProvider(),
    }
```

**Krok 3**: Dodaj API key do `config.py` (opcjonalnie):

```python
nowy_provider_api_key: str | None = None
```

**Krok 4**: Dodaj endpoint do listy modeli (`api/providers.py`):

```python
@router.get("/models/nowy_provider")
async def get_nowy_provider_models():
    # Pobierz listę modeli z API
    return {"models": [...]}
```

### Dodawanie Nowego Agenta

**Krok 1**: Zdefiniuj rolę w `ReviewOrchestrator` (`orchestrators/review.py`):

```python
AGENT_PROMPTS = {
    # ... istniejące
    "documentation": """Jesteś ekspertem dokumentacji kodu.
    Przeanalizuj kod pod kątem jakości dokumentacji (komentarze, docstrings, README).
    ..."""
}
```

**Krok 2**: Dodaj do frontendu (`components/ReviewConfigDialog.tsx`):

```typescript
const AGENT_ROLES = [
  // ... istniejące
  { id: "documentation", label: "Documentation Expert", icon: FileText }
];
```

**Krok 3**: Zaktualizuj model bazy (`models/review.py`):

```python
role: str = Field(max_length=50)  # general, security, performance, style, documentation
```

**Krok 4**: Migracja Alembic:

```bash
alembic revision --autogenerate -m "Add documentation agent"
alembic upgrade head
```

### Dodawanie Nowego Trybu Review

**Przykład**: Tryb "Consensus" (głosowanie agentów).

**Krok 1**: Dodaj do modelu (`models/review.py`):

```python
review_mode: str = Field(
    default="council",
    max_length=20,
    description="'council', 'arena', 'consensus'"
)
```

**Krok 2**: Utwórz orchestrator (`orchestrators/consensus.py`):

```python
class ConsensusOrchestrator:
    async def run_consensus(self, review_id: int, ...):
        # 1. Uruchom agentów
        # 2. Zbierz głosy (issues z każdym agentem głosującym)
        # 3. Oblicz konsensus (issue jest potwierdzone jeśli >50% agentów zgadza się)
        # 4. Zapisz wyniki
        pass
```

**Krok 3**: Dodaj endpoint (`api/reviews.py`):

```python
@router.post("/reviews/{id}/consensus")
async def run_consensus(...):
    orchestrator = ConsensusOrchestrator(session)
    await orchestrator.run_consensus(...)
```

**Krok 4**: Dodaj UI w frontendzie.

### Testowanie

#### Backend (Pytest)

**Struktura**:
```
backend/tests/
├── conftest.py          # Fixtures (test client, db session)
├── test_auth.py         # Testy autentykacji
├── test_reviews.py      # Testy review
└── test_llm_fallback.py # Testy fallback logic
```

**Przykład**:
```python
def test_create_review(client: TestClient, auth_token: str):
    response = client.post(
        "/projects/1/reviews",
        json={"agent_roles": ["general"]},
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    assert response.json()["review_id"] > 0
```

#### Frontend (Vitest)

**Przykład**:
```typescript
import { render, screen } from '@testing-library/react';
import { ReviewDetail } from '@/pages/ReviewDetail';

test('displays review summary', () => {
  render(<ReviewDetail />);
  expect(screen.getByText('Review #1')).toBeInTheDocument();
});
```

#### E2E (Playwright)

**Plik**: `e2e/review-flow.spec.ts`

```typescript
test('complete review flow', async ({ page }) => {
  await page.goto('/login');
  await page.fill('[name=email]', 'test@example.com');
  await page.fill('[name=password]', 'password123');
  await page.click('button[type=submit]');
  
  await page.goto('/projects/1');
  await page.click('text=Nowy Review');
  await page.selectOption('[name=provider]', 'mock');
  await page.click('text=Uruchom');
  
  await expect(page.locator('text=Review zakończony')).toBeVisible();
});
```

---

## Podsumowanie

**AI Code Review Arena** to zaawansowana aplikacja wykorzystująca:

- **Multi-agent architecture** - wiele specjalistycznych agentów AI
- **Dwa tryby pracy** - Council (współpraca) i Arena (debata)
- **Modularny design** - łatwe dodawanie nowych providerów i agentów
- **Modern stack** - FastAPI, React, TypeScript, SQLModel
- **Security-first** - JWT, CSRF, rate limiting, bcrypt
- **Real-time updates** - WebSocket dla monitorowania postępu
- **Production-ready** - Docker, migrations, testing, monitoring

Aplikacja została zaprojektowana z myślą o skalowalności, niezawodności i łatwości rozbudowy.

---

## Dalsza Literatura

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [React Documentation](https://react.dev/)
- [SQLModel Documentation](https://sqlmodel.tiangolo.com/)
- [TanStack Query Documentation](https://tanstack.com/query)
- [Ollama Documentation](https://ollama.ai/docs)
- [Gemini API Documentation](https://ai.google.dev/docs)

---

**Autor**: AI Code Review Arena Team  
**Wersja**: 1.0.0  
**Data**: 2025-01-16
