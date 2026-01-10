"""Integration tests for LLM fallback mechanism."""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from app.providers.router import ProviderRouter
from app.providers.base import LLMMessage, LLMProvider


class TestRefusalDetection:
    """Tests for refusal detection mechanism."""

    def test_is_refusal_detects_polish_refusal(self):
        """Should detect Polish refusal patterns."""
        router = ProviderRouter()

        test_cases = [
            "Przykro mi, ale nie mogę kontynuować",
            "Nie mogę pomóc w tym zadaniu",
            "Nie jestem w stanie tego zrobić",
            "Przepraszam, ale to wykracza poza moje możliwości",
        ]

        for text in test_cases:
            assert router._is_refusal(text), f"Failed to detect refusal in: {text}"

    def test_is_refusal_detects_english_refusal(self):
        """Should detect English refusal patterns."""
        router = ProviderRouter()

        test_cases = [
            "I'm sorry, but I cannot continue",
            "I can't help with this task",
            "I cannot assist with that",
            "I apologize, but I'm not able to do this",
            "As an AI assistant, I cannot help with this",
            "I don't feel comfortable with this request",
        ]

        for text in test_cases:
            assert router._is_refusal(text), f"Failed to detect refusal in: {text}"

    def test_is_refusal_does_not_detect_normal_response(self):
        """Should not falsely detect refusal in normal responses."""
        router = ProviderRouter()

        normal_responses = [
            "Here is my analysis of the code...",
            "I found several issues in the implementation:",
            "The function can be improved by...",
            "This code looks good overall.",
            "Let me explain the problem:",
        ]

        for text in normal_responses:
            assert not router._is_refusal(text), f"False positive for: {text}"

    def test_is_refusal_checks_only_beginning(self):
        """Should only check the first 200 characters."""
        router = ProviderRouter()

        # Refusal at start - should detect
        text_start = "Przykro mi, ale nie mogę. " + "x" * 500
        assert router._is_refusal(text_start)

        # Refusal after 200 chars - should NOT detect
        text_end = "x" * 250 + "Przykro mi, ale nie mogę"
        assert not router._is_refusal(text_end)


class TestFallbackMechanism:
    """Integration tests for fallback mechanism."""

    @pytest.mark.asyncio
    async def test_mock_provider_always_succeeds(self):
        """Mock provider should always succeed without refusal."""
        router = ProviderRouter()
        messages = [LLMMessage(role="user", content="Test prompt")]

        # Use mock provider directly
        result, provider_used, _ = await router.generate(
            messages,
            provider_name="mock",
            model="default"
        )

        assert result is not None
        assert len(result) > 0
        assert provider_used == "mock"
        # Mock should not refuse
        assert not router._is_refusal(result)

    @pytest.mark.asyncio
    async def test_provider_router_handles_invalid_provider_gracefully(self):
        """Should handle invalid provider names gracefully."""
        router = ProviderRouter()
        messages = [LLMMessage(role="user", content="Test prompt")]

        # Try with non-existent provider
        # Should either fallback or raise appropriate error
        try:
            result, provider_used, _ = await router.generate(
                messages,
                provider_name="nonexistent",
                model="default"
            )
            # If it succeeds, it should have fallen back
            assert provider_used in ["ollama", "mock"]
        except Exception as e:
            # Or it raises an error, which is also valid
            assert "provider" in str(e).lower() or "error" in str(e).lower()

    @pytest.mark.asyncio
    async def test_retry_sanitizes_combat_language(self):
        """Retry should sanitize 'Combat' wording and succeed on second try."""
        class CombatSensitiveProvider(LLMProvider):
            name = "sensitive"

            def __init__(self):
                self.calls = 0

            def is_available(self) -> bool:
                return True

            async def generate(self, messages, model=None, temperature=0.0, max_tokens=4096) -> str:
                self.calls += 1
                if any("Combat" in m.content for m in messages):
                    return "Przykro mi, ale nie mogę kontynuować"
                return "OK"

        router = ProviderRouter()
        provider = CombatSensitiveProvider()
        router.providers["sensitive"] = provider

        messages = [LLMMessage(role="user", content="Combat Arena prompt test")]
        result, provider_used, _ = await router.generate(messages, provider_name="sensitive", model="default")

        assert result == "OK"
        assert provider_used == "sensitive"
        assert provider.calls == 2

    @pytest.mark.asyncio
    async def test_refusal_triggers_fallback_to_mock(self):
        """If provider refuses and retry still fails, fallback to mock should succeed."""
        class RefusingProvider(LLMProvider):
            name = "refuse"

            def is_available(self) -> bool:
                return True

            async def generate(self, messages, model=None, temperature=0.0, max_tokens=4096) -> str:
                return "Przykro mi, ale nie mogę kontynuować"

        router = ProviderRouter()
        router.providers["refuse"] = RefusingProvider()

        messages = [LLMMessage(role="user", content="Test prompt")]
        result, provider_used, _ = await router.generate(messages, provider_name="refuse", model="default")

        assert result
        assert provider_used == "mock"
        assert not router._is_refusal(result)


class TestFallbackLogging:
    """Tests for fallback logging and monitoring."""

    @pytest.mark.asyncio
    async def test_provider_router_logs_llm_calls(self, caplog):
        """Should log LLM calls for monitoring."""
        import logging
        caplog.set_level(logging.INFO)

        router = ProviderRouter()
        messages = [LLMMessage(role="user", content="Test prompt for logging")]

        # Make a call with mock provider
        await router.generate(messages, provider_name="mock", model="default")

        # Check that some logging occurred
        assert len(caplog.records) > 0
        # Should have logged the LLM call
        log_messages = [record.message for record in caplog.records]
        # Look for common logging patterns
        has_llm_log = any("LLM" in msg or "mock" in msg for msg in log_messages)
        assert has_llm_log
