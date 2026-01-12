"""Ollama API endpoints."""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from app.providers.ollama import OllamaProvider
from app.utils.cache import cache
from app.api.deps import get_current_user
import httpx


router = APIRouter(prefix="/ollama", tags=["ollama"])


class ModelsResponse(BaseModel):
    """Response model for list of available models."""

    models: list[str]
    cached: bool = False


@router.get("/models", response_model=ModelsResponse)
async def list_ollama_models(current_user=Depends(get_current_user)):
    """List available Ollama models.

    Returns cached results for 60 seconds to avoid hammering Ollama API.

    Requires authentication.

    Returns:
        ModelsResponse: List of available model names

    Raises:
        HTTPException: If Ollama is not available or request fails
    """
    cache_key = "ollama:models"

    # Try to get from cache first
    cached_models = cache.get(cache_key)
    if cached_models is not None:
        return ModelsResponse(models=cached_models, cached=True)

    # Fetch from Ollama
    try:
        ollama = OllamaProvider()
        models = await ollama.list_models()

        # Remove duplicates and sort
        unique_models = sorted(list(set(models)))

        # Cache for 60 seconds
        cache.set(cache_key, unique_models, ttl=60)

        return ModelsResponse(models=unique_models, cached=False)

    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Ollama is not available. Make sure Ollama is running at the configured URL. Error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch Ollama models: {str(e)}"
        )


@router.get("/health")
async def check_ollama_health(current_user=Depends(get_current_user)):
    """Check if Ollama is available and responding.

    Requires authentication.

    Returns:
        dict: Health status

    Raises:
        HTTPException: If Ollama is not available
    """
    try:
        ollama = OllamaProvider()
        is_available = ollama.is_available()

        if not is_available:
            raise HTTPException(
                status_code=503,
                detail="Ollama is not available. Make sure Ollama is running."
            )

        return {
            "status": "healthy",
            "ollama_url": ollama.base_url,
            "available": True
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to check Ollama health: {str(e)}"
        )
