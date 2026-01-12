"""Ollama LLM provider for local models."""
import httpx
from app.providers.base import LLMProvider, LLMMessage
from app.config import settings


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
            with httpx.Client(timeout=2.0) as client:
                response = client.get(f"{self.base_url}/api/tags")
                return response.status_code == 200
        except Exception:
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

        # Make request to Ollama with retry on timeout
        # Increased timeout to 120s for large models that need loading time
        async with httpx.AsyncClient(timeout=120.0) as client:
            max_retries = 2
            last_error = None

            for attempt in range(max_retries):
                try:
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
                    response.raise_for_status()
                    result = response.json()
                    return result["response"]

                except httpx.TimeoutException as e:
                    last_error = e
                    if attempt < max_retries - 1:
                        # Retry on timeout (except last attempt)
                        continue
                    # On last attempt, raise the error
                    raise

            # Should not reach here, but just in case
            if last_error:
                raise last_error
            return ""
