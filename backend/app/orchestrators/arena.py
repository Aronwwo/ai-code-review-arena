"""Arena orchestrator - przeprowadza walkę dwóch zespołów AI.

Przepływ:
1. Pobiera projekt i pliki do analizy
2. Uruchamia Zespół A (4 agentów analizują kod)
3. Uruchamia Zespół B (4 agentów analizują kod)
4. Generuje podsumowania dla każdego zespołu
5. Ustawia status na "voting" - czeka na głos użytkownika
"""
import logging
from datetime import datetime, timezone
from sqlmodel import Session, select
from pydantic import BaseModel, ValidationError

from app.models.project import Project
from app.models.file import File
from app.models.arena import ArenaSession
from app.providers.base import LLMMessage
from app.providers.router import provider_router, CustomProviderConfig
from app.config import settings

logger = logging.getLogger(__name__)


class IssueSchema(BaseModel):
    """Schema dla pojedynczego problemu znalezionego przez agenta."""
    severity: str  # info, warning, error
    category: str
    title: str
    description: str
    file_name: str | None = None
    line_start: int | None = None
    line_end: int | None = None
    suggested_code: str | None = None  # Sugestia naprawy kodu
    explanation: str | None = None  # Dodatkowe wyjaśnienie problemu


class TeamResultSchema(BaseModel):
    """Schema dla wyników zespołu."""
    issues: list[IssueSchema]
    summary: str


