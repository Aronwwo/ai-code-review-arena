"""Mock LLM provider for testing and demos."""
import json
from app.providers.base import LLMProvider, LLMMessage


class MockProvider(LLMProvider):
    """Mock provider that returns realistic but fake responses."""

    @property
    def name(self) -> str:
        """Provider name."""
        return "mock"

    def is_available(self) -> bool:
        """Mock provider is always available."""
        return True

    async def generate(
        self,
        messages: list[LLMMessage],
        model: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 4096
    ) -> str:
        """Generate mock response based on message content."""
        # Extract the last user message to determine context
        user_messages = [m for m in messages if m.role == "user"]
        last_message = user_messages[-1].content if user_messages else ""

        # Check if this is a review request
        if "review" in last_message.lower() or "code" in last_message.lower():
            return self._generate_review_response(messages)

        # Check if this is a conversation/debate
        if "prosecutor" in last_message.lower() or "defender" in last_message.lower():
            return self._generate_debate_response(messages)

        if "moderator" in last_message.lower():
            return self._generate_moderator_response(messages)

        # Default: generate generic response
        return self._generate_generic_response(messages)

    def _generate_review_response(self, messages: list[LLMMessage]) -> str:
        """Generate a mock code review response with role-specific issues.

        Analyzes the system message to determine the agent role (security, performance,
        or style) and generates appropriate mock issues for testing.

        Args:
            messages: List of conversation messages including system prompt

        Returns:
            JSON-formatted string containing mock code review issues
        """
        # Determine agent role from system message
        system_messages = [m for m in messages if m.role == "system"]
        role = "general"

        if system_messages:
            system_content = system_messages[0].content.lower()
            if "security" in system_content:
                role = "security"
            elif "performance" in system_content:
                role = "performance"
            elif "style" in system_content:
                role = "style"

        # Generate role-specific issues
        issues = []

        if role == "security":
            issues = [
                {
                    "severity": "error",
                    "category": "security",
                    "title": "Potential SQL Injection Vulnerability",
                    "description": "User input is concatenated directly into SQL query without sanitization. This could allow an attacker to execute arbitrary SQL commands.",
                    "file_name": "app.py",
                    "line_start": 42,
                    "line_end": 44,
                    "suggested_fix": "Use parameterized queries or an ORM with automatic escaping."
                },
                {
                    "severity": "warning",
                    "category": "security",
                    "title": "Hardcoded API Key",
                    "description": "API key is hardcoded in source code. This is a security risk if the code is committed to version control.",
                    "file_name": "config.py",
                    "line_start": 15,
                    "line_end": 15,
                    "suggested_fix": "Move API keys to environment variables or a secure secrets manager."
                }
            ]
        elif role == "performance":
            issues = [
                {
                    "severity": "warning",
                    "category": "performance",
                    "title": "N+1 Query Problem",
                    "description": "Loop executes a database query on each iteration. This causes N+1 queries instead of a single batch query.",
                    "file_name": "models.py",
                    "line_start": 78,
                    "line_end": 82,
                    "suggested_fix": "Use eager loading or a single query with JOIN to fetch all related data at once."
                },
                {
                    "severity": "info",
                    "category": "performance",
                    "title": "Large File Read in Memory",
                    "description": "Entire file is loaded into memory at once. For large files, this could cause memory issues.",
                    "file_name": "utils.py",
                    "line_start": 123,
                    "line_end": 125,
                    "suggested_fix": "Use streaming/chunked reading for large files."
                }
            ]
        elif role == "style":
            issues = [
                {
                    "severity": "info",
                    "category": "style",
                    "title": "Inconsistent Naming Convention",
                    "description": "Function uses camelCase instead of snake_case which is PEP 8 convention for Python.",
                    "file_name": "helpers.py",
                    "line_start": 34,
                    "line_end": 34,
                    "suggested_fix": "Rename function from 'getUserData' to 'get_user_data'."
                },
                {
                    "severity": "info",
                    "category": "style",
                    "title": "Missing Docstring",
                    "description": "Public function lacks a docstring explaining its purpose and parameters.",
                    "file_name": "api.py",
                    "line_start": 56,
                    "line_end": 56,
                    "suggested_fix": "Add a docstring describing the function's purpose, parameters, and return value."
                }
            ]
        else:  # general
            issues = [
                {
                    "severity": "warning",
                    "category": "best-practices",
                    "title": "Error Handling Missing",
                    "description": "Function does not handle potential exceptions. If the operation fails, it will crash the application.",
                    "file_name": "main.py",
                    "line_start": 67,
                    "line_end": 70,
                    "suggested_fix": "Add try-except block to handle potential errors gracefully."
                },
                {
                    "severity": "info",
                    "category": "maintainability",
                    "title": "Function Too Complex",
                    "description": "Function has high cyclomatic complexity (8). Consider breaking it into smaller functions.",
                    "file_name": "processor.py",
                    "line_start": 112,
                    "line_end": 145,
                    "suggested_fix": "Extract logical blocks into separate helper functions."
                }
            ]

        # Add a deterministic additional issue
        issues.append({
            "severity": "info",
            "category": "code-quality",
            "title": "Consider Using Type Hints",
            "description": "Function parameters and return types lack type hints, making the code less maintainable.",
            "file_name": "services.py",
            "line_start": 89,
            "line_end": 89,
            "suggested_fix": "Add type hints: def process_data(data: dict[str, Any]) -> list[Result]:"
        })

        # Format as JSON
        response = {
            "issues": issues,
            "summary": f"Found {len(issues)} issues in the codebase from {role} perspective."
        }

        return json.dumps(response, indent=2)

    def _generate_debate_response(self, messages: list[LLMMessage]) -> str:
        """Generate a mock debate response for adversarial mode.

        Creates mock arguments from either prosecutor (arguing for issue severity)
        or defender (arguing against) perspective based on system prompt.

        Args:
            messages: List of conversation messages including system prompt

        Returns:
            Text argument from prosecutor or defender perspective
        """
        # Determine role
        system_messages = [m for m in messages if m.role == "system"]
        role = "unknown"

        if system_messages:
            system_content = system_messages[0].content.lower()
            if "prosecutor" in system_content:
                role = "prosecutor"
            elif "defender" in system_content:
                role = "defender"

        if role == "prosecutor":
            return """This issue represents a critical security vulnerability that could lead to data breaches. SQL injection attacks are consistently ranked in the OWASP Top 10 and have been responsible for numerous high-profile security incidents.

The concatenation of user input directly into SQL queries creates an attack vector where malicious actors can inject arbitrary SQL commands. This could allow them to:
- Extract sensitive data from the database
- Modify or delete data
- Bypass authentication
- Execute administrative operations

The severity should remain as ERROR because this is not a theoretical risk - it's an easily exploitable vulnerability that poses immediate danger to the application and its users."""

        elif role == "defender":
            return """While SQL injection is indeed a serious category of vulnerability, we need to consider the specific context of this code:

1. **Input Validation**: The application has input validation middleware that sanitizes user input before it reaches this function.

2. **Limited Scope**: This query only operates on a read-only view, not the main database tables. Even if exploited, the damage would be minimal.

3. **Access Control**: The endpoint is only accessible to authenticated administrators with IP whitelist restrictions.

4. **Legacy Code**: This is legacy code scheduled for refactoring in the next sprint. The team is already aware and has planned its replacement.

Given these mitigating factors, downgrading the severity to WARNING would be more appropriate. The issue should be fixed, but it doesn't pose the immediate critical risk suggested by ERROR status."""

        return "I understand both perspectives on this issue."

    def _generate_moderator_response(self, messages: list[LLMMessage]) -> str:
        """Generate a mock moderator response for council/arena modes.

        Creates mock verdicts for arena mode (confirming/rejecting issues after debate)
        or summary responses for council mode (synthesizing agent discussions).

        Args:
            messages: List of conversation messages

        Returns:
            JSON-formatted verdict or summary
        """
        # Check if this is an arena verdict
        if any("prosecutor" in m.content.lower() or "defender" in m.content.lower() for m in messages):
            # Generate verdict
            verdict = {
                "confirmed": random.choice([True, False]),
                "final_severity": random.choice(["warning", "error"]),
                "moderator_comment": "After reviewing both arguments, the prosecutor presents compelling evidence about the inherent risk of SQL injection. However, the defender raises valid points about mitigating controls. The issue warrants attention but the existing safeguards reduce immediate risk.",
                "keep_issue": True
            }
            return json.dumps(verdict, indent=2)

        # Council mode summary
        summary = {
            "issues": [
                {
                    "severity": "warning",
                    "category": "security",
                    "title": "Input Validation Needed",
                    "description": "Based on the council discussion, we recommend adding comprehensive input validation across all user-facing endpoints.",
                    "suggested_code": "from pydantic import BaseModel, validator\n\nclass UserInput(BaseModel):\n    data: str\n    \n    @validator('data')\n    def validate_data(cls, v):\n        # Add validation logic\n        return v",
                    "explanation": "The team consensus is that validation is essential for security and reliability."
                }
            ],
            "summary": "The council has identified several key areas for improvement, with security and performance being the highest priorities."
        }
        return json.dumps(summary, indent=2)

    def _generate_generic_response(self, messages: list[LLMMessage]) -> str:
        """Generate a generic mock response for testing.

        Fallback response generator for cases that don't match specific review,
        debate, or moderator patterns.

        Args:
            messages: List of conversation messages

        Returns:
            Generic placeholder text
        """
        return "This is a mock response from the AI Code Review Arena. In production, this would be replaced with actual LLM output."
