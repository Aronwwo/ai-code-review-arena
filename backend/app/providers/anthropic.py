"""Anthropic Claude LLM provider."""
import httpx
from app.providers.base import LLMProvider, LLMMessage
from app.config import settings


class AnthropicProvider(LLMProvider):
    """Anthropic provider for Claude models."""

    def __init__(self, api_key: str | None = None):
        """Initialize Anthropic provider.

        Args:
            api_key: Anthropic API key (default from settings)
        """
        self.api_key = api_key or getattr(settings, 'anthropic_api_key', None)
        self.base_url = "https://api.anthropic.com/v1"

    @property
    def name(self) -> str:
        """Provider name."""
        return "anthropic"

    def is_available(self) -> bool:
        """Check if Anthropic API key is configured."""
        return bool(self.api_key)

    async def generate(
        self,
        messages: list[LLMMessage],
        model: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 4096
    ) -> str:
        """Generate text using Anthropic Claude.

        Args:
            messages: List of conversation messages
            model: Claude model name (default: claude-3-5-sonnet-20250114)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate

        Returns:
            Generated text
        """
        if not self.is_available():
            raise ValueError("Anthropic API key not configured")

        if model is None:
            model = "claude-3-5-sonnet-20250114"  # Latest Claude 3.5 Sonnet (January 2025)

        # Separate system message from conversation
        system_message = ""
        conversation_messages = []

        for msg in messages:
            if msg.role == "system":
                system_message = msg.content
            else:
                conversation_messages.append({
                    "role": msg.role,
                    "content": msg.content
                })

        # Make request to Anthropic
        async with httpx.AsyncClient(timeout=60.0) as client:
            request_body = {
                "model": model,
                "messages": conversation_messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }

            # Add system message if present
            if system_message:
                request_body["system"] = system_message

            response = await client.post(
                f"{self.base_url}/messages",
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json"
                },
                json=request_body
            )
            response.raise_for_status()

            result = response.json()
            return result["content"][0]["text"]
