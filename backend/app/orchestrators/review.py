"""Review orchestrator for conducting multi-agent code reviews."""
import json
import hashlib
from datetime import datetime
from sqlmodel import Session, select, func
from pydantic import BaseModel, ValidationError
from app.models.project import Project
from app.models.file import File
from app.models.review import Review, ReviewAgent, Issue, Suggestion, IssueSeverity, AgentConfig
from app.providers.base import LLMMessage
from app.providers.router import provider_router, CustomProviderConfig
from app.utils.cache import cache
from app.utils.websocket import ws_manager
from app.config import settings


class IssueSchema(BaseModel):
    """Schema for parsing issue from LLM response."""
    severity: IssueSeverity
    category: str
    title: str
    description: str
    file_name: str | None = None
    line_start: int | None = None
    line_end: int | None = None
    suggested_fix: str | None = None


class ReviewResponseSchema(BaseModel):
    """Schema for parsing review response from LLM."""
    issues: list[IssueSchema]
    summary: str | None = None


class ReviewOrchestrator:
    """Orchestrates multi-agent code reviews."""

    AGENT_PROMPTS = {
        "general": """You are an expert code reviewer focused on overall code quality and best practices.

Your responsibilities:
- Identify bugs and logical errors
- Check for code maintainability and readability
- Evaluate error handling and edge cases
- Assess code organization and structure
- Review documentation completeness

Analyze the code with a critical but constructive eye.""",

        "security": """You are a security expert code reviewer focused on identifying security vulnerabilities.

Your responsibilities:
- Identify injection vulnerabilities (SQL, XSS, command injection)
- Check for authentication and authorization flaws
- Review cryptography usage
- Detect sensitive data exposure
- Identify insecure configurations
- Check for known vulnerable dependencies

Be thorough and paranoid - security is critical.""",

        "performance": """You are a performance expert code reviewer focused on optimization opportunities.

Your responsibilities:
- Identify algorithmic inefficiencies (O(n²) where O(n) possible)
- Detect N+1 query problems
- Review memory usage patterns
- Check for unnecessary computations
- Identify blocking operations that could be async
- Review caching opportunities

Focus on measurable performance impacts.""",

        "style": """You are a code style reviewer focused on consistency and conventions.

Your responsibilities:
- Check naming conventions
- Review code formatting
- Verify documentation standards
- Check for consistent patterns
- Identify code smells
- Review type hints and annotations

Maintain high standards for code quality and consistency."""
    }

    def __init__(self, session: Session):
        """Initialize review orchestrator.

        Args:
            session: Database session
        """
        self.session = session

    async def conduct_review(
        self,
        review_id: int,
        provider_name: str | None = None,
        model: str | None = None,
        api_keys: dict[str, str] | None = None,
        agent_configs: dict[str, AgentConfig] | None = None
    ) -> Review:
        """Conduct a code review using multiple agents.

        Args:
            review_id: Review ID to conduct
            provider_name: LLM provider to use
            model: Model name to use
            api_keys: Dict of provider name to API key
            agent_configs: Per-agent configurations (may include custom_provider)

        Returns:
            Completed Review object
        """
        # Get review and project
        review = self.session.get(Review, review_id)
        if not review:
            raise ValueError(f"Review {review_id} not found")

        project = self.session.get(Project, review.project_id)
        if not project:
            raise ValueError(f"Project {review.project_id} not found")

        # Update review status
        review.status = "running"
        self.session.add(review)
        self.session.commit()

        try:
            # Get agents for this review
            agents_query = select(ReviewAgent).where(ReviewAgent.review_id == review_id)
            agents_list = self.session.exec(agents_query).all()

            # Send review started event
            agent_roles = [agent.role for agent in agents_list]
            await ws_manager.send_review_started(review_id, agent_roles)

            # Run each agent with their configured provider/model
            for agent in agents_list:
                # Get agent config if available
                agent_config = agent_configs.get(agent.role) if agent_configs else None

                # Use agent's provider/model if configured, otherwise fall back to parameters
                agent_provider = agent.provider if agent.provider != "mock" else (provider_name or agent.provider)
                agent_model = agent.model if agent.model != "default" else (model or agent.model)

                # Get API key for this agent's provider
                agent_api_key = None
                if api_keys and agent_provider:
                    agent_api_key = api_keys.get(agent_provider.lower())

                # Get custom provider config if available
                custom_provider_config = None
                if agent_config and agent_config.custom_provider:
                    cp = agent_config.custom_provider
                    custom_provider_config = CustomProviderConfig(
                        id=cp.id,
                        name=cp.name,
                        base_url=cp.base_url,
                        api_key=cp.api_key,
                        header_name=cp.header_name,
                        header_prefix=cp.header_prefix
                    )

                await self._run_agent(
                    review, project, agent.role, agent_provider, agent_model,
                    agent_api_key, custom_provider_config
                )

            # Mark review as completed
            review.status = "completed"
            review.completed_at = datetime.utcnow()

            # Get total issue count and send completed event
            issue_count_stmt = select(func.count(Issue.id)).where(Issue.review_id == review_id)
            total_issues = self.session.exec(issue_count_stmt).one()
            await ws_manager.send_review_completed(review_id, total_issues)

        except Exception as e:
            # Mark review as failed
            review.status = "failed"
            review.error_message = str(e)[:2000]
            review.completed_at = datetime.utcnow()

            # Send failed event
            await ws_manager.send_review_failed(review_id, str(e)[:500])

        self.session.add(review)
        self.session.commit()
        self.session.refresh(review)

        return review

    async def _run_agent(
        self,
        review: Review,
        project: Project,
        agent_role: str,
        provider_name: str | None,
        model: str | None,
        api_key: str | None = None,
        custom_provider_config: CustomProviderConfig | None = None
    ):
        """Run a single agent for the review.

        Args:
            review: Review object
            project: Project being reviewed
            agent_role: Agent role (general, security, performance, style)
            provider_name: LLM provider to use
            model: Model name to use
            api_key: API key for the provider (optional)
            custom_provider_config: Configuration for custom provider (optional)
        """
        # Send agent started event
        await ws_manager.send_agent_started(review.id, agent_role)

        # Build prompt
        system_prompt = self.AGENT_PROMPTS.get(agent_role, self.AGENT_PROMPTS["general"])
        user_prompt = self._build_user_prompt(project)

        messages = [
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(role="user", content=user_prompt)
        ]

        # Check cache if enabled
        cache_key = None
        effective_provider = custom_provider_config.id if custom_provider_config else (provider_name or settings.default_provider)
        if settings.enable_agent_caching:
            cache_key = cache.generate_llm_cache_key(
                provider=effective_provider,
                model=model or settings.default_model,
                prompt=system_prompt + user_prompt,
                temperature=0.0
            )
            cached_response = cache.get(cache_key)
            if cached_response:
                raw_output = cached_response
                response_provider = effective_provider
                response_model = model or settings.default_model
            else:
                # Generate response
                raw_output, response_provider, response_model = await provider_router.generate(
                    messages=messages,
                    provider_name=provider_name,
                    model=model,
                    temperature=0.0,
                    max_tokens=4096,
                    api_key=api_key,
                    custom_provider_config=custom_provider_config
                )
                # Cache the response
                cache.set(cache_key, raw_output)
        else:
            # Generate response without caching
            raw_output, response_provider, response_model = await provider_router.generate(
                messages=messages,
                provider_name=provider_name,
                model=model,
                temperature=0.0,
                max_tokens=4096,
                api_key=api_key,
                custom_provider_config=custom_provider_config
            )

        # Parse response
        parsed_successfully, issues_data = self._parse_response(raw_output)

        # Store agent record
        agent_record = ReviewAgent(
            review_id=review.id,
            role=agent_role,
            provider=response_provider,
            model=response_model,
            raw_output=raw_output[:50000],  # Truncate if too long
            parsed_successfully=parsed_successfully
        )
        self.session.add(agent_record)
        self.session.commit()

        # Store issues
        for issue_data in issues_data:
            await self._store_issue(review, issue_data)

        # Send agent completed event
        await ws_manager.send_agent_completed(
            review.id,
            agent_role,
            len(issues_data),
            parsed_successfully
        )

    def _build_user_prompt(self, project: Project) -> str:
        """Build user prompt with project code.

        Args:
            project: Project being reviewed

        Returns:
            Formatted prompt string
        """
        # Get all files for the project
        from sqlmodel import select
        statement = select(File).where(File.project_id == project.id).limit(20)
        files = self.session.exec(statement).all()

        # Build prompt
        prompt = f"""Please review the following project: {project.name}

Description: {project.description or "No description provided"}

Files ({len(files)}):

"""

        for file in files:
            # Truncate very long files
            content = file.content
            if len(content) > 5000:
                content = content[:5000] + "\n... (truncated)"

            prompt += f"""
---
File: {file.name}
Language: {file.language or "unknown"}

```
{content}
```

"""

        prompt += """
Please analyze this code and return your findings as JSON in the following format:

{
  "issues": [
    {
      "severity": "info" | "warning" | "error",
      "category": "security" | "performance" | "style" | "best-practices" | etc,
      "title": "Brief title",
      "description": "Detailed description",
      "file_name": "filename.ext",
      "line_start": 10,
      "line_end": 15,
      "suggested_fix": "Optional suggested fix"
    }
  ],
  "summary": "Optional overall summary"
}

Return ONLY valid JSON, no other text."""

        return prompt

    def _parse_response(self, raw_output: str) -> tuple[bool, list[dict]]:
        """Parse LLM response into issues.

        Args:
            raw_output: Raw LLM output

        Returns:
            Tuple of (success, issues_list)
        """
        try:
            # Try to parse as JSON
            data = json.loads(raw_output)
            schema = ReviewResponseSchema(**data)
            issues_data = [issue.model_dump() for issue in schema.issues]
            return True, issues_data

        except (json.JSONDecodeError, ValidationError):
            # Fallback: try to extract JSON from text
            try:
                # Look for JSON block
                import re
                json_match = re.search(r'\{[\s\S]*\}', raw_output)
                if json_match:
                    data = json.loads(json_match.group(0))
                    schema = ReviewResponseSchema(**data)
                    issues_data = [issue.model_dump() for issue in schema.issues]
                    return True, issues_data
            except Exception:
                pass

        # Parsing failed
        return False, []

    async def _store_issue(self, review: Review, issue_data: dict):
        """Store an issue in the database.

        Args:
            review: Review object
            issue_data: Issue data dictionary
        """
        # Find file_id if file_name is provided
        file_id = None
        if issue_data.get("file_name"):
            from sqlmodel import select
            statement = select(File).where(
                File.project_id == review.project_id,
                File.name == issue_data["file_name"]
            )
            file = self.session.exec(statement).first()
            if file:
                file_id = file.id

        # Create issue
        issue = Issue(
            review_id=review.id,
            file_id=file_id,
            severity=issue_data["severity"],
            category=issue_data["category"],
            title=issue_data["title"],
            description=issue_data["description"],
            file_name=issue_data.get("file_name"),
            line_start=issue_data.get("line_start"),
            line_end=issue_data.get("line_end")
        )
        self.session.add(issue)
        self.session.commit()
        self.session.refresh(issue)

        # Create suggestion if provided
        if issue_data.get("suggested_fix"):
            suggestion = Suggestion(
                issue_id=issue.id,
                suggested_code=issue_data["suggested_fix"],
                explanation="Suggested fix from code review agent"
            )
            self.session.add(suggestion)
            self.session.commit()
