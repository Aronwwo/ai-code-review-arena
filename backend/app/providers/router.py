"""Provider router for selecting and routing to LLM providers."""
from app.providers.base import LLMProvider, LLMMessage
from app.providers.mock import MockProvider
from app.providers.ollama import OllamaProvider
from app.providers.openai import OpenAIProvider
from app.providers.anthropic import AnthropicProvider
from app.providers.groq import GroqProvider
from app.providers.gemini import GeminiProvider
from app.providers.cloudflare import CloudflareProvider
from app.providers.custom import CustomProvider
from app.config import settings
from pydantic import BaseModel


class CustomProviderConfig(BaseModel):
    """Configuration for a custom provider from frontend."""
    id: str
    name: str
    base_url: str
    api_key: str | None = None
    header_name: str | None = "Authorization"
    header_prefix: str | None = "Bearer "


class ProviderRouter:
    """Routes LLM requests to the appropriate provider with fallback logic."""

    def __init__(self):
        """Initialize provider router with all available providers."""
        self.providers: dict[str, LLMProvider] = {
            "mock": MockProvider(),
            "ollama": OllamaProvider(),
            "openai": OpenAIProvider(),
            "anthropic": AnthropicProvider(),
            "groq": GroqProvider(),
            "gemini": GeminiProvider(),
            "cloudflare": CloudflareProvider(),
        }

    def get_provider(self, provider_name: str | None = None) -> LLMProvider:
        """Get a provider by name with fallback logic.

        Args:
            provider_name: Name of desired provider (groq, gemini, ollama, mock, etc.)

        Returns:
            LLMProvider instance

        Fallback order:
        1. Specified provider (if available)
        2. Default provider from settings (if available)
        3. Ollama (if running)
        4. Mock (always available)
        """
        # Try specified provider
        if provider_name:
            provider = self.providers.get(provider_name.lower())
            if provider and provider.is_available():
                return provider

        # Try default provider from settings
        default_provider = self.providers.get(settings.default_provider.lower())
        if default_provider and default_provider.is_available():
            return default_provider

        # Try Ollama as fallback
        ollama = self.providers["ollama"]
        if ollama.is_available():
            return ollama

        # Final fallback: Mock
        return self.providers["mock"]

    def get_provider_with_key(self, provider_name: str, api_key: str | None = None) -> LLMProvider:
        """Get a provider instance with a specific API key.

        Args:
            provider_name: Name of provider
            api_key: API key to use (optional)

        Returns:
            LLMProvider instance configured with the API key
        """
        provider_name_lower = provider_name.lower()

        # For providers that don't need API keys, use the default instance
        if provider_name_lower in ["mock", "ollama"]:
            return self.providers[provider_name_lower]

        # Create a new provider instance with the API key
        if provider_name_lower == "openai":
            return OpenAIProvider(api_key=api_key)
        elif provider_name_lower == "anthropic":
            return AnthropicProvider(api_key=api_key)
        elif provider_name_lower == "groq":
            return GroqProvider(api_key=api_key)
        elif provider_name_lower == "gemini":
            return GeminiProvider(api_key=api_key)
        elif provider_name_lower == "cloudflare":
            return CloudflareProvider(api_key=api_key)
        else:
            # Fallback to default provider
            return self.get_provider(provider_name)

    def get_custom_provider(self, config: CustomProviderConfig) -> LLMProvider:
        """Create a custom provider from frontend configuration.

        Args:
            config: Custom provider configuration

        Returns:
            CustomProvider instance
        """
        return CustomProvider(
            provider_id=config.id,
            provider_name=config.name,
            base_url=config.base_url,
            api_key=config.api_key,
            header_name=config.header_name,
            header_prefix=config.header_prefix,
        )

    async def generate(
        self,
        messages: list[LLMMessage],
        provider_name: str | None = None,
        model: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 4096,
        api_key: str | None = None,
        custom_provider_config: CustomProviderConfig | None = None
    ) -> tuple[str, str, str]:
        """Generate text using the selected provider.

        Args:
            messages: List of conversation messages
            provider_name: Desired provider name
            model: Model name
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            api_key: Optional API key for the provider
            custom_provider_config: Configuration for custom provider

        Returns:
            Tuple of (generated_text, provider_name, model_name)
        """
        # Use custom provider if config provided
        if custom_provider_config:
            provider = self.get_custom_provider(custom_provider_config)
        # Get provider (with API key if provided)
        elif api_key and provider_name:
            provider = self.get_provider_with_key(provider_name, api_key)
        else:
            provider = self.get_provider(provider_name)

        # Use default model if not specified
        if model is None:
            model = settings.default_model

        # Generate text
        text = await provider.generate(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens
        )

        return text, provider.name, model

    def is_provider_available(self, provider_name: str) -> bool:
        """Check if a provider is available.

        Args:
            provider_name: Provider name to check

        Returns:
            True if provider is available, False otherwise
        """
        provider = self.providers.get(provider_name.lower())
        return provider.is_available() if provider else False


# Global provider router instance
provider_router = ProviderRouter()
