# CODE GUIDE - AI Code Review Arena
## Kompletny przewodnik po architekturze i kodzie projektu

---

## 📚 SPIS TREŚCI

1. [Architektura projektu](#architektura-projektu)
2. [Backend - Szczegółowy przegląd](#backend)
3. [Frontend - Szczegółowy przegląd](#frontend)
4. [Przepływ danych](#przepływ-danych)
5. [Bezpieczeństwo](#bezpieczeństwo)
6. [Deployment](#deployment)

---

## ARCHITEKTURA PROJEKTU

```
ai-code-review-arena/
├── backend/               # Python FastAPI - REST API
│   ├── app/
│   │   ├── api/          # 📍 Endpointy API (routes)
│   │   ├── models/       # 📊 Modele bazy danych (SQLModel)
│   │   ├── orchestrators/# 🤖 Logika AI agentów
│   │   ├── providers/    # ☁️ Integracje z LLM (Ollama, Groq, etc.)
│   │   ├── utils/        # 🛠️ Funkcje pomocnicze
│   │   ├── main.py       # ⚡ Entry point aplikacji
│   │   ├── config.py     # ⚙️ Konfiguracja (.env)
│   │   └── database.py   # 💾 Połączenie z bazą danych
│   ├── alembic/          # 🔄 Migracje bazy danych
│   └── data/             # 📁 SQLite database file
├── frontend/             # React + TypeScript - UI
│   ├── src/
│   │   ├── components/   # 🧩 Reusable components
│   │   ├── pages/        # 📄 Strony aplikacji
│   │   ├── contexts/     # 🔐 React Context (Auth, Theme)
│   │   ├── hooks/        # 🪝 Custom hooks (WebSocket)
│   │   ├── lib/          # 📡 API client (axios)
│   │   └── main.tsx      # ⚡ Entry point
│   └── package.json      # Dependencies
├── .env                  # 🔑 Zmienne środowiskowe (NIE commituj!)
└── README.md             # Dokumentacja użytkownika
```

---

## BACKEND

### 1. ENTRY POINT - `app/main.py`

**Rola:** Główny plik aplikacji FastAPI

**Co robi:**
```python
# 1. Konfiguracja FastAPI
app = FastAPI(title="AI Code Review Arena")

# 2. Middleware
- CORS (cross-origin requests)
- Rate Limiting (60 req/min per IP)

# 3. Lifecycle hooks
@lifespan
- Startup: create_db_and_tables()
- Shutdown: cleanup

# 4. Routing
- Include wszystkie routery z app/api/
```

**Uruchomienie:**
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

### 2. KONFIGURACJA - `app/config.py`

**Rola:** Zarządzanie wszystkimi ustawieniami aplikacji

**Źródła danych:**
1. Zmienne środowiskowe (export VAR=value)
2. Plik `.env`
3. Wartości domyślne

**Kluczowe ustawienia:**
```python
# Database
DATABASE_URL = "sqlite:///./data/code_review.db"

# Security
JWT_SECRET_KEY = "change-in-production"  # ⚠️ WAŻNE!
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 60

# LLM Providers
OLLAMA_BASE_URL = "http://localhost:11434"
GROQ_API_KEY = None  # Opcjonalne
GEMINI_API_KEY = None  # Opcjonalne

# Rate Limiting
RATE_LIMIT_PER_MINUTE = 60
MAX_FILE_SIZE_MB = 10
```

---

### 3. BAZA DANYCH - `app/database.py`

**Rola:** Zarządzanie połączeniem z bazą danych

**Stack:**
- SQLModel (Pydantic + SQLAlchemy)
- SQLite dla development
- PostgreSQL możliwy dla production

**Komponenty:**
```python
# 1. Engine - globalna instancja połączenia
engine = create_engine(settings.database_url)

# 2. Session factory - per-request
def get_session():
    with Session(engine) as session:
        yield session  # FastAPI Depends()

# 3. Tworzenie tabel
def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
```

**Tabele:**
| Tabela | Model | Opis |
|--------|-------|------|
| users | User | Użytkownicy (email, hashed_password) |
| projects | Project | Projekty kodu |
| files | File | Pliki w projekcie |
| reviews | Review | Przeglądy kodu |
| review_agents | ReviewAgent | Status poszczególnych agentów |
| issues | Issue | Znalezione problemy |
| suggestions | Suggestion | Sugestie poprawek |
| conversations | Conversation | Dyskusje agentów (Council/Arena) |
| messages | Message | Wiadomości w dyskusjach |
| audit_logs | AuditLog | Logi audytowe |

---

### 4. MODELE - `app/models/`

#### **User Model** (`user.py`)
```python
class User(SQLModel, table=True):
    __tablename__ = "users"

    id: int | None = Field(default=None, primary_key=True)
    email: str = Field(index=True, unique=True)  # Unikalny email
    username: str
    hashed_password: str  # Bcrypt hash
    is_active: bool = True
    is_superuser: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)

# Relacje:
# - projects: List[Project] (1-to-many)
# - audit_logs: List[AuditLog] (1-to-many)
```

#### **Project Model** (`project.py`)
```python
class Project(SQLModel, table=True):
    __tablename__ = "projects"

    id: int | None = Field(default=None, primary_key=True)
    name: str  # Nazwa projektu
    description: str | None  # Opcjonalny opis
    owner_id: int = Field(foreign_key="users.id")  # FK do User
    created_at: datetime
    updated_at: datetime

# Relacje:
# - owner: User (many-to-1)
# - files: List[File] (1-to-many)
# - reviews: List[Review] (1-to-many)
```

#### **File Model** (`file.py`)
```python
class File(SQLModel, table=True):
    __tablename__ = "files"

    id: int | None = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="projects.id")
    name: str  # Nazwa pliku (np. "main.py")
    content: str  # Zawartość pliku (TEXT)
    language: str  # Język programowania ("python", "javascript")
    content_hash: str  # MD5 hash (detekcja duplikatów)
    size_bytes: int
    created_at: datetime

# Relacje:
# - project: Project (many-to-1)
# - issues: List[Issue] (1-to-many)
```

#### **Review Model** (`review.py`)
```python
class Review(SQLModel, table=True):
    __tablename__ = "reviews"

    id: int | None = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="projects.id")
    status: str  # "pending", "running", "completed", "failed"
    provider: str  # "ollama", "groq", "gemini", "mock"
    model: str  # Model name (np. "qwen2.5-coder:1.5b")
    started_at: datetime | None
    completed_at: datetime | None
    error_message: str | None

# Relacje:
# - project: Project (many-to-1)
# - agents: List[ReviewAgent] (1-to-many)
# - issues: List[Issue] (1-to-many)
# - conversations: List[Conversation] (1-to-many)

class ReviewAgent(SQLModel, table=True):
    """Status pojedynczego agenta w review."""
    review_id: int
    agent_name: str  # "General Reviewer", "Security Expert", etc.
    status: str  # "pending", "running", "completed", "failed"
    result: str | None  # JSON response z LLM

class Issue(SQLModel, table=True):
    """Pojedynczy problem znaleziony w kodzie."""
    review_id: int
    file_id: int | None
    severity: str  # "info", "warning", "error"
    category: str  # "security", "performance", "style"
    title: str
    description: str
    line_start: int | None
    line_end: int | None
    confirmed: bool  # Czy potwierdzony przez Arena?
    final_severity: str | None  # Finalna waga po Arena
    moderator_comment: str | None  # Komentarz moderatora Arena
```

#### **Conversation Model** (`conversation.py`)
```python
class Conversation(SQLModel, table=True):
    __tablename__ = "conversations"

    id: int | None = Field(default=None, primary_key=True)
    review_id: int = Field(foreign_key="reviews.id")
    mode: str  # "council" (współpraca) lub "arena" (debata)
    topic_type: str  # "file", "issue", "general"
    topic_id: int | None  # ID pliku lub issue
    status: str  # "pending", "running", "completed", "failed"
    summary: str | None  # JSON podsumowanie
    completed_at: datetime | None

# Relacje:
# - review: Review (many-to-1)
# - messages: List[Message] (1-to-many)

class Message(SQLModel, table=True):
    """Pojedyncza wiadomość w dyskusji."""
    conversation_id: int
    sender_type: str  # "agent", "moderator"
    sender_name: str  # "Prosecutor", "Defender", "Moderator"
    turn_index: int  # Kolejność w dyskusji
    content: str  # Treść wiadomości
    is_summary: bool  # Czy to podsumowanie?
```

---

### 5. API ENDPOINTS - `app/api/`

#### **Auth** (`auth.py`)
```
POST   /auth/register       - Rejestracja nowego użytkownika
POST   /auth/login          - Logowanie (zwraca JWT token)
POST   /auth/refresh        - Odświeżenie tokena
GET    /auth/me             - Informacje o zalogowanym użytkowniku
```

**Flow rejestracji:**
```python
1. User wysyła: {email, username, password}
2. Backend:
   - Waliduje password (min 8 znaków, wielka litera, cyfra)
   - Hashuje password (bcrypt)
   - Tworzy User w bazie
   - Zwraca access_token + refresh_token
3. Frontend zapisuje tokeny w localStorage
```

#### **Projects** (`projects.py`)
```
GET    /projects            - Lista projektów użytkownika (pagination)
POST   /projects            - Utworzenie nowego projektu
GET    /projects/{id}       - Szczegóły projektu
PATCH  /projects/{id}       - Aktualizacja projektu
DELETE /projects/{id}       - Usunięcie projektu

POST   /projects/{id}/files - Dodanie pliku do projektu
GET    /projects/{id}/files - Lista plików w projekcie
```

**Autoryzacja:** Każdy endpoint wymaga JWT token w header `Authorization: Bearer <token>`

**Ownership check:**
```python
# Tylko owner projektu może go modyfikować
if project.owner_id != current_user.id:
    raise HTTPException(403, "Not authorized")
```

#### **Reviews** (`reviews.py`)
```
POST   /projects/{id}/reviews     - Uruchomienie nowego review
GET    /reviews/{id}              - Status review
GET    /reviews/{id}/issues       - Lista znalezionych problemów
PATCH  /reviews/{id}/cancel       - Anulowanie review
```

**Flow review:**
```python
1. User kliknie "Run Review" w UI
2. POST /projects/{id}/reviews
   {
     "agent_names": ["General Reviewer", "Security Expert"],
     "provider": "ollama",
     "model": "qwen2.5-coder:1.5b"
   }
3. Backend:
   - Tworzy Review(status="pending")
   - Uruchamia ReviewOrchestrator w tle (BackgroundTask)
   - Zwraca review_id od razu
4. ReviewOrchestrator:
   - Dla każdego agenta:
     - Buduje prompt z kodem
     - Wywołuje LLM (przez provider_router)
     - Parsuje response (szuka issues w JSON)
     - Zapisuje Issues do bazy
   - Aktualizuje status na "completed"
5. Frontend:
   - WebSocket otrzymuje event "review_completed"
   - Refetch issues z GET /reviews/{id}/issues
```

#### **Conversations** (`conversations.py`)
```
POST   /reviews/{id}/conversations        - Council mode (współpraca)
POST   /issues/{id}/conversations         - Arena mode (debata o issue)
GET    /conversations/{id}                - Status konwersacji
GET    /conversations/{id}/messages       - Wiadomości w dyskusji
```

**Council Mode:**
```python
1. User kliknie "Council" w UI
2. POST /reviews/{id}/conversations {mode: "council"}
3. Backend (ConversationOrchestrator):
   - 1 runda dyskusji
   - 4 agentów: General, Security, Performance, Style
   - Każdy dostaje prompt + kontekst kodu + poprzednie wiadomości
   - Moderator syntetyzuje do JSON {issues: [...], summary: "..."}
4. Czas: ~30-60 sekund
```

**Arena Mode:**
```python
1. User wybiera issue i kliknie "Debatuj"
2. POST /issues/{id}/conversations {mode: "arena"}
3. Backend (ConversationOrchestrator):
   - Prosecutor: argumentuje dlaczego problem jest poważny
   - Defender: podaje kontekst i czynniki łagodzące
   - Moderator: wydaje werdykt {confirmed: bool, final_severity: str}
4. Issue zostaje zaktualizowany
5. Czas: ~30-60 sekund
```

---

### 6. ORCHESTRATORS - `app/orchestrators/`

#### **ReviewOrchestrator** (`review.py`)

**Rola:** Zarządza całym procesem code review

**Główne metody:**
```python
async def run_review(review_id: int) -> Review:
    """Główna pętla review.

    1. Pobierz review z bazy
    2. Załaduj pliki z projektu
    3. Dla każdego agenta:
       - Zbuduj prompt (system + user)
       - Wywołaj LLM przez ProviderRouter
       - Parsuj response (szukaj JSON)
       - Ekstraktuj issues
       - Zapisz do bazy
    4. Oznacz review jako completed
    """

async def _analyze_with_agent(agent_name, files, provider, model):
    """Analiza kodu przez pojedynczego agenta.

    Prompt template:
    System: "Jesteś {agent_name}. Przeanalizuj kod..."
    User: "Kod:\n{file_content}\n\nZnajdź problemy w JSON."

    Expected response (JSON):
    {
      "issues": [
        {
          "severity": "error",
          "category": "security",
          "title": "SQL Injection",
          "description": "...",
          "line_start": 10,
          "line_end": 15
        }
      ]
    }
    """
```

**Agent names:**
- `Recenzent Ogólny` - Ogólna jakość kodu
- `Ekspert Bezpieczeństwa` - Luki bezpieczeństwa (OWASP Top 10)
- `Analityk Wydajności` - Performance issues (O(n²), memory leaks)
- `Specjalista Jakości Kodu` - Style, naming, best practices

#### **ConversationOrchestrator** (`conversation.py`)

**Rola:** Zarządza dyskusjami agentów (Council i Arena)

**Council Mode:**
```python
async def _run_council_mode(conversation, provider, model):
    """Współpracująca dyskusja.

    1 runda × 4 agentów = 4 LLM calls
    Każdy agent:
    - Widzi poprzednie wiadomości
    - Dodaje swoją perspektywę
    - Max 512 tokens (3-4 zdania)

    Moderator synthesis:
    - Zbiera wszystkie wiadomości
    - Syntetyzuje do JSON {issues: [], summary: "..."}
    - 1024 tokens
    """
```

**Arena Mode:**
```python
async def _run_arena_mode(conversation, provider, model):
    """Debata o konkretnym issue.

    3 LLM calls:
    1. Prosecutor: "Ten problem jest poważny bo..."
    2. Defender: "Ale należy uwzględnić..."
    3. Moderator: JSON verdict {confirmed, final_severity, moderator_comment}

    Issue zostaje zaktualizowany:
    - issue.confirmed = verdict.confirmed
    - issue.final_severity = verdict.final_severity
    - issue.moderator_comment = verdict.moderator_comment
    """
```

---

### 7. PROVIDERS - `app/providers/`

**Rola:** Abstrakcja nad różnymi LLM providerami

**Architektura:**
```
ProviderRouter (router.py)
├── OllamaProvider (ollama.py)      - Lokalny Ollama
├── GroqProvider (groq.py)          - Groq Cloud API
├── GeminiProvider (gemini.py)      - Google Gemini API
├── CloudflareProvider (cloudflare.py) - Cloudflare Workers AI
└── MockProvider (mock.py)          - Fake responses (demo/testing)
```

**ProviderRouter:**
```python
class ProviderRouter:
    """Centralny router - wybiera providera i wywołuje LLM."""

    async def generate(
        messages: list[LLMMessage],
        provider_name: str | None = None,
        model: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 4096
    ) -> str:
        """Główna metoda - wywołuje LLM.

        1. Wybierz providera (lub użyj default z settings)
        2. Wywołaj provider.generate(messages, model, ...)
        3. Zwróć response text

        Returns:
            str: Odpowiedź LLM
        """
```

**OllamaProvider:**
```python
class OllamaProvider(BaseLLMProvider):
    """Provider dla lokalnego Ollama.

    API Endpoint: http://localhost:11434/api/generate

    Prompt building:
    messages = [
        {role: "system", content: "..."},
        {role: "user", content: "..."}
    ]
    →
    prompt = "System: ...\n\nUser: ...\n\nAssistant: "

    Request:
    {
      "model": "qwen2.5-coder:1.5b",
      "prompt": "...",
      "stream": false,
      "options": {"temperature": 0.0, "num_predict": 512}
    }

    Response:
    {
      "response": "..."
    }
    """
```

---

### 8. UTILS - `app/utils/`

#### **auth.py**
```python
# Password hashing (bcrypt)
pwd_context = CryptContext(schemes=["bcrypt"])

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

# JWT tokens
def create_access_token(user_id: int) -> str:
    payload = {
        "user_id": user_id,
        "exp": datetime.utcnow() + timedelta(minutes=60),
        "type": "access"
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm="HS256")

def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret_key, algorithms=["HS256"])

# Current user dependency
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(HTTPBearer())
) -> User:
    token = credentials.credentials
    payload = decode_token(token)
    user = session.get(User, payload["user_id"])
    if not user or not user.is_active:
        raise HTTPException(401, "Invalid authentication")
    return user
```

#### **rate_limit.py**
```python
# In-memory cache dla rate limiting
request_counts: dict[str, list[datetime]] = {}

def check_rate_limit(request: Request):
    """Rate limiting - 60 requests per minute per IP.

    1. Pobierz IP z request.client.host
    2. Pobierz timestamps z ostatniej minuty
    3. Jeśli > 60 → raise HTTPException(429)
    4. Dodaj current timestamp
    """
```

#### **websocket.py**
```python
class WebSocketManager:
    """Zarządza WebSocket connections dla real-time updates."""

    active_connections: dict[int, list[WebSocket]] = {}

    async def connect(self, review_id: int, websocket: WebSocket):
        await websocket.accept()
        if review_id not in self.active_connections:
            self.active_connections[review_id] = []
        self.active_connections[review_id].append(websocket)

    async def broadcast_event(self, review_id: int, event: dict):
        """Wysyła event do wszystkich połączonych klientów."""
        if review_id in self.active_connections:
            for ws in self.active_connections[review_id]:
                await ws.send_json(event)
```

---

## FRONTEND

### 1. ENTRY POINT - `src/main.tsx`

**Rola:** Inicjalizacja aplikacji React

```typescript
import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import App from './App'
import './index.css'

// React Query - cache i state management dla API calls
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,  // Nie refetch przy focus
      retry: 1,  // Retry raz przy błędzie
      staleTime: 60000,  // Cache ważny przez 1 min
    },
  },
})

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>  {/* React Router - routing */}
      <QueryClientProvider client={queryClient}>  {/* React Query */}
        <App />
      </QueryClientProvider>
    </BrowserRouter>
  </React.StrictMode>,
)
```

---

### 2. APP COMPONENT - `src/App.tsx`

**Rola:** Główny komponent - routing i autentykacja

```typescript
function App() {
  return (
    <AuthProvider>  {/* Context - zalogowany user */}
      <ThemeProvider>  {/* Context - dark/light mode */}
        <Toaster />  {/* Toast notifications */}
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />

          {/* Protected routes - wymagają logowania */}
          <Route element={<ProtectedRoute />}>
            <Route path="/home" element={<Home />} />
            <Route path="/projects" element={<Projects />} />
            <Route path="/projects/:id" element={<ProjectDetail />} />
            <Route path="/reviews/:id" element={<ReviewDetail />} />
            <Route path="/settings" element={<Settings />} />
          </Route>
        </Routes>
      </ThemeProvider>
    </AuthProvider>
  )
}
```

---

### 3. API CLIENT - `src/lib/api.ts`

**Rola:** Centralna konfiguracja axios dla wszystkich API calls

```typescript
import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

// Axios instance z bazowym URL
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor - dodaje JWT token do każdego requesta
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// Response interceptor - obsługa 401 (token expired)
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Token expired - wyloguj
      localStorage.removeItem('token')
      localStorage.removeItem('refresh_token')
      localStorage.removeItem('user')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export default api
```

**Użycie:**
```typescript
import api from '@/lib/api'

// GET request
const response = await api.get('/projects')
const projects = response.data

// POST request
const response = await api.post('/projects', {
  name: 'My Project',
  description: 'Test project'
})
```

---

### 4. AUTH CONTEXT - `src/contexts/AuthContext.tsx`

**Rola:** Globalny stan zalogowanego użytkownika

```typescript
interface AuthContextType {
  user: User | null
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => void
  register: (email: string, username: string, password: string) => Promise<void>
}

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  // Przy starcie - sprawdź czy user jest zalogowany
  useEffect(() => {
    const token = localStorage.getItem('token')
    const savedUser = localStorage.getItem('user')

    if (token && savedUser) {
      setUser(JSON.parse(savedUser))
    }
    setLoading(false)
  }, [])

  const login = async (email: string, password: string) => {
    const response = await api.post('/auth/login', { email, password })
    const { access_token, user: userData } = response.data

    localStorage.setItem('token', access_token)
    localStorage.setItem('user', JSON.stringify(userData))
    setUser(userData)
  }

  const logout = () => {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, register }}>
      {children}
    </AuthContext.Provider>
  )
}

// Hook do używania w komponentach
export const useAuth = () => {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth must be used within AuthProvider')
  return context
}
```

---

### 5. WEBSOCKET HOOK - `src/hooks/useReviewWebSocket.ts`

**Rola:** Real-time updates dla review status

```typescript
export const useReviewWebSocket = ({
  reviewId,
  onEvent,
}: {
  reviewId: number
  onEvent: (event: WebSocketEvent) => void
}) => {
  useEffect(() => {
    const ws = new WebSocket(`ws://localhost:8000/ws/reviews/${reviewId}`)

    ws.onopen = () => {
      console.log('WebSocket connected')
    }

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data)
      onEvent(data)  // Callback do komponentu
    }

    ws.onerror = (error) => {
      console.error('WebSocket error:', error)
    }

    ws.onclose = () => {
      console.log('WebSocket disconnected')
    }

    // Cleanup przy unmount
    return () => {
      ws.close()
    }
  }, [reviewId])
}
```

**Użycie w komponencie:**
```typescript
const ReviewDetail = () => {
  const { id } = useParams()
  const queryClient = useQueryClient()

  useReviewWebSocket({
    reviewId: id,
    onEvent: (event) => {
      if (event.type === 'review_completed') {
        // Refetch review data
        queryClient.invalidateQueries(['review', id])
        toast.success('Przegląd zakończony!')
      }
    },
  })
}
```

---

### 6. PAGES - `src/pages/`

#### **Login.tsx**
```typescript
const Login = () => {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    try {
      await login(email, password)
      navigate('/home')  // Redirect po zalogowaniu
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Login failed')
    }
  }

  return (
    <form onSubmit={handleSubmit}>
      <Input value={email} onChange={(e) => setEmail(e.target.value)} />
      <Input type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
      {error && <p className="text-red-600">{error}</p>}
      <Button type="submit">Login</Button>
    </form>
  )
}
```

#### **Projects.tsx**
```typescript
const Projects = () => {
  // React Query - fetch projects z cache
  const { data: projects, isLoading } = useQuery({
    queryKey: ['projects'],
    queryFn: async () => {
      const response = await api.get('/projects')
      return response.data.items
    },
  })

  // Mutation - create new project
  const createProjectMutation = useMutation({
    mutationFn: async (data: { name: string; description: string }) => {
      const response = await api.post('/projects', data)
      return response.data
    },
    onSuccess: () => {
      // Invalidate cache - refetch projects
      queryClient.invalidateQueries(['projects'])
      toast.success('Projekt utworzony!')
    },
  })

  if (isLoading) return <Skeleton />

  return (
    <div>
      <Button onClick={() => setShowDialog(true)}>New Project</Button>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {projects.map((project) => (
          <ProjectCard key={project.id} project={project} />
        ))}
      </div>
    </div>
  )
}
```

#### **ReviewDetail.tsx**
```typescript
const ReviewDetail = () => {
  const { id } = useParams()
  const [activeTab, setActiveTab] = useState('issues')  // issues | discussions | files
  const [selectedIssueForDebate, setSelectedIssueForDebate] = useState<number | null>(null)

  // Fetch review
  const { data: review } = useQuery({
    queryKey: ['review', id],
    queryFn: async () => {
      const response = await api.get(`/reviews/${id}`)
      return response.data
    },
  })

  // Fetch issues
  const { data: issues } = useQuery({
    queryKey: ['review', id, 'issues'],
    queryFn: async () => {
      const response = await api.get(`/reviews/${id}/issues`)
      return response.data
    },
  })

  // WebSocket dla real-time updates
  useReviewWebSocket({
    reviewId: id,
    onEvent: (event) => {
      if (event.type === 'agent_completed') {
        queryClient.invalidateQueries(['review', id])
      }
      if (event.type === 'review_completed') {
        queryClient.invalidateQueries(['review', id, 'issues'])
        toast.success('Przegląd zakończony!')
      }
    },
  })

  // Start Arena debate
  const startArenaDebate = (issueId: number) => {
    setSelectedIssueForDebate(issueId)
    setActiveTab('discussions')
    toast.info('Wybrano issue do debaty. Kliknij "Arena" poniżej.')
  }

  return (
    <Tabs value={activeTab} onValueChange={setActiveTab}>
      <TabsList>
        <TabsTrigger value="issues">Issues ({issues?.length})</TabsTrigger>
        <TabsTrigger value="discussions">Dyskusje AI</TabsTrigger>
        <TabsTrigger value="files">Pliki</TabsTrigger>
      </TabsList>

      <TabsContent value="issues">
        {issues?.map((issue) => (
          <IssueCard
            key={issue.id}
            issue={issue}
            onDebate={() => startArenaDebate(issue.id)}
          />
        ))}
      </TabsContent>

      <TabsContent value="discussions">
        {selectedIssueForDebate && (
          <Alert>Issue #{selectedIssueForDebate} wybrany do debaty Arena</Alert>
        )}
        <ConversationView
          reviewId={id}
          issueId={selectedIssueForDebate}
        />
      </TabsContent>
    </Tabs>
  )
}
```

---

## PRZEPŁYW DANYCH

### Scenariusz 1: User tworzy projekt i uruchamia review

```
1. USER INTERACTION
   │
   ├─> Klik "New Project"
   │   └─> POST /projects {name, description}
   │       └─> Backend: Project.create() → save to DB
   │           └─> Response: {id: 1, name: "My Project", ...}
   │               └─> Frontend: queryClient.invalidateQueries(['projects'])
   │                   └─> Re-fetch projects list
   │
   ├─> Klik "Add File"
   │   └─> POST /projects/1/files {name, content, language}
   │       └─> Backend: File.create() → save to DB
   │           └─> Response: {id: 1, name: "main.py", ...}
   │               └─> Frontend: queryClient.invalidateQueries(['project', 1])
   │
   └─> Klik "Run Review"
       └─> Dialog: wybór agentów, provider, model
           └─> POST /projects/1/reviews
               {
                 agent_names: ["General Reviewer", "Security Expert"],
                 provider: "ollama",
                 model: "qwen2.5-coder:1.5b"
               }
               └─> Backend:
                   ├─> Review.create(status="pending")
                   ├─> BackgroundTask: ReviewOrchestrator.run_review()
                   └─> Response immediate: {id: 1, status: "pending"}
                       └─> Frontend:
                           ├─> Navigate to /reviews/1
                           └─> WebSocket connect ws://localhost:8000/ws/reviews/1
                               └─> Listen for events

