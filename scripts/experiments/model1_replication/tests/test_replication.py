import sys
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from run_replication import features, triple_barrier, folds


def bars(n=320):
    dates = pd.bdate_range("2010-01-01", periods=n)
    close = 100 + np.arange(n) * 0.05 + np.sin(np.arange(n) / 5)
    return pd.DataFrame({
        "tradedate": dates, "open": close - 0.1, "high": close + 0.8,
        "low": close - 0.8, "close": close,
        "volume": 1000 + np.arange(n) * 2, "value": 1_000_000.0,
    })


def test_features_are_causal():
    x = bars()
    a = features(x)
    y = x.copy()
    y.loc[281:, ["open", "high", "low", "close", "volume"]] *= 1.7
    b = features(y)
    cols = [c for c in a if c not in {"open", "high", "low", "close", "volume", "value"}]
    pd.testing.assert_frame_equal(a.loc[:x.tradedate.iloc[280], cols],
                                  b.loc[:x.tradedate.iloc[280], cols])


def test_triple_barrier_enters_next_session():
    x = bars()
    labels = triple_barrier(x)
    assert labels.entry_date.iloc[0] == x.tradedate.iloc[1]
    assert labels.entry.iloc[0] == x.open.iloc[1]


def test_last_observation_has_no_entry_label():
    labels = triple_barrier(bars())
    assert pd.isna(labels.tp_hit.iloc[-1])
    assert pd.isna(labels.sl_hit.iloc[-1])


def test_wf_purge_and_test_blocks():
    dates = pd.bdate_range("2005-01-01", "2015-12-31")
    result = folds(dates)
    assert result
    for f in result:
        assert f["train_end"] < f["test_start"]
        assert (f["test_start"] - f["train_end"]).days >= 10
    for a, b in zip(result, result[1:]):
        assert b["test_start"] > a["test_end"]


def test_warmed_features_are_finite():
    x = features(bars())
    numeric = x.select_dtypes(include=[np.number]).iloc[250:]
    assert np.isfinite(numeric.to_numpy(dtype=float)).all()
