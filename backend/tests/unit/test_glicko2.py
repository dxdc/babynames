"""Unit tests for the Glicko-2 rating algorithm."""

import pytest
from babynames.ranking.glicko2 import (
    INITIAL_MU,
    INITIAL_PHI,
    INITIAL_SIGMA,
    Rating,
    update,
    win_probability,
)


class TestRating:
    def test_defaults(self):
        r = Rating()
        assert r.mu == INITIAL_MU
        assert r.phi == INITIAL_PHI
        assert r.sigma == INITIAL_SIGMA

    def test_settled_high_rd(self):
        r = Rating(phi=350.0)
        assert not r.settled

    def test_settled_low_rd(self):
        r = Rating(phi=50.0)
        assert r.settled


class TestUpdate:
    def test_winner_rating_increases(self):
        player = Rating()
        opponent = Rating()
        result = update(player, opponent, score=1.0)
        assert result.mu > INITIAL_MU

    def test_loser_rating_decreases(self):
        player = Rating()
        opponent = Rating()
        result = update(player, opponent, score=0.0)
        assert result.mu < INITIAL_MU

    def test_rd_decreases_after_match(self):
        player = Rating()
        opponent = Rating()
        result = update(player, opponent, score=1.0)
        assert result.phi < INITIAL_PHI

    def test_upset_win_larger_change(self):
        """Beating a much higher-rated opponent should give a larger boost."""
        weak = Rating(mu=1200.0)
        strong = Rating(mu=1800.0)
        result = update(weak, strong, score=1.0)
        # Beating someone 600 points higher should produce a big increase
        assert result.mu > 1300.0

    def test_expected_win_small_change(self):
        """Beating a much weaker opponent should give a small boost."""
        strong = Rating(mu=1800.0, phi=100.0)
        weak = Rating(mu=1200.0, phi=100.0)
        result = update(strong, weak, score=1.0)
        # Should increase but not by much
        assert result.mu > 1800.0
        assert result.mu < 1850.0

    def test_convergence_after_many_matches(self):
        """After many matches, RD should decrease significantly from initial 350."""
        player = Rating()
        opponent = Rating(mu=1500.0, phi=100.0)
        for _ in range(20):
            player = update(player, opponent, score=1.0)
        assert player.phi < INITIAL_PHI / 2  # Should at least halve from 350

    def test_volatility_stays_bounded(self):
        player = Rating()
        opponent = Rating()
        result = update(player, opponent, score=1.0)
        assert 0.01 < result.sigma < 0.15

    def test_symmetric_results(self):
        """Winner's gain and loser's loss should be roughly symmetric for equal players."""
        a = Rating()
        b = Rating()
        a_after = update(a, b, score=1.0)
        b_after = update(b, a, score=0.0)
        gain = a_after.mu - INITIAL_MU
        loss = INITIAL_MU - b_after.mu
        assert abs(gain - loss) < 5.0  # Allow small asymmetry from volatility


class TestWinProbability:
    def test_equal_players(self):
        a = Rating()
        b = Rating()
        prob = win_probability(a, b)
        assert abs(prob - 0.5) < 0.01

    def test_stronger_player_favoured(self):
        strong = Rating(mu=1800.0)
        weak = Rating(mu=1200.0)
        assert win_probability(strong, weak) > 0.9

    def test_probability_bounded(self):
        a = Rating(mu=2000.0)
        b = Rating(mu=1000.0)
        prob = win_probability(a, b)
        assert 0.0 < prob < 1.0
