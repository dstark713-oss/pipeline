
import numpy as np
import pandas as pd

from hac_calendar import calendar_aware_hac


def make_calendar(n=500):
    return pd.RangeIndex(n, name="session")


def test_iid():
    rng = np.random.default_rng(42)
    calendar = make_calendar(1000)

    values = rng.normal(0, 1, size=1000)
    series = pd.Series(values, index=calendar)

    result = calendar_aware_hac(series, calendar, bandwidth=10)

    assert result.n_observations == 1000
    assert result.n_sessions == 1000

    # IID: SE should be close to the conventional SE.
    conventional_se = values.std(ddof=1) / np.sqrt(len(values))

    assert np.isclose(
        result.std_error,
        conventional_se,
        rtol=0.25,
    )


def test_positive_autocorrelation():
    rng = np.random.default_rng(42)
    calendar = make_calendar(2000)

    # Generate AR(1) with positive autocorrelation.
    phi = 0.8
    eps = rng.normal(size=2000)

    values = np.zeros(2000)

    for t in range(1, 2000):
        values[t] = phi * values[t - 1] + eps[t]

    series = pd.Series(values, index=calendar)

    result = calendar_aware_hac(series, calendar, bandwidth=20)

    conventional_se = values.std(ddof=1) / np.sqrt(len(values))

    # Positive serial dependence should generally increase the SE.
    assert result.std_error > conventional_se


def test_missing_sessions_preserve_calendar_lags():
    calendar = make_calendar(100)

    values = np.sin(np.arange(100) / 4.0)

    series = pd.Series(values, index=calendar)

    # Remove several sessions.
    missing_sessions = [10, 11, 12, 30, 31, 60]

    sparse_series = series.drop(missing_sessions)

    result_calendar = calendar_aware_hac(
        sparse_series,
        calendar,
        bandwidth=5,
    )

    # Incorrect alternative:
    # compress time by using only observed dates as consecutive positions.
    compressed_calendar = pd.RangeIndex(len(sparse_series))

    compressed_series = pd.Series(
        sparse_series.to_numpy(),
        index=compressed_calendar,
    )

    result_compressed = calendar_aware_hac(
        compressed_series,
        compressed_calendar,
        bandwidth=5,
    )

    # The calendar-aware result and compressed-time result
    # should differ because their lag structures differ.
    assert not np.isclose(
        result_calendar.variance,
        result_compressed.variance,
    )


def test_no_missing_matches_manual_newey_west():
    rng = np.random.default_rng(123)

    T = 500
    L = 10

    calendar = make_calendar(T)

    values = rng.normal(size=T)
    series = pd.Series(values, index=calendar)

    result = calendar_aware_hac(
        series,
        calendar,
        bandwidth=L,
    )

    mean = values.mean()
    u = values - mean

    meat = np.dot(u, u)

    for lag in range(1, L + 1):
        weight = 1 - lag / (L + 1)

        cross_product = np.dot(
            u[lag:],
            u[:-lag],
        )

        meat += 2 * weight * cross_product

    expected_variance = meat / (T ** 2)

    assert np.isclose(
        result.variance,
        expected_variance,
        atol=1e-12,
    )


def test_missing_observations_count():
    calendar = make_calendar(100)

    values = np.arange(100, dtype=float)

    series = pd.Series(values, index=calendar)

    series.iloc[::5] = np.nan

    result = calendar_aware_hac(
        series,
        calendar,
        bandwidth=4,
    )

    assert result.n_observations == 80
    assert result.n_sessions == 100

def test_calendar_lag_pairs_manual_verification():
    """
    Explicitly verifies calendar-aware lag contributions.

    Calendar: sessions 1, 2, 3, 4, 5
    Observed IC: sessions 1, 2, 3, 5
    Missing IC: session 4

    At lag 1:
        (1,2), (2,3)

    At lag 2:
        (1,3), (3,5)

    Session 3 and session 5 are separated by 2 sessions,
    not 1. Their contribution must appear only at lag 2.
    """

    calendar = pd.RangeIndex(1, 6, name="session")

    series = pd.Series(
        [1.0, 2.0, 4.0, 10.0],
        index=pd.Index([1, 2, 3, 5], name="session"),
    )

    L = 2

    result = calendar_aware_hac(
        series,
        calendar,
        bandwidth=L,
    )

    # Independently construct calendar-aligned score vector.
    observed_values = np.array([1.0, 2.0, 4.0, 10.0])
    mean = observed_values.mean()

    # Calendar positions: 1, 2, 3, 4, 5
    # Session 4 is missing and contributes zero.
    u = np.array([
        1.0 - mean,
        2.0 - mean,
        4.0 - mean,
        0.0,
        10.0 - mean,
    ])

    # Lag zero.
    gamma_0_sum = np.dot(u, u)

    # Lag 1: only adjacent observed session pairs.
    gamma_1_sum = (
        u[1] * u[0]
        + u[2] * u[1]
        + u[3] * u[2]
        + u[4] * u[3]
    )

    # Lag 2: explicitly calendar-separated pairs.
    gamma_2_sum = (
        u[2] * u[0]
        + u[3] * u[1]
        + u[4] * u[2]
    )

    weight_1 = 1 - 1 / (L + 1)
    weight_2 = 1 - 2 / (L + 1)

    expected_meat = (
        gamma_0_sum
        + 2 * weight_1 * gamma_1_sum
        + 2 * weight_2 * gamma_2_sum
    )

    expected_variance = expected_meat / (len(observed_values) ** 2)

    assert np.isclose(
        result.mean,
        mean,
        atol=1e-12,
    )

    assert np.isclose(
        result.variance,
        expected_variance,
        atol=1e-12,
    )