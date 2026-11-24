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
    method: str
    long_run_variance: float

    @property
    def variance_of_mean(self) -> float:
        """Variance of the estimated sample mean."""
        return self.variance


def _validate_inputs(
    values: pd.Series,
    calendar: pd.Index,
    bandwidth: int,
) -> tuple[np.ndarray, np.ndarray, int, int]:
    if isinstance(bandwidth, bool) or not isinstance(bandwidth, (int, np.integer)):
        raise TypeError("bandwidth must be an integer")
    if bandwidth < 0:
        raise ValueError("bandwidth must be >= 0")

    calendar = pd.Index(calendar)
    if len(calendar) == 0:
        raise ValueError("calendar must not be empty")
    if not calendar.is_unique:
        raise ValueError("calendar must contain unique sessions")
    calendar = calendar.sort_values()

    if not values.index.is_unique:
        raise ValueError("IC index must contain unique dates")
    if not values.index.isin(calendar).all():
        raise ValueError("IC dates must belong to the calendar")

    aligned = pd.to_numeric(values.reindex(calendar), errors="coerce").to_numpy(dtype=float)
    observed = np.isfinite(aligned)
    n = int(observed.sum())
    sessions = len(calendar)
    if n < 2:
        raise ValueError("At least two finite IC values are required")
    return aligned, observed, n, sessions


def _result(
    mean: float,
    long_run_variance: float,
    n: int,
    sessions: int,
    bandwidth: int,
    method: str,
) -> HACResult:
    # Numerical round-off can create a tiny negative estimate.
    long_run_variance = max(float(long_run_variance), 0.0)
    variance = long_run_variance / n
    std_error = float(np.sqrt(variance))
    if std_error == 0.0:
        t_stat = np.nan
        p_value = np.nan
    else:
        t_stat = float(mean / std_error)
        p_value = float(2.0 * norm.sf(abs(t_stat)))
    return HACResult(
        mean=float(mean),
        variance=float(variance),
        std_error=std_error,
        t_stat=t_stat,
        p_value=p_value,
        n_observations=n,
        n_sessions=sessions,
        bandwidth=bandwidth,
        method=method,
        long_run_variance=long_run_variance,
    )


def calendar_aware_hac(
    ic_series: pd.Series,
    calendar: pd.Index,
    bandwidth: int,
) -> HACResult:
    """
    Amplitude-modulated (AM) HAC for a series with missing calendar sessions.

    This follows Datta & Du (2012): missing observations have g_t=0;
    observed demeaned scores are z*_t - g_t * mean. Autocovariances
    retain the original calendar lag and are normalized by S, the
    number of observed values. The variance of the observed mean is
    the Bartlett LRV estimate divided by S.
    """
    values, observed, n, sessions = _validate_inputs(
        ic_series, calendar, bandwidth
    )
    mean = float(values[observed].mean())

    # z*_t - g_t * mean, with zero contribution at missing sessions.
    scores = np.zeros(sessions, dtype=float)
    scores[observed] = values[observed] - mean

    meat = float(np.dot(scores, scores))
    max_lag = min(bandwidth, sessions - 1)
    for lag in range(1, max_lag + 1):
        weight = 1.0 - lag / (bandwidth + 1.0)
        meat += 2.0 * weight * float(
            np.dot(scores[lag:], scores[:-lag])
        )

    # Datta-Du AM LRV uses denominator S, not calendar length T.
    long_run_variance = meat / n
    return _result(
        mean, long_run_variance, n, sessions, bandwidth, "AM"
    )


def equal_spacing_hac(
    ic_series: pd.Series,
    calendar: pd.Index,
    bandwidth: int,
) -> HACResult:
    """
    Equal-spacing (ES) HAC comparator.

    Finite observations are relabelled as consecutive observations.
    Therefore lags refer to observed-IC time, not trading-session time.
    """
    _, observed, n, sessions = _validate_inputs(
        ic_series, calendar, bandwidth
    )
    aligned = pd.to_numeric(
        ic_series.reindex(pd.Index(calendar).sort_values()),
        errors="coerce",
    ).to_numpy(dtype=float)
    x = aligned[observed]
    mean = float(x.mean())
    residual = x - mean

    meat = float(np.dot(residual, residual))
    max_lag = min(bandwidth, n - 1)
    for lag in range(1, max_lag + 1):
        weight = 1.0 - lag / (bandwidth + 1.0)
        meat += 2.0 * weight * float(
            np.dot(residual[lag:], residual[:-lag])
        )

    # ES LRV is normalized by observed sample size S.
    long_run_variance = meat / n
    return _result(
        mean, long_run_variance, n, sessions, bandwidth, "ES"
    )
