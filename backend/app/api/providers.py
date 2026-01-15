"""API endpoints for provider utilities."""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
import hashlib
import httpx
import asyncio

from app.api.deps import get_current_user
from app.utils.cache import cache


router = APIRouter(prefix="/api/providers", tags=["providers"])


class ProviderModelsRequest(BaseModel):
    provider_id: str
    base_url: str | None = None
    api_key: str | None = None
    header_name: str | None = "Authorization"
    header_prefix: str | None = "Bearer "


class ProviderModelsResponse(BaseModel):
    models: list[str]
    cached: bool


async def _fetch_json_with_retry(url: str, headers: dict[str, str] | None = None) -> dict:
    """Fetch JSON with retry/backoff for transient failures."""
    attempts = 3
    base_delay = 0.5
    last_error: Exception | None = None

    for attempt in range(1, attempts + 1):
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as exc:
            last_error = exc
            if attempt == attempts:
                break
            await asyncio.sleep(base_delay * (2 ** (attempt - 1)))

    raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail=f"Failed to fetch models: {str(last_error)}"
    )


@router.post("/models", response_model=ProviderModelsResponse)
async def list_provider_models(
    data: ProviderModelsRequest,
    current_user=Depends(get_current_user),
):
    """List models for a provider using its API key."""
    provider_id = data.provider_id.lower()

    if provider_id == "mock":
        return ProviderModelsResponse(models=["mock-fast", "mock-smart"], cached=True)

    if provider_id == "ollama":
        return ProviderModelsResponse(models=[], cached=True)

    if not data.api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="API key is required",
        )

    cache_key_base = f"{provider_id}:{data.base_url or ''}:{data.header_name or ''}:{data.header_prefix or ''}:{data.api_key}"
    cache_key = f"provider_models:{hashlib.sha256(cache_key_base.encode()).hexdigest()}"
    cached_models = cache.get(cache_key)
    if cached_models is not None:
        return ProviderModelsResponse(models=cached_models, cached=True)

    if provider_id == "gemini":
        base_url = (data.base_url or "https://generativelanguage.googleapis.com/v1beta").rstrip("/")
        url = f"{base_url}/models?key={data.api_key}"
        payload = await _fetch_json_with_retry(url)

        raw_models = payload.get("models", [])
        models = []
        for model in raw_models:
            name = model.get("name", "")
            if name.startswith("models/"):
                name = name.replace("models/", "", 1)
            if name:
                models.append(name)
        models = sorted(set(models))
        cache.set(cache_key, models, ttl=300)
        return ProviderModelsResponse(models=models, cached=False)

    if not data.base_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Base URL is required for this provider",
        )

    url = f"{data.base_url.rstrip('/')}/models"
    headers: dict[str, str] = {}
    header_name = data.header_name or "Authorization"
    header_prefix = data.header_prefix or ""
    if header_name:
        headers[header_name] = f"{header_prefix}{data.api_key}" if header_prefix else data.api_key

    payload = await _fetch_json_with_retry(url, headers=headers)

    models: list[str] = []
    if isinstance(payload.get("data"), list):
        models = [item.get("id") for item in payload["data"] if item.get("id")]
    elif isinstance(payload.get("models"), list):
        models = [
            item.get("id") or item.get("name")
            for item in payload["models"]
            if item.get("id") or item.get("name")
        ]
    else:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unexpected response format from provider",
        )

    models = sorted(set(models))
    cache.set(cache_key, models, ttl=300)
    return ProviderModelsResponse(models=models, cached=False)
