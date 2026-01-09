"""Main FastAPI application.

Ten plik jest punktem wejścia całego backendu. Definiuje:
- Konfigurację aplikacji FastAPI
- Middleware (CORS, rate limiting)
- Routing wszystkich endpointów API
- Lifecycle hooks (startup/shutdown)
"""

# ==================== IMPORTS ====================
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Importy z naszej aplikacji
from app.config import settings  # Ustawienia z .env (klucze API, DB URL, etc.)
from app.database import create_db_and_tables  # Funkcja inicjalizująca bazę danych
from app.api import auth, projects, files, reviews, conversations, ollama, websocket, audit, evaluations, arena  # Wszystkie routery API
from app.utils.rate_limit import check_rate_limit  # Rate limiting (60 req/min)

# ==================== LOGGING CONFIGURATION ====================
# Konfiguracja systemu logowania - poziom z settings (INFO/DEBUG/ERROR)
# Format: "2025-01-09 12:30:45,123 - app.main - INFO - Application started"
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),  # Domyślnie INFO
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)  # Logger dla tego modułu



# ==================== APPLICATION LIFECYCLE ====================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events - wykonywane przy starcie i zatrzymaniu serwera.

    Startup (przed pierwszym requestem):
    - Tworzy tabele w bazie danych jeśli nie istnieją
    - Uruchamia Alembic migrations

    Shutdown (przy zatrzymaniu serwera):
    - Cleanup zasobów (np. zamknięcie połączeń)
    """
    # === STARTUP ===
    logger.info("🚀 Starting AI Code Review Arena...")
    create_db_and_tables()  # Tworzy tabele: users, projects, files, reviews, issues, etc.
    logger.info("✅ Database initialized")

    yield  # Aplikacja działa między yield a końcem

    # === SHUTDOWN ===
    logger.info("👋 Shutting down gracefully...")
    # Tutaj można dodać cleanup (zamykanie połączeń, flush cache, etc.)


# ==================== FASTAPI APP INSTANCE ====================
# Główna instancja aplikacji FastAPI - to jest serwer HTTP
app = FastAPI(
    title=settings.app_name,  # "AI Code Review Arena" z config.py
    description="Multi-agent AI code review with debate capabilities",
    version="1.0.0",
    lifespan=lifespan  # Hook dla startup/shutdown
)

# ==================== CORS MIDDLEWARE ====================
# Cross-Origin Resource Sharing - pozwala frontendowi (localhost:3000)
# wysyłać requesty do backendu (localhost:8000)
# Domeny są konfigurowane w .env przez CORS_ORIGINS (domyślnie localhost:3000,5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,  # Z config.py - tylko dozwolone domeny
    allow_credentials=False,  # Nie wysyłamy cookies cross-origin
    allow_methods=["*"],  # Wszystkie metody: GET, POST, PUT, DELETE, PATCH
    allow_headers=["*"],  # Wszystkie headery (Authorization, Content-Type, etc.)
)



# ==================== RATE LIMITING MIDDLEWARE ====================
# Middleware wykonuje się dla KAŻDEGO requesta przed dotarciem do endpointu
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """Rate limiting - ogranicza liczbę requestów do 60/minutę na IP.

    Chroni przed:
    - Spam attacks (zbyt wiele requestów)
    - Brute force attacks (próby zgadywania haseł)
    - DDoS attacks (przeciążenie serwera)

    Implementacja w app/utils/rate_limit.py
    """
    # Pomiń rate limiting dla endpointów publicznych i diagnostycznych
    if request.url.path in ["/health", "/docs", "/redoc", "/openapi.json", "/"] or request.method == "OPTIONS":
        return await call_next(request)  # Kontynuuj bez sprawdzania

    # Sprawdź limit requestów dla tego IP (in-memory cache lub Redis)
    try:
        check_rate_limit(request)  # Rzuca HTTPException jeśli przekroczono limit
    except Exception as e:
        # Zwróć 429 Too Many Requests
        return JSONResponse(
            status_code=429,
            content={"detail": str(e.detail) if hasattr(e, 'detail') else "Rate limit exceeded"}
        )

    # Wszystko OK - kontynuuj do endpointu
    response = await call_next(request)
    return response


# ==================== API ROUTERS ====================
# Każdy router dodaje swoje endpointy do aplikacji
# Format: app.include_router(router, prefix="/api", tags=["tag"])

app.include_router(auth.router)  # /auth/* - rejestracja, login, refresh token
app.include_router(projects.router)  # /projects/* - CRUD projektów
app.include_router(files.router)  # /files/* - operacje na plikach
app.include_router(reviews.router)  # /reviews/* - przeglądy kodu
app.include_router(reviews.projects_router)  # /projects/{id}/reviews - przeglądy per projekt
app.include_router(conversations.router)  # /conversations/* - dyskusje agentów
app.include_router(conversations.reviews_router)  # /reviews/{id}/conversations
app.include_router(conversations.issues_router)  # /issues/{id}/conversations - Arena mode
app.include_router(ollama.router)  # /ollama/* - komunikacja z Ollama (lista modeli)
app.include_router(websocket.router)  # /ws/* - WebSocket dla real-time updates
app.include_router(audit.router)  # /audit/* - logi audytowe (admin only)
app.include_router(evaluations.router)  # /evaluations/* - Model Duel (porównania i rankingi)
app.include_router(arena.router)  # /arena/* - Combat Arena (porównywanie pełnych schematów review)


# ==================== HEALTH CHECK ENDPOINTS ====================
@app.get("/health")
async def health_check():
    """Health check endpoint - sprawdza czy serwer działa.

    Używane przez:
    - Docker health checks
    - Load balancers
    - Monitoring tools (Prometheus, Datadog)

    Returns:
        dict: Status serwera, environment, wersja
    """
    return {
        "status": "healthy",
        "environment": settings.environment,  # development/production/test
        "version": "1.0.0"
    }


@app.get("/")
async def root():
    """Root endpoint - podstawowe info o API.

    Endpoint główny - pokazuje gdzie znaleźć dokumentację.

    Returns:
        dict: Welcome message i linki do dokumentacji
    """
    return {
        "message": "AI Code Review Arena API",
        "docs": "/docs",  # Swagger UI - interaktywna dokumentacja
        "health": "/health"  # Health check
    }
