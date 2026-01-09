"""Base LLM provider interface."""
from abc import ABC, abstractmethod
from typing import Any, Literal
from pydantic import BaseModel


class LLMMessage(BaseModel):
    """Message for LLM conversation."""

    role: Literal["system", "user", "assistant"]
    content: str


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    async def generate(
        self,
        messages: list[LLMMessage],
        model: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 4096
    ) -> str:
        """Generate text from messages.

        Args:
            messages: List of conversation messages
            model: Model name (provider-specific)
            temperature: Sampling temperature (0.0 = deterministic, 1.0 = creative)
            max_tokens: Maximum tokens to generate

        Returns:
            Generated text
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this provider is available (e.g., API key configured)."""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name."""
        pass
