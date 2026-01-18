"""Ollama LLM provider for local models."""
import logging
import httpx
from app.providers.base import LLMProvider, LLMMessage
from app.config import settings

logger = logging.getLogger(__name__)


class OllamaProvider(LLMProvider):
    """Ollama provider for local LLM models."""

    def __init__(self, base_url: str | None = None):
        """Initialize Ollama provider.

        Args:
            base_url: Ollama API base URL (default from settings)
        """
        self.base_url = base_url or settings.ollama_base_url

    @property
    def name(self) -> str:
        """Provider name."""
        return "ollama"

    def is_available(self) -> bool:
        """Check if Ollama is available."""
        try:
            logger.debug(f"Checking Ollama availability at {self.base_url}/api/tags")
            with httpx.Client(timeout=5.0) as client:
                response = client.get(f"{self.base_url}/api/tags")
                is_available = response.status_code == 200
                if is_available:
                    logger.info(f"✅ Ollama is available at {self.base_url}")
                else:
                    logger.warning(f"⚠️ Ollama returned status {response.status_code} at {self.base_url}")
                return is_available
        except httpx.ConnectError as e:
            logger.error(f"❌ Cannot connect to Ollama at {self.base_url}: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Ollama availability check failed: {type(e).__name__}: {e}")
            return False

    async def list_models(self) -> list[str]:
        """List available Ollama models.

        Returns:
            List of model names

        Raises:
            httpx.HTTPError: If Ollama is not available or request fails
        """
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{self.base_url}/api/tags")
            response.raise_for_status()

            data = response.json()
            models = data.get("models", [])

            # Extract full model names WITH tags (e.g., "qwen2.5-coder:1.5b")
            # Ollama requires the tag to be included in API calls
            return [model.get("name", "") for model in models if model.get("name")]

    async def generate(
        self,
        messages: list[LLMMessage],
        model: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 4096
    ) -> str:
        """Generate text using Ollama.

        Args:
            messages: List of conversation messages
            model: Ollama model name (default: qwen2.5-coder:1.5b)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate

        Returns:
            Generated text
        """
        if model is None:
            model = "qwen2.5-coder:latest"

        # Check if Ollama is available first
        if not self.is_available():
            error_msg = f"Ollama is not available at {self.base_url}. Is Ollama running?"
            logger.error(error_msg)
            raise ValueError(error_msg)

        # Verify model exists
        try:
            available_models = await self.list_models()
            if model not in available_models:
                # Try to find similar model
                similar = [m for m in available_models if model.split(':')[0] in m]
                if similar:
                    logger.warning(f"Model {model} not found. Available models: {available_models}. Using similar: {similar[0]}")
                    model = similar[0]
                else:
                    error_msg = f"Model {model} not found. Available models: {available_models}"
                    logger.error(error_msg)
                    raise ValueError(error_msg)
        except Exception as e:
            logger.warning(f"Could not verify model {model}: {e}. Proceeding anyway...")

        # Build prompt from messages
        # Ollama /api/generate endpoint expects a single prompt
        prompt = ""
        for msg in messages:
            if msg.role == "system":
                prompt += f"System: {msg.content}\n\n"
            elif msg.role == "user":
                prompt += f"User: {msg.content}\n\n"
            elif msg.role == "assistant":
                prompt += f"Assistant: {msg.content}\n\n"

        prompt += "Assistant: "

        logger.info(
            f"🦙 Ollama API call | Model: {model} | Base URL: {self.base_url} | "
            f"Temp: {temperature} | Max tokens: {max_tokens} | Prompt length: {len(prompt)} chars"
        )
        logger.debug(f"Ollama Request Prompt (first 500 chars):\n{prompt[:500]}...")

        # Make request to Ollama with retry on timeout
        # Increased timeout to 300s (5 min) for large models that need loading time
        # This matches the agent timeout to avoid premature HTTP timeouts
        async with httpx.AsyncClient(timeout=300.0) as client:
            max_retries = 2
            last_error = None

            for attempt in range(max_retries):
                try:
                    logger.info(f"🦙 Ollama request attempt {attempt + 1}/{max_retries} to {self.base_url}/api/generate")
                    response = await client.post(
                        f"{self.base_url}/api/generate",
                        json={
                            "model": model,
                            "prompt": prompt,
                            "stream": False,
                            "options": {
                                "temperature": temperature,
                                "num_predict": max_tokens,
                            }
                        }
                    )
                    logger.info(f"🦙 Ollama response status: {response.status_code}")
                    response.raise_for_status()
                    result = response.json()
                    response_text = result.get("response", "")
                    
                    logger.info(f"🦙 Ollama response length: {len(response_text)} chars")
                    logger.debug(f"Ollama Response (first 500 chars):\n{response_text[:500]}...")
                    
                    # Check if response is empty
                    if not response_text or not response_text.strip():
                        logger.warning(f"Ollama returned empty response for model {model}")
                        raise ValueError(f"Ollama model {model} returned empty response")
                    
                    return response_text

                except httpx.TimeoutException as e:
                    last_error = e
                    logger.warning(f"Ollama timeout on attempt {attempt + 1}/{max_retries} for model {model}")
                    if attempt < max_retries - 1:
                        # Retry on timeout (except last attempt)
                        continue
                    # On last attempt, raise the error
                    raise
                except httpx.HTTPStatusError as e:
                    # HTTP error (404, 500, etc.)
                    error_msg = f"Ollama API HTTP error ({e.response.status_code}): {e.response.text[:200]}"
                    logger.error(f"{error_msg} for model {model}")
                    raise ValueError(error_msg) from e
                except httpx.RequestError as e:
                    # Network error
                    error_msg = f"Ollama network error: {str(e)[:200]}"
                    logger.error(f"{error_msg} for model {model}")
                    raise ValueError(error_msg) from e
                except Exception as e:
                    # Other errors
                    error_msg = f"Ollama error: {type(e).__name__}: {str(e)[:200]}"
                    logger.error(f"{error_msg} for model {model}")
                    raise ValueError(error_msg) from e

            # Should not reach here, but just in case
            if last_error:
                raise last_error
            raise ValueError("Ollama failed after all retries")
