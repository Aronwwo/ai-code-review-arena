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
        model = model.strip()
        if model.startswith("models/"):
            model = model.replace("models/", "", 1)
        model_normalized = model.lower()
        
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
        
        # Try alternative model names if the primary one fails with 404
        # Some accounts may need versioned model names like gemini-1.5-flash-002
        model_alternatives = [model]
        if model == "gemini-1.5-flash":
            model_alternatives.extend(["gemini-1.5-flash-002", "gemini-1.5-flash-latest"])
        elif model == "gemini-1.5-pro":
            model_alternatives.extend(["gemini-1.5-pro-002", "gemini-1.5-pro-latest"])
        
        # Try both v1beta and v1 base URLs in case one is unavailable
        base_urls = [self.base_url.rstrip("/")]
        if base_urls[0].endswith("/v1beta"):
            base_urls.append(base_urls[0][:-6] + "/v1")
        elif base_urls[0].endswith("/v1"):
            base_urls.append(base_urls[0][:-3] + "/v1beta")
        base_urls = list(dict.fromkeys(base_urls))
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            last_error = None
            
            # Try each base URL + model alternative
            for base_url in base_urls:
                move_to_next_base = False
                for model_to_try in model_alternatives:
                    last_error = None  # Reset error for each model
                    for attempt in range(max_retries):
                        try:
                            # Gemini API accepts key as query parameter (some docs show header, but query param works more reliably)
                            headers = {
                                "Content-Type": "application/json"
                            }
                            
                            response = await client.post(
                                f"{base_url}/models/{model_to_try}:generateContent",
                                params={"key": self.api_key},
                                headers=headers,
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
                            
                            # If 404 and we have more alternatives, try next model
                            if response.status_code == 404 and model_to_try != model_alternatives[-1]:
                                logger.warning(
                                    f"Gemini model '{model_to_try}' returned 404 at '{base_url}', trying next alternative..."
                                )
                                last_error = None  # Clear error to try next model
                                break  # Break inner loop, try next model
                            # If 404 and this is the last model, try next base URL if available
                            if response.status_code == 404 and base_url != base_urls[-1]:
                                logger.warning(
                                    f"Gemini model '{model_to_try}' returned 404 at '{base_url}', trying next base URL..."
                                )
                                last_error = None
                                move_to_next_base = True
                                break
                            
                            # For other status codes, raise if not successful
                            response.raise_for_status()

                            # Extract text from response
                            result = response.json()
                            if "candidates" in result and len(result["candidates"]) > 0:
                                candidate = result["candidates"][0]
                                if "content" in candidate and "parts" in candidate["content"]:
                                    parts = candidate["content"]["parts"]
                                    if len(parts) > 0 and "text" in parts[0]:
                                        if model_to_try != model:
                                            logger.info(
                                                f"✅ Gemini API call succeeded with alternative model '{model_to_try}' "
                                                f"(original: '{model}')"
                                            )
                                        elif attempt > 0:
                                            logger.info(f"✅ Gemini API call succeeded after {attempt} retry(ies)")
                                        return parts[0]["text"]

                            raise ValueError("Unexpected Gemini API response format")
                            
                        except httpx.HTTPStatusError as e:
                            last_error = e
                            if e.response.status_code == 429 and attempt < max_retries - 1:
                                # Already handled above, but just in case
                                continue
                            elif e.response.status_code == 404:
                                # 404 means model not found - try next alternative if available
                                if model_to_try != model_alternatives[-1]:
                                    # Try next model alternative
                                    last_error = None  # Clear error to try next model
                                    break  # Break attempt loop, continue with next model
                                if base_url != base_urls[-1]:
                                    # Try next base URL
                                    last_error = None
                                    move_to_next_base = True
                                    break
                                
                                # Last alternative failed - log error
                                error_detail = ""
                                try:
                                    error_json = e.response.json()
                                    error_detail = error_json.get("error", {}).get("message", "")
                                except:
                                    error_detail = e.response.text[:200] if e.response.text else ""
                                
                                logger.error(
                                    f"❌ Gemini API 404 error for all model alternatives. "
                                    f"Tried: {model_alternatives}. "
                                    f"Last URL: {e.request.url}. "
                                    f"Error: {error_detail}. "
                                    f"This usually means the models are not available or the endpoint URL is incorrect."
                                )
                                # Raise error if all alternatives failed
                                raise
                            # For other HTTP errors, raise immediately
                            raise
                        except Exception as e:
                            last_error = e
                            # For non-HTTP errors, don't retry
                            raise
                        if move_to_next_base:
                            break
                    if move_to_next_base:
                        break
                if move_to_next_base:
                    continue
            
            # If we get here, all models failed - raise the last error
            if last_error:
                raise last_error
            raise ValueError("Gemini API call failed for all model alternatives")
