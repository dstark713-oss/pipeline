
from __future__ import annotations

import numpy as np
import pandas as pd

from hac_calendar import calendar_aware_hac


def simulate_ar1(
    rng: np.random.Generator,
    n: int,
    phi: float,
) -> np.ndarray:
    """
    Generate a stationary AR(1) process with unit variance.

    X_t = phi * X_(t-1) + epsilon_t

    Innovation variance is adjusted to produce
    approximately unit marginal variance.
    """

    eps = rng.normal(
        loc=0.0,
        scale=np.sqrt(1 - phi**2),
        size=n,
    )

    values = np.zeros(n, dtype=float)

    values[0] = rng.normal()

    for t in range(1, n):
        values[t] = phi * values[t - 1] + eps[t]

    return values


def run_simulation(
    name: str,
    process: str,
    phi: float,
    missing_rate: float,
    n_sessions: int = 500,
    n_simulations: int = 500,
    bandwidth: int = 20,
    seed: int = 42,
) -> dict:

    rng = np.random.default_rng(seed)

    calendar = pd.RangeIndex(
        n_sessions,
        name="session",
    )

    coverage_count = 0
    rejection_count = 0
    se_sum = 0.0
    mean_n = 0.0

    for _ in range(n_simulations):

        if process == "iid":
            values = rng.normal(size=n_sessions)

        elif process == "ar1":
            values = simulate_ar1(
                rng=rng,
                n=n_sessions,
                phi=phi,
            )

        else:
            raise ValueError(
                f"Unknown process: {process}"
            )

        missing_mask = (
            rng.random(n_sessions) < missing_rate
        )

        values[missing_mask] = np.nan

        series = pd.Series(
            values,
            index=calendar,
        )

        result = calendar_aware_hac(
            ic_series=series,
            calendar=calendar,
            bandwidth=bandwidth,
        )

        lower = result.mean - 1.96 * result.std_error
        upper = result.mean + 1.96 * result.std_error

        # True population mean is zero.
        if lower <= 0.0 <= upper:
            coverage_count += 1

        if result.p_value < 0.05:
            rejection_count += 1

        se_sum += result.std_error
        mean_n += result.n_observations

    coverage = coverage_count / n_simulations
    rejection_rate = rejection_count / n_simulations

    return {
        "scenario": name,
        "coverage": coverage,
        "rejection_rate": rejection_rate,
        "mean_se": se_sum / n_simulations,
        "mean_observations": mean_n / n_simulations,
        "simulations": n_simulations,
        "bandwidth": bandwidth,
    }



def main():

    scenarios = [
        {
            "name": "IID / no missing",
            "process": "iid",
            "phi": 0.0,
            "missing_rate": 0.0,
        },
        {
            "name": "IID / 20% missing",
            "process": "iid",
            "phi": 0.0,
            "missing_rate": 0.2,
        },
        {
            "name": "AR1(0.5) / no missing",
            "process": "ar1",
            "phi": 0.5,
            "missing_rate": 0.0,
        },
        {
            "name": "AR1(0.5) / 20% missing",
            "process": "ar1",
            "phi": 0.5,
            "missing_rate": 0.2,
        },
    ]

    bandwidths = [4, 10, 20, 60]
    results = []

    for scenario in scenarios:
        for bandwidth in bandwidths:

            result = run_simulation(
                **scenario,
                n_sessions=5471,
                n_simulations=1000,
                bandwidth=bandwidth,
                seed=42,
            )

            results.append(result)

    report = pd.DataFrame(results)

    print("\nMonte Carlo HAC bandwidth sensitivity")
    print("=" * 90)

    print(
        report.to_string(
            index=False,
            formatters={
                "coverage": "{:.3f}".format,
                "rejection_rate": "{:.3f}".format,
                "mean_se": "{:.5f}".format,
                "mean_observations": "{:.1f}".format,
            },
        )
    )

    print("\nReference:")
    print("Nominal coverage: 0.950")
    print("Nominal rejection rate: 0.050")
    print("Simulations per scenario: 2000")


if __name__ == "__main__":
    main()

