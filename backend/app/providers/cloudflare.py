"""Cloudflare Workers AI provider."""
import httpx
from app.providers.base import LLMProvider, LLMMessage
from app.config import settings


class CloudflareProvider(LLMProvider):
    """Cloudflare Workers AI provider."""

    def __init__(self, api_token: str | None = None, account_id: str | None = None):
        """Initialize Cloudflare provider.

        Args:
            api_token: Cloudflare API token (default from settings)
            account_id: Cloudflare account ID (default from settings)
        """
        self.api_token = api_token or settings.cloudflare_api_token
        self.account_id = account_id or settings.cloudflare_account_id
        self.base_url = f"https://api.cloudflare.com/client/v4/accounts/{self.account_id}/ai/run"

    @property
    def name(self) -> str:
        """Provider name."""
        return "cloudflare"

    def is_available(self) -> bool:
        """Check if Cloudflare API token and account ID are configured."""
        return bool(self.api_token and self.account_id)

    async def generate(
        self,
        messages: list[LLMMessage],
        model: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 4096
    ) -> str:
        """Generate text using Cloudflare Workers AI.

        Args:
            messages: List of conversation messages
            model: Cloudflare model name (default: @cf/meta/llama-3-8b-instruct)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate

        Returns:
            Generated text
        """
        if not self.is_available():
            raise ValueError("Cloudflare API token or account ID not configured")

        if model is None:
            model = "@cf/meta/llama-3-8b-instruct"

        # Convert messages to Cloudflare format
        cf_messages = [
            {"role": m.role, "content": m.content}
            for m in messages
        ]

        # Make request to Cloudflare
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.base_url}/{model}",
                headers={
                    "Authorization": f"Bearer {self.api_token}",
                    "Content-Type": "application/json"
                },
                json={
                    "messages": cf_messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                }
            )
            response.raise_for_status()

            result = response.json()

            # Extract response
            if "result" in result and "response" in result["result"]:
                return result["result"]["response"]

            raise ValueError("Unexpected Cloudflare API response format")
