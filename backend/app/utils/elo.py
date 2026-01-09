"""ELO rating calculation utilities."""
import math


def get_result_value(choice: str, is_player_a: bool) -> float:
    """Convert vote choice to result value for a player.

    Args:
        choice: Vote choice ("candidate_a", "candidate_b", "tie")
        is_player_a: Whether we're calculating for player A

    Returns:
        1.0 for win, 0.5 for tie, 0.0 for loss
    """
    if choice == "tie":
        return 0.5

    if is_player_a:
        return 1.0 if choice == "candidate_a" else 0.0
    else:
        return 1.0 if choice == "candidate_b" else 0.0


def calculate_expected_score(rating_a: float, rating_b: float) -> tuple[float, float]:
    """Calculate expected scores for both players.

    Args:
        rating_a: ELO rating of player A
        rating_b: ELO rating of player B

    Returns:
        Tuple of (expected_a, expected_b)
    """
    expected_a = 1.0 / (1.0 + math.pow(10, (rating_b - rating_a) / 400.0))
    expected_b = 1.0 - expected_a
    return expected_a, expected_b


def elo_update(
    rating_a: float,
    rating_b: float,
    result: str,
    k_factor: float = 32.0
) -> tuple[float, float]:
    """Calculate new ELO ratings after a match.

    Args:
        rating_a: Current ELO rating of player A
        rating_b: Current ELO rating of player B
        result: Match result ("candidate_a", "candidate_b", "tie")
        k_factor: K-factor for rating adjustment (default 32)

    Returns:
        Tuple of (new_rating_a, new_rating_b)
    """
    # Calculate expected scores
    expected_a, expected_b = calculate_expected_score(rating_a, rating_b)

    # Get actual scores
    actual_a = get_result_value(result, is_player_a=True)
    actual_b = get_result_value(result, is_player_a=False)

    # Calculate new ratings
    new_rating_a = rating_a + k_factor * (actual_a - expected_a)
    new_rating_b = rating_b + k_factor * (actual_b - expected_b)

    return new_rating_a, new_rating_b


def get_k_factor(games_played: int) -> float:
    """Get K-factor based on number of games played.

    New players get higher K-factor for faster rating adjustment.

    Args:
        games_played: Number of games played

    Returns:
        K-factor value
    """
    if games_played < 10:
        return 40.0
    elif games_played < 30:
        return 32.0
    else:
        return 24.0
