"""Custom LLM provider for OpenAI-compatible APIs."""
import httpx
from app.providers.base import LLMProvider, LLMMessage


class CustomProvider(LLMProvider):
    """Custom provider for any OpenAI-compatible API.

    Allows users to connect to any API that follows the OpenAI chat completions format.
    Supports custom authentication headers and base URLs.
    """

    def __init__(
        self,
        provider_id: str,
        provider_name: str,
        base_url: str,
        api_key: str | None = None,
        header_name: str = "Authorization",
        header_prefix: str = "Bearer ",
    ):
        """Initialize custom provider.

        Args:
            provider_id: Unique identifier for this provider
            provider_name: Display name for the provider
            base_url: Base URL for the API (e.g., https://api.example.com/v1)
            api_key: API key for authentication
            header_name: Name of the auth header (default: Authorization)
            header_prefix: Prefix for the API key (default: "Bearer ")
        """
        self.provider_id = provider_id
        self.provider_name = provider_name
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.header_name = header_name or "Authorization"
        self.header_prefix = header_prefix if header_prefix is not None else "Bearer "

    @property
    def name(self) -> str:
        """Provider name."""
        return self.provider_name

    def is_available(self) -> bool:
        """Check if API key is configured."""
        return bool(self.api_key and self.base_url)

    async def generate(
        self,
        messages: list[LLMMessage],
        model: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 4096
    ) -> str:
        """Generate text using the custom API.

        Args:
            messages: List of conversation messages
            model: Model name
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate

        Returns:
            Generated text
        """
        if not self.is_available():
            raise ValueError(f"Custom provider {self.provider_name} not configured")

        if model is None:
            raise ValueError("Model must be specified for custom providers")

        # Convert messages to OpenAI format
        openai_messages = [
            {"role": m.role, "content": m.content}
            for m in messages
        ]

        # Build auth header
        headers = {
            "Content-Type": "application/json"
        }

        if self.api_key:
            auth_value = f"{self.header_prefix}{self.api_key}"
            headers[self.header_name] = auth_value

        # Make request to custom API
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
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
