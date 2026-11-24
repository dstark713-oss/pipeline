import numpy as np
import pandas as pd

from evaluation import build_hac_inference, calculate_daily_ic


def test_daily_ic_preserves_complete_calendar_and_missing_reason():
    dates = pd.bdate_range("2020-01-01", periods=3)
    rows = []
    for ticker in range(20):
        rows.append({
            "tradedate": dates[0],
            "secid": f"S{ticker}",
            "feature_a": float(ticker),
            "target": float(ticker % 2),
        })
    frame = pd.DataFrame(rows)

    result = calculate_daily_ic(frame, ["feature_a"], dates)

    assert len(result) == 3
    assert result.loc[0, "ic"] == result.loc[0, "ic"]
    assert result.loc[1, "missing_reason"] == "no_signal_rows"
    assert result.loc[2, "missing_reason"] == "no_signal_rows"


def test_hac_inference_emits_full_specification_grid():
    dates = pd.bdate_range("2020-01-01", periods=80)
    rng = np.random.default_rng(123)
    values = rng.normal(0.01, 0.05, size=len(dates))
    daily = pd.DataFrame({
        "tradedate": dates,
        "feature": "feature_a",
        "ic": values,
        "rank_ic": values * 0.8 + rng.normal(0, 0.01, len(dates)),
    })

    result = build_hac_inference(
        daily, dates, bandwidths=(4, 10), min_observations=30
    )

    assert len(result) == 2 * 2 * 2
    assert set(result["metric"]) == {"ic", "rank_ic"}
    assert set(result["estimator"]) == {"AM", "ES"}
    assert set(result["bandwidth"]) == {4, 10}
    assert result["status"].eq("ok").all()
    assert result["q_value"].between(0, 1).all()
