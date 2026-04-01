"""Glicko-2 rating system implementation.

Ported from glicko.js. Reference: https://www.glicko.net/glicko/glicko2.pdf

All functions operate on Glicko-1 scale values (mu ~1500, phi ~350)
and handle Glicko-2 conversion internally.
"""

import math
from dataclasses import dataclass

# Glicko-2 system constants
INITIAL_MU = 1500.0
INITIAL_PHI = 350.0  # Rating deviation (high = uncertain)
INITIAL_SIGMA = 0.06  # Volatility
TAU = 0.5  # Constrains volatility change
GLICKO2_SCALE = 173.7178  # ln(10)/400 inverted
CONVERGENCE_EPSILON = 1e-6
CONVERGENCE_PHI = 80.0  # RD below this = "settled"


@dataclass
class Rating:
    """A player's Glicko-2 rating state."""

    mu: float = INITIAL_MU
    phi: float = INITIAL_PHI
    sigma: float = INITIAL_SIGMA

    @property
    def settled(self) -> bool:
        """True if rating deviation is low enough to be considered stable."""
        return self.phi < CONVERGENCE_PHI


def _to_glicko2(mu: float, phi: float) -> tuple[float, float]:
    """Convert Glicko-1 to Glicko-2 scale."""
    return (mu - 1500.0) / GLICKO2_SCALE, phi / GLICKO2_SCALE


def _from_glicko2(mu2: float, phi2: float) -> tuple[float, float]:
    """Convert Glicko-2 back to Glicko-1 scale."""
    return mu2 * GLICKO2_SCALE + 1500.0, phi2 * GLICKO2_SCALE


def _g(phi: float) -> float:
    """g(phi) function."""
    return 1.0 / math.sqrt(1.0 + 3.0 * phi * phi / (math.pi * math.pi))


def _e(mu: float, mu_j: float, phi_j: float) -> float:
    """E(mu, mu_j, phi_j) — expected score."""
    return 1.0 / (1.0 + math.exp(-_g(phi_j) * (mu - mu_j)))


def update(player: Rating, opponent: Rating, score: float) -> Rating:
    """Update player rating after a single match.

    Args:
        player: Current player rating.
        opponent: Opponent rating.
        score: 1.0 = win, 0.0 = loss, 0.5 = draw.

    Returns:
        New Rating with updated mu, phi, sigma.
    """
    # Step 1: Convert to Glicko-2 scale
    p_mu, p_phi = _to_glicko2(player.mu, player.phi)
    o_mu, o_phi = _to_glicko2(opponent.mu, opponent.phi)

    # Step 2: Compute variance v
    g_phi = _g(o_phi)
    e_mu = _e(p_mu, o_mu, o_phi)
    v = 1.0 / (g_phi * g_phi * e_mu * (1.0 - e_mu))

    # Step 3: Compute estimated improvement delta
    delta = v * g_phi * (score - e_mu)

    # Step 4: Determine new volatility (Illinois algorithm)
    a = math.log(player.sigma * player.sigma)
    phi2 = p_phi * p_phi
    delta2 = delta * delta

    def f(x: float) -> float:
        ex = math.exp(x)
        d2v = delta2 - phi2 - v - ex
        denom = phi2 + v + ex
        term1 = (ex * d2v) / (2.0 * denom * denom)
        term2 = (x - a) / (TAU * TAU)
        return term1 - term2

    # Bisection
    big_a = a
    if delta2 > phi2 + v:
        big_b = math.log(delta2 - phi2 - v)
    else:
        k = 1
        while f(a - k * TAU) < 0:
            k += 1
        big_b = a - k * TAU

    f_a = f(big_a)
    f_b = f(big_b)

    while abs(big_b - big_a) > CONVERGENCE_EPSILON:
        c = big_a + (big_a - big_b) * f_a / (f_b - f_a)
        f_c = f(c)
        if f_c * f_b <= 0:
            big_a = big_b
            f_a = f_b
        else:
            f_a = f_a / 2.0
        big_b = c
        f_b = f_c

    new_sigma = math.exp(big_a / 2.0)

    # Step 5: Update rating deviation
    phi_star = math.sqrt(phi2 + new_sigma * new_sigma)

    # Step 6: Update rating and RD
    new_phi = 1.0 / math.sqrt(1.0 / (phi_star * phi_star) + 1.0 / v)
    new_mu = p_mu + new_phi * new_phi * g_phi * (score - e_mu)

    # Convert back to Glicko-1 scale
    final_mu, final_phi = _from_glicko2(new_mu, new_phi)

    return Rating(mu=final_mu, phi=final_phi, sigma=new_sigma)


def win_probability(player: Rating, opponent: Rating) -> float:
    """Expected probability that player beats opponent."""
    p_mu, _ = _to_glicko2(player.mu, player.phi)
    o_mu, o_phi = _to_glicko2(opponent.mu, opponent.phi)
    return _e(p_mu, o_mu, o_phi)
