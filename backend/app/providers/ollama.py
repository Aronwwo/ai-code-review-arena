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

            # Extract model names
            return [model.get("name", "").split(":")[0] for model in models if model.get("name")]

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
            model = "qwen2.5-coder:1.5b"

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

        # Make request to Ollama
        async with httpx.AsyncClient(timeout=180.0) as client:
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