2. BACKGROUND PROCESSING (ReviewOrchestrator)
   │
   ├─> Update Review(status="running")
   │   └─> WebSocket broadcast: {type: "review_started"}
   │
   ├─> For each agent:
   │   ├─> ReviewAgent.create(status="running")
   │   │   └─> WebSocket broadcast: {type: "agent_started", agent: "General Reviewer"}
   │   │
   │   ├─> Build prompt with code
   │   ├─> Call LLM: ProviderRouter.generate()
   │   │   └─> OllamaProvider.generate()
   │   │       └─> HTTP POST http://localhost:11434/api/generate
   │   │           └─> Response: {response: "...JSON with issues..."}
   │   │
   │   ├─> Parse JSON response
   │   ├─> Extract issues
   │   ├─> Create Issue records in DB
   │   └─> ReviewAgent.update(status="completed")
   │       └─> WebSocket broadcast: {type: "agent_completed", agent: "General Reviewer"}
   │
   └─> All agents done
       ├─> Review.update(status="completed")
       └─> WebSocket broadcast: {type: "review_completed"}
           └─> Frontend:
               ├─> toast.success("Przegląd zakończony!")
               └─> queryClient.invalidateQueries(['review', 1, 'issues'])
                   └─> Re-fetch issues from GET /reviews/1/issues

