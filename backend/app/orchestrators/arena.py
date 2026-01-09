"""Orkiestrator dla Combat Arena - porównywanie pełnych schematów review.

Combat Arena pozwala użytkownikowi porównać dwa kompletne schematy konfiguracji:
- Schemat A: pełna konfiguracja dla wszystkich 4 ról
- Schemat B: pełna konfiguracja dla wszystkich 4 ról

Orkiestrator:
1. Tworzy ArenaSession
2. Uruchamia dwa osobne review (A i B) równolegle
3. Po zakończeniu czeka na głosowanie użytkownika
4. Aktualizuje rankingi ELO na podstawie wyniku
"""
import logging
import hashlib
import json
import asyncio
from datetime import datetime
from sqlmodel import Session, select
from app.models.arena import ArenaSession, SchemaRating
from app.models.review import Review, ReviewAgent, AgentConfig
from app.orchestrators.review import ReviewOrchestrator
from app.utils.elo import elo_update, get_k_factor
from app.providers.router import CustomProviderConfig

logger = logging.getLogger(__name__)


class ArenaOrchestrator:
    """Orkiestrator dla Combat Arena mode.

    Odpowiedzialny za:
    - Tworzenie sesji Arena
    - Uruchamianie dwóch równoległych review (Schemat A i B)
    - Zbieranie wyników i głosów
    - Aktualizację rankingów ELO
    """

    def __init__(self, session: Session):
        """Inicjalizacja orkiestratora.

        Args:
            session: Sesja bazodanowa SQLModel
        """
        self.session = session
        self.review_orchestrator = ReviewOrchestrator(session)

    async def conduct_arena(
        self,
        arena_session_id: int,
        api_keys: dict[str, str] | None = None
    ) -> ArenaSession:
        """Przeprowadź sesję Arena - uruchom dwa review i porównaj wyniki.

        Proces:
        1. Pobierz ArenaSession z bazy
        2. Utwórz Review dla Schematu A
        3. Utwórz Review dla Schematu B
        4. Uruchom oba review RÓWNOLEGLE (dla szybkości)
        5. Oznacz sesję jako ukończoną (czeka na głosowanie)

        Args:
            arena_session_id: ID sesji Arena
            api_keys: Opcjonalne klucze API dla providerów

        Returns:
            Zaktualizowana ArenaSession

        Raises:
            ValueError: Jeśli sesja nie istnieje
        """
        # Walidacja: czy sesja istnieje
        arena_session = self.session.get(ArenaSession, arena_session_id)
        if not arena_session:
            raise ValueError(f"Arena session {arena_session_id} nie istnieje")

        # Oznacz jako running
        arena_session.status = "running"
        self.session.add(arena_session)
        self.session.commit()

        logger.info(f"Arena session {arena_session_id} rozpoczęta - uruchamiam review A i B")

        try:
            # Uruchom oba review równolegle (dla szybkości)
            review_a_task = self._create_and_run_review(
                arena_session=arena_session,
                schema_name="A",
                schema_config=arena_session.schema_a_config,
                api_keys=api_keys
            )

            review_b_task = self._create_and_run_review(
                arena_session=arena_session,
                schema_name="B",
                schema_config=arena_session.schema_b_config,
                api_keys=api_keys
            )

            # Czekaj na oba review (równolegle)
            review_a, review_b = await asyncio.gather(
                review_a_task,
                review_b_task,
                return_exceptions=True  # Nie crashuj jeśli jeden z nich failuje
            )

            # Sprawdź czy były błędy
            if isinstance(review_a, Exception):
                logger.error(f"Review A failed: {review_a}")
                arena_session.status = "failed"
                arena_session.error_message = f"Schema A failed: {str(review_a)[:1000]}"
                self.session.add(arena_session)
                self.session.commit()
                return arena_session

            if isinstance(review_b, Exception):
                logger.error(f"Review B failed: {review_b}")
                arena_session.status = "failed"
                arena_session.error_message = f"Schema B failed: {str(review_b)[:1000]}"
                self.session.add(arena_session)
                self.session.commit()
                return arena_session

            # Zapisz ID review
            arena_session.review_a_id = review_a.id
            arena_session.review_b_id = review_b.id

            # Oznacz jako completed (czeka na głosowanie)
            arena_session.status = "completed"
            arena_session.completed_at = datetime.utcnow()

            logger.info(
                f"Arena session {arena_session_id} zakończona - "
                f"Review A: {review_a.id}, Review B: {review_b.id}"
            )

        except Exception as e:
            # Obsługa nieoczekiwanych błędów
            logger.error(f"Arena session {arena_session_id} failed: {e}", exc_info=True)
            arena_session.status = "failed"
            arena_session.error_message = str(e)[:2000]

        # Zapisz zmiany
        self.session.add(arena_session)
        self.session.commit()
        self.session.refresh(arena_session)

        return arena_session

    async def _create_and_run_review(
        self,
        arena_session: ArenaSession,
        schema_name: str,
        schema_config: dict,
        api_keys: dict[str, str] | None
    ) -> Review:
        """Utwórz i uruchom review dla jednego schematu.

        Proces:
        1. Utwórz Review z odpowiednimi polami Arena
        2. Utwórz ReviewAgent dla każdej roli (general, security, performance, style)
        3. Uruchom review przez ReviewOrchestrator
        4. Zwróć ukończony Review

        Args:
            arena_session: Sesja Arena
            schema_name: Nazwa schematu ("A" lub "B")
            schema_config: Konfiguracja schematu (dict z 4 rolami)
            api_keys: Klucze API dla providerów

        Returns:
            Ukończony Review

        Raises:
            Exception: Jeśli review failuje
        """
        logger.info(f"Tworzę review dla schematu {schema_name}")

        # Walidacja: czy schemat ma wszystkie 4 role
        required_roles = {"general", "security", "performance", "style"}
        provided_roles = set(schema_config.keys())
        if provided_roles != required_roles:
            raise ValueError(
                f"Schema {schema_name} musi mieć wszystkie 4 role. "
                f"Brakuje: {required_roles - provided_roles}, "
                f"Nadmiarowe: {provided_roles - required_roles}"
            )

        # 1. Utwórz Review
        review = Review(
            project_id=arena_session.project_id,
            created_by=arena_session.created_by,
            status="pending",
            review_mode="combat_arena",
            arena_schema_name=schema_name,
            arena_session_id=arena_session.id
        )
        self.session.add(review)
        self.session.commit()
        self.session.refresh(review)

        logger.info(f"Review {review.id} utworzony dla schematu {schema_name}")

        # 2. Utwórz ReviewAgent dla każdej roli
        agent_configs_typed = {}
        for role, config_dict in schema_config.items():
            # Walidacja: czy config ma wymagane pola
            if "provider" not in config_dict or "model" not in config_dict:
                raise ValueError(
                    f"Config dla roli {role} w schemacie {schema_name} "
                    f"musi mieć 'provider' i 'model'"
                )

            # Utwórz ReviewAgent
            agent = ReviewAgent(
                review_id=review.id,
                role=role,
                provider=config_dict["provider"],
                model=config_dict["model"]
            )
            self.session.add(agent)

            # Przygotuj AgentConfig dla orkiestratora
            agent_config = AgentConfig(**config_dict)
            agent_configs_typed[role] = agent_config

        self.session.commit()

        logger.info(f"Review {review.id}: utworzono {len(agent_configs_typed)} agentów")

        # 3. Uruchom review
        try:
            await self.review_orchestrator.conduct_review(
                review_id=review.id,
                provider_name=None,  # Każdy agent ma własną konfigurację
                model=None,
                api_keys=api_keys,
                agent_configs=agent_configs_typed
            )
        except Exception as e:
            logger.error(f"Review {review.id} (schema {schema_name}) failed: {e}")
            raise

        # Odśwież review z najnowszymi danymi
        self.session.refresh(review)

        logger.info(
            f"Review {review.id} (schema {schema_name}) zakończony - "
            f"status: {review.status}"
        )

        return review

    async def submit_vote(
        self,
        arena_session_id: int,
        winner: str,  # "A", "B", "tie"
        voter_id: int,
        comment: str | None = None
    ) -> ArenaSession:
        """Zapisz głos i zaktualizuj rankingi ELO.

        Proces:
        1. Waliduj sesję i głos
        2. Zapisz wynik głosowania
        3. Zaktualizuj rankingi ELO dla obu schematów
        4. Zwróć zaktualizowaną sesję

        Args:
            arena_session_id: ID sesji Arena
            winner: Zwycięzca ("A", "B", "tie")
            voter_id: ID użytkownika głosującego
            comment: Opcjonalny komentarz

        Returns:
            Zaktualizowana ArenaSession

        Raises:
            ValueError: Jeśli sesja nie istnieje lub głos jest nieprawidłowy
        """
        # Walidacja: czy sesja istnieje
        arena_session = self.session.get(ArenaSession, arena_session_id)
        if not arena_session:
            raise ValueError(f"Arena session {arena_session_id} nie istnieje")

        # Walidacja: czy sesja jest completed
        if arena_session.status != "completed":
            raise ValueError(
                f"Nie można głosować - sesja ma status '{arena_session.status}', "
                f"wymagany 'completed'"
            )

        # Walidacja: czy już zagłosowano
        if arena_session.winner is not None:
            raise ValueError(
                f"W tej sesji już zagłosowano - zwycięzca: {arena_session.winner}"
            )

        # Walidacja: czy winner jest prawidłowy
        if winner not in ["A", "B", "tie"]:
            raise ValueError(f"Winner musi być 'A', 'B' lub 'tie', otrzymano: {winner}")

        logger.info(
            f"Arena session {arena_session_id}: zapisuję głos - "
            f"zwycięzca: {winner}, voter: {voter_id}"
        )

        # Zapisz wynik głosowania
        arena_session.winner = winner
        arena_session.vote_comment = comment
        arena_session.voter_id = voter_id
        arena_session.voted_at = datetime.utcnow()
        self.session.add(arena_session)
        self.session.commit()

        # Zaktualizuj rankingi ELO
        try:
            await self._update_schema_ratings(
                schema_a_config=arena_session.schema_a_config,
                schema_b_config=arena_session.schema_b_config,
                winner=winner
            )
            logger.info(f"Arena session {arena_session_id}: rankingi ELO zaktualizowane")
        except Exception as e:
            logger.error(
                f"Arena session {arena_session_id}: "
                f"nie udało się zaktualizować rankingów: {e}",
                exc_info=True
            )
            # Nie failuj całego głosowania jeśli ELO nie działa

        self.session.refresh(arena_session)
        return arena_session

    async def _update_schema_ratings(
        self,
        schema_a_config: dict,
        schema_b_config: dict,
        winner: str
    ):
        """Zaktualizuj rankingi ELO dla obu schematów.

        Używa algorytmu ELO do obliczenia nowych ratingów na podstawie wyniku.
        K-factor zależy od liczby rozegranych gier (nowe schematy mają wyższy K-factor).

        Args:
            schema_a_config: Konfiguracja Schematu A
            schema_b_config: Konfiguracja Schematu B
            winner: Zwycięzca ("A", "B", "tie")
        """
        # Generuj hash dla każdego schematu (identyfikacja)
        hash_a = self._compute_schema_hash(schema_a_config)
        hash_b = self._compute_schema_hash(schema_b_config)

        logger.info(f"Aktualizuję rankingi ELO - Hash A: {hash_a[:8]}..., Hash B: {hash_b[:8]}...")

        # Pobierz lub utwórz rating dla każdego schematu
        rating_a = self._get_or_create_schema_rating(hash_a, schema_a_config)
        rating_b = self._get_or_create_schema_rating(hash_b, schema_b_config)

        # Oblicz K-factor (zależy od doświadczenia)
        k_a = get_k_factor(rating_a.games_played)
        k_b = get_k_factor(rating_b.games_played)
        k_factor = (k_a + k_b) / 2  # Średni K-factor

        logger.info(
            f"ELO przed: A={rating_a.elo_rating:.0f}, B={rating_b.elo_rating:.0f}, "
            f"K={k_factor:.1f}"
        )

        # Oblicz nowe ratingi
        result_for_elo = f"candidate_{winner.lower()}"  # "candidate_a", "candidate_b", "tie"
        new_rating_a, new_rating_b = elo_update(
            rating_a=rating_a.elo_rating,
            rating_b=rating_b.elo_rating,
            result=result_for_elo,
            k_factor=k_factor
        )

        # Zaktualizuj rating A
        rating_a.elo_rating = new_rating_a
        rating_a.games_played += 1
        if winner == "A":
            rating_a.wins += 1
        elif winner == "B":
            rating_a.losses += 1
        else:  # tie
            rating_a.ties += 1
        rating_a.updated_at = datetime.utcnow()
        rating_a.last_used_at = datetime.utcnow()

        # Zaktualizuj rating B
        rating_b.elo_rating = new_rating_b
        rating_b.games_played += 1
        if winner == "B":
            rating_b.wins += 1
        elif winner == "A":
            rating_b.losses += 1
        else:  # tie
            rating_b.ties += 1
        rating_b.updated_at = datetime.utcnow()
        rating_b.last_used_at = datetime.utcnow()

        # Zapisz zmiany
        self.session.add(rating_a)
        self.session.add(rating_b)
        self.session.commit()

        logger.info(
            f"ELO po: A={new_rating_a:.0f} ({rating_a.wins}W-{rating_a.losses}L-{rating_a.ties}T), "
            f"B={new_rating_b:.0f} ({rating_b.wins}W-{rating_b.losses}L-{rating_b.ties}T)"
        )

    def _compute_schema_hash(self, schema_config: dict) -> str:
        """Oblicz SHA-256 hash dla konfiguracji schematu.

        Hash jest używany jako unikalny identyfikator schematu.
        Posortowanie kluczy zapewnia, że identyczna konfiguracja
        zawsze da ten sam hash.

        Args:
            schema_config: Konfiguracja schematu

        Returns:
            64-znakowy hash hex
        """
        # Posortuj klucze dla konsystencji
        config_json = json.dumps(schema_config, sort_keys=True)
        hash_obj = hashlib.sha256(config_json.encode())
        return hash_obj.hexdigest()

    def _get_or_create_schema_rating(
        self,
        schema_hash: str,
        schema_config: dict
    ) -> SchemaRating:
        """Pobierz lub utwórz rating dla schematu.

        Args:
            schema_hash: Hash schematu (identyfikator)
            schema_config: Pełna konfiguracja schematu

        Returns:
            SchemaRating (istniejący lub nowo utworzony)
        """
        # Sprawdź czy rating już istnieje
        stmt = select(SchemaRating).where(SchemaRating.schema_hash == schema_hash)
        rating = self.session.exec(stmt).first()

        if rating:
            logger.debug(f"Rating istnieje: hash={schema_hash[:8]}..., ELO={rating.elo_rating:.0f}")
            return rating

        # Utwórz nowy rating (start: 1500 ELO)
        rating = SchemaRating(
            schema_hash=schema_hash,
            schema_config=schema_config,
            elo_rating=1500.0,
            games_played=0,
            wins=0,
            losses=0,
            ties=0
        )
        self.session.add(rating)
        self.session.commit()
        self.session.refresh(rating)

        logger.info(f"Utworzono nowy rating: hash={schema_hash[:8]}..., ELO=1500.0")

        return rating
