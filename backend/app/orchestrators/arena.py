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


class TeamResultSchema(BaseModel):
    """Schema dla wyników zespołu."""
    issues: list[IssueSchema]
    summary: str


class ArenaOrchestrator:
    """Orkiestrator sesji Arena."""

    # Prompty dla agentów (te same co w review)
    AGENT_PROMPTS = {
        "general": """Jesteś ekspertem ds. przeglądów kodu. Analizuj kod pod kątem:
- Błędów logicznych i bugów
- Czytelności i maintainability
- Obsługi błędów
- Struktury kodu

Odpowiadaj krótko i konkretnie po polsku.""",

        "security": """Jesteś ekspertem ds. bezpieczeństwa. Szukaj:
- Luk injection (SQL, XSS, command)
- Błędów uwierzytelniania/autoryzacji
- Wycieku danych wrażliwych
- Niebezpiecznych konfiguracji

Odpowiadaj krótko i konkretnie po polsku.""",

        "performance": """Jesteś ekspertem ds. wydajności. Szukaj:
- Nieefektywnych algorytmów
- Problemów N+1
- Wycieków pamięci
- Blokujących operacji

Odpowiadaj krótko i konkretnie po polsku.""",

        "style": """Jesteś ekspertem ds. stylu kodu. Sprawdzaj:
- Konwencje nazewnictwa
- Formatowanie
- Dokumentację
- Code smells

Odpowiadaj krótko i konkretnie po polsku."""
    }

    SUMMARY_PROMPT = """Na podstawie analiz 4 agentów (general, security, performance, style),
napisz zwięzłe podsumowanie znalezionych problemów.

Analizy agentów:
{agent_analyses}

Napisz podsumowanie w formacie:
1. Najważniejsze problemy (max 3)
2. Ogólna ocena jakości kodu (1-10)
3. Rekomendacja (1-2 zdania)

Odpowiadaj po polsku, zwięźle i konkretnie."""

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
        """Uruchom zespół agentów i zbierz wyniki.

        Args:
            team_config: Konfiguracja zespołu (4 role)
            code_context: Kod do analizy
            api_keys: Klucze API
            team_name: Nazwa zespołu (A lub B)

        Returns:
            TeamResultSchema z issues i summary
        """
        all_issues = []
        agent_analyses = {}

        # Uruchom każdego agenta
        for role in ["general", "security", "performance", "style"]:
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
      "description": "opis problemu",
      "file_name": "nazwa pliku lub null",
      "line_start": numer linii lub null,
      "line_end": numer linii lub null
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

            try:
                # Wywołaj LLM
                response, _, _ = await provider_router.generate(
                    messages=messages,
                    provider_name=provider,
                    model=model,
                    temperature=0.2,
                    max_tokens=4096,
                    api_key=api_key
                )

                # Parsuj odpowiedź
                issues, analysis = self._parse_agent_response(response, role)
                all_issues.extend(issues)
                agent_analyses[role] = analysis

            except Exception as e:
                logger.warning(f"Zespół {team_name}, {role} failed: {e}")
                agent_analyses[role] = f"Błąd: {str(e)[:200]}"

        # Wygeneruj podsumowanie
        summary = await self._generate_summary(agent_analyses, api_keys, team_config)

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

        try:
            response, _, _ = await provider_router.generate(
                messages=messages,
                provider_name=provider,
                model=model,
                temperature=0.3,
                max_tokens=1024,
                api_key=api_key
            )
            return response
        except Exception as e:
            logger.warning(f"Summary generation failed: {e}")
            return f"Podsumowanie niedostępne (błąd: {str(e)[:100]})"
