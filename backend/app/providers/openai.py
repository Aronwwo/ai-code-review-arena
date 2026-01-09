"""OpenAI LLM provider."""
import httpx
from app.providers.base import LLMProvider, LLMMessage
from app.config import settings


class OpenAIProvider(LLMProvider):
    """OpenAI provider for GPT models."""

    def __init__(self, api_key: str | None = None):
        """Initialize OpenAI provider.

        Args:
            api_key: OpenAI API key (default from settings)
        """
        self.api_key = api_key or getattr(settings, 'openai_api_key', None)
        self.base_url = "https://api.openai.com/v1"

    @property
    def name(self) -> str:
        """Provider name."""
        return "openai"

    def is_available(self) -> bool:
        """Check if OpenAI API key is configured."""
        return bool(self.api_key)

    async def generate(
        self,
        messages: list[LLMMessage],
        model: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 4096
    ) -> str:
        """Generate text using OpenAI.

        Args:
            messages: List of conversation messages
            model: OpenAI model name (default: gpt-4o-mini)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate

        Returns:
            Generated text
        """
        if not self.is_available():
            raise ValueError("OpenAI API key not configured")

        if model is None:
            model = "gpt-4o-mini"

        # Convert messages to OpenAI format
        openai_messages = [
            {"role": m.role, "content": m.content}
            for m in messages
        ]

        # Make request to OpenAI
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
