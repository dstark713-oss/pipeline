# Folder: scripts/experiments/ml_1/rolling_statistical_moments/
# File: features.py
# Purpose: Calculate rolling moments from daily adjusted-close log returns.

from __future__ import annotations

import numpy as np
import pandas as pd

from config import WINDOWS


def calculate_log_returns(close: pd.Series) -> pd.Series:
    """One-session log returns; never bridge missing sessions."""
    close = pd.to_numeric(close, errors="coerce")
    valid_pair = close.notna() & close.shift(1).notna()
    result = np.log(close / close.shift(1))
    return result.where(valid_pair).replace([np.inf, -np.inf], np.nan)


def calculate_rolling_moments(
    log_returns: pd.Series,
    windows: tuple[int, ...] = WINDOWS,
) -> pd.DataFrame:
    """
    Calculate 4 rolling moments.

    pandas Rolling.skew() and Rolling.kurt() use bias-corrected sample
    estimators. Rolling.kurt() returns Fisher excess kurtosis (normal = 0).
    Every window requires a complete set of non-missing observations.
    """
    result = pd.DataFrame(index=log_returns.index)

    for window in windows:
        rolling = log_returns.rolling(
            window=window,
            min_periods=window,
        )

        result[f"rolling_mean_{window}"] = rolling.mean()
        result[f"rolling_variance_{window}"] = rolling.var(ddof=1)
        result[f"rolling_skewness_{window}"] = rolling.skew()
        result[f"rolling_excess_kurtosis_{window}"] = rolling.kurt()

    return result.replace([np.inf, -np.inf], np.nan)


def calculate_binary_target(
    close: pd.Series,
    horizon: int,
) -> pd.Series:
    """1 if Close[t+h] > Close[t], 0 if lower; ties/unavailable -> NaN."""
    future_close = close.shift(-horizon)
    target = pd.Series(np.nan, index=close.index, dtype="float64")

    valid = close.notna() & future_close.notna()
    target.loc[valid & (future_close > close)] = 1.0
    target.loc[valid & (future_close < close)] = 0.0

    return target
