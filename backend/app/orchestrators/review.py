"""Review orchestrator for conducting multi-agent code reviews."""
import asyncio
import json
import hashlib
import logging
from datetime import datetime, timezone
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

logger = logging.getLogger(__name__)


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
        "general": """Jesteś ekspertem ds. przeglądów kodu, skupiającym się na ogólnej jakości kodu i najlepszych praktykach.

Twoje obowiązki:
- Identyfikuj błędy i błędy logiczne
- Sprawdzaj łatwość konserwacji i czytelność kodu
- Oceniaj obsługę błędów i przypadki brzegowe
- Oceniaj organizację i strukturę kodu
- Sprawdzaj kompletność dokumentacji

Analizuj kod z krytycznym, ale konstruktywnym podejściem.
Odpowiadaj krótko, rzeczowo i tylko w ramach tej roli.

WAŻNE: Preferuj język polski; jeśli nie możesz, użyj angielskiego. Dbaj o szybkie odpowiedzi i ograniczaj długość.""",

        "security": """Jesteś ekspertem ds. bezpieczeństwa, skupiającym się na identyfikacji luk w zabezpieczeniach.

Twoje obowiązki:
- Identyfikuj luki injection (SQL, XSS, command injection)
- Sprawdzaj błędy uwierzytelniania i autoryzacji
- Przeglądaj użycie kryptografii
- Wykrywaj narażenie wrażliwych danych
- Identyfikuj niebezpieczne konfiguracje
- Sprawdzaj znane podatne zależności

Bądź dokładny i ostrożny - bezpieczeństwo jest kluczowe.
Odpowiadaj krótko, rzeczowo i tylko w ramach tej roli.

WAŻNE: Preferuj język polski; jeśli nie możesz, użyj angielskiego. Dbaj o szybkie odpowiedzi i ograniczaj długość.""",

        "performance": """Jesteś ekspertem ds. wydajności, skupiającym się na możliwościach optymalizacji.

Twoje obowiązki:
- Identyfikuj nieefektywność algorytmiczną (O(n²) gdzie możliwe O(n))
- Wykrywaj problemy N+1 zapytań
- Przeglądaj wzorce użycia pamięci
- Sprawdzaj niepotrzebne obliczenia
- Identyfikuj operacje blokujące, które mogłyby być async
- Przeglądaj możliwości cache'owania

Skup się na mierzalnym wpływie na wydajność.
Odpowiadaj krótko, rzeczowo i tylko w ramach tej roli.

WAŻNE: Preferuj język polski; jeśli nie możesz, użyj angielskiego. Dbaj o szybkie odpowiedzi i ograniczaj długość.""",

        "style": """Jesteś recenzentem stylu kodu, skupiającym się na spójności i konwencjach.

Twoje obowiązki:
- Sprawdzaj konwencje nazewnictwa
- Przeglądaj formatowanie kodu
- Weryfikuj standardy dokumentacji
- Sprawdzaj spójne wzorce
- Identyfikuj code smells
- Przeglądaj type hints i adnotacje

Utrzymuj wysokie standardy jakości i spójności kodu.
Odpowiadaj krótko, rzeczowo i tylko w ramach tej roli.

WAŻNE: Preferuj język polski; jeśli nie możesz, użyj angielskiego. Dbaj o szybkie odpowiedzi i ograniczaj długość."""
    }

    MODERATOR_PROMPT = """Jesteś Moderatorem przeglądu kodu. Poniżej znajdują się odpowiedzi od różnych agentów-ekspertów.

UWAGA: Agenci oznaczeni jako [TIMEOUT] nie odpowiedzieli w wyznaczonym czasie - IGNORUJ ich całkowicie.

Twoim zadaniem jest:
1. Przeanalizować odpowiedzi wszystkich agentów (oprócz tych z timeout)
2. Stworzyć JEDEN końcowy raport, który syntetyzuje wszystkie znalezione problemy
3. Usunąć duplikaty i podsumować najważniejsze kwestie
4. Ocenić ogólną jakość kodu

Odpowiedz w formacie JSON:
{
  "summary": "Ogólne podsumowanie przeglądu kodu PO POLSKU - 2-3 zdania",
  "issues": [
    {
      "severity": "info" | "warning" | "error",
      "category": "security" | "performance" | "style" | "best-practices",
      "title": "Krótki tytuł PO POLSKU",
      "description": "Szczegółowy opis PO POLSKU",
      "suggested_fix": "Sugestia naprawy PO POLSKU (opcjonalne)"
    }
  ],
  "overall_quality": "Ocena ogólna: świetny / dobry / wymaga poprawy / słaby"
}

Zwróć TYLKO poprawny JSON, bez dodatkowego tekstu."""

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
        agent_configs: dict[str, AgentConfig] | None = None,
        moderator_config: dict | None = None
    ) -> Review:
        """Przeprowadź code review używając wielu agentów AI.

        Uproszczony flow dla obu trybów (council/arena):
        1. Każdy agent daje JEDNĄ odpowiedź (z konfigurowlnym timeout)
        2. Moderator syntetyzuje wszystkie odpowiedzi w jeden raport
        3. Agenci z timeout są oznaczani i ignorowani przez moderatora

        Args:
            review_id: ID review do przeprowadzenia
            provider_name: Provider LLM (opcjonalny fallback)
            model: Nazwa modelu (opcjonalny fallback)
            api_keys: Klucze API per provider: {provider_name: api_key}
            agent_configs: Konfiguracja per agent: {role: AgentConfig} z timeout_seconds
            moderator_config: Konfiguracja moderatora

        Returns:
            Ukończony obiekt Review ze statusem 'completed' lub 'failed'
        """
        # Pobierz review i projekt
        review = self.session.get(Review, review_id)
        if not review:
            raise ValueError(f"Review {review_id} nie istnieje")

        project = self.session.get(Project, review.project_id)
        if not project:
            raise ValueError(f"Project {review.project_id} nie istnieje")

        review_mode = review.review_mode or "council"
        logger.info(f"Review {review_id}: tryb {review_mode.upper()}")

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

            # Normalize configs
            typed_agent_configs: dict[str, AgentConfig] = {}
            if agent_configs:
                for role, config in agent_configs.items():
                    typed_agent_configs[role] = config if isinstance(config, AgentConfig) else AgentConfig(**config)

            typed_moderator_config = None
            if moderator_config:
                typed_moderator_config = (
                    moderator_config
                    if isinstance(moderator_config, AgentConfig)
                    else AgentConfig(**moderator_config)
                )

            # === KROK 1: Uruchom wszystkich agentów ===
            agent_responses: dict[str, str | None] = {}

            for agent in agents_list:
                # Get agent config if available
                agent_config = typed_agent_configs.get(agent.role)

                # Use agent's provider/model if configured
                agent_provider = agent.provider if agent.provider != "mock" else (provider_name or agent.provider)
                agent_model = agent.model if agent.model != "default" else (model or agent.model)

                # Get timeout from config (default 180s = 3 min)
                timeout_seconds = agent_config.timeout_seconds if agent_config else 180

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

                # Run agent with timeout
                response = await self._run_agent(
                    review, project, agent, agent_provider, agent_model,
                    agent_api_key, custom_provider_config, timeout_seconds
                )
                agent_responses[agent.role] = response

            # === KROK 2: Uruchom moderatora ===
            await self._run_moderator(
                review=review,
                project=project,
                agent_responses=agent_responses,
                moderator_config=typed_moderator_config,
                provider_name=provider_name,
                model=model,
                api_keys=api_keys
            )

            # Mark review as completed
            review.status = "completed"
            review.completed_at = datetime.now(timezone.utc)

            # Get total issue count and send completed event
            issue_count_stmt = select(func.count(Issue.id)).where(Issue.review_id == review_id)
            total_issues = self.session.exec(issue_count_stmt).one()
            await ws_manager.send_review_completed(review_id, total_issues)

        except Exception as e:
            logger.exception(f"Review {review_id} failed: {e}")
            # Mark review as failed
            review.status = "failed"
            review.error_message = str(e)[:2000]
            review.completed_at = datetime.now(timezone.utc)

            # Send failed event
            await ws_manager.send_review_failed(review_id, str(e)[:500])

        self.session.add(review)
        self.session.commit()
        self.session.refresh(review)

        return review

    async def _run_moderator(
        self,
        review: Review,
        project: Project,
        agent_responses: dict[str, str | None],
        moderator_config: AgentConfig | None,
        provider_name: str | None,
        model: str | None,
        api_keys: dict[str, str] | None
    ):
        """Run moderator to synthesize all agent responses into final report.

        Args:
            review: Review object
            project: Project being reviewed
            agent_responses: Dict of {role: response} (None means timeout)
            moderator_config: Moderator configuration
            provider_name: Fallback provider
            model: Fallback model
            api_keys: API keys per provider
        """
        # Build moderator prompt with all agent responses
        responses_text = ""
        for role, response in agent_responses.items():
            role_name = {
                "general": "Ekspert Ogólny",
                "security": "Ekspert Bezpieczeństwa",
                "performance": "Ekspert Wydajności",
                "style": "Ekspert Stylu"
            }.get(role, role.title())

            if response is None:
                responses_text += f"\n### {role_name} [TIMEOUT]\nAgent nie odpowiedział w wyznaczonym czasie.\n"
            else:
                responses_text += f"\n### {role_name}\n{response}\n"

        user_prompt = f"""Projekt: {project.name}

Odpowiedzi agentów:
{responses_text}

Stwórz końcowy raport przeglądu kodu."""

        messages = [
            LLMMessage(role="system", content=self.MODERATOR_PROMPT),
            LLMMessage(role="user", content=user_prompt)
        ]

        # Get moderator provider/model
        mod_provider = moderator_config.provider if moderator_config else provider_name
        mod_model = moderator_config.model if moderator_config else model
        mod_timeout = moderator_config.timeout_seconds if moderator_config else 300  # 5 min default for moderator

        # Get API key
        mod_api_key = None
        if api_keys and mod_provider:
            mod_api_key = api_keys.get(mod_provider.lower())

        # Custom provider for moderator
        custom_provider_config = None
        if moderator_config and moderator_config.custom_provider:
            cp = moderator_config.custom_provider
            custom_provider_config = CustomProviderConfig(
                id=cp.id,
                name=cp.name,
                base_url=cp.base_url,
                api_key=cp.api_key,
                header_name=cp.header_name,
                header_prefix=cp.header_prefix
            )

        try:
            async with asyncio.timeout(mod_timeout):
                raw_output, response_provider, response_model = await provider_router.generate(
                    messages=messages,
                    provider_name=mod_provider,
                    model=mod_model,
                    temperature=0.0,
                    max_tokens=8192,
                    api_key=mod_api_key,
                    custom_provider_config=custom_provider_config
                )

            # Store moderator summary in review
            review.summary = raw_output[:50000]
            self.session.add(review)
            self.session.commit()

            # Parse and store issues from moderator response
            await self._store_moderator_issues(review, raw_output)

            logger.info(f"Moderator completed for review {review.id}")

        except asyncio.TimeoutError:
            logger.error(f"Moderator timed out for review {review.id}")
            review.summary = "[TIMEOUT] Moderator przekroczył limit czasu"
            self.session.add(review)
            self.session.commit()

    async def _run_agent(
        self,
        review: Review,
        project: Project,
        agent: ReviewAgent,
        provider_name: str | None,
        model: str | None,
        api_key: str | None = None,
        custom_provider_config: CustomProviderConfig | None = None,
        timeout_seconds: int = 180
    ):
        """Run a single agent for the review with timeout handling.

        Args:
            review: Review object
            project: Project being reviewed
            agent: ReviewAgent record to update
            provider_name: LLM provider to use
            model: Model name to use
            api_key: API key for the provider (optional)
            custom_provider_config: Configuration for custom provider (optional)
            timeout_seconds: Maximum time for agent response (default 180s = 3 min)
        """
        # Send agent started event
        await ws_manager.send_agent_started(review.id, agent.role)

        # Store configured timeout
        agent.timeout_seconds = timeout_seconds

        # Build prompt
        system_prompt = self.AGENT_PROMPTS.get(agent.role, self.AGENT_PROMPTS["general"])
        user_prompt = self._build_user_prompt(project)

        messages = [
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(role="user", content=user_prompt)
        ]

        try:
            # Run with timeout
            async with asyncio.timeout(timeout_seconds):
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

            # Update the existing agent record - SUCCESS
            agent.provider = response_provider
            agent.model = response_model
            agent.raw_output = raw_output[:50000]  # Truncate if too long
            agent.parsed_successfully = parsed_successfully
            agent.timed_out = False

            self.session.add(agent)
            self.session.commit()

            # Send agent completed event
            await ws_manager.send_agent_completed(
                review.id,
                agent.role,
                len(issues_data),
                parsed_successfully
            )

            return raw_output  # Return response for moderator

        except asyncio.TimeoutError:
            # Agent timed out
            logger.warning(f"Agent {agent.role} timed out after {timeout_seconds}s")

            agent.timed_out = True
            agent.parsed_successfully = False
            agent.raw_output = f"[TIMEOUT] Agent przekroczył limit czasu ({timeout_seconds} sekund)"

            self.session.add(agent)
            self.session.commit()

            # Send agent completed event with timeout flag
            await ws_manager.send_agent_completed(
                review.id,
                agent.role,
                0,
                False
            )

            return None  # No response

    async def _store_moderator_issues(self, review: Review, summary_text: str | None):
        """Parse moderator JSON summary and store issues for council review."""
        if not summary_text:
            logger.warning("Council summary missing - no issues stored")
            return

        try:
            data = json.loads(summary_text)
        except json.JSONDecodeError:
            logger.error("Council summary is not valid JSON - no issues stored")
            return

        issues = data.get("issues", [])
        if not isinstance(issues, list):
            logger.error("Council summary issues is not a list - no issues stored")
            return

        # Remove any existing issues for this review before storing moderator issues
        existing_issues = self.session.exec(select(Issue).where(Issue.review_id == review.id)).all()
        for issue in existing_issues:
            self.session.delete(issue)
        self.session.commit()

        for issue_data in issues:
            description = (issue_data.get("description") or "").strip()
            title = description.split(".")[0][:120] if description else "Zgłoszony problem"

            issue = Issue(
                review_id=review.id,
                file_id=None,
                severity=issue_data.get("severity", "info"),
                category=issue_data.get("category", "style"),
                title=title,
                description=description,
                file_name=None,
                line_start=None,
                line_end=None
            )
            self.session.add(issue)
            self.session.commit()
            self.session.refresh(issue)

            suggested_code = issue_data.get("suggested_code")
            if suggested_code:
                suggestion = Suggestion(
                    issue_id=issue.id,
                    suggested_code=suggested_code,
                    explanation="Suggested fix from moderator"
                )
                self.session.add(suggestion)
                self.session.commit()

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
        prompt = f"""Proszę przejrzyj następujący projekt: {project.name}

Opis: {project.description or "Brak opisu"}

Pliki ({len(files)}):

"""

        for file in files:
            # Truncate very long files
            content = file.content
            if len(content) > 5000:
                content = content[:5000] + "\n... (obcięte)"

            prompt += f"""
---
Plik: {file.name}
Język: {file.language or "nieznany"}

```
{content}
```

"""

        prompt += """
Przeanalizuj ten kod i zwróć swoje uwagi w formacie JSON:

{
  "issues": [
    {
      "severity": "info" | "warning" | "error",
      "category": "security" | "performance" | "style" | "best-practices" | itp,
      "title": "Krótki tytuł PO POLSKU",
      "description": "Szczegółowy opis PO POLSKU",
      "file_name": "nazwa_pliku.ext",
      "line_start": 10,
      "line_end": 15,
      "suggested_fix": "Opcjonalna sugestia poprawki PO POLSKU"
    }
  ],
  "summary": "Opcjonalne podsumowanie PO POLSKU"
}

KRYTYCZNE: Wszystkie pola tekstowe (title, description, suggested_fix, summary) MUSZĄ być PO POLSKU.
Zwróć TYLKO poprawny JSON, bez dodatkowego tekstu."""

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

        except json.JSONDecodeError as e:
            logger.warning(f"JSON decode error in LLM response: {str(e)[:200]}")
            logger.debug(f"Raw output preview: {raw_output[:500]}...")

            # Fallback: try to extract JSON from text
            try:
                # Look for JSON block
                import re
                json_match = re.search(r'\{[\s\S]*\}', raw_output)
                if json_match:
                    data = json.loads(json_match.group(0))
                    schema = ReviewResponseSchema(**data)
                    issues_data = [issue.model_dump() for issue in schema.issues]
                    logger.info("Successfully recovered JSON from text")
                    return True, issues_data
            except Exception as fallback_error:
                logger.error(f"Fallback parsing also failed: {str(fallback_error)[:200]}")

        except ValidationError as e:
            logger.error(f"Pydantic validation error in LLM response: {e.errors()}")
            logger.debug(f"Raw output preview: {raw_output[:500]}...")

        # Parsing failed
        logger.error("Failed to parse LLM response after all attempts")
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