3. USER VIEWS RESULTS
   │
   ├─> Tab "Issues" shows all found issues
   │   └─> Issues grouped by severity (error, warning, info)
   │
   ├─> Click issue to expand
   │   └─> Shows: description, code snippet, line numbers
   │
   └─> Click "Debatuj" button
       └─> Opens Arena debate (see Scenariusz 2)
```

### Scenariusz 2: Arena debate o konkretnym issue

```
1. USER SELECTS ISSUE FOR DEBATE
   │
   └─> Click "Debatuj" on Issue #5
       └─> Frontend:
           ├─> setSelectedIssueForDebate(5)
           ├─> setActiveTab('discussions')
           └─> Shows info banner: "Issue #5 wybrany do debaty"

2. USER STARTS ARENA
   │
   └─> Click "Arena" button
       └─> POST /issues/5/conversations {mode: "arena"}
           └─> Backend (ConversationOrchestrator):
               │
               ├─> Conversation.create(mode="arena", topic_type="issue", topic_id=5)
               ├─> Issue #5 data: {title, severity, description, file, lines}
               │
               ├─> PROSECUTOR ARGUMENT (LLM call 1)
               │   ├─> Prompt: "Argumentuj dlaczego ten problem jest poważny"
               │   ├─> Context: Issue details + file code
               │   ├─> LLM response: "Ten problem to SQL Injection które może..."
               │   └─> Message.create(sender_name="Prosecutor", content="...")
               │
               ├─> DEFENDER COUNTERARGUMENT (LLM call 2)
               │   ├─> Prompt: "Dostarcz kontekst i argumentuj za rozsądną interpretacją"
               │   ├─> Context: Issue + Prosecutor argument
               │   ├─> LLM response: "Należy uwzględnić że aplikacja ma..."
               │   └─> Message.create(sender_name="Defender", content="...")
               │
               └─> MODERATOR VERDICT (LLM call 3)
                   ├─> Prompt: "Wydaj werdykt w formacie JSON"
                   ├─> Context: Prosecutor + Defender arguments
                   ├─> LLM response JSON:
                   │   {
                   │     "confirmed": true,
                   │     "final_severity": "error",
                   │     "moderator_comment": "Problem jest poważny bo...",
                   │     "keep_issue": true
                   │   }
                   │
                   ├─> Parse JSON verdict
                   ├─> Update Issue #5:
                   │   ├─> confirmed = true
                   │   ├─> final_severity = "error"
                   │   └─> moderator_comment = "..."
                   │
                   ├─> Message.create(sender_name="Moderator", content=JSON)
                   └─> Conversation.update(status="completed")
                       └─> Response: {id: 10, mode: "arena", status: "completed"}

