"""Review orchestrator for conducting single-agent code reviews."""
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
    """Orchestrates single-agent code reviews."""

    AGENT_PROMPTS = {
        "general": """Jesteś Ekspertem Poprawności Kodu. Znajdujesz TYLKO błędy które sprawiają że kod się NIE SKOMPILUJE lub CRASHUJE.

RAPORTUJ TYLKO FAKTYCZNE BŁĘDY:
- Python: brak dwukropka po def/if/for/while, brak nawiasów [], (), {}
- TypeError: konkatenacja str + int
- IndexError: dostęp poza zakresem listy
- NameError: użycie niezdefiniowanej zmiennej
- ZeroDivisionError: dzielenie przez zero (tylko jeśli FAKTYCZNIE widzisz!)

IGNORUJ problemy bezpieczeństwa, wydajności i stylu.

Jeśli brak błędów: {"issues": [], "summary": "Kod poprawny"}"""
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
        """Przeprowadź code review używając jednego agenta AI.

        Flow:
        1. Agent daje JEDNĄ odpowiedź (z konfigurowlnym timeout)
        2. Agent zapisuje znalezione problemy bezpośrednio do bazy danych
        3. Review kończy się po zakończeniu agenta

        Args:
            review_id: ID review do przeprowadzenia
            provider_name: Provider LLM (opcjonalny fallback)
            model: Nazwa modelu (opcjonalny fallback)
            api_keys: Klucze API per provider: {provider_name: api_key}
            agent_configs: Konfiguracja per agent: {role: AgentConfig} z timeout_seconds

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
            # Enforce General-only execution
            agents_list = [agent for agent in agents_list if agent.role == "general"]
            if not agents_list:
                raise ValueError(f"Review {review_id} has no general agent configured")

            # Send review started event
            agent_roles = [agent.role for agent in agents_list]
            await ws_manager.send_review_started(review_id, agent_roles)

            # Normalize configs
            typed_agent_configs: dict[str, AgentConfig] = {}
            if agent_configs:
                for role, config in agent_configs.items():
                    typed_agent_configs[role] = config if isinstance(config, AgentConfig) else AgentConfig(**config)

            general_agent = agents_list[0]
            logger.info("🤖 Uruchamiam GENERAL agenta (pojedyncza analiza)...")

            agent_config = typed_agent_configs.get(general_agent.role)
            agent_provider = general_agent.provider if general_agent.provider != "mock" else (provider_name or general_agent.provider)
            agent_model = general_agent.model if general_agent.model != "default" else (model or general_agent.model)
            timeout_seconds = agent_config.timeout_seconds if agent_config else 300
            max_tokens = agent_config.max_tokens if agent_config else 4096

            agent_api_key = None
            if api_keys and agent_provider:
                agent_api_key = api_keys.get(agent_provider.lower())

            custom_provider_config = None
            if agent_config and agent_config.custom_provider:
                cp = agent_config.custom_provider
                custom_provider_config = CustomProviderConfig(
                    id=cp.id, name=cp.name, base_url=cp.base_url,
                    api_key=cp.api_key, header_name=cp.header_name,
                    header_prefix=cp.header_prefix
                )
            elif agent_provider and agent_provider.lower() == "perplexity":
                # Fallback: build custom provider config for Perplexity when not provided by frontend
                custom_provider_config = CustomProviderConfig(
                    id="perplexity",
                    name="Perplexity",
                    base_url="https://api.perplexity.ai",
                    api_key=agent_api_key,
                    header_name="Authorization",
                    header_prefix="Bearer ",
                )

            response = await self._run_agent(
                review, project, general_agent, agent_provider, agent_model,
                agent_api_key, custom_provider_config, timeout_seconds, max_tokens
            )

            if response is None:
                logger.warning("❌ General agent zwrócił None - brak odpowiedzi")
            elif response and response.strip().startswith(("[BŁĄD]", "[ERROR]", "[TIMEOUT]", "[EMPTY]")):
                logger.warning(f"❌ General agent zwrócił błąd: {response[:100]}")
            else:
                logger.info("✅ General agent zakończony pomyślnie")

            # All agents completed - set summary to None (no moderator report)
            review.summary = None

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

    async def _run_agent(
        self,
        review: Review,
        project: Project,
        agent: ReviewAgent,
        provider_name: str | None,
        model: str | None,
        api_key: str | None = None,
        custom_provider_config: CustomProviderConfig | None = None,
        timeout_seconds: int = 300,
        max_tokens: int = 4096
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
            timeout_seconds: Maximum time for agent response (default 300s = 5 min)
        """
        # Send agent started event
        await ws_manager.send_agent_started(review.id, agent.role)

        # Store configured timeout
        agent.timeout_seconds = timeout_seconds

        # Build prompt
        system_prompt = self.AGENT_PROMPTS.get(agent.role, self.AGENT_PROMPTS["general"])
        user_prompt = self._build_user_prompt(project)
        
        # Log prompt preview for debugging
        logger.info(f"📝 Agent {agent.role} - Prompt preview (first 500 chars): {user_prompt[:500]}...")
        
        # Check if user_prompt has actual content (not just headers)
        if not user_prompt or len(user_prompt) < 100:
            logger.warning(f"⚠️ Agent {agent.role} - User prompt is very short or empty! Prompt length: {len(user_prompt) if user_prompt else 0}")
        
        # Check if project has files
        from sqlmodel import select
        files_check = self.session.exec(select(File).where(File.project_id == project.id)).all()
        if not files_check:
            logger.error(f"❌ Agent {agent.role} - Project {project.id} has no files! Cannot analyze empty project.")
            raise ValueError(f"Project {project.id} has no files to analyze")

        messages = [
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(role="user", content=user_prompt)
        ]

        async def _generate_with_cache():
            """Helper to run generation with caching logic."""
            cache_key = None
            effective_provider = custom_provider_config.id if custom_provider_config else (provider_name or settings.default_provider)
            if settings.enable_agent_caching:
                # Include review_id and project content hash in cache key to avoid stale cache
                # This ensures that recreating a review doesn't use old cached responses
                from app.models.file import File
                from sqlmodel import select
                project_files = self.session.exec(select(File).where(File.project_id == project.id)).all()
                # Create a hash of file contents to ensure cache is invalidated when files change
                import hashlib
                file_contents_hash = hashlib.md5(
                    "|".join(sorted([f"{f.name}:{f.content_hash}" for f in project_files])).encode()
                ).hexdigest()[:8]
                
                # Include review_id and content hash in cache key so recreate doesn't use old cache
                cache_key = cache.generate_llm_cache_key(
                    provider=effective_provider,
                    model=model or settings.default_model,
                    prompt=system_prompt + user_prompt + f"|review_id:{review.id}|content_hash:{file_contents_hash}",
                    temperature=0.0
                )
                cached_response = cache.get(cache_key)
                if cached_response:
                    logger.info(f"💾 Agent {agent.role} - Using cached response (cache_key includes review_id and content hash)")
                    return cached_response, effective_provider, model or settings.default_model
                else:
                    logger.info(f"🔄 Agent {agent.role} - No cache hit, generating new response")
                    # Generate response
                    raw_out, resp_provider, resp_model = await provider_router.generate(
                        messages=messages,
                        provider_name=provider_name,
                        model=model,
                        temperature=0.0,
                        max_tokens=max_tokens,
                        api_key=api_key,
                        custom_provider_config=custom_provider_config
                    )
                    # Cache the response
                    cache.set(cache_key, raw_out)
                    logger.info(f"💾 Agent {agent.role} - Cached new response")
                    return raw_out, resp_provider, resp_model
            else:
                # Generate response without caching
                logger.info(f"🔄 Agent {agent.role} - Cache disabled, generating new response")
                return await provider_router.generate(
                    messages=messages,
                    provider_name=provider_name,
                    model=model,
                    temperature=0.0,
                    max_tokens=max_tokens,  # Use max_tokens parameter instead of hardcoded 4096
                    api_key=api_key,
                    custom_provider_config=custom_provider_config
                )

        try:
            # Run with timeout + RETRY LOGIC with exponential backoff
            logger.info(f"🔄 Agent {agent.role} ({provider_name}/{model}) - Starting generation with timeout {timeout_seconds}s...")

            max_retries = 3
            retry_delay = 2  # Initial delay in seconds
            raw_output, response_provider, response_model = None, None, None

            for attempt in range(1, max_retries + 1):
                try:
                    logger.info(f"🔄 Attempt {attempt}/{max_retries} for agent {agent.role}...")
                    raw_output, response_provider, response_model = await asyncio.wait_for(
                        _generate_with_cache(),
                        timeout=timeout_seconds
                    )
                    logger.info(f"✅ Agent {agent.role} received response: provider={response_provider}, model={response_model}, length={len(raw_output) if raw_output else 0} chars")
                    break  # Success - exit retry loop

                except asyncio.TimeoutError:
                    if attempt < max_retries:
                        # Exponential backoff: 2s, 4s, 8s
                        delay = retry_delay * (2 ** (attempt - 1))
                        logger.warning(f"⏱️ Agent {agent.role} timed out on attempt {attempt}/{max_retries}. Retrying in {delay}s...")
                        await asyncio.sleep(delay)
                    else:
                        # Final attempt failed - re-raise timeout
                        logger.error(f"❌ Agent {agent.role} timed out after {max_retries} attempts (total {timeout_seconds * max_retries}s)")
                        raise

            # If we got here without raw_output, something went wrong
            if raw_output is None:
                raise ValueError(f"Agent {agent.role} failed to generate response after {max_retries} attempts")

            # Check if response is empty
            if not raw_output or not raw_output.strip():
                logger.warning(f"Agent {agent.role} returned empty response")
                agent.raw_output = "[EMPTY] Agent zwrócił pustą odpowiedź"
                agent.parsed_successfully = False
                agent.timed_out = False
                agent.provider = response_provider or provider_name or "unknown"
                agent.model = response_model or model or "unknown"
                
                self.session.add(agent)
                self.session.commit()
                self.session.refresh(agent)
                
                await ws_manager.send_agent_completed(
                    review.id,
                    agent.role,
                    0,
                    False
                )
                return None

            # Parse response
            parsed_successfully, issues_data = self._parse_response(raw_output)
            logger.info(f"📊 Agent {agent.role} - Parsing result: parsed_successfully={parsed_successfully}, issues_count={len(issues_data)}")

            # Filter out placeholder and invalid issues before storing
            filtered_issues_data = []
            for issue_data in issues_data:
                if isinstance(issue_data, dict):
                    title = issue_data.get("title", "")
                    description = issue_data.get("description", "")
                    # Check if issue contains placeholders
                    if not self._contains_placeholders(title) and not self._contains_placeholders(description):
                        # Additional semantic validation - check for nonsense
                        if self._is_valid_issue(issue_data, agent.role):
                            filtered_issues_data.append(issue_data)
                        else:
                            logger.warning(f"⚠️ Agent {agent.role} - Rejected invalid issue (semantic validation): title='{title[:100]}', desc='{description[:100]}'")
                    else:
                        logger.warning(f"⚠️ Agent {agent.role} - Rejected placeholder issue: title='{title[:100]}'")
                else:
                    logger.warning(f"⚠️ Agent {agent.role} - Rejected non-dict issue: {type(issue_data)}")

            logger.info(f"📊 Agent {agent.role} - After filtering: {len(filtered_issues_data)} issues to store (from {len(issues_data)} parsed)")

            # Store issues directly from agent response (with agent_role information)
            # IMPORTANT: Even if parsing failed or issues_data is empty, we should still try to store
            # valid issues that passed filtering (they might have been extracted from malformed JSON)
            if filtered_issues_data and len(filtered_issues_data) > 0:
                logger.info(f"💾 Zapisuję {len(filtered_issues_data)} problemów znalezionych przez agenta {agent.role} (filtrowanie: {len(issues_data)} -> {len(filtered_issues_data)}, parsed_successfully={parsed_successfully})")
                stored_count = 0
                for idx, issue_data in enumerate(filtered_issues_data):
                    try:
                        # Add agent_role to issue data
                        issue_data['agent_role'] = agent.role
                        logger.debug(f"📝 Storing issue #{idx+1}/{len(filtered_issues_data)}: title='{issue_data.get('title', '')[:80]}', severity={issue_data.get('severity')}, category={issue_data.get('category')}")
                        await self._store_issue(review, issue_data)
                        stored_count += 1
                    except Exception as e:
                        logger.error(f"❌ Błąd zapisywania problemu #{idx+1} od agenta {agent.role}: {e}", exc_info=True)
                        logger.error(f"❌ Issue data that failed: {issue_data}")
                logger.info(f"✅ Successfully stored {stored_count}/{len(filtered_issues_data)} problemów od agenta {agent.role}")
            else:
                logger.warning(f"⚠️ Agent {agent.role} zwrócił odpowiedź, ale nie ma żadnych problemów do zapisania (parsed_successfully={parsed_successfully}, parsed={len(issues_data)}, filtered={len(filtered_issues_data)})")
                if raw_output and len(raw_output) > 100:
                    logger.warning(f"📄 Raw output preview (first 500 chars): {raw_output[:500]}")

            # Clean special model tokens from raw_output before saving
            import re
            cleaned_raw_output = raw_output
            cleaned_raw_output = re.sub(r'<｜[^｜]+｜>', '', cleaned_raw_output)
            cleaned_raw_output = re.sub(r'<\|[^\|]+\|>', '', cleaned_raw_output)
            cleaned_raw_output = re.sub(r'<[｜\|][^>]*', '', cleaned_raw_output)

            # Update the existing agent record - SUCCESS
            agent.provider = response_provider or provider_name or "unknown"
            agent.model = response_model or model or "unknown"
            agent.raw_output = cleaned_raw_output[:50000]  # Truncate if too long (after cleaning)
            agent.parsed_successfully = parsed_successfully
            agent.timed_out = False

            self.session.add(agent)
            self.session.commit()
            self.session.refresh(agent)

            # Send agent completed event
            await ws_manager.send_agent_completed(
                review.id,
                agent.role,
                len(filtered_issues_data),
                parsed_successfully
            )

            return raw_output

        except asyncio.TimeoutError:
            # Agent timed out
            logger.warning(f"Agent {agent.role} timed out after {timeout_seconds}s")

            agent.timed_out = True
            agent.parsed_successfully = False
            agent.raw_output = f"[TIMEOUT] Agent przekroczył limit czasu ({timeout_seconds} sekund)"
            agent.provider = provider_name or "unknown"
            agent.model = model or "unknown"

            self.session.add(agent)
            self.session.commit()
            self.session.refresh(agent)

            # Send agent completed event with timeout flag
            await ws_manager.send_agent_completed(
                review.id,
                agent.role,
                0,
                False
            )

            return None  # No response

        except Exception as e:
            # Handle any other errors (API errors, network errors, etc.)
            error_msg = str(e)[:500]  # Truncate error message
            error_type = type(e).__name__
            
            # Special handling for common errors
            is_rate_limit = "429" in error_msg or "Too Many Requests" in error_msg or "rate limit" in error_msg.lower()
            is_ollama_error = "Ollama" in error_type or "ollama" in error_msg.lower()
            is_value_error = error_type == "ValueError"
            
            if is_rate_limit:
                error_output = f"[BŁĄD] Rate limiting: Przekroczono limit zapytań do API. Spróbuj ponownie za kilka minut."
                logger.warning(f"Agent {agent.role} hit rate limit (429) for provider {provider_name}. Error: {error_msg}")
            elif is_ollama_error or (is_value_error and "ollama" in error_msg.lower()):
                # Ollama-specific error messages
                if "not available" in error_msg.lower() or "is not available" in error_msg.lower():
                    error_output = f"[BŁĄD] Ollama nie jest dostępny: {error_msg}. Sprawdź czy Ollama jest uruchomiony (np. 'ollama serve')."
                elif "model" in error_msg.lower() and "not found" in error_msg.lower():
                    error_output = f"[BŁĄD] Model Ollama nie został znaleziony: {error_msg}. Sprawdź dostępne modele (np. 'ollama list')."
                elif "timeout" in error_msg.lower():
                    error_output = f"[BŁĄD] Ollama timeout: Przekroczono limit czasu ({timeout_seconds}s). Model może potrzebować więcej czasu lub Ollama nie odpowiada."
                else:
                    error_output = f"[BŁĄD] Ollama błąd: {error_msg}"
                logger.error(f"🦙 Agent {agent.role} - Ollama error: {error_type}: {error_msg}", exc_info=True)
            else:
                error_output = f"[BŁĄD] {error_type}: {error_msg}"
            
            logger.error(f"Agent {agent.role} ({provider_name}/{model}) failed with error: {error_type}: {error_msg}", exc_info=True)

            agent.timed_out = False
            agent.parsed_successfully = False
            agent.raw_output = error_output
            agent.provider = provider_name or "unknown"
            agent.model = model or "unknown"

            logger.info(f"Saving error for agent {agent.role}: raw_output='{error_output[:100]}'")
            self.session.add(agent)
            self.session.commit()
            self.session.refresh(agent)
            logger.info(f"Agent {agent.role} saved with raw_output length: {len(agent.raw_output) if agent.raw_output else 0}")

            # Send agent completed event with error flag
            await ws_manager.send_agent_completed(
                review.id,
                agent.role,
                0,
                False
            )

            # Return error message instead of None
            return error_output

    async def _store_moderator_issues(self, review: Review, raw_summary: str):
        """Store moderator issues parsed from a JSON summary."""
        import json
        try:
            data = json.loads(raw_summary)
        except json.JSONDecodeError:
            logger.warning("Moderator summary is not valid JSON - skipping issue storage")
            return

        issues = data.get("issues", [])
        if not isinstance(issues, list):
            logger.warning("Moderator summary issues field is not a list - skipping")
            return

        from datetime import datetime, timezone
        for issue_data in issues:
            if not isinstance(issue_data, dict):
                continue
            issue = Issue(
                review_id=review.id,
                severity=issue_data.get("severity") or "info",
                category=issue_data.get("category") or "general",
                title=issue_data.get("title") or "Moderator issue",
                description=issue_data.get("description") or "Brak opisu problemu.",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            self.session.add(issue)

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
        
        # Log file count for debugging
        logger.info(f"📁 Building prompt for project {project.id} ({project.name}): {len(files)} files found")
        if len(files) == 0:
            logger.error(f"❌ Project {project.id} has NO FILES! Cannot build review prompt.")
            raise ValueError(f"Project {project.id} has no files to review")
        
        for file in files:
            logger.debug(f"  - File: {file.name} ({len(file.content) if file.content else 0} chars)")

        # Build prompt
        prompt = f"""Proszę przejrzyj następujący projekt: {project.name}

Opis: {project.description or "Brak opisu"}

Pliki ({len(files)}):

"""

        files_with_content = 0
        for file in files:
            # Check if file has content
            content = file.content or ""
            if not content or not content.strip():
                logger.warning(f"⚠️ File {file.name} in project {project.id} is empty or has no content - skipping")
                continue
            
            files_with_content += 1
            
            # Truncate very long files
            if len(content) > 5000:
                content = content[:5000] + "\n... (obcięte)"
                logger.debug(f"  File {file.name}: truncated from {len(file.content)} to 5000 chars")

            prompt += f"""
---
Plik: {file.name}
Język: {file.language or "nieznany"}

```
{content}
```

"""
        
        if files_with_content == 0:
            logger.error(f"❌ Project {project.id} has no files with content! Cannot build review prompt.")
            raise ValueError(f"Project {project.id} has no files with content to review")
        
        logger.info(f"✅ Built prompt with {files_with_content} files with content (out of {len(files)} total files)")

        prompt += """
Przeanalizuj ten kod i zwróć swoje uwagi TYLKO w formacie JSON (bez dodatkowego tekstu, bez markdown code blocks).

Format odpowiedzi JSON:
{
  "issues": [
    {
      "severity": "info|warning|error",
      "category": "kategoria problemu (np. syntax, bug, security, performance, style)",
      "title": "krótki konkretny tytuł rzeczywistego problemu z kodu",
      "description": "szczegółowy opis rzeczywistego problemu znalezionego w kodzie",
      "file_name": "nazwa_pliku.ext lub null",
      "line_start": numer_linii lub null,
      "line_end": numer_linii lub null,
      "code_snippet": "fragment kodu z problemem lub null",
      "suggested_fix": "konkretna sugestia naprawy lub null"
    }
  ],
  "summary": "krótkie podsumowanie analizy kodu po polsku"
}

KRYTYCZNE ZASADY:
- Przeanalizuj RZECZYWISTY kod powyżej i znajdź PRAWDZIWE problemy
- NIE używaj przykładowych wartości - wszystkie pola muszą zawierać RZECZYWISTE dane z analizy
- NIE kopiuj tekstów z tego prompta - pisz własne opisy na podstawie analizy kodu
- Jeśli nie ma problemów, zwróć: {"issues": [], "summary": "Nie znaleziono problemów"}
- Wszystkie teksty muszą być po polsku
- Zwróć TYLKO JSON, bez markdown, bez dodatkowego tekstu, bez ```json ani ```"""

        return prompt

    def _contains_placeholders(self, text: str) -> bool:
        """Check if text contains placeholder patterns that should be rejected.
        
        Args:
            text: Text to check
            
        Returns:
            True if placeholders detected
        """
        if not text or len(text.strip()) < 10:
            return False  # Too short to be a real placeholder issue
        
        text_lower = text.lower()
        
        # Strong indicators - these are almost certainly placeholders
        strong_patterns = [
            "po polsku",  # Must be exact phrase (from old prompt examples)
            "wypełnij",
            "krótki tytuł",
            "szczegółowy opis",
            "opcjonalne podsumowanie",
            "ogólne podsumowanie przeglądu kodu",
            "sugestia naprawy po polsku",
            "opcjonalna sugestia poprawki po polsku",
            "| \"warning\" | \"error\"",  # Example syntax from prompts
            "\"info\" | \"warning\"",  # Example syntax
            "rzeczywisty tytuł problemu",  # Full phrase from prompt
            "rzeczywiste podsumowanie przeglądu kodu",  # Full phrase from prompt
            "szczegółowy opis znalezionego problemu po polsku",  # Full phrase from prompt
            # Exact strings from old prompt template
            "tytuł problemu po polsku",
            "opis problemu po polsku",
            "sugestia poprawki po polsku",
            "podsumowanie analizy po polsku",
            "nazwa_pliku.ext",  # Exact placeholder from template
            "fragment kodu",  # Generic placeholder
            "numer_linii",  # Placeholder value
        ]
        
        for pattern in strong_patterns:
            if pattern in text_lower:
                return True
        
        # Weak indicators - check context (must appear in suspicious context)
        weak_patterns = [
            ("rzeczywisty", ["tytuł", "problem", "podsumowanie", "opis"]),
            ("rzeczywiste", ["podsumowanie", "dane"]),
        ]
        
        for word, context_words in weak_patterns:
            if word in text_lower:
                # Check if it appears with context words that suggest it's from a prompt
                for ctx in context_words:
                    if ctx in text_lower:
                        # Check proximity - if they're close together, it's likely a placeholder
                        word_pos = text_lower.find(word)
                        ctx_pos = text_lower.find(ctx)
                        if word_pos != -1 and ctx_pos != -1:
                            distance = abs(word_pos - ctx_pos)
                            if distance < 50:  # Words are close together
                                return True
        
        return False

    def _is_valid_issue(self, issue_data: dict, agent_role: str) -> bool:
        """Validate if an issue makes semantic sense.
        
        Args:
            issue_data: Issue data dictionary
            agent_role: Agent role (general, security, performance, style)
            
        Returns:
            True if issue is valid, False if it's nonsense
        """
        title = (issue_data.get("title") or "").lower()
        description = (issue_data.get("description") or "").lower()
        category = (issue_data.get("category") or "").lower()
        
        # Check for obvious nonsense patterns
        nonsense_patterns = [
            # Contradictory statements
            ("brak kodu", ["sql injection", "bezpieczeństwa", "błęd"]),  # "Brak kodu SQL injection" as a problem
            ("nie ma", ["problem", "błęd", "kod"]),  # "Nie ma problemu" as a problem
            # SQL injection mentioned without SQL code
            ("sql injection", ["return a + b", "def add"]),  # SQL injection in add() function
            # Generic meaningless statements
            ("tytuł problemu", []),
            ("opis problemu", []),
            ("podsumowanie analizy", []),
        ]
        
        for pattern, context in nonsense_patterns:
            if pattern in title or pattern in description:
                # Check if context makes it invalid
                if not context:
                    return False  # Pattern alone is invalid
                # Check if context words are present (making it more likely to be nonsense)
                for ctx_word in context:
                    if ctx_word in title or ctx_word in description:
                        return False
        
        # Role-specific validation
        if agent_role == "security":
            # Security agent shouldn't report "Brak kodu SQL injection" or similar negatives
            if any(phrase in title or phrase in description for phrase in ["brak kodu", "nie ma"]):
                if "bezpieczeństwa" in category or "security" in category:
                    return False
        
        if agent_role == "general":
            # General agent shouldn't report SQL injection unless there's actual SQL
            if "sql injection" in title or "sql injection" in description:
                # Check if there's actual SQL-like code mentioned
                if not any(sql_word in description for sql_word in ["select", "insert", "update", "delete", "query", "sql"]):
                    return False
        
        # Issue must have meaningful content (but be lenient - allow shorter if they're real issues)
        title_len = len(title.strip()) if title else 0
        desc_len = len(description.strip()) if description else 0
        
        # Minimum lengths - but be more lenient (especially for syntax errors which might be short)
        if title_len < 3:
            return False  # Title must be at least 3 chars
        if desc_len < 5:
            return False  # Description must be at least 5 chars
        
        return True

    def _clean_perplexity_response(self, raw_output: str) -> str:
        """Clean Perplexity response by removing <think> sections and extracting JSON.
        
        Args:
            raw_output: Raw LLM response
            
        Returns:
            Cleaned response with JSON extracted
        """
        import re
        
        # Remove <think>...</think> sections (multiline)
        cleaned = re.sub(r'<think>.*?</think>', '', raw_output, flags=re.DOTALL)
        
        # Remove standalone <think> tags
        cleaned = re.sub(r'<think>.*?$', '', cleaned, flags=re.DOTALL | re.MULTILINE)
        cleaned = re.sub(r'^.*?</think>', '', cleaned, flags=re.DOTALL | re.MULTILINE)
        
        # Try to extract JSON if it's wrapped in markdown code blocks
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', cleaned, re.DOTALL)
        if json_match:
            cleaned = json_match.group(1)
        
        # If JSON is at the start, extract it
        json_start = cleaned.find('{')
        json_end = cleaned.rfind('}')
        if json_start >= 0 and json_end > json_start:
            cleaned = cleaned[json_start:json_end + 1]
        
        return cleaned.strip()
    
    def _parse_response(self, raw_output: str) -> tuple[bool, list[dict]]:
        """Parse LLM response into issues.

        Args:
            raw_output: Raw LLM output

        Returns:
            Tuple of (success, issues_list)
        """
        # Check for placeholder patterns first
        if self._contains_placeholders(raw_output):
            logger.warning("Response contains placeholder patterns - rejecting")
            return False, []
        
        # Clean Perplexity responses first (remove <think> sections)
        cleaned_output = self._clean_perplexity_response(raw_output)
        if cleaned_output.startswith("```json"):
            cleaned_output = cleaned_output.replace("```json", "", 1).strip()
        if cleaned_output.startswith("```"):
            cleaned_output = cleaned_output.replace("```", "", 1).strip()
        if cleaned_output.endswith("```"):
            cleaned_output = cleaned_output[:-3].strip()

        # Remove special model tokens (e.g., DeepSeek's <｜begin▁of▁sentence｜>)
        # These can appear anywhere in the response, including inside JSON values
        import re
        cleaned_output = re.sub(r'<｜[^｜]+｜>', '', cleaned_output)
        cleaned_output = re.sub(r'<\|[^\|]+\|>', '', cleaned_output)
        # Also remove tokens that may have been corrupted or partial
        cleaned_output = re.sub(r'<[｜\|][^>]*', '', cleaned_output)
        
        try:
            # Aggressively clean JSON - remove empty array elements and fix malformed structures
            import re
            
            # Log raw output for debugging (especially important for Perplexity issues)
            logger.info(f"🔍 Raw output before cleaning (first 1000 chars): {raw_output[:1000]}")
            logger.debug(f"Raw output before cleaning (first 500 chars): {raw_output[:500]}")
            
            # Remove markdown code block fences if still present
            if cleaned_output.startswith("```json"):
                cleaned_output = cleaned_output.replace("```json", "", 1).strip()
            if cleaned_output.startswith("```"):
                cleaned_output = cleaned_output.replace("```", "", 1).strip()
            if cleaned_output.endswith("```"):
                cleaned_output = cleaned_output[:-3].strip()
            
            # Fix common JSON malformations from LLMs (especially Perplexity):
            # 0. Fix Perplexity-specific issue: "issues": [ , , , ] -> "issues": []
            # This handles cases where Perplexity returns empty comma-separated values
            cleaned_output = re.sub(r'"issues"\s*:\s*\[\s*,+\s*\]', '"issues": []', cleaned_output, flags=re.IGNORECASE)
            cleaned_output = re.sub(r'"issues"\s*:\s*\[\s*(?:,\s*)+\]', '"issues": []', cleaned_output, flags=re.IGNORECASE)
            # Remove all sequences of just commas and whitespace in arrays: [ , , , ] -> []
            cleaned_output = re.sub(r'\[\s*(?:,\s*)+\]', '[]', cleaned_output)
            # 1. Remove trailing commas before closing brackets/braces
            cleaned_output = re.sub(r',\s*([}\]])', r'\1', cleaned_output)
            # 2. Remove empty array elements (multiple commas in a row)
            cleaned_output = re.sub(r',\s*,+', ',', cleaned_output)
            # 3. Remove leading comma in arrays
            cleaned_output = re.sub(r'\[\s*,+', '[', cleaned_output)
            # 4. Remove trailing comma in arrays
            cleaned_output = re.sub(r',+\s*\]', ']', cleaned_output)
            # 5. Remove empty object elements like ",{}" or ", { }"
            cleaned_output = re.sub(r',\s*\{\s*\}', '', cleaned_output)
            # 6. Remove empty array elements like ",[]" or ", [ ]"
            cleaned_output = re.sub(r',\s*\[\s*\]', '', cleaned_output)
            # 7. Fix cases where issues array has only commas and whitespace (backup)
            cleaned_output = re.sub(r'"issues"\s*:\s*\[\s*,+\s*\]', '"issues": []', cleaned_output, flags=re.IGNORECASE)
            # 8. Remove any remaining sequences of just commas and whitespace within arrays
            cleaned_output = re.sub(r'(\[)\s*,+\s*(\])', r'\1\2', cleaned_output)  # Empty array with only commas
            cleaned_output = re.sub(r'(\[)\s*,+(\s+\{)', r'\1\2', cleaned_output)  # Remove leading commas
            # 9. Fix malformed objects in array - remove objects that are just ", " or empty strings
            cleaned_output = re.sub(r',\s*\{\s*"title"\s*:\s*",\s*"\s*\}', '', cleaned_output, flags=re.IGNORECASE)
            cleaned_output = re.sub(r',\s*\{\s*"description"\s*:\s*",\s*"\s*\}', '', cleaned_output, flags=re.IGNORECASE)
            # 10. Fix cases where array has only commas/whitespace after "issues":
            cleaned_output = re.sub(r'"issues"\s*:\s*\[\s*(?:,\s*)+"summary"', '"issues": [], "summary"', cleaned_output, flags=re.IGNORECASE)
            # 11. Fix Perplexity-specific: "issues": [ , , , ] -> "issues": [] (before any other field)
            # Match: "issues": [ any whitespace/commas ] followed by comma and another field
            cleaned_output = re.sub(r'"issues"\s*:\s*\[\s*(?:,\s*)+\]\s*,', '"issues": [],', cleaned_output, flags=re.IGNORECASE)
            # 12. Fix any remaining patterns like: , , , ] -> ]
            cleaned_output = re.sub(r',\s*(?:,\s*)+(\])', r'\1', cleaned_output)
            # 13. Fix patterns where we have comma-space-comma before closing bracket: , , ] -> ]
            cleaned_output = re.sub(r',\s*,\s*(\])', r'\1', cleaned_output)
            
            # Try to extract valid JSON structure if the whole thing is malformed
            # Look for the JSON object boundaries
            json_start = cleaned_output.find('{')
            json_end = cleaned_output.rfind('}')
            if json_start >= 0 and json_end > json_start:
                cleaned_output = cleaned_output[json_start:json_end+1]
            
            # Try to parse as JSON
            data = json.loads(cleaned_output)
            
            # Log parsed data for debugging
            issues_count = len(data.get('issues', []))
            summary_exists = bool(data.get('summary'))
            logger.info(f"✅ Successfully parsed JSON. Issues count: {issues_count}, Has summary: {summary_exists}")
            
            # Log first few issues for debugging
            if issues_count > 0:
                for idx, issue in enumerate(data.get('issues', [])[:3]):
                    if isinstance(issue, dict):
                        logger.info(f"📋 Issue #{idx+1}: title='{issue.get('title', '')[:80]}', severity={issue.get('severity')}, category={issue.get('category')}")
            else:
                logger.warning(f"⚠️ Parsed JSON has 0 issues! Summary: {data.get('summary', '')[:200]}")
            
            # Filter out empty/invalid issues before validation
            if isinstance(data, dict):
                issues = data.get("issues", [])
                
                # If issues array exists but is empty or has only empty values, but summary mentions problems
                # This handles Perplexity cases where JSON Schema may return malformed issues array
                summary = data.get("summary", "")
                if (not issues or len([i for i in issues if isinstance(i, dict) and (i.get("title") or i.get("description"))]) == 0) and summary:
                    # Check if summary mentions finding issues
                    import re
                    issue_mentions = re.findall(r'\d+\s+(?:problem|błąd|issue)', summary.lower())
                    if issue_mentions:
                        logger.warning(f"⚠️ Issues array is empty but summary mentions {issue_mentions[0]}. This may indicate Perplexity JSON Schema parsing issue.")
                        # Try to extract what we can - at least log the summary
                        logger.info(f"📝 Summary content: {summary[:300]}")
                
                # Remove empty dictionaries and dictionaries with only empty/null values
                valid_issues = []
                issues_filtered_count = 0
                
                for issue in issues:
                    if not isinstance(issue, dict):
                        issues_filtered_count += 1
                        continue
                    
                    # Check if issue has any meaningful content
                    title = str(issue.get("title", "")).strip()
                    description = str(issue.get("description", "")).strip()
                    
                    # Remove common placeholder/empty patterns
                    title = title.replace(",", "").strip()
                    description = description.replace(",", "").strip()
                    
                    # Check if issue has meaningful content
                    has_content = False
                    
                    # Title must be non-empty and longer than 2 chars (not just ",", " ", etc.)
                    # Be lenient for syntax errors which might have short titles
                    if title and len(title.strip()) > 2 and not re.match(r'^[\s,]+$', title):
                        has_content = True
                    
                    # Description must be non-empty and longer than 5 chars
                    # Be lenient for syntax errors which might have short descriptions
                    if description and len(description.strip()) > 3 and not re.match(r'^[\s,]+$', description):
                        has_content = True
                    
                    # Log issues that don't have content for debugging
                    if not has_content:
                        logger.debug(f"⚠️ Skipping issue without content: title='{title[:50]}' (len={len(title.strip())}), desc='{description[:50]}' (len={len(description.strip())})")
                    
                    if has_content:
                        # Validate placeholders only if content exists
                        if not self._contains_placeholders(title) and not self._contains_placeholders(description):
                            if self._is_valid_issue(issue, "unknown"):  # We'll validate with actual role later
                                valid_issues.append(issue)
                            else:
                                logger.debug(f"Rejected invalid issue (semantic validation): {title[:50]}")
                                issues_filtered_count += 1
                        else:
                            logger.debug(f"Rejected placeholder issue: {title[:50]}")
                            issues_filtered_count += 1
                    else:
                        logger.debug(f"Skipping empty issue: title='{title[:30]}', desc='{description[:30]}'")
                        issues_filtered_count += 1
                
                # Log filtering results
                if issues_filtered_count > 0:
                    logger.info(f"Filtered out {issues_filtered_count} empty/invalid issues, kept {len(valid_issues)} valid ones")
                
                # Update data with filtered issues
                data["issues"] = valid_issues
                
                # Check summary for placeholders
                summary = data.get("summary", "")
                
                # If we have no valid issues but summary exists and mentions problems, log warning
                # This handles Perplexity cases where JSON Schema returns malformed issues array
                if len(valid_issues) == 0 and summary and not self._contains_placeholders(summary):
                    import re
                    issue_mentions = re.findall(r'\d+\s+(?:problem|błąd|issue|błęd)', summary.lower())
                    if issue_mentions:
                        logger.error(f"⚠️ WARNING: Summary mentions {issue_mentions[0]} but issues array is empty/malformed. This is likely a Perplexity JSON Schema parsing issue.")
                        logger.error(f"📝 Summary content: {summary[:500]}")
                        # Don't reject - at least summary will be displayed, even if issues are empty
                
                if summary and self._contains_placeholders(summary):
                    logger.warning("Summary contains placeholder patterns - rejecting")
                    return False, []
            
            # Validate with schema (only valid issues)
            schema = ReviewResponseSchema(**data)
            issues_data = [issue.model_dump() for issue in schema.issues]
            return True, issues_data

        except json.JSONDecodeError as e:
            logger.warning(f"JSON decode error in LLM response: {str(e)[:200]}")
            logger.error(f"❌ Raw output (full, first 1500 chars): {raw_output[:1500]}")
            logger.error(f"❌ Cleaned output (first 1000 chars): {cleaned_output[:1000]}")
            logger.debug(f"Raw output preview: {raw_output[:500]}...")
            logger.debug(f"Cleaned output preview: {cleaned_output[:500]}...")

            # Fallback 1: Try to extract and fix JSON more aggressively
            try:
                import re
                # Look for JSON block with more lenient regex
                json_match = re.search(r'\{[\s\S]{10,}\}', cleaned_output)  # At least 10 chars inside
                if json_match:
                    json_str = json_match.group(0)
                    # Try even more aggressive cleaning
                    json_str = re.sub(r',\s*,+', '', json_str)  # Remove multiple commas
                    json_str = re.sub(r'\[\s*,+\s*\]', '[]', json_str)  # Fix empty arrays with commas
                    json_str = re.sub(r',+\s*\]', ']', json_str)  # Remove trailing commas in arrays
                    json_str = re.sub(r',+\s*\}', '}', json_str)  # Remove trailing commas in objects
                    
                    data = json.loads(json_str)
                    # Filter issues as before
                    if isinstance(data, dict):
                        issues = data.get("issues", [])
                        valid_issues = [issue for issue in issues if isinstance(issue, dict) and 
                                      (issue.get("title") or issue.get("description"))]
                        data["issues"] = valid_issues
                    
                    schema = ReviewResponseSchema(**data)
                    issues_data = [issue.model_dump() for issue in schema.issues]
                    logger.info(f"Successfully recovered JSON from text (extracted {len(issues_data)} issues)")
                    return True, issues_data
            except Exception as fallback_error:
                logger.warning(f"Fallback JSON extraction failed: {str(fallback_error)[:200]}")
                
                # Fallback 2: If summary mentions issues count, create placeholder issues
                # This is a last resort - better to show something than nothing
                try:
                    summary_match = re.search(r'"summary"\s*:\s*"([^"]+)"', raw_output, re.IGNORECASE)
                    if summary_match:
                        summary_text = summary_match.group(1)
                        # Check if summary mentions finding issues
                        issue_count_match = re.search(r'(\d+)\s+problem', summary_text, re.IGNORECASE)
                        if issue_count_match:
                            count = int(issue_count_match.group(1))
                            if count > 0:
                                logger.warning(f"JSON parsing completely failed, but summary mentions {count} issues. This indicates the model found issues but failed to format them correctly.")
                                # Return empty list but log the issue - we can't reliably extract details
                                return False, []
                except Exception:
                    pass

        except ValidationError as e:
            logger.error(f"Pydantic validation error in LLM response: {e.errors()}")
            logger.debug(f"Raw output preview: {raw_output[:500]}...")

        # Parsing failed
        logger.error("Failed to parse LLM response after all attempts")
        return False, []

    async def _store_issue(self, review: Review, issue_data: dict, agent_role: str | None = None):
        """Store an issue in the database.

        Args:
            review: Review object
            issue_data: Issue data dictionary
            agent_role: Agent role that found this issue (optional, can be in issue_data)
        """
        try:
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

            # Get agent_role from issue_data or parameter
            agent_role_value = issue_data.get("agent_role") or agent_role

            # Validate required fields
            if not issue_data.get("severity"):
                issue_data["severity"] = "info"
            if not issue_data.get("category"):
                issue_data["category"] = "general"
            if not issue_data.get("title"):
                # Generate title from description if missing
                desc = issue_data.get("description", "")
                issue_data["title"] = desc.split(".")[0][:120] if desc else "Zgłoszony problem"
            if not issue_data.get("description"):
                issue_data["description"] = issue_data.get("title", "Brak opisu")

            # Check for duplicates before creating issue
            # An issue is a duplicate if it has the same title, line_start, and file_name
            from sqlmodel import select
            duplicate_check = select(Issue).where(
                Issue.review_id == review.id,
                Issue.title == issue_data["title"],
                Issue.line_start == issue_data.get("line_start"),
                Issue.file_name == issue_data.get("file_name")
            )
            existing_issue = self.session.exec(duplicate_check).first()

            if existing_issue:
                logger.info(f"⏭️ Skipping duplicate issue: {issue_data['title']} at line {issue_data.get('line_start')} (already exists from {existing_issue.agent_role})")
                return  # Skip saving duplicate

            # Create issue
            issue = Issue(
                review_id=review.id,
                file_id=file_id,
                severity=issue_data["severity"],
                category=issue_data["category"],
                title=issue_data["title"],
                description=issue_data["description"],
                agent_role=agent_role_value,  # Store which agent found this issue
                file_name=issue_data.get("file_name"),
                line_start=issue_data.get("line_start"),
                line_end=issue_data.get("line_end")
            )
            self.session.add(issue)
            self.session.commit()
            self.session.refresh(issue)
            
            logger.debug(f"✅ Zapisano problem: {issue.title} (agent: {agent_role_value})")

            # Create suggestion if provided
            if issue_data.get("suggested_fix"):
                suggestion = Suggestion(
                    issue_id=issue.id,
                    suggested_code=issue_data["suggested_fix"],
                    explanation=issue_data.get("explanation") or "Sugestia poprawki od agenta"
                )
                self.session.add(suggestion)
                self.session.commit()
        except Exception as e:
            logger.error(f"❌ Błąd zapisywania problemu do bazy danych: {e}", exc_info=True)
            logger.error(f"   Issue data: {issue_data}")
            # Rollback on error
            self.session.rollback()
            raise
