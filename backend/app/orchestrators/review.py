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

    MODERATOR_PROMPT = """Jesteś Moderatorem przeglądu kodu. Twoim zadaniem jest TYLKO sformatować odpowiedzi od agentów-ekspertów w czytelny raport.

UWAGA: Agenci oznaczeni jako [BRAK ODPOWIEDZI] nie odpowiedzieli w wyznaczonym czasie lub wystąpił błąd - IGNORUJ ich całkowicie.

KRYTYCZNE ZASADY:
- Twoim zadaniem jest TYLKO sformatować i zsyntetyzować odpowiedzi od agentów, którzy odpowiedzieli
- NIE generuj własnej analizy kodu - opieraj się TYLKO na odpowiedziach od agentów
- Jeśli NIE MA żadnych odpowiedzi od agentów, zwróć: {"summary": "Nie można ocenić kodu - brak odpowiedzi od agentów", "issues": [], "overall_quality": "Ocena ogólna: nie można ocenić"}
- NIE oceniaj kodu negatywnie tylko dlatego, że niektórzy agenci nie odpowiedzieli
- Jeśli agenci nie znaleźli problemów, ocena powinna być "dobry" lub "świetny", NIE "wymaga poprawy"

Twoim zadaniem jest:
1. Przeanalizować odpowiedzi wszystkich agentów, którzy odpowiedzieli (oprócz tych z [BRAK ODPOWIEDZI])
2. Stworzyć JEDEN końcowy raport, który syntetyzuje wszystkie znalezione problemy
3. Usunąć duplikaty i podsumować najważniejsze kwestie
4. Ocenić ogólną jakość kodu na podstawie TYLKO dostępnych odpowiedzi

Odpowiedz TYLKO w formacie JSON (bez żadnego dodatkowego tekstu, bez markdown code blocks):
{
  "summary": "Twoje podsumowanie przeglądu kodu po polsku (2-3 zdania)",
  "issues": [
    {
      "severity": "info",
      "category": "security",
      "title": "Tytuł problemu po polsku",
      "description": "Opis problemu po polsku",
      "file_name": "nazwa_pliku.ext",
      "line_start": 10,
      "line_end": 15,
      "code_snippet": "fragment kodu",
      "suggested_fix": "Sugestia poprawki po polsku"
    }
  ],
  "overall_quality": "Ocena ogólna: świetny / dobry / wymaga poprawy / słaby"
}

WAŻNE - FORMATOWANIE ODPOWIEDZI:
- Formatuj TYLKO odpowiedzi od agentów - NIE generuj własnej analizy
- Zbierz problemy TYLKO z odpowiedzi agentów (zignoruj [BRAK ODPOWIEDZI])
- Usuń duplikaty i zsyntetyzuj podobne problemy
- Jeśli w odpowiedziach agentów nie ma problemów, zwróć: {"summary": "Kod jest poprawny, nie znaleziono problemów", "issues": [], "overall_quality": "Ocena ogólna: dobry"}
- Jeśli są problemy w odpowiedziach agentów, użyj oceny: "dobry" (drobne), "wymaga poprawy" (średnie), "słaby" (poważne)
- NIE dodawaj własnych problemów - TYLKO te z odpowiedzi agentów
- Wszystkie teksty po polsku
- Zwróć TYLKO JSON, bez markdown, bez ```json ani ```"""

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

            # === KROK 1: Uruchom wszystkich agentów SEKWENCYJNIE (jeden po drugim) ===
            # WAŻNE: Kolejny agent uruchamia się DOPIERO po otrzymaniu odpowiedzi od poprzedniego
            # To zapobiega rate limiting i zapewnia stabilność, gdy agenci używają tego samego API key
            agent_responses: dict[str, str | None] = {}

            for idx, agent in enumerate(agents_list):
                logger.info(f"🤖 [{idx + 1}/{len(agents_list)}] Uruchamiam agenta {agent.role}...")
                
                # Get agent config if available
                agent_config = typed_agent_configs.get(agent.role)

                # Use agent's provider/model if configured
                agent_provider = agent.provider if agent.provider != "mock" else (provider_name or agent.provider)
                agent_model = agent.model if agent.model != "default" else (model or agent.model)

                # Get timeout from config (default 180s = 3 min)
                timeout_seconds = agent_config.timeout_seconds if agent_config else 180
                # Get max_tokens from config (default 4096)
                max_tokens = agent_config.max_tokens if agent_config else 4096

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

                # Run agent and WAIT for response before starting next agent
                # await gwarantuje, że kolejny agent nie ruszy dopóki ten nie zakończy
                logger.info(f"⏳ [{idx + 1}/{len(agents_list)}] Czekam na odpowiedź od agenta {agent.role}...")
                response = await self._run_agent(
                    review, project, agent, agent_provider, agent_model,
                    agent_api_key, custom_provider_config, timeout_seconds, max_tokens
                )
                agent_responses[agent.role] = response
                
                # Log what we got from agent
                if response is None:
                    logger.warning(f"❌ [{idx + 1}/{len(agents_list)}] Agent {agent.role} zwrócił None - brak odpowiedzi")
                elif response and response.strip().startswith(("[BŁĄD]", "[ERROR]", "[TIMEOUT]", "[EMPTY]")):
                    logger.warning(f"❌ [{idx + 1}/{len(agents_list)}] Agent {agent.role} zwrócił błąd: {response[:100]}")
                else:
                    logger.info(f"✅ [{idx + 1}/{len(agents_list)}] Agent {agent.role} zakończony. Odpowiedź otrzymana: {response[:100] if response else 'Brak odpowiedzi'}...")
                
                # Add delay between agents to avoid rate limiting (especially for Gemini free tier)
                # Wait 5 seconds between agents to respect rate limits (Gemini free tier is strict)
                if idx < len(agents_list) - 1:  # Don't wait after last agent
                    delay_seconds = 5.0  # Increased delay for free tier Gemini API
                    logger.info(f"⏸️  Czekam {delay_seconds} sekund przed uruchomieniem następnego agenta (aby uniknąć rate limiting Gemini free tier)...")
                    await asyncio.sleep(delay_seconds)
                
                # Teraz możemy przejść do następnego agenta (dopiero po otrzymaniu odpowiedzi i opóźnieniu)

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
        # Check if we have any valid responses from agents
        # Filter out None, empty strings, and error messages
        error_prefixes = ["[BŁĄD]", "[ERROR]", "[TIMEOUT]", "[EMPTY]"]
        valid_responses = {}
        logger.info(f"🔍 MODERATOR: Analizowanie odpowiedzi od agentów. Otrzymano {len(agent_responses)} odpowiedzi.")
        
        for role, resp in agent_responses.items():
            logger.info(f"🔍 MODERATOR: Sprawdzam odpowiedź od agenta {role}: {type(resp).__name__}, długość: {len(str(resp)) if resp else 0}")
            
            if resp is not None and resp.strip():
                # Check if response is an error message
                resp_stripped = resp.strip()
                is_error = any(resp_stripped.startswith(prefix) for prefix in error_prefixes)
                if not is_error:
                    valid_responses[role] = resp
                    logger.info(f"✅ MODERATOR: Valid response from agent {role}: {resp[:100]}...")
                else:
                    logger.info(f"❌ MODERATOR: Filtered out error response from agent {role}: {resp_stripped[:100]}...")
            else:
                logger.info(f"⚠️ MODERATOR: Agent {role} returned None or empty response (resp={repr(resp)})")
        
        logger.info(f"📊 MODERATOR: Total agent responses: {len(agent_responses)}, Valid responses: {len(valid_responses)}")
        if valid_responses:
            logger.info(f"✅ MODERATOR: Valid response roles: {list(valid_responses.keys())}")
        else:
            logger.warning(f"⚠️ MODERATOR: BRAK PRAWIDŁOWYCH ODPOWIEDZI - wszystkie agenci zwrócili None/błąd")
        
        # If no agents responded, return appropriate message
        if not valid_responses:
            logger.warning(f"No valid agent responses for review {review.id} - all agents failed or timed out. Total agents: {len(agent_responses)}")
            review.summary = json.dumps({
                "summary": "Nie można przeprowadzić przeglądu kodu, ponieważ żaden z agentów nie zwrócił odpowiedzi. Wszyscy agenci przekroczyli limit czasu lub wystąpił błąd.",
                "issues": [],
                "overall_quality": "Ocena ogólna: nie można ocenić (brak odpowiedzi od agentów)"
            }, ensure_ascii=False)
            self.session.add(review)
            self.session.commit()
            return
        
        # Build moderator prompt with all agent responses
        # Use valid_responses (already filtered) instead of agent_responses
        responses_text = ""
        valid_count = 0
        timeout_count = 0
        
        for role in ["general", "security", "performance", "style"]:
            role_name = {
                "general": "Ekspert Ogólny",
                "security": "Ekspert Bezpieczeństwa",
                "performance": "Ekspert Wydajności",
                "style": "Ekspert Stylu"
            }.get(role, role.title())

            if role in valid_responses:
                valid_count += 1
                response = valid_responses[role]
                # Remove markdown code blocks before passing to moderator
                cleaned_response = response.strip()
                if cleaned_response.startswith("```json"):
                    cleaned_response = cleaned_response.replace("```json", "", 1).strip()
                if cleaned_response.startswith("```"):
                    cleaned_response = cleaned_response.replace("```", "", 1).strip()
                if cleaned_response.endswith("```"):
                    cleaned_response = cleaned_response[:-3].strip()
                
                responses_text += f"\n### {role_name}\n{cleaned_response}\n"
            else:
                timeout_count += 1
                responses_text += f"\n### {role_name} [BRAK ODPOWIEDZI]\nAgent nie odpowiedział w wyznaczonym czasie lub wystąpił błąd.\n"

        # CRITICAL: Double-check if we have any valid responses
        # This is a safety check - if valid_count is 0 OR valid_responses is empty, don't call moderator
        if valid_count == 0 or not valid_responses:
            logger.warning(f"🚫 MODERATOR: valid_count={valid_count}, valid_responses={len(valid_responses)} (roles: {list(valid_responses.keys())}) - NIE WYWOŁUJĘ moderatora LLM!")
            logger.warning(f"🚫 MODERATOR: Review {review.id} - all agents failed or timed out. Not calling moderator LLM.")
            
            # Log all agent responses for debugging
            logger.warning(f"🔍 MODERATOR DEBUG: All agent_responses:")
            for role, resp in agent_responses.items():
                logger.warning(f"  - {role}: {type(resp).__name__} = {repr(resp)[:200] if resp else 'None'}")
            
            review.summary = json.dumps({
                "summary": "Nie można przeprowadzić przeglądu kodu, ponieważ żaden z agentów nie zwrócił odpowiedzi. Wszyscy agenci przekroczyli limit czasu lub wystąpił błąd.",
                "issues": [],
                "overall_quality": "Ocena ogólna: nie można ocenić (brak odpowiedzi od agentów)"
            }, ensure_ascii=False)
            self.session.add(review)
            self.session.commit()
            logger.info(f"✅ MODERATOR: Ustawiono summary na komunikat o braku odpowiedzi. NIE WYWOŁAŁEM moderatora LLM.")
            return
        
        logger.info(f"✅ MODERATOR: valid_count={valid_count} > 0, valid_responses={len(valid_responses)} (roles: {list(valid_responses.keys())}) - WYWOŁUJĘ moderatora LLM")

        user_prompt = f"""Odpowiedzi od agentów-ekspertów:

{responses_text}

ZADANIE:
Sformatuj powyższe odpowiedzi od agentów w JEDEN końcowy raport JSON.

KRYTYCZNE ZASADY:
- Masz {valid_count} odpowiedzi od agentów (zignoruj {timeout_count} oznaczone jako [BRAK ODPOWIEDZI])
- TYLKO formatuj i syntetyzuj odpowiedzi od agentów - NIE analizuj kodu samodzielnie
- TYLKO zebierz problemy z odpowiedzi agentów - NIE dodawaj własnych problemów
- Jeśli w odpowiedziach agentów nie ma problemów, zwróć: {{"summary": "Kod jest poprawny, nie znaleziono problemów", "issues": [], "overall_quality": "Ocena ogólna: dobry"}}
- Jeśli w odpowiedziach agentów są problemy, zsyntetyzuj je i usuń duplikaty
- Ocenę ogólną wyznacz TYLKO na podstawie problemów znalezionych przez agentów

Przykład poprawnej odpowiedzi (gdy agenci znaleźli problemy):
{{"summary": "Agenci znaleźli kilka problemów: [synteza problemów z odpowiedzi agentów]", "issues": [synteza issues z odpowiedzi agentów, bez duplikatów], "overall_quality": "Ocena ogólna: wymaga poprawy"}}

Przykład poprawnej odpowiedzi (gdy agenci nie znaleźli problemów):
{{"summary": "Kod jest poprawny, nie znaleziono problemów", "issues": [], "overall_quality": "Ocena ogólna: dobry"}}

Zwróć TYLKO JSON, bez dodatkowego tekstu."""

        messages = [
            LLMMessage(role="system", content=self.MODERATOR_PROMPT),
            LLMMessage(role="user", content=user_prompt)
        ]

        # Get moderator provider/model
        mod_provider = moderator_config.provider if moderator_config else provider_name
        mod_model = moderator_config.model if moderator_config else model
        mod_timeout = moderator_config.timeout_seconds if moderator_config else 300  # 5 min default for moderator
        mod_max_tokens = moderator_config.max_tokens if moderator_config else 4096  # Default 4096 for moderator

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
            raw_output, response_provider, response_model = await asyncio.wait_for(
                provider_router.generate(
                    messages=messages,
                    provider_name=mod_provider,
                    model=mod_model,
                    temperature=0.0,
                    max_tokens=mod_max_tokens,
                    api_key=mod_api_key,
                    custom_provider_config=custom_provider_config
                ),
                timeout=mod_timeout
            )

            # Remove markdown code block fences if present
            cleaned_output = raw_output.strip()
            if cleaned_output.startswith("```json"):
                cleaned_output = cleaned_output.replace("```json", "", 1).strip()
            if cleaned_output.startswith("```"):
                cleaned_output = cleaned_output.replace("```", "", 1).strip()
            if cleaned_output.endswith("```"):
                cleaned_output = cleaned_output[:-3].strip()
            
            # Check for placeholders BEFORE storing
            if self._contains_placeholders(cleaned_output):
                logger.warning("Moderator response contains placeholder patterns - rejecting")
                review.summary = "[BŁĄD] Moderator zwrócił odpowiedź z placeholderami zamiast rzeczywistej analizy"
                self.session.add(review)
                self.session.commit()
                return
            
            # Auto-correct overall_quality if inconsistent with issues count
            try:
                moderator_data = json.loads(cleaned_output)
                
                # Check parsed data for placeholders
                summary = moderator_data.get("summary", "")
                if self._contains_placeholders(summary):
                    logger.warning("Moderator summary contains placeholder patterns - rejecting")
                    review.summary = "[BŁĄD] Moderator zwrócił odpowiedź z placeholderami zamiast rzeczywistej analizy"
                    self.session.add(review)
                    self.session.commit()
                    return
                
                # Check issues for placeholders
                issues = moderator_data.get("issues", [])
                for issue in issues:
                    if isinstance(issue, dict):
                        title = issue.get("title", "")
                        description = issue.get("description", "")
                        if self._contains_placeholders(title) or self._contains_placeholders(description):
                            logger.warning(f"Moderator issue contains placeholder patterns - rejecting entire response")
                            review.summary = "[BŁĄD] Moderator zwrócił odpowiedź z placeholderami zamiast rzeczywistej analizy"
                            self.session.add(review)
                            self.session.commit()
                            return
                
                issues_count = len(issues)
                overall_quality = moderator_data.get("overall_quality", "")
                
                # If no issues but quality says "wymaga poprawy" or "słaby", correct it
                if issues_count == 0:
                    if "wymaga poprawy" in overall_quality.lower() or "słaby" in overall_quality.lower():
                        logger.info(f"Auto-correcting overall_quality: no issues but quality was '{overall_quality}'")
                        moderator_data["overall_quality"] = "Ocena ogólna: dobry"
                        cleaned_output = json.dumps(moderator_data, ensure_ascii=False)
                
                # Store cleaned version
                raw_output = cleaned_output
            except (json.JSONDecodeError, KeyError, TypeError) as e:
                logger.debug(f"Could not auto-correct overall_quality: {e}")
                # Still use cleaned output even if auto-correction failed
                raw_output = cleaned_output

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
        timeout_seconds: int = 180,
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

        async def _generate_with_cache():
            """Helper to run generation with caching logic."""
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
                    return cached_response, effective_provider, model or settings.default_model
                else:
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
                    return raw_out, resp_provider, resp_model
            else:
                # Generate response without caching
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
            # Run with timeout
            logger.info(f"🔄 Agent {agent.role} ({provider_name}/{model}) - Starting generation with timeout {timeout_seconds}s...")
            raw_output, response_provider, response_model = await asyncio.wait_for(
                _generate_with_cache(),
                timeout=timeout_seconds
            )
            logger.info(f"✅ Agent {agent.role} received response: provider={response_provider}, model={response_model}, length={len(raw_output) if raw_output else 0} chars")

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

            # Update the existing agent record - SUCCESS
            agent.provider = response_provider or provider_name or "unknown"
            agent.model = response_model or model or "unknown"
            agent.raw_output = raw_output[:50000]  # Truncate if too long
            agent.parsed_successfully = parsed_successfully
            agent.timed_out = False

            self.session.add(agent)
            self.session.commit()
            self.session.refresh(agent)

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

            # Return error message instead of None, so it can be logged/filtered by moderator
            # Moderator will filter out responses starting with [BŁĄD] etc.
            return error_output

    async def _store_moderator_issues(self, review: Review, summary_text: str | None):
        """Parse moderator JSON summary and store issues for council review."""
        if not summary_text:
            logger.warning("Council summary missing - no issues stored")
            return

        # Check for placeholder patterns before parsing
        if self._contains_placeholders(summary_text):
            logger.warning("Moderator response contains placeholder patterns - rejecting")
            review.summary = "[BŁĄD] Moderator zwrócił odpowiedź z placeholderami zamiast rzeczywistej analizy"
            self.session.add(review)
            self.session.commit()
            return

        # Remove markdown code block fences if present
        cleaned_text = summary_text.strip()
        if cleaned_text.startswith("```json"):
            cleaned_text = cleaned_text.replace("```json", "", 1).strip()
        if cleaned_text.startswith("```"):
            cleaned_text = cleaned_text.replace("```", "", 1).strip()
        if cleaned_text.endswith("```"):
            cleaned_text = cleaned_text[:-3].strip()

        try:
            data = json.loads(cleaned_text)
        except json.JSONDecodeError as e:
            logger.error(f"Council summary is not valid JSON - no issues stored. Error: {e}")
            logger.debug(f"Cleaned text preview: {cleaned_text[:500]}...")
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
                file_name=issue_data.get("file_name"),
                line_start=issue_data.get("line_start"),
                line_end=issue_data.get("line_end")
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
Przeanalizuj ten kod i zwróć swoje uwagi TYLKO w formacie JSON (bez dodatkowego tekstu, bez markdown code blocks):