3. FRONTEND DISPLAYS RESULTS
   │
   └─> GET /conversations/10/messages
       └─> Returns:
           [
             {sender_name: "Prosecutor", content: "..."},
             {sender_name: "Defender", content: "..."},
             {sender_name: "Moderator", content: "{verdict JSON}"}
           ]
           └─> Display:
               ├─> Red card: Prosecutor argument
               ├─> Green card: Defender argument
               └─> Blue card: Moderator verdict
                   ├─> Badge: Confirmed ✓ / Dismissed ✗
                   ├─> Severity badge: Error (upgraded/downgraded)
                   └─> Moderator comment
```

---

## BEZPIECZEŃSTWO

### 1. Autentykacja (Authentication)

**JWT Tokens:**
```
Access Token:
- Ważność: 60 minut
- Payload: {user_id, exp, type: "access"}
- Algorytm: HS256
- Secret: settings.jwt_secret_key (⚠️ zmień w produkcji!)

Refresh Token:
- Ważność: 7 dni
- Payload: {user_id, exp, type: "refresh"}
- Używany do odświeżenia access tokena
```

**Flow:**
```
1. Login: POST /auth/login {email, password}
   └─> Backend:
       ├─> Verify password (bcrypt)
       ├─> Generate access_token + refresh_token
       └─> Response: {access_token, refresh_token, user}

