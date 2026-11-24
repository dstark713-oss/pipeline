
import numpy as np
import pandas as pd
import pytest

from hac_calendar import calendar_aware_hac, equal_spacing_hac, HACResult


def manual_calendar_hac(values, calendar, bandwidth):
    series = values.reindex(calendar).astype(float)
    observed = series.notna()
    n = int(observed.sum())

    mean = float(series[observed].mean())

    u = np.zeros(len(calendar), dtype=float)
    u[observed.to_numpy()] = (
        series[observed].to_numpy() - mean
    )

    meat = float(np.dot(u, u))

    for lag in range(1, min(bandwidth, len(calendar) - 1) + 1):
        weight = 1.0 - lag / (bandwidth + 1)
        meat += 2.0 * weight * float(
            np.dot(u[lag:], u[:-lag])
        )

    variance = max(meat / (n ** 2), 0.0)
    std_error = np.sqrt(variance)

    return mean, variance, std_error


def make_series(data):
    calendar = pd.bdate_range(
        "2020-01-01",
        periods=len(data),
    )
    series = pd.Series(data, index=calendar, dtype=float)
    return series, calendar


@pytest.mark.parametrize("bandwidth", [0, 1, 2, 4])
def test_matches_manual_formula(bandwidth):
    values, calendar = make_series([
        0.10, 0.20, np.nan, 0.30, 0.40,
        0.15, np.nan, 0.25, 0.35, 0.05,
    ])

    result = calendar_aware_hac(
        values, calendar, bandwidth
    )

    expected = manual_calendar_hac(
        values, calendar, bandwidth
    )

    assert result.mean == pytest.approx(expected[0])
    assert result.variance == pytest.approx(expected[1])
    assert result.std_error == pytest.approx(expected[2])


def test_no_missing_observations():
    values, calendar = make_series(
        np.random.default_rng(42).normal(size=500)
    )

    result = calendar_aware_hac(values, calendar, 10)

    assert result.n_observations == 500
    assert result.n_sessions == 500


def test_calendar_gaps_are_preserved():
    values, calendar = make_series([
        0.10, 0.20, np.nan, 0.30, 0.40
    ])

    result = calendar_aware_hac(values, calendar, 2)

    expected = manual_calendar_hac(
        values, calendar, 2
    )

    assert result.mean == pytest.approx(expected[0])
    assert result.variance == pytest.approx(expected[1])


def test_missing_observation_counts():
    values, calendar = make_series([
        0.1, np.nan, 0.2, np.nan, 0.3
    ])

    result = calendar_aware_hac(values, calendar, 1)

    assert result.n_observations == 3
    assert result.n_sessions == 5


def test_duplicate_calendar_rejected():
    values, calendar = make_series([0.1, 0.2, 0.3])
    duplicated = calendar.append(calendar[:1])

    with pytest.raises(ValueError):
        calendar_aware_hac(values, duplicated, 1)


def test_duplicate_ic_dates_rejected():
    values, calendar = make_series([0.1, 0.2, 0.3])
    duplicated = pd.Series(
        [0.1, 0.2],
        index=[calendar[0], calendar[0]],
    )

    with pytest.raises(ValueError):
        calendar_aware_hac(duplicated, calendar, 1)


def test_unknown_dates_rejected():
    values, calendar = make_series([0.1, 0.2, 0.3])

    outside = pd.Series(
        [0.5],
        index=[pd.Timestamp("2030-01-01")],
    )

    with pytest.raises(ValueError):
        calendar_aware_hac(outside, calendar, 1)


def test_negative_bandwidth_rejected():
    values, calendar = make_series([0.1, 0.2, 0.3])

    with pytest.raises(ValueError):
        calendar_aware_hac(values, calendar, -1)


def test_single_observation_rejected():
    values, calendar = make_series([0.1, np.nan, np.nan])

    with pytest.raises(ValueError):
        calendar_aware_hac(values, calendar, 1)


def test_result_type():
    values, calendar = make_series([0.1, 0.2, 0.3])

    result = calendar_aware_hac(values, calendar, 1)

    assert isinstance(result, HACResult)



def test_am_and_es_match_when_no_missing_values():
    values, calendar = make_series(
        np.random.default_rng(7).normal(size=200)
    )
    am = calendar_aware_hac(values, calendar, 10)
    es = equal_spacing_hac(values, calendar, 10)
    assert am.mean == pytest.approx(es.mean)
    assert am.variance == pytest.approx(es.variance)
    assert am.long_run_variance == pytest.approx(es.long_run_variance)


def test_am_and_es_differ_when_calendar_gaps_exist():
    values, calendar = make_series([
        0.1, 0.2, np.nan, 0.3, 0.4,
        0.15, np.nan, 0.25, 0.35, 0.05,
    ])
    am = calendar_aware_hac(values, calendar, 2)
    es = equal_spacing_hac(values, calendar, 2)
    assert am.n_observations == es.n_observations == 8
    assert am.n_sessions == es.n_sessions == 10
    assert not np.isclose(am.variance, es.variance)


def test_non_finite_values_are_treated_as_missing():
    values, calendar = make_series([0.1, 0.2, 0.3, 0.4, 0.5])
    values.iloc[1] = np.inf
    values.iloc[3] = -np.inf
    result = calendar_aware_hac(values, calendar, 1)
    assert result.n_observations == 3
    assert np.isfinite(result.std_error)


def test_bandwidth_type_is_validated():
    values, calendar = make_series([0.1, 0.2, 0.3])
    with pytest.raises(TypeError):
        calendar_aware_hac(values, calendar, 1.5)
