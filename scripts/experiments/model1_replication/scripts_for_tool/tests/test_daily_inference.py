import sys
from pathlib import Path

import pandas as pd

SOURCE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SOURCE_DIR))

from daily_inference import complete_horizon_map


def test_complete_horizon_map_is_per_security_and_requires_full_horizon():
    dates_a = pd.bdate_range("2020-01-01", periods=7)
    dates_b = pd.bdate_range("2020-02-01", periods=6)
    history = pd.concat(
        [
            pd.DataFrame({"secid": "AAA", "tradedate": dates_a}),
            pd.DataFrame({"secid": "BBB", "tradedate": dates_b}),
        ],
        ignore_index=True,
    )

    result = complete_horizon_map(history)
    aaa = result.loc[result["secid"].eq("AAA")].reset_index(drop=True)
    bbb = result.loc[result["secid"].eq("BBB")].reset_index(drop=True)

    assert aaa.loc[0, "label_horizon_end"] == dates_a[5]
    assert pd.isna(aaa.loc[2, "label_horizon_end"])
    assert bbb.loc[0, "label_horizon_end"] == dates_b[5]
    assert bbb["label_horizon_end"].notna().sum() == 1
