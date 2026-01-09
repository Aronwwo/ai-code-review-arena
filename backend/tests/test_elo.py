"""Unit tests for ELO calculation utilities."""
import pytest
import math
from app.utils.elo import (
    get_result_value,
    calculate_expected_score,
    elo_update,
    get_k_factor
)


class TestGetResultValue:
    """Tests for get_result_value function."""

    def test_tie_returns_half_for_player_a(self):
        """Tie should return 0.5 for player A."""
        result = get_result_value("tie", is_player_a=True)
        assert result == 0.5

    def test_tie_returns_half_for_player_b(self):
        """Tie should return 0.5 for player B."""
        result = get_result_value("tie", is_player_a=False)
        assert result == 0.5

    def test_player_a_wins(self):
        """Player A winning should return 1.0 for A, 0.0 for B."""
        result_a = get_result_value("candidate_a", is_player_a=True)
        result_b = get_result_value("candidate_a", is_player_a=False)
        assert result_a == 1.0
        assert result_b == 0.0

    def test_player_b_wins(self):
        """Player B winning should return 0.0 for A, 1.0 for B."""
        result_a = get_result_value("candidate_b", is_player_a=True)
        result_b = get_result_value("candidate_b", is_player_a=False)
        assert result_a == 0.0
        assert result_b == 1.0


class TestCalculateExpectedScore:
    """Tests for calculate_expected_score function."""

    def test_equal_ratings_give_fifty_percent(self):
        """Equal ratings should give 50% expected score for both."""
        expected_a, expected_b = calculate_expected_score(1500.0, 1500.0)
        assert abs(expected_a - 0.5) < 0.001
        assert abs(expected_b - 0.5) < 0.001

    def test_higher_rating_gives_higher_expectation(self):
        """Higher rated player should have higher expected score."""
        expected_a, expected_b = calculate_expected_score(1600.0, 1400.0)
        assert expected_a > 0.5
        assert expected_b < 0.5
        assert abs(expected_a + expected_b - 1.0) < 0.001

    def test_lower_rating_gives_lower_expectation(self):
        """Lower rated player should have lower expected score."""
        expected_a, expected_b = calculate_expected_score(1400.0, 1600.0)
        assert expected_a < 0.5
        assert expected_b > 0.5
        assert abs(expected_a + expected_b - 1.0) < 0.001

    def test_large_rating_difference(self):
        """Large rating difference should give very skewed expectations."""
        expected_a, expected_b = calculate_expected_score(2000.0, 1200.0)
        assert expected_a > 0.95
        assert expected_b < 0.05

    def test_expected_scores_sum_to_one(self):
        """Expected scores should always sum to 1.0."""
        test_cases = [
            (1500.0, 1500.0),
            (1600.0, 1400.0),
            (2100.0, 1300.0),
            (1000.0, 2000.0),
        ]
        for rating_a, rating_b in test_cases:
            expected_a, expected_b = calculate_expected_score(rating_a, rating_b)
            assert abs(expected_a + expected_b - 1.0) < 0.001


class TestEloUpdate:
    """Tests for elo_update function."""

    def test_equal_ratings_winner_gains_expected_gains_loser_loses(self):
        """With equal ratings, winner should gain and loser should lose."""
        new_a, new_b = elo_update(1500.0, 1500.0, "candidate_a", k_factor=32.0)
        assert new_a > 1500.0
        assert new_b < 1500.0
        # Should gain/lose approximately 16 points (32 * (1 - 0.5))
        assert abs(new_a - 1516.0) < 0.1
        assert abs(new_b - 1484.0) < 0.1

    def test_tie_with_equal_ratings_no_change(self):
        """Tie with equal ratings should not change ratings."""
        new_a, new_b = elo_update(1500.0, 1500.0, "tie", k_factor=32.0)
        assert abs(new_a - 1500.0) < 0.001
        assert abs(new_b - 1500.0) < 0.001

    def test_underdog_wins_gains_more_points(self):
        """Underdog winning should gain more points than favorite would."""
        # Lower rated player wins
        new_a_underdog, new_b_favorite = elo_update(1400.0, 1600.0, "candidate_a", k_factor=32.0)
        gain_underdog = new_a_underdog - 1400.0

        # Higher rated player wins
        new_a_favorite, new_b_underdog = elo_update(1600.0, 1400.0, "candidate_a", k_factor=32.0)
        gain_favorite = new_a_favorite - 1600.0

        assert gain_underdog > gain_favorite

    def test_favorite_loses_loses_more_points(self):
        """Favorite losing should lose more points than underdog would."""
        # Higher rated player loses
        new_a_favorite, new_b_underdog = elo_update(1600.0, 1400.0, "candidate_b", k_factor=32.0)
        loss_favorite = 1600.0 - new_a_favorite

        # Lower rated player loses
        new_a_underdog, new_b_favorite = elo_update(1400.0, 1600.0, "candidate_b", k_factor=32.0)
        loss_underdog = 1400.0 - new_a_underdog

        assert loss_favorite > loss_underdog

    def test_k_factor_scales_rating_change(self):
        """Higher K-factor should result in larger rating changes."""
        new_a_k16, new_b_k16 = elo_update(1500.0, 1500.0, "candidate_a", k_factor=16.0)
        new_a_k32, new_b_k32 = elo_update(1500.0, 1500.0, "candidate_a", k_factor=32.0)

        change_k16 = new_a_k16 - 1500.0
        change_k32 = new_a_k32 - 1500.0

        assert abs(change_k32) > abs(change_k16)
        assert abs(change_k32 / change_k16 - 2.0) < 0.01  # Should be approximately 2x

    def test_rating_conservation(self):
        """Total rating points should be conserved (zero-sum)."""
        test_cases = [
            (1500.0, 1500.0, "candidate_a"),
            (1600.0, 1400.0, "candidate_b"),
            (2000.0, 1200.0, "tie"),
        ]
        for rating_a, rating_b, result in test_cases:
            new_a, new_b = elo_update(rating_a, rating_b, result, k_factor=32.0)
            old_total = rating_a + rating_b
            new_total = new_a + new_b
            assert abs(old_total - new_total) < 0.001


