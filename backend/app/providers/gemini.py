"""Google Gemini LLM provider."""
import asyncio
import logging
import httpx
from app.providers.base import LLMProvider, LLMMessage
from app.config import settings

logger = logging.getLogger(__name__)


class GeminiProvider(LLMProvider):
    """Google Gemini provider."""

    def __init__(self, api_key: str | None = None):
        """Initialize Gemini provider.

        Args:
            api_key: Google AI API key (default from settings)
        """
        self.api_key = api_key or settings.gemini_api_key
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"

    @property
    def name(self) -> str:
        """Provider name."""
        return "gemini"

    def is_available(self) -> bool:
        """Check if Gemini API key is configured."""
        return bool(self.api_key)

    async def generate(
        self,
        messages: list[LLMMessage],
        model: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 4096
    ) -> str:
        """Generate text using Gemini.

        Args:
            messages: List of conversation messages
            model: Gemini model name (default: gemini-2.0-flash-exp)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate

        Returns:
            Generated text
        """
        if not self.is_available():
            raise ValueError("Gemini API key not configured")

        # List of models available in FREE Google AI Studio API
        # These models are available for free tier users
        free_tier_models = [
            "gemini-1.5-flash",           # Stable, fast, free tier available (RECOMMENDED)
            "gemini-1.5-flash-latest",    # Latest version of 1.5 Flash
            "gemini-1.5-pro",             # Pro model (may have rate limits on free tier)
            "gemini-1.5-pro-latest",      # Latest version of 1.5 Pro
            # Note: gemini-2.0-flash-exp and gemini-2.5-flash may not be available in free tier
        ]
        
        if model is None:
            model = "gemini-1.5-flash"  # Stable, free tier model (RECOMMENDED)
        
        # Normalize model name (remove any prefixes/suffixes)
        model_normalized = model.lower().strip()
        
        # Check if model is in free tier list, if not, warn and use fallback
        if model_normalized not in [m.lower() for m in free_tier_models]:
            # Allow gemini-2.0-flash-exp and gemini-2.5-flash but warn
            if "gemini-2" in model_normalized or "gemini-3" in model_normalized:
                logger.warning(
                    f"⚠️ Gemini model '{model}' may not be available in free tier or may have strict rate limits. "
                    f"Recommended free tier models: {', '.join(free_tier_models[:2])}. "
                    f"Using '{model}' anyway, but expect possible rate limiting."
                )
            else:
                logger.warning(
                    f"⚠️ Gemini model '{model}' may not be available in free tier. "
                    f"Free tier models: {', '.join(free_tier_models)}. "
                    f"Using fallback: gemini-1.5-flash"
                )
                model = "gemini-1.5-flash"  # Safe fallback for free tier

        # Convert messages to Gemini format
        # Gemini uses "user" and "model" roles, and combines system message into first user message
        gemini_contents = []
        system_message = ""

        for msg in messages:
            if msg.role == "system":
                system_message = msg.content
            elif msg.role == "user":
                content = msg.content
                # Prepend system message to first user message
                if system_message:
                    content = f"{system_message}\n\n{content}"
                    system_message = ""
                gemini_contents.append({
                    "role": "user",
                    "parts": [{"text": content}]
                })
            elif msg.role == "assistant":
                gemini_contents.append({
                    "role": "model",
                    "parts": [{"text": msg.content}]
                })

        # Make request to Gemini with retry on 429 (rate limiting)
        # Gemini free tier has strict rate limits - use longer delays
        max_retries = 3
        base_delay = 5.0  # Start with 5 seconds for free tier (was 2s)
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            last_error = None
            
            for attempt in range(max_retries):
                try:
                    response = await client.post(
                        f"{self.base_url}/models/{model}:generateContent",
                        params={"key": self.api_key},
                        json={
                            "contents": gemini_contents,
                            "generationConfig": {
                                "temperature": temperature,
                                "maxOutputTokens": max_tokens,
                            }
                        }
                    )
                    
                    # Handle 429 (Too Many Requests) with exponential backoff
                    if response.status_code == 429:
                        if attempt < max_retries - 1:
                            delay = base_delay * (2 ** attempt)  # Exponential backoff: 2s, 4s, 8s
                            logger.warning(
                                f"Gemini API rate limit (429) hit. Retrying in {delay}s "
                                f"(attempt {attempt + 1}/{max_retries})"
                            )
                            await asyncio.sleep(delay)
                            continue
                        else:
                            # Last attempt - raise error
                            response.raise_for_status()
                    
                    # For other status codes, raise if not successful
                    response.raise_for_status()

                    result = response.json()

                    # Extract text from response
                    if "candidates" in result and len(result["candidates"]) > 0:
                        candidate = result["candidates"][0]
                        if "content" in candidate and "parts" in candidate["content"]:
                            parts = candidate["content"]["parts"]
                            if len(parts) > 0 and "text" in parts[0]:
                                if attempt > 0:
                                    logger.info(f"✅ Gemini API call succeeded after {attempt} retry(ies)")
                                return parts[0]["text"]

                    raise ValueError("Unexpected Gemini API response format")
                    
                except httpx.HTTPStatusError as e:
                    last_error = e
                    if e.response.status_code == 429 and attempt < max_retries - 1:
                        # Already handled above, but just in case
                        continue
                    # For other HTTP errors, raise immediately
                    raise
                except Exception as e:
                    last_error = e
                    # For non-HTTP errors, don't retry
                    raise
            
            # If we get here, all retries failed
            if last_error:
                raise last_error
            raise ValueError("Gemini API call failed after all retries")
