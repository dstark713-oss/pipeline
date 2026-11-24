
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.stats import norm


@dataclass(frozen=True)
class HACResult:
    mean: float
    variance: float
    std_error: float
    t_stat: float
    p_value: float
    n_observations: int
    n_sessions: int
    bandwidth: int


def calendar_aware_hac(
    ic_series: pd.Series,
    calendar: pd.Index,
    bandwidth: int,
) -> HACResult:
    """
    Calendar-aware HAC estimator for the mean of a time series
    with missing observations.

    Missing IC values remain missing on the calendar.
    Lag pairs are matched by actual trading-session distance.

    Parameters
    ----------
    ic_series : pd.Series
        IC values indexed by trading-session dates.

    calendar : pd.Index
        Complete, ordered trading-session calendar.

    bandwidth : int
        Maximum HAC lag in trading sessions.

    Returns
    -------
    HACResult
        Mean, variance, standard error, t-statistic,
        two-sided normal p-value and sample diagnostics.
    """

    if bandwidth < 0:
        raise ValueError("bandwidth must be >= 0")

    if not calendar.is_unique:
        raise ValueError("calendar must contain unique sessions")

    calendar = pd.Index(calendar).sort_values()

    if not ic_series.index.is_unique:
        raise ValueError("IC index must contain unique dates")

    if not ic_series.index.isin(calendar).all():
        raise ValueError("IC dates must belong to the calendar")

    series = ic_series.reindex(calendar).astype(float)

    observed = series.notna()
    n = int(observed.sum())
    T = len(calendar)

    if n < 2:
        raise ValueError("At least two observed IC values are required")

    mean_ic = float(series[observed].mean())

    # Calendar-aligned demeaned scores.
    # Missing observations contribute zero to the score sequence.
    u = np.zeros(T, dtype=float)
    u[observed.to_numpy()] = (
        series[observed].to_numpy() - mean_ic
    )

    # Lag-zero covariance contribution.
    meat = float(np.dot(u, u))

    # Bartlett-weighted calendar autocovariance contributions.
    for lag in range(1, min(bandwidth, T - 1) + 1):
        weight = 1.0 - lag / (bandwidth + 1)

        cross_product = float(
            np.dot(u[lag:], u[:-lag])
        )

        meat += 2.0 * weight * cross_product

    variance = meat / (n ** 2)

    # Guard against tiny negative values due to numerical precision.
    variance = max(variance, 0.0)

    std_error = float(np.sqrt(variance))

    if std_error == 0.0:
        t_stat = np.nan
        p_value = np.nan
    else:
        t_stat = mean_ic / std_error
        p_value = float(2.0 * norm.sf(abs(t_stat)))

    return HACResult(
        mean=mean_ic,
        variance=variance,
        std_error=std_error,
        t_stat=float(t_stat),
        p_value=p_value,
        n_observations=n,
        n_sessions=T,
        bandwidth=bandwidth,
    )