{
  "issues": [
    {
      "severity": "info",
      "category": "security",
      "title": "Tytuł problemu po polsku",
      "description": "Opis problemu po polsku",
      "file_name": "nazwa_pliku.ext",
      "line_start": 10,
      "line_end": 15,
      "code_snippet": "fragment kodu",
      "suggested_fix": "Sugestia poprawki po polsku"
    }
  ],
  "summary": "Podsumowanie analizy po polsku"
}

WAŻNE:
- Przeanalizuj kod i znajdź PRAWDZIWE problemy
- Wypełnij wszystkie pola PRAWDZIWYMI danymi z analizy
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
            "po polsku",  # Must be exact phrase
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
        
        # Remove markdown code block fences if present
        cleaned_output = raw_output.strip()
        if cleaned_output.startswith("```json"):
            cleaned_output = cleaned_output.replace("```json", "", 1).strip()
        if cleaned_output.startswith("```"):
            cleaned_output = cleaned_output.replace("```", "", 1).strip()
        if cleaned_output.endswith("```"):
            cleaned_output = cleaned_output[:-3].strip()
        
        try:
            # Try to parse as JSON
            data = json.loads(cleaned_output)
            
            # Check parsed data for placeholders
            if isinstance(data, dict):
                summary = data.get("summary", "")
                if self._contains_placeholders(summary):
                    logger.warning("Summary contains placeholder patterns - rejecting")
                    return False, []
                
                issues = data.get("issues", [])
                for issue in issues:
                    if isinstance(issue, dict):
                        title = issue.get("title", "")
                        description = issue.get("description", "")
                        if self._contains_placeholders(title) or self._contains_placeholders(description):
                            logger.warning("Issue contains placeholder patterns - rejecting")
                            return False, []
            schema = ReviewResponseSchema(**data)
            issues_data = [issue.model_dump() for issue in schema.issues]
            return True, issues_data

        except json.JSONDecodeError as e:
            logger.warning(f"JSON decode error in LLM response: {str(e)[:200]}")
            logger.debug(f"Raw output preview: {raw_output[:500]}...")

            # Fallback: try to extract JSON from text (already cleaned, but try regex)
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
