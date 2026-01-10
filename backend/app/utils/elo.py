"""ELO rating calculation utilities."""


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


def elo_update(
    rating_a: float,
    rating_b: float,
    result: str,
    games_played_a: int,
    games_played_b: int
) -> tuple[float, float]:
    """Calculate new ELO ratings after a match.

    Args:
        rating_a: Current ELO rating of player A
        rating_b: Current ELO rating of player B
        result: Match result ("candidate_a", "candidate_b", "tie")
        games_played_a: Games played by player A
        games_played_b: Games played by player B

    Returns:
        Tuple of (new_rating_a, new_rating_b)
    """
    k_a = get_k_factor(games_played_a)
    k_b = get_k_factor(games_played_b)

    if result == "tie":
        base_delta = 5.0
        if rating_a == rating_b:
            return rating_a, rating_b
        if rating_a < rating_b:
            return rating_a + base_delta * (k_a / 32.0), rating_b - base_delta * (k_b / 32.0)
        return rating_a - base_delta * (k_a / 32.0), rating_b + base_delta * (k_b / 32.0)

    base_delta = 20.0
    if result == "candidate_a":
        return rating_a + base_delta * (k_a / 32.0), rating_b - base_delta * (k_b / 32.0)

    return rating_a - base_delta * (k_a / 32.0), rating_b + base_delta * (k_b / 32.0)


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