class TestGetKFactor:
    """Tests for get_k_factor function."""

    def test_new_player_gets_high_k_factor(self):
        """New players (< 10 games) should get K=40."""
        for games in range(10):
            k = get_k_factor(games)
            assert k == 40.0

    def test_intermediate_player_gets_medium_k_factor(self):
        """Intermediate players (10-29 games) should get K=32."""
        for games in range(10, 30):
            k = get_k_factor(games)
            assert k == 32.0

    def test_experienced_player_gets_low_k_factor(self):
        """Experienced players (30+ games) should get K=24."""
        for games in [30, 50, 100, 1000]:
            k = get_k_factor(games)
            assert k == 24.0

    def test_boundary_cases(self):
        """Test boundary values."""
        assert get_k_factor(9) == 40.0
        assert get_k_factor(10) == 32.0
        assert get_k_factor(29) == 32.0
        assert get_k_factor(30) == 24.0


class TestEloIntegration:
    """Integration tests for complete ELO rating scenarios."""

    def test_tournament_scenario(self):
        """Simulate a mini-tournament and verify ratings behave correctly."""
        # Three schemas with equal starting ratings
        ratings = {"schema_a": 1500.0, "schema_b": 1500.0, "schema_c": 1500.0}

        # Schema A beats B
        ratings["schema_a"], ratings["schema_b"] = elo_update(
            ratings["schema_a"], ratings["schema_b"], "candidate_a", k_factor=32.0
        )

        # Schema A beats C
        ratings["schema_a"], ratings["schema_c"] = elo_update(
            ratings["schema_a"], ratings["schema_c"], "candidate_a", k_factor=32.0
        )

        # Schema B beats C
        ratings["schema_b"], ratings["schema_c"] = elo_update(
            ratings["schema_b"], ratings["schema_c"], "candidate_a", k_factor=32.0
        )

        # Verify ranking: A > B > C
        assert ratings["schema_a"] > ratings["schema_b"]
        assert ratings["schema_b"] > ratings["schema_c"]
        assert ratings["schema_a"] > 1500.0
        assert ratings["schema_c"] < 1500.0

    def test_rating_stability_over_many_ties(self):
        """Many ties should not significantly change ratings."""
        rating_a, rating_b = 1500.0, 1500.0

        # Simulate 100 ties
        for _ in range(100):
            rating_a, rating_b = elo_update(rating_a, rating_b, "tie", k_factor=32.0)

        # Ratings should remain essentially unchanged
        assert abs(rating_a - 1500.0) < 0.01
        assert abs(rating_b - 1500.0) < 0.01

    def test_rating_convergence(self):
        """Ratings should converge to reflect true strength over time."""
        # Start with equal ratings but simulate consistent performance difference
        rating_a, rating_b = 1500.0, 1500.0

        # Player A wins 80% of matches (distributed throughout)
        # Use a pattern that distributes wins/losses more evenly
        import random
        random.seed(42)  # Reproducible results
        results = ["candidate_a"] * 80 + ["candidate_b"] * 20
        random.shuffle(results)

        for i, result in enumerate(results):
            k = get_k_factor(i)
            rating_a, rating_b = elo_update(
                rating_a, rating_b, result, k_factor=k
            )

        # Player A (stronger, 80% win rate) should have significantly higher rating than B (20% win rate)
        assert rating_a > rating_b
        assert rating_a - rating_b > 150  # Should have meaningful separation
