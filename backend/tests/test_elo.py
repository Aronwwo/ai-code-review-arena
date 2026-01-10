"""Unit tests for ELO calculation utilities (spec-based)."""
from app.utils.elo import elo_update, get_k_factor


def test_win_loss_fixed_delta_default_k():
    """Winner gets +20, loser -20 with default K=32."""
    new_a, new_b = elo_update(1500.0, 1500.0, "candidate_a", games_played_a=10, games_played_b=10)
    assert new_a == 1520.0
    assert new_b == 1480.0


def test_draw_fixed_delta_default_k_with_favorite_penalty():
    """Draw penalizes the favorite and rewards the underdog by 5 points (K=32)."""
    new_a, new_b = elo_update(1600.0, 1400.0, "tie", games_played_a=10, games_played_b=10)
    assert new_a == 1595.0
    assert new_b == 1405.0


def test_dynamic_k_factor_scales_delta():
    """New players get larger rating swings than experienced ones."""
    # Player A is new (K=40), player B is experienced (K=24)
    new_a, new_b = elo_update(1500.0, 1500.0, "candidate_a", games_played_a=0, games_played_b=40)
    assert new_a == 1525.0
    assert new_b == 1485.0


def test_get_k_factor_thresholds():
    """K-factor follows spec thresholds."""
    assert get_k_factor(0) == 40.0
    assert get_k_factor(9) == 40.0
    assert get_k_factor(10) == 32.0
    assert get_k_factor(29) == 32.0
    assert get_k_factor(30) == 24.0