2. Protected Request: GET /projects (Authorization: Bearer <token>)
   └─> Backend middleware:
       ├─> Decode JWT token
       ├─> Verify signature
       ├─> Check expiration
       ├─> Load User from DB
       └─> If valid: proceed to endpoint
           If invalid: 401 Unauthorized

3. Token Refresh: POST /auth/refresh {refresh_token}
   └─> Backend:
       ├─> Verify refresh_token
       ├─> Generate new access_token
       └─> Response: {access_token}
```

### 2. Autoryzacja (Authorization)

**Ownership checks:**
```python
# Tylko owner projektu może go modyfikować
@router.patch("/projects/{id}")
async def update_project(
    id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    project = session.get(Project, id)
    if not project:
        raise HTTPException(404, "Project not found")

    if project.owner_id != current_user.id:
        raise HTTPException(403, "Not authorized to modify this project")

    # OK - user jest ownerem
    # ... update logic
```

### 3. Password Security

**Hashing:**
```python
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Registration
hashed = pwd_context.hash("MyPassword123!")
# → "$2b$12$..."

# Login
is_valid = pwd_context.verify("MyPassword123!", hashed)
# → True/False
```

**Password strength validation:**
```python
def validate_password_strength(password: str) -> tuple[bool, str]:
    if len(password) < 8:
        return False, "Password must be at least 8 characters"

    if not re.search(r'[A-Z]', password):
        return False, "Password must contain uppercase letter"

    if not re.search(r'[a-z]', password):
        return False, "Password must contain lowercase letter"

    if not re.search(r'\d', password):
        return False, "Password must contain digit"

    return True, ""
```

### 4. SQL Injection Prevention

**ORM Parametrization:**
```python
# ✅ SAFE - SQLModel używa parameterized queries
username = request.form.get("username")
statement = select(User).where(User.username == username)
user = session.exec(statement).first()

# Generated SQL (safe):
# SELECT * FROM users WHERE username = ?
# Parameters: ('john',)

# ❌ UNSAFE - raw SQL z f-string
query = f"SELECT * FROM users WHERE username = '{username}'"
# Vulnerable to: username = "admin' OR '1'='1"
```

### 5. XSS Prevention

**Frontend (React):**
```typescript
// ✅ SAFE - React auto-escapes JSX
const userInput = "<script>alert('XSS')</script>"
return <div>{userInput}</div>
// Rendered as: &lt;script&gt;alert('XSS')&lt;/script&gt;

// ❌ UNSAFE - dangerouslySetInnerHTML
return <div dangerouslySetInnerHTML={{__html: userInput}} />
// Executes script!
```

**Backend:**
```python
# Content-Type headers
return JSONResponse(content=data)  # application/json (safe)

# HTML escaping if needed
from html import escape
sanitized = escape(user_input)
```

### 6. Rate Limiting

```python
# 60 requests per minute per IP
RATE_LIMIT_WINDOW = 60  # seconds
RATE_LIMIT_MAX = 60

request_counts: dict[str, list[datetime]] = {}

def check_rate_limit(request: Request):
    ip = request.client.host
    now = datetime.utcnow()

    # Get requests from last minute
    if ip not in request_counts:
        request_counts[ip] = []

    # Filter last minute
    request_counts[ip] = [
        ts for ts in request_counts[ip]
        if (now - ts).total_seconds() < RATE_LIMIT_WINDOW
    ]

    # Check limit
    if len(request_counts[ip]) >= RATE_LIMIT_MAX:
        raise HTTPException(429, "Too many requests")

    # Add current request
    request_counts[ip].append(now)
```

### 7. Audit Logging

```python
class AuditLog(SQLModel, table=True):
    """Logi wszystkich ważnych akcji."""
    user_id: int
    action: str  # "LOGIN", "PROJECT_CREATE", "REVIEW_CREATE"
    ip_address: str
    user_agent: str
    created_at: datetime

# Usage
audit_log = AuditLog(
    user_id=current_user.id,
    action="LOGIN",
    ip_address=request.client.host,
    user_agent=request.headers.get("user-agent"),
    created_at=datetime.utcnow()
)
session.add(audit_log)
```

---

## DEPLOYMENT

### Development

**Backend:**
```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Frontend:**
```bash
cd frontend
npm run dev  # Vite dev server na port 3000
```

**Ollama:**
```bash
ollama serve  # Port 11434
ollama pull qwen2.5-coder:1.5b
```

### Production

**Backend (Docker):**
```bash
# Build
docker build -t ai-code-review-backend ./backend

# Run
docker run -p 8000:8000 \
  -e DATABASE_URL=postgresql://user:pass@db:5432/dbname \
  -e JWT_SECRET_KEY=your-secret-key \
  -e OLLAMA_BASE_URL=http://ollama:11434 \
  ai-code-review-backend
```

**Frontend (Vite build):**
```bash
cd frontend
npm run build  # Generuje dist/

# Serve z nginx
nginx -c nginx.conf
```

**Database:**
```bash
# PostgreSQL
docker run -d \
  -e POSTGRES_PASSWORD=secret \
  -e POSTGRES_DB=code_review \
  -p 5432:5432 \
  postgres:15

# Migrations
alembic upgrade head
```

**Environment Variables (.env):**
```bash
# ⚠️ WAŻNE - W PRODUKCJI:
JWT_SECRET_KEY=<generate strong secret>
DATABASE_URL=postgresql://user:pass@host:5432/dbname
ENVIRONMENT=production
DEBUG=false
CORS_ORIGINS=https://yourdomain.com
```

---

## PODSUMOWANIE

**Architektura:**
- Backend: FastAPI + SQLModel + SQLite/PostgreSQL
- Frontend: React + TypeScript + Vite + Tailwind CSS
- AI: Multi-provider (Ollama, Groq, Gemini) z routing
- Real-time: WebSocket connections
- Security: JWT auth, bcrypt, rate limiting, audit logs

**Kluczowe flows:**
1. Auth: Register → Login → JWT token → Protected routes
2. Code Review: Upload files → Run review → LLM analysis → Issues
3. Council: Multi-agent discussion → Moderator synthesis
4. Arena: Prosecutor vs Defender → Moderator verdict

**Bezpieczeństwo:**
- Passwords: bcrypt hashing + strength validation
- Auth: JWT tokens (60min access, 7day refresh)
- SQL: ORM parametrization (no SQL injection)
- XSS: React auto-escaping
- Rate limiting: 60 req/min per IP
- Audit logs: All actions tracked

**Next steps:**
- Add README.md with setup instructions
- Add unit tests (pytest, Jest)
- Add API documentation comments
- Deploy to production

**Wszystkie szczegóły w kodzie - czytaj komentarze!** 📖
