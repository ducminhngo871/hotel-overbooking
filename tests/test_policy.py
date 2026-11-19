"""Sanity checks for the overbooking decision and backtest arithmetic."""
import numpy as np

from hotel_ob.policy import best_overbook, expected_curve, realized


def test_no_overbooking_means_no_gain():
    gain, walked = realized(100, [0, 0], [0.1, 0.0], [80, 80], w=3)
    assert np.allclose(gain, 0) and np.allclose(walked, 0)


def test_no_cancellations_means_no_overbooking():
    assert best_overbook(100, 0.0, w=3) == 0


def test_more_cancellations_more_overbooking():
    assert best_overbook(200, 0.15, w=3) > best_overbook(200, 0.05, w=3)


def test_higher_walk_cost_less_overbooking():
    assert best_overbook(200, 0.10, w=5) <= best_overbook(200, 0.10, w=1.5)


def test_newsvendor_quantile():
    """At the chosen x, P(late losses <= x) should be close to 1/(1+w)."""
    from scipy.stats import binom
    C, p, w = 200, 0.10, 3.0
    x = best_overbook(C, p, w)
    prob = binom.cdf(x, C + x, p)
    assert abs(prob - 1 / (1 + w)) < 0.08


def test_walking_costs_money():
    gain, walked = realized(100, [10], [0.0], [100], w=3)   # nobody cancels, 10 extra sold
    assert walked[0] == 10 and gain[0] == -10 * 3 * 100


def test_curve_starts_at_zero():
    curve = expected_curve(100, 0.1, 3)
    assert abs(curve.net_gain.iloc[0]) < 1e-9


# ---------------------------------------------------------------- clumping and service level
import pandas as pd  # noqa: E402
import pytest  # noqa: E402

from hotel_ob.policy import POLICIES, add_policy_inputs, backtest, estimate_clumping, loss_pmf, rolling_rate  # noqa: E402


@pytest.mark.parametrize("rho", [0.0, 0.02])
def test_loss_distribution_is_a_distribution(rho):
    pm = loss_pmf(200, 0.08, rho)
    k = np.arange(201)
    assert abs(pm.sum() - 1) < 1e-9
    assert abs((k * pm).sum() - 200 * 0.08) < 1e-6          # same mean either way


def test_clumping_widens_the_spread():
    k = np.arange(201)
    var = [((k - 16) ** 2 * loss_pmf(200, 0.08, r)).sum() for r in (0.0, 0.02)]
    expected = 200 * 0.08 * 0.92 * (1 + 199 * 0.02)
    assert var[1] > 3 * var[0] and abs(var[1] - expected) / expected < 0.01


def test_clumping_means_less_overbooking():
    assert best_overbook(220, 0.08, 3, rho=0.03) < best_overbook(220, 0.08, 3)


def test_service_level_limit_is_respected():
    for cap in (0.05, 0.2):
        x = best_overbook(220, 0.08, 3, max_walk_prob=cap)
        assert expected_curve(220, 0.08, 3).p_any_walk[x] <= cap
    assert best_overbook(220, 0.08, 3, max_walk_prob=0.05) <= best_overbook(220, 0.08, 3)


def _nights(days=120, seed=0, clumped=False):
    rng = np.random.default_rng(seed)
    night = pd.date_range("2016-01-01", periods=days)
    booked = np.full(days, 200)
    p = rng.beta(2, 23, days) if clumped else np.full(days, 0.08)    # clumped: the rate itself moves
    lost = rng.binomial(booked, p)
    return pd.DataFrame({"hotel": "H", "night": night, "booked": booked, "lost": lost,
                         "p_actual": lost / booked, "p_pred": 0.08, "adr": 100.0})


def test_rolling_rate_never_looks_ahead():
    n = _nights()
    before = rolling_rate(n)
    n2 = n.copy()
    n2.loc[60:, "p_actual"] = 0.99                       # change the future
    after = rolling_rate(n2)
    assert before.iloc[:68].equals(after.iloc[:68])      # 60 + 8-day lag: nothing earlier moves


def test_estimate_clumping():
    plain = add_policy_inputs(_nights(400, clumped=False))
    clumped = add_policy_inputs(_nights(400, clumped=True))
    assert estimate_clumping(plain) < 0.003 < estimate_clumping(clumped)


def test_gaps_in_nights_are_refused():
    with pytest.raises(AssertionError):
        add_policy_inputs(_nights().drop(index=10))


def test_backtest_on_synthetic_nights():
    n = _nights(200, clumped=True)
    summary, detail = backtest(n, pd.Series({"H": 190}), w=3, test_start="2016-05-01")
    assert summary.policy.tolist() == POLICIES
    none = summary.set_index("policy").loc["No overbooking"]
    assert none.gain_eur == 0 and none.guests_walked == 0
    assert len(detail) == len(POLICIES) * (n.night >= "2016-05-01").sum()
    # every decision stays between 0 and MAX_OVERBOOK
    assert detail.overbook.between(0, 40).all()
