"""Conversation orchestrator for agent discussions (Council and Arena modes)."""
import json
import logging
from datetime import datetime, UTC
from sqlmodel import Session, select
from pydantic import BaseModel, ValidationError
from app.models.conversation import Conversation, Message
from app.models.review import Review, Issue
from app.models.project import Project
from app.models.file import File
from app.providers.base import LLMMessage
from app.providers.router import provider_router
from app.config import settings

logger = logging.getLogger(__name__)


class ArenaVerdictSchema(BaseModel):
    """Schema for arena moderator verdict."""
    confirmed: bool
    final_severity: str
    moderator_comment: str
    keep_issue: bool


class CouncilIssueSchema(BaseModel):
    """Schema for council-generated issue."""
    severity: str
    category: str
    title: str
    description: str
    suggested_code: str | None = None
    explanation: str


class CouncilSummarySchema(BaseModel):
    """Schema for council summary."""
    issues: list[CouncilIssueSchema]
    summary: str


class ConversationOrchestrator:
    """Orchestrates agent conversations in council and arena modes."""

    COUNCIL_AGENTS = ["Recenzent Ogólny", "Ekspert Bezpieczeństwa", "Analityk Wydajności", "Specjalista Jakości Kodu"]

    PROSECUTOR_PROMPT = """Jesteś Prokuratorem w debacie o przeglądzie kodu. Twoją rolą jest argumentowanie, dlaczego zgłoszony problem jest poważny i powinien zostać naprawiony.

Bądź dokładny i przekonujący:
- Cytuj konkretne zagrożenia i potencjalne konsekwencje
- Odwołuj się do najlepszych praktyk i standardów (OWASP, wytyczne branżowe)
- Podawaj przykłady rzeczywistych incydentów
- Wyjaśniaj wektory ataków lub scenariusze awarii

Pozostań jednak profesjonalny i oparty na faktach. Twoim celem jest prawda, a nie zwycięstwo za wszelką cenę.

WAŻNE: Odpowiadaj TYLKO po polsku. Bądź zwięzły - maksymalnie 4-5 zdań."""

    DEFENDER_PROMPT = """Jesteś Obrońcą w debacie o przeglądzie kodu. Twoją rolą jest dostarczanie kontekstu i argumentowanie za rozsądną interpretacją problemów.

Rozważ czynniki łagodzące:
- Istniejące zabezpieczenia i warstwy walidacji
- Ograniczony zakres lub restrykcje dostępu
- Kompromisy między wydajnością a bezpieczeństwem
- Ograniczenia starszego kodu (legacy)
- Priorytety rozwojowe

Bądź wyważony - uznawaj prawdziwe problemy, ale dostarczaj ważny kontekst, który Prokurator może pominąć.

WAŻNE: Odpowiadaj TYLKO po polsku. Bądź zwięzły - maksymalnie 4-5 zdań."""

    MODERATOR_ARENA_PROMPT = """Jesteś Moderatorem w debacie o przeglądzie kodu. Wysłuchałeś argumentów zarówno Prokuratora, jak i Obrońcy.

Wydaj sprawiedliwy, wyważony werdykt w formacie JSON:
{
  "confirmed": true/false,  // Czy to jest prawdziwy problem?
  "final_severity": "info" | "warning" | "error",  // Końcowy poziom ważności
  "moderator_comment": "Twoje uzasadnienie po polsku...",
  "keep_issue": true/false  // Czy ten problem powinien pozostać na liście?
}

Bądź obiektywny. Rozważ oba argumenty uważnie. Opieraj swoją decyzję na faktach, a nie na retoryce.

WAŻNE: Pole "moderator_comment" musi być po polsku. Zwróć TYLKO poprawny JSON, bez dodatkowego tekstu."""

    MODERATOR_COUNCIL_PROMPT = """Jesteś Moderatorem syntetyzującym dyskusję rady. Agenci przedyskutowali kod z różnych perspektyw.

WAŻNE: NIE analizujesz kodu bezpośrednio. Twoje zadanie to TYLKO synteza wypowiedzi agentów.
Bazuj WYŁĄCZNIE na tym co powiedzieli agenci - nie dodawaj własnych obserwacji o kodzie.

Zsyntetyzuj ich spostrzeżenia w ustrukturyzowane podsumowanie JSON:
{
  "issues": [
    {
      "severity": "info" | "warning" | "error",
      "category": "security" | "performance" | "style" | "best-practices" | etc,
      "title": "Krótki tytuł po polsku",
      "description": "Szczegółowy opis po polsku",
      "suggested_code": "Opcjonalna sugestia kodu",
      "explanation": "Dlaczego to jest ważne - po polsku"
    }
  ],
  "summary": "Ogólna ocena i kluczowe wnioski po polsku"
}

WAŻNE: Wszystkie teksty (title, description, explanation, summary) muszą być PO POLSKU.
Zwróć TYLKO poprawny JSON, bez dodatkowego tekstu."""

    def __init__(self, session: Session):
        """Initialize conversation orchestrator.

        Args:
            session: Database session
        """
        self.session = session

    async def run_conversation(
        self,
        conversation_id: int,
        provider_name: str | None = None,
        model: str | None = None
    ) -> Conversation:
        """Run a conversation (council or arena mode).

        Args:
            conversation_id: Conversation ID to run
            provider_name: LLM provider to use
            model: Model name to use

        Returns:
            Completed Conversation object
        """
        conversation = self.session.get(Conversation, conversation_id)
        if not conversation:
            raise ValueError(f"Conversation {conversation_id} not found")

        # Update status
        conversation.status = "running"
        self.session.add(conversation)
        self.session.commit()

        try:
            if conversation.mode in ("cooperative", "council"):
                await self._run_council_mode(conversation, provider_name, model)
            elif conversation.mode in ("adversarial", "arena"):
                await self._run_arena_mode(conversation, provider_name, model)
            else:
                raise ValueError(f"Unknown conversation mode: {conversation.mode}")

            conversation.status = "completed"
            conversation.completed_at = datetime.now(UTC)

        except Exception as e:
            conversation.status = "failed"
            conversation.meta_info = {"error": str(e)}
            conversation.completed_at = datetime.now(UTC)

        self.session.add(conversation)
        self.session.commit()
        self.session.refresh(conversation)

        return conversation

    async def _run_council_mode(
        self,
        conversation: Conversation,
        provider_name: str | None,
        model: str | None
    ):
        """Run cooperative council discussion.

        Args:
            conversation: Conversation object
            provider_name: LLM provider
            model: Model name
        """
        # Get context
        context = await self._build_context(conversation)

        # Run single round of discussion (optimized for demo)
        turn_index = 0
        for agent_name in self.COUNCIL_AGENTS:
            logger.info(f"👤 AGENT TURN | Agent: {agent_name} | Turn: {turn_index} | Mode: council")

            # Build messages for this agent
            system_prompt = f"""Jesteś {agent_name} uczestniczącym w współpracującej dyskusji o przeglądzie kodu.

Poprzedni kontekst dyskusji:
{self._get_conversation_history(conversation)}

Przedstaw swoją perspektywę na kod. Rozwijaj to, co powiedzieli inni. Bądź zwięzły, ale wnikliwy.

WAŻNE: Odpowiadaj TYLKO po polsku. Maksymalnie 3-4 zdania."""

            messages = [
                LLMMessage(role="system", content=system_prompt),
                LLMMessage(role="user", content=f"Kontekst kodu:\n{context}\n\nPodziel się swoją analizą:")
            ]

            logger.debug(
                f"📝 AGENT PROMPT | Agent: {agent_name} | "
                f"System prompt length: {len(system_prompt)} | "
                f"Context length: {len(context)} | "
                f"History length: {len(self._get_conversation_history(conversation))}"
            )

            # Generate response
            response, used_provider, used_model = await provider_router.generate(
                messages=messages,
                provider_name=provider_name,
                model=model,
                temperature=0.3,  # Some creativity for discussion
                max_tokens=512  # Reduced for faster responses
            )

            logger.info(
                f"✅ AGENT RESPONSE | Agent: {agent_name} | "
                f"Provider: {used_provider} | Model: {used_model} | "
                f"Response length: {len(response)} chars"
            )

            # Store message
            message = Message(
                conversation_id=conversation.id,
                sender_type="agent",
                sender_name=agent_name,
                turn_index=turn_index,
                content=response,
                is_summary=False
            )
            self.session.add(message)
            turn_index += 1

        self.session.commit()

        # Moderator synthesis
        await self._council_moderator_synthesis(conversation, context, provider_name, model)

    async def _run_arena_mode(
        self,
        conversation: Conversation,
        provider_name: str | None,
        model: str | None
    ):
        """Run adversarial arena debate.

        Args:
            conversation: Conversation object
            provider_name: LLM provider
            model: Model name
        """
        # Get issue being debated
        if conversation.topic_type != "issue" or not conversation.topic_id:
            raise ValueError("Arena mode requires an issue topic")

        issue = self.session.get(Issue, conversation.topic_id)
        if not issue:
            raise ValueError(f"Issue {conversation.topic_id} not found")

        # Get file context if available
        file_context = ""
        if issue.file_id:
            file = self.session.get(File, issue.file_id)
            if file:
                # Truncate long files
                content = file.content[:2000] + "..." if len(file.content) > 2000 else file.content
                file_context = f"\n\nFile: {file.name}\n```\n{content}\n```"

        issue_description = f"""Issue: {issue.title}

Severity: {issue.severity}
Category: {issue.category}

Description: {issue.description}

File: {issue.file_name or 'N/A'}
Lines: {issue.line_start}-{issue.line_end if issue.line_end else issue.line_start}
{file_context}"""

        # Prosecutor's argument
        prosecutor_messages = [
            LLMMessage(role="system", content=self.PROSECUTOR_PROMPT),
            LLMMessage(role="user", content=f"Argumentuj, dlaczego ten problem jest poważny:\n\n{issue_description}")
        ]

        prosecutor_response, _, _ = await provider_router.generate(
            messages=prosecutor_messages,
            provider_name=provider_name,
            model=model,
            temperature=0.2,
            max_tokens=512  # Reduced for faster debate
        )

        prosecutor_msg = Message(
            conversation_id=conversation.id,
            sender_type="agent",
            sender_name="Prosecutor",
            turn_index=0,
            content=prosecutor_response,
            is_summary=False
        )
        self.session.add(prosecutor_msg)
        self.session.commit()

        # Defender's counterargument
        defender_messages = [
            LLMMessage(role="system", content=self.DEFENDER_PROMPT),
            LLMMessage(role="user", content=f"Dostarcz kontekst i argumentuj za rozsądną interpretacją:\n\n{issue_description}\n\nArgument Prokuratora:\n{prosecutor_response}")
        ]

        defender_response, _, _ = await provider_router.generate(
            messages=defender_messages,
            provider_name=provider_name,
            model=model,
            temperature=0.2,
            max_tokens=512  # Reduced for faster debate
        )

        defender_msg = Message(
            conversation_id=conversation.id,
            sender_type="agent",
            sender_name="Defender",
            turn_index=1,
            content=defender_response,
            is_summary=False
        )
        self.session.add(defender_msg)
        self.session.commit()

        # Moderator's verdict
        await self._arena_moderator_verdict(
            conversation, issue, prosecutor_response, defender_response,
            provider_name, model
        )

    async def _council_moderator_synthesis(
        self,
        conversation: Conversation,
        context: str,
        provider_name: str | None,
        model: str | None
    ):
        """Generate moderator synthesis for council mode.

        IMPORTANT: Moderator ONLY analyzes agent discussions, NOT code directly.
        The moderator synthesizes insights from agent perspectives into structured output.

        Args:
            conversation: Conversation object
            context: Code context (NOT used by moderator - only for reference)
            provider_name: LLM provider
            model: Model name
        """
        discussion_history = self._get_conversation_history(conversation)

        # FIXED: Moderator receives ONLY agent discussions, NOT code
        # This follows specification requirement: "Moderator NIE analizuje kodu bezpośrednio"
        messages = [
            LLMMessage(role="system", content=self.MODERATOR_COUNCIL_PROMPT),
            LLMMessage(role="user", content=f"Dyskusja agentów:\n{discussion_history}\n\nDostarcz swoją syntezę w formacie JSON:")
        ]

        logger.info(f"🎭 MODERATOR SYNTHESIS | Mode: council | Discussion length: {len(discussion_history)} chars")

        response, _, _ = await provider_router.generate(
            messages=messages,
            provider_name=provider_name,
            model=model,
            temperature=0.0,  # Deterministic
            max_tokens=1024  # Reduced for faster synthesis
        )

        # Parse and store summary
        try:
            data = json.loads(response)
            summary_obj = CouncilSummarySchema(**data)
            summary_text = json.dumps(data, indent=2)
        except json.JSONDecodeError as e:
            logger.warning(f"Council summary JSON decode error: {str(e)[:200]}")
            logger.debug(f"Raw response preview: {response[:500]}...")
            # Fallback
            summary_text = response
        except ValidationError as e:
            logger.error(f"Council summary validation error: {e.errors()}")
            # Fallback
            summary_text = response

        conversation.summary = summary_text

        # Store moderator message
        message = Message(
            conversation_id=conversation.id,
            sender_type="moderator",
            sender_name="Moderator",
            turn_index=999,
            content=response,
            is_summary=True
        )
        self.session.add(message)
        self.session.add(conversation)
        self.session.commit()

    async def _arena_moderator_verdict(
        self,
        conversation: Conversation,
        issue: Issue,
        prosecutor_arg: str,
        defender_arg: str,
        provider_name: str | None,
        model: str | None
    ):
        """Generate moderator verdict for arena mode.

        Args:
            conversation: Conversation object
            issue: Issue being debated
            prosecutor_arg: Prosecutor's argument
            defender_arg: Defender's argument
            provider_name: LLM provider
            model: Model name
        """
        messages = [
            LLMMessage(role="system", content=self.MODERATOR_ARENA_PROMPT),
            LLMMessage(role="user", content=f"""Issue: {issue.title}
Current Severity: {issue.severity}

Prosecutor's Argument:
{prosecutor_arg}

Defender's Argument:
{defender_arg}

Render your verdict as JSON:""")
        ]

        response, _, _ = await provider_router.generate(
            messages=messages,
            provider_name=provider_name,
            model=model,
            temperature=0.0,
            max_tokens=512  # Reduced for faster verdict
        )

        # Parse verdict and update issue
        try:
            data = json.loads(response)
            verdict = ArenaVerdictSchema(**data)

            # Update issue with verdict
            issue.confirmed = verdict.confirmed
            issue.final_severity = verdict.final_severity  # type: ignore
            issue.moderator_comment = verdict.moderator_comment

            if not verdict.keep_issue:
                issue.status = "dismissed"

            self.session.add(issue)

        except json.JSONDecodeError as e:
            logger.warning(f"Arena verdict JSON decode error: {str(e)[:200]}")
            logger.debug(f"Raw verdict response preview: {verdict_response[:500]}...")
            # Keep original issue state if parsing fails
        except ValidationError as e:
            logger.error(f"Arena verdict validation error: {e.errors()}")
            # Keep original issue state if parsing fails

        # Store verdict as summary
        conversation.summary = response

        # Store moderator message
        message = Message(
            conversation_id=conversation.id,
            sender_type="moderator",
            sender_name="Moderator",
            turn_index=2,
            content=response,
            is_summary=True
        )
        self.session.add(message)
        self.session.add(conversation)
        self.session.commit()

    async def _build_context(self, conversation: Conversation) -> str:
        """Build code context for conversation.

        Args:
            conversation: Conversation object

        Returns:
            Context string
        """
        review = self.session.get(Review, conversation.review_id)
        if not review:
            return "No context available"

        project = self.session.get(Project, review.project_id)
        if not project:
            return "No context available"

        # Get files
        statement = select(File).where(File.project_id == project.id).limit(5)
        files = self.session.exec(statement).all()

        context = f"Project: {project.name}\n\n"

        if conversation.topic_type == "file" and conversation.topic_id:
            # Focus on specific file
            file = self.session.get(File, conversation.topic_id)
            if file:
                content = file.content[:3000] + "..." if len(file.content) > 3000 else file.content
                context += f"File: {file.name}\n```\n{content}\n```\n"
        else:
            # Include multiple files
            for file in files:
                content = file.content[:1000] + "..." if len(file.content) > 1000 else file.content
                context += f"\nFile: {file.name}\n```\n{content}\n```\n"

        return context

    def _get_conversation_history(self, conversation: Conversation) -> str:
        """Get conversation history as string.

        Args:
            conversation: Conversation object

        Returns:
            History string
        """
        statement = (
            select(Message)
            .where(Message.conversation_id == conversation.id)
            .where(Message.is_summary == False)
            .order_by(Message.turn_index)
        )
        messages = self.session.exec(statement).all()

        history = []
        for msg in messages:
            history.append(f"{msg.sender_name}: {msg.content}")

        return "\n\n".join(history) if history else "No discussion yet"
