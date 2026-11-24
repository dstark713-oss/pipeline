from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
REPLICATION_DIR = ROOT / "scripts" / "experiments" / "model1_replication"
if str(REPLICATION_DIR) not in sys.path:
    sys.path.insert(0, str(REPLICATION_DIR))

import run_replication as replication  # noqa: E402


OUTPUT_DIR = ROOT / "data" / "interim" / "model1_daily_scores"
HORIZON = int(replication.TARGET["h"])
REQUIRED_PANEL_COLUMNS = {
    "tradedate", "secid", "bar_available", "ranking_asof_date"
}


def load_latest_panel() -> tuple[pd.Timestamp, pd.DataFrame]:
    path = replication.PANEL
    if not path.is_file():
        raise FileNotFoundError(path)

    panel = pd.read_parquet(path)
    missing = REQUIRED_PANEL_COLUMNS.difference(panel.columns)
    if missing:
        raise RuntimeError(f"TOP50 panel missing columns: {sorted(missing)}")

    panel = panel.copy()
    panel["tradedate"] = pd.to_datetime(panel["tradedate"], errors="coerce")
    panel["ranking_asof_date"] = pd.to_datetime(
        panel["ranking_asof_date"], errors="coerce"
    )
    panel["secid"] = panel["secid"].astype(str).str.strip().str.upper()
    panel["bar_available"] = (
        pd.to_numeric(panel["bar_available"], errors="coerce")
        .fillna(0)
        .astype(int)
    )
    panel = panel.dropna(subset=["tradedate", "ranking_asof_date", "secid"])

    if panel.duplicated(["tradedate", "secid"]).any():
        raise RuntimeError("Duplicate date/SECID rows in TOP50 panel")
    if not (panel["ranking_asof_date"] < panel["tradedate"]).all():
        raise RuntimeError("PIT ranking_asof_date must precede tradedate")

    asof = panel["tradedate"].max()
    latest = panel.loc[panel["tradedate"].eq(asof)].copy()
    if len(latest) != 50 or latest["secid"].nunique() != 50:
        raise RuntimeError(
            f"Expected exactly 50 unique securities on latest panel date "
            f"{asof.date()}, got {len(latest)} rows / "
            f"{latest['secid'].nunique()} unique SECIDs"
        )
    return asof, latest.sort_values("secid").reset_index(drop=True)


def prepare_training_data(
    panel: pd.DataFrame, history: pd.DataFrame, asof: pd.Timestamp
) -> tuple[pd.DataFrame, list[str]]:
    # Reuse the replicated PIT sample, feature definitions and labels unchanged.
    full, feature_columns, _ = replication.build_dataset(panel, history)

    # A Triple Barrier label is usable only when all five forward sessions exist.
    # The replication helper labels a truncated tail as timeout, so explicitly
    # remove rows without a complete H-session horizon before fitting.
    horizon_map = (
        history.sort_values(["secid", "tradedate"])
        .groupby("secid", sort=False)["tradedate"]
        .shift(-HORIZON)
        .rename("label_horizon_end")
        .reset_index()
    )
    horizon_map["secid"] = history.sort_values(
        ["secid", "tradedate"]
    )["secid"].to_numpy()
    full = full.merge(
        horizon_map,
        on=["secid", "tradedate"],
        how="left",
        validate="one_to_one",
    )
    full = full.loc[
        full["label_horizon_end"].notna()
        & full["label_horizon_end"].le(asof)
    ].copy()

    if full.empty:
        raise RuntimeError("No training rows with complete five-session labels")
    for target in ("tp_hit", "sl_hit"):
        if full[target].nunique() < 2:
            raise RuntimeError(
                f"Training target {target} contains fewer than two classes"
            )
    return full.sort_values(["tradedate", "secid"]).reset_index(drop=True), feature_columns


def build_latest_features(
    latest_panel: pd.DataFrame,
    history: pd.DataFrame,
    asof: pd.Timestamp,
    feature_columns: list[str],
) -> tuple[pd.DataFrame, list[dict]]:
    history = history.loc[history["tradedate"].le(asof)].copy()
    groups = {
        secid: group.sort_values("tradedate")
        for secid, group in history.groupby("secid", sort=False)
    }

    rows: list[dict] = []
    feature_rows: list[dict] = []
    for item in latest_panel.itertuples(index=False):
        secid = str(item.secid).upper()
        row = {
            "tradedate": asof.date().isoformat(),
            "secid": secid,
            "ranking_asof_date": pd.Timestamp(item.ranking_asof_date).date().isoformat(),
            "bar_available": int(item.bar_available),
            "tp_raw_score": np.nan,
            "sl_raw_score": np.nan,
            "composite_score": np.nan,
            "rank": np.nan,
            "status": "pending",
        }

        if secid in replication.EXCLUDED:
            row["status"] = "excluded_by_replicated_model"
            rows.append(row)
            continue
        if int(item.bar_available) != 1:
            row["status"] = "bar_unavailable_in_panel"
            rows.append(row)
            continue

        bars = groups.get(secid)
        if bars is None or bars.empty or not bars["tradedate"].eq(asof).any():
            row["status"] = "latest_bar_missing"
            rows.append(row)
            continue
        if len(bars) < 300:
            row["status"] = "insufficient_history"
            rows.append(row)
            continue

        latest_features = replication.features(bars).iloc[-1]
        values = latest_features.reindex(feature_columns)
        if values.isna().any() or not np.isfinite(values.to_numpy(dtype=float)).all():
            row["status"] = "incomplete_features"
            rows.append(row)
            continue

        row["status"] = "ready_for_scoring"
        rows.append(row)
        feature_rows.append({"secid": secid, **values.to_dict()})

    return pd.DataFrame(rows), feature_rows


