"""Groq LLM provider."""
import httpx
from app.providers.base import LLMProvider, LLMMessage
from app.config import settings


class GroqProvider(LLMProvider):
    """Groq provider for fast inference."""

    def __init__(self, api_key: str | None = None):
        """Initialize Groq provider.

        Args:
            api_key: Groq API key (default from settings)
        """
        self.api_key = api_key or settings.groq_api_key
        self.base_url = "https://api.groq.com/openai/v1"

    @property
    def name(self) -> str:
        """Provider name."""
        return "groq"

    def is_available(self) -> bool:
        """Check if Groq API key is configured."""
        return bool(self.api_key)

    async def generate(
        self,
        messages: list[LLMMessage],
        model: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 4096
    ) -> str:
        """Generate text using Groq.

        Args:
            messages: List of conversation messages
            model: Groq model name (default: mixtral-8x7b-32768)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate

        Returns:
            Generated text
        """
        if not self.is_available():
            raise ValueError("Groq API key not configured")

        if model is None:
            model = "mixtral-8x7b-32768"

        # Convert messages to OpenAI format (Groq uses OpenAI-compatible API)
        openai_messages = [
            {"role": m.role, "content": m.content}
            for m in messages
        ]

        # Make request to Groq
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": model,
                    "messages": openai_messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                }
            )
            response.raise_for_status()

            result = response.json()
            return result["choices"][0]["message"]["content"]
