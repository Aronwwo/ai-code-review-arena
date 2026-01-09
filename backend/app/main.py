"""Main FastAPI application."""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.config import settings
from app.database import create_db_and_tables
from app.api import auth, projects, files, reviews, conversations, ollama, websocket, audit
from app.utils.rate_limit import check_rate_limit

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    create_db_and_tables()
    yield
    # Shutdown
    pass


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    description="Multi-agent AI code review with debate capabilities",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Rate limiting middleware
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """Apply rate limiting to all requests."""
    # Skip rate limiting for health check, docs, and OPTIONS (CORS preflight)
    if request.url.path in ["/health", "/docs", "/redoc", "/openapi.json", "/"] or request.method == "OPTIONS":
        return await call_next(request)

    # Apply rate limiting (uses IP-based limiting)
    try:
        check_rate_limit(request)
    except Exception as e:
        return JSONResponse(
            status_code=429,
            content={"detail": str(e.detail) if hasattr(e, 'detail') else "Rate limit exceeded"}
        )

    response = await call_next(request)
    return response


# Include routers
app.include_router(auth.router)
app.include_router(projects.router)
app.include_router(files.router)
app.include_router(reviews.router)
app.include_router(reviews.projects_router)
app.include_router(conversations.router)
app.include_router(conversations.reviews_router)
app.include_router(conversations.issues_router)
app.include_router(ollama.router)
app.include_router(websocket.router)
app.include_router(audit.router)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "environment": settings.environment,
        "version": "1.0.0"
    }


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "AI Code Review Arena API",
        "docs": "/docs",
        "health": "/health"
    }