def score_latest(
    train: pd.DataFrame,
    feature_columns: list[str],
    latest_panel: pd.DataFrame,
    history: pd.DataFrame,
    asof: pd.Timestamp,
) -> pd.DataFrame:
    latest, feature_rows = build_latest_features(
        latest_panel, history, asof, feature_columns
    )
    if not feature_rows:
        raise RuntimeError("No current PIT TOP50 securities are eligible for scoring")

    X_latest = pd.DataFrame(feature_rows).set_index("secid")
    X_latest = X_latest[feature_columns]

    tp_model = replication.fit(train[feature_columns], train["tp_hit"])
    sl_model = replication.fit(train[feature_columns], train["sl_hit"])

    tp_scores = pd.Series(
        tp_model.predict_proba(X_latest)[:, 1], index=X_latest.index
    )
    sl_scores = pd.Series(
        sl_model.predict_proba(X_latest)[:, 1], index=X_latest.index
    )

    ready = latest["status"].eq("ready_for_scoring")
    latest.loc[ready, "tp_raw_score"] = latest.loc[ready, "secid"].map(tp_scores)
    latest.loc[ready, "sl_raw_score"] = latest.loc[ready, "secid"].map(sl_scores)
    latest.loc[ready, "composite_score"] = (
        latest.loc[ready, "tp_raw_score"]
        * (1.0 - latest.loc[ready, "sl_raw_score"])
    )

    scored = latest["composite_score"].notna()
    latest.loc[scored, "status"] = "scored"
    latest.loc[scored, "rank"] = (
        latest.loc[scored, "composite_score"]
        .rank(method="first", ascending=False)
        .astype(int)
    )
    return latest.sort_values(
        ["rank", "secid"], na_position="last"
    ).reset_index(drop=True)


def run(output_dir: Path = OUTPUT_DIR) -> Path:
    asof, latest_panel = load_latest_panel()
    # Training universe follows the same PIT/bar-available rules as replication.
    training_panel = replication.load_panel()
    training_panel = training_panel.loc[
        training_panel["tradedate"].le(asof)
    ].copy()

    secids = sorted(training_panel["secid"].unique())
    history = replication.load_history(secids)
    history["tradedate"] = pd.to_datetime(history["tradedate"], errors="coerce")
    history = history.loc[history["tradedate"].le(asof)].copy()

    train, feature_columns = prepare_training_data(
        training_panel, history, asof
    )
    result = score_latest(
        train, feature_columns, latest_panel, history, asof
    )

    if len(result) != 50 or result["secid"].nunique() != 50:
        raise RuntimeError(
            f"Output integrity check failed: {len(result)} rows, "
            f"{result['secid'].nunique()} unique SECIDs"
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    date_tag = asof.strftime("%Y%m%d")
    dated_path = output_dir / f"model1_scores_{date_tag}.csv"
    latest_path = output_dir / "model1_scores_latest.csv"
    result.to_csv(dated_path, index=False, encoding="utf-8-sig")
    result.to_csv(latest_path, index=False, encoding="utf-8-sig")

    print("=" * 68)
    print("MODEL1 DAILY TOP50 SCORES")
    print("=" * 68)
    print(f"Signal date:       {asof.date()}")
    print(f"Training rows:     {len(train):,}")
    print(f"Training dates:    {train['tradedate'].nunique():,}")
    print(f"Training SECIDs:   {train['secid'].nunique():,}")
    print(f"Features:          {len(feature_columns)}")
    print(f"Scored securities: {int(result['composite_score'].notna().sum())}/50")
    print(f"CSV:               {dated_path}")
    print(f"Latest alias:      {latest_path}")
    print(
        "Note: TP/SL outputs are raw model scores, not calibrated probabilities."
    )
    return dated_path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Retrain model1 on all eligible history and score the latest PIT TOP50."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=OUTPUT_DIR,
        help="Directory for dated and latest CSV outputs.",
    )
    args = parser.parse_args()
    run(args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
