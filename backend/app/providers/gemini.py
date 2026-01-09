"""Google Gemini LLM provider."""
import httpx
from app.providers.base import LLMProvider, LLMMessage
from app.config import settings


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
            model: Gemini model name (default: gemini-1.5-flash)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate

        Returns:
            Generated text
        """
        if not self.is_available():
            raise ValueError("Gemini API key not configured")

        if model is None:
            model = "gemini-1.5-flash"

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

        # Make request to Gemini
        async with httpx.AsyncClient(timeout=60.0) as client:
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
            response.raise_for_status()

            result = response.json()

            # Extract text from response
            if "candidates" in result and len(result["candidates"]) > 0:
                candidate = result["candidates"][0]
                if "content" in candidate and "parts" in candidate["content"]:
                    parts = candidate["content"]["parts"]
                    if len(parts) > 0 and "text" in parts[0]:
                        return parts[0]["text"]

            raise ValueError("Unexpected Gemini API response format")
