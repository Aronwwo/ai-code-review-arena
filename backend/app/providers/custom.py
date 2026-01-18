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

        # Build request payload
        request_payload = {
            "model": model,
            "messages": openai_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        # JSON Schema disabled for Perplexity - it causes mock/placeholder responses
        # Perplexity will return plain JSON based on the prompt instructions instead

        # Make request to custom API
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=request_payload
                )
                response.raise_for_status()

                result = response.json()
                content = result["choices"][0]["message"]["content"]
                
                # For Perplexity reasoning models, remove <think> sections if present
                if self.provider_id == "perplexity" or "perplexity" in self.provider_name.lower():
                    content = self._clean_perplexity_response(content)
                
                return content
        except httpx.HTTPStatusError as e:
            # Handle specific HTTP error codes with helpful messages
            status_code = e.response.status_code
            
            if status_code == 402:
                # 402 Payment Required - API key issue or billing problem
                error_msg = (
                    f"Błąd płatności dla providera '{self.provider_name}'. "
                    f"Sprawdź czy Twój API key jest ważny i czy konto ma wystarczające środki. "
                    f"Kod błędu: {status_code}"
                )
                raise ValueError(error_msg) from e
            elif status_code == 401:
                # 401 Unauthorized - Invalid API key
                error_msg = (
                    f"Błąd autoryzacji dla providera '{self.provider_name}'. "
                    f"Sprawdź czy Twój API key jest poprawny. "
                    f"Kod błędu: {status_code}"
                )
                raise ValueError(error_msg) from e
            elif status_code == 429:
                # 429 Too Many Requests - Rate limit
                error_msg = (
                    f"Przekroczono limit zapytań dla providera '{self.provider_name}'. "
                    f"Poczekaj chwilę i spróbuj ponownie. "
                    f"Kod błędu: {status_code}"
                )
                raise ValueError(error_msg) from e
            elif status_code == 404:
                # 404 Not Found - Model or endpoint not found
                error_msg = (
                    f"Model '{model}' lub endpoint nie został znaleziony dla providera '{self.provider_name}'. "
                    f"Sprawdź czy nazwa modelu jest poprawna. "
                    f"Kod błędu: {status_code}"
                )
                raise ValueError(error_msg) from e
            else:
                # Generic HTTP error
                error_text = e.response.text[:200] if e.response.text else "Brak szczegółów"
                error_msg = (
                    f"Błąd HTTP {status_code} dla providera '{self.provider_name}': {error_text}"
                )
                raise ValueError(error_msg) from e
        except httpx.RequestError as e:
            # Network errors
            error_msg = f"Błąd sieci dla providera '{self.provider_name}': {str(e)[:200]}"
            raise ValueError(error_msg) from e
    
    def _clean_perplexity_response(self, content: str) -> str:
        """Clean Perplexity response by removing <think> sections.
        
        Reasoning models (sonar-reasoning-pro) include <think> sections
        that need to be removed before parsing JSON.
        
        Args:
            content: Raw response content
            
        Returns:
            Cleaned content with <think> sections removed
        """
        import re
        
        # Remove <think>...</think> sections (multiline)
        content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL)
        
        # Remove standalone <think> tags
        content = re.sub(r'<think>.*?$', '', content, flags=re.DOTALL | re.MULTILINE)
        content = re.sub(r'^.*?</think>', '', content, flags=re.DOTALL | re.MULTILINE)
        
        # Clean up extra whitespace
        content = content.strip()
        
        return content