class ArenaOrchestrator:
    """Orkiestrator sesji Arena."""

    # Prompt dla pojedynczego agenta (General)
    AGENT_PROMPTS = {
        "general": """Jesteś Ekspertem Poprawności Kodu (Code Correctness Specialist). Twoją JEDYNĄ odpowiedzialnością jest znajdowanie błędów składniowych, logicznych i bugów.

KRYTYCZNE ZASADY:
- Skupiaj się WYŁĄCZNIE na: błędach składniowych (brakujące znaki, niepoprawna składnia), błędach logicznych (błędna logika, nieprawidłowe obliczenia), bugach (wyjątki, crashy, przypadki brzegowe)
- IGNORUJ: bezpieczeństwo, wydajność, styl

Odpowiadaj krótko i konkretnie po polsku."""
    }

    SUMMARY_PROMPT = """Jesteś moderatorem przeglądu kodu. Twoim zadaniem jest STWORZYĆ ZWIĘZŁE PODSUMOWANIE na podstawie RZECZYWISTYCH analiz od 1 agenta-eksperta.

KRYTYCZNE ZASADY:
- TYLKO syntetyzuj i podsumuj odpowiedzi od agentów - NIE analizuj kodu samodzielnie
- TYLKO używaj problemów znalezionych przez agentów - NIE dodawaj własnych problemów
- Jeśli agenci nie znaleźli problemów, napisz: "Agenci nie znaleźli problemów w kodzie"
- Jeśli agenci znaleźli problemy, wymień tylko te problemy, które są w ich analizach

Analizy agentów (rzeczywiste odpowiedzi):
{agent_analyses}

Twoim zadaniem jest:
1. Przeczytać wszystkie analizy od agentów
2. Wyodrębnić najważniejsze problemy (max 3-5)
3. Napisać zwięzłe podsumowanie (2-3 zdania)

Format odpowiedzi (TYLKO zwykły tekst, NIE JSON):
1. Najważniejsze problemy: [wymień problemy znalezione przez agentów]
2. Ogólna ocena: [ocena 1-10 na podstawie liczby i ważności problemów znalezionych przez agentów]
3. Rekomendacja: [krótka rekomendacja na podstawie problemów znalezionych przez agentów]

Odpowiadaj po polsku, zwięźle i konkretnie. Używaj TYLKO informacji z analiz agentów powyżej."""

    def __init__(self, session: Session):
        """Inicjalizacja orchestratora."""
        self.session = session

    async def run_arena(self, session_id: int, api_keys: dict | None = None):
        """Przeprowadź sesję Arena.

        Args:
            session_id: ID sesji Arena
            api_keys: Klucze API per provider
        """
        arena_session = self.session.get(ArenaSession, session_id)
        if not arena_session:
            raise ValueError(f"ArenaSession {session_id} nie istnieje")

        project = self.session.get(Project, arena_session.project_id)
        if not project:
            raise ValueError(f"Project {arena_session.project_id} nie istnieje")

        # Aktualizuj status
        arena_session.status = "running"
        self.session.add(arena_session)
        self.session.commit()

        try:
            # Pobierz pliki projektu
            files_query = select(File).where(File.project_id == project.id)
            files = self.session.exec(files_query).all()

            if not files:
                raise ValueError("Projekt nie ma żadnych plików do analizy")

            # Zbuduj kontekst kodu
            code_context = self._build_code_context(files)

            # Uruchom oba zespoły
            logger.info(f"Arena {session_id}: Uruchamiam Zespół A...")
            team_a_result = await self._run_team(
                arena_session.team_a_config, code_context, api_keys, "A"
            )

            logger.info(f"Arena {session_id}: Uruchamiam Zespół B...")
            team_b_result = await self._run_team(
                arena_session.team_b_config, code_context, api_keys, "B"
            )

            # Zapisz wyniki
            arena_session.team_a_issues = [i.model_dump() for i in team_a_result.issues]
            arena_session.team_b_issues = [i.model_dump() for i in team_b_result.issues]
            arena_session.team_a_summary = team_a_result.summary
            arena_session.team_b_summary = team_b_result.summary
            arena_session.status = "voting"

            logger.info(f"Arena {session_id}: Zakończono, czekam na głos")

        except Exception as e:
            arena_session.status = "failed"
            arena_session.error_message = str(e)[:2000]
            logger.error(f"Arena {session_id} failed: {e}")

        self.session.add(arena_session)
        self.session.commit()

    def _build_code_context(self, files: list[File]) -> str:
        """Zbuduj kontekst kodu dla agentów."""
        context_parts = []
        for f in files:
            context_parts.append(f"=== {f.name} ===\n{f.content}\n")
        return "\n".join(context_parts)

    async def _run_team(
        self,
        team_config: dict,
        code_context: str,
        api_keys: dict | None,
        team_name: str
    ) -> TeamResultSchema:
        """Uruchom zespół agenta i zbierz wyniki.

        Args:
            team_config: Konfiguracja zespołu (tylko general)
            code_context: Kod do analizy
            api_keys: Klucze API
            team_name: Nazwa zespołu (A lub B)

        Returns:
            TeamResultSchema z issues i summary
        """
        all_issues = []
        agent_analyses = {}

        # Uruchom tylko agenta general
        for role in ["general"]:
            config = team_config.get(role, {})
            provider = config.get("provider", "ollama")
            model = config.get("model", "qwen2.5-coder:latest")

            logger.info(f"Zespół {team_name}, {role}: {provider}/{model}")

            # Zbuduj prompt
            system_prompt = self.AGENT_PROMPTS.get(role, self.AGENT_PROMPTS["general"])
            user_prompt = f"""Przeanalizuj poniższy kod i znajdź problemy.

KOD DO ANALIZY:
{code_context}

Odpowiedz w formacie JSON:
{{
  "issues": [
    {{
      "severity": "info|warning|error",
      "category": "kategoria problemu",
      "title": "krótki tytuł",
      "description": "szczegółowy opis problemu",
      "file_name": "nazwa pliku lub null",
      "line_start": numer linii lub null,
      "line_end": numer linii lub null,
      "suggested_code": "poprawiony kod lub null",
      "explanation": "dodatkowe wyjaśnienie dlaczego to problem i jak naprawić"
    }}
  ],
  "analysis": "Twoja ogólna analiza kodu (1-2 zdania)"
}}"""

            messages = [
                LLMMessage(role="system", content=system_prompt),
                LLMMessage(role="user", content=user_prompt)
            ]

            # Pobierz klucz API
            api_key = api_keys.get(provider) if api_keys else None

            # Build custom_provider_config for Perplexity and other custom providers
            custom_provider_config = None
            if provider and provider.lower() == "perplexity":
                # Build custom provider config for Perplexity
                custom_provider_config = CustomProviderConfig(
                    id="perplexity",
                    name="Perplexity",
                    base_url="https://api.perplexity.ai",
                    api_key=api_key,
                    header_name="Authorization",
                    header_prefix="Bearer ",
                )

            try:
                # Wywołaj LLM
                response, _, _ = await provider_router.generate(
                    messages=messages,
                    provider_name=provider,
                    model=model,
                    temperature=0.2,
                    max_tokens=4096,
                    api_key=api_key,
                    custom_provider_config=custom_provider_config
                )

                # Parsuj odpowiedź
                issues, analysis = self._parse_agent_response(response, role)
                all_issues.extend(issues)
                
                # Store actual raw response from agent, not just parsed analysis
                # This ensures we're using REAL agent responses, not generated summaries
                if analysis:
                    agent_analyses[role] = analysis
                else:
                    # Fallback: use raw response if analysis is empty
                    agent_analyses[role] = response[:500] if response else f"Agent {role} nie zwrócił odpowiedzi"
                
                logger.info(f"Zespół {team_name}, {role}: znaleziono {len(issues)} problemów, analiza: {analysis[:100] if analysis else 'brak'}...")

            except Exception as e:
                logger.warning(f"Zespół {team_name}, {role} failed: {e}")
                agent_analyses[role] = f"Błąd: {str(e)[:200]}"

        # Log actual agent analyses before generating summary
        logger.info(f"Zespół {team_name}: Analizy od agentów:")
        for role, analysis in agent_analyses.items():
            logger.info(f"  - {role}: {analysis[:200] if analysis else 'BRAK ANALIZY'}...")
        
        # Wygeneruj podsumowanie TYLKO jeśli mamy jakiekolwiek analizy
        if not agent_analyses or not any(agent_analyses.values()):
            logger.warning(f"Zespół {team_name}: Brak analiz od agentów - używam fallback summary")
            summary = f"Zespół {team_name} nie dostarczył analiz. Wszyscy agenci zwrócili błędy lub puste odpowiedzi."
        else:
            summary = await self._generate_summary(agent_analyses, api_keys, team_config)
        
        logger.info(f"Zespół {team_name}: Wygenerowano podsumowanie: {summary[:200] if summary else 'BRAK'}...")

        return TeamResultSchema(issues=all_issues, summary=summary)

    def _parse_agent_response(self, response: str, role: str) -> tuple[list[IssueSchema], str]:
        """Parsuj odpowiedź agenta.

        Args:
            response: Surowa odpowiedź LLM
            role: Rola agenta

        Returns:
            tuple: (lista issues, analiza tekstowa)
        """
        import json

        issues = []
        analysis = ""

        try:
            # Znajdź JSON w odpowiedzi
            start = response.find("{")
            end = response.rfind("}") + 1
            if start >= 0 and end > start:
                json_str = response[start:end]
                data = json.loads(json_str)

                # Parsuj issues
                for issue_data in data.get("issues", []):
                    try:
                        issue = IssueSchema(**issue_data)
                        issues.append(issue)
                    except ValidationError:
                        pass

                analysis = data.get("analysis", "")
        except json.JSONDecodeError:
            # Jeśli nie JSON, użyj całej odpowiedzi jako analizy
            analysis = response[:1000]

        return issues, analysis or f"Analiza {role}: {len(issues)} problemów"

    def _cleanup_summary(self, response: str) -> str:
        """Wyczyść podsumowanie z JSON i sformatuj czytelnie.

        Args:
            response: Surowa odpowiedź LLM

        Returns:
            str: Czytelne podsumowanie
        """
        import json
        import re

        # Sprawdź czy response to JSON
        try:
            # Spróbuj znaleźć JSON w odpowiedzi
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                json_str = json_match.group()
                data = json.loads(json_str)

                # Jeśli to JSON, sformatuj czytelnie
                lines = []

                # Podsumowanie
                if "summary" in data:
                    lines.append(data["summary"])

                # Issues
                if "issues" in data and data["issues"]:
                    lines.append(f"\n{len(data['issues'])} problemów:")
                    for i, issue in enumerate(data["issues"][:5], 1):  # Max 5
                        title = issue.get("title", "Problem")
                        lines.append(f"{i}. {title}")

                # Ogólna ocena
                if "summary" in data or "issues" in data:
                    if data.get("issues"):
                        lines.append(f"\nOgólna ocena: {10 - min(len(data['issues']), 7)}/10")
                    else:
                        lines.append("\nOgólna ocena: 10/10")

                # Rekomendacja
                if "summary" in data and data["summary"]:
                    lines.append(f"\nRekomendacja: {data['summary']}")

                return "\n".join(lines) if lines else response
        except (json.JSONDecodeError, KeyError):
            pass

        # Jeśli nie JSON lub parsing failed, zwróć oryginalny response
        return response

    async def _generate_summary(
        self,
        agent_analyses: dict[str, str],
        api_keys: dict | None,
        team_config: dict
    ) -> str:
        """Wygeneruj podsumowanie dla zespołu.

        Args:
            agent_analyses: Analizy od poszczególnych agentów
            api_keys: Klucze API
            team_config: Konfiguracja zespołu

        Returns:
            str: Podsumowanie
        """
        # Użyj modelu z roli "general" do podsumowania
        config = team_config.get("general", {})
        provider = config.get("provider", "ollama")
        model = config.get("model", "qwen2.5-coder:latest")

        # Zbuduj prompt
        analyses_text = "\n\n".join([
            f"**{role.upper()}**:\n{analysis}"
            for role, analysis in agent_analyses.items()
        ])

        prompt = self.SUMMARY_PROMPT.format(agent_analyses=analyses_text)

        messages = [
            LLMMessage(role="system", content="Jesteś moderatorem code review."),
            LLMMessage(role="user", content=prompt)
        ]

        api_key = api_keys.get(provider) if api_keys else None

        # Build custom_provider_config for Perplexity
        custom_provider_config = None
        if provider and provider.lower() == "perplexity":
            custom_provider_config = CustomProviderConfig(
                id="perplexity",
                name="Perplexity",
                base_url="https://api.perplexity.ai",
                api_key=api_key,
                header_name="Authorization",
                header_prefix="Bearer ",
            )

        try:
            logger.info(f"🔄 Generowanie podsumowania dla zespołu z {len(agent_analyses)} analizami od agentów...")
            logger.debug(f"📝 Rzeczywiste analizy od agentów:\n{analyses_text[:1000]}...")

            response, _, _ = await provider_router.generate(
                messages=messages,
                provider_name=provider,
                model=model,
                temperature=0.3,
                max_tokens=1024,
                api_key=api_key,
                custom_provider_config=custom_provider_config
            )
            
            logger.info(f"✅ Wygenerowano podsumowanie ({len(response)} chars): {response[:200]}...")

            # Validate that summary is not a placeholder or generated without agent data
            if not response or len(response.strip()) < 20:
                logger.warning("Summary too short or empty - using fallback")
                return "Podsumowanie niedostępne - agenci nie dostarczyli wystarczających danych."

            # Clean up response - remove JSON if present and convert to readable text
            response = self._cleanup_summary(response)

            return response
        except Exception as e:
            logger.warning(f"Summary generation failed: {e}", exc_info=True)
            # Return a summary based on issues count if available
            total_issues = sum(1 for a in agent_analyses.values() if a and "problem" in a.lower())
            if total_issues > 0:
                return f"Znaleziono problemy w kodzie. Agenci zidentyfikowali {total_issues} problemów."
            return f"Podsumowanie niedostępne (błąd: {str(e)[:100]})"
