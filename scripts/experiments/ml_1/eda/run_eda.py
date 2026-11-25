"""Run descriptive EDA. Run from repository root with pandas, numpy and pyarrow installed."""
from __future__ import annotations

import sys
from datetime import datetime, timezone

import pandas as pd

from analysis import (
    consistency_analysis, distribution_analysis, future_price_analysis,
    temporal_analysis,
)
from config import (
    ADJUSTED_DB_PATH, HORIZONS, OUTPUT_DIR, PANEL_PATH,
)
from data_loader import load_market_history, load_panel
from reporting import write_outputs


def main() -> None:
    started = datetime.now(timezone.utc)
    print("[EDA] Loading PIT TOP50 panel...", flush=True)
    panel = load_panel()
    print(f"[EDA] Panel rows={len(panel):,}; SECIDs={panel['secid'].nunique():,}", flush=True)

    print("[EDA] Loading read-only adjusted price history...", flush=True)
    prices, calendar = load_market_history(sorted(panel["secid"].unique()))
    print(f"[EDA] Price rows={len(prices):,}; market sessions={len(calendar):,}", flush=True)

    print("[EDA] Descriptive distributions...", flush=True)
    distribution, distribution_by_year, by_secid = distribution_analysis(panel)
    print("[EDA] Temporal structure and membership dynamics...", flush=True)
    temporal_yearly, temporal_detail = temporal_analysis(panel)
    print("[EDA] Internal consistency diagnostics...", flush=True)
    consistency = consistency_analysis(panel)
    print(f"[EDA] Future adjusted-close horizons={HORIZONS}...", flush=True)
    future_summary, future_by_year, future_by_secid = future_price_analysis(
        panel, prices, calendar
    )

    metadata = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "started_at_utc": started.isoformat(),
        "panel_path": str(PANEL_PATH),
        "adjusted_db_path": str(ADJUSTED_DB_PATH),
        "panel_start": str(panel["tradedate"].min().date()),
        "panel_end": str(panel["tradedate"].max().date()),
        "panel_rows": int(len(panel)),
        "dates": int(panel["tradedate"].nunique()),
        "secids": int(panel["secid"].nunique()),
        "calendar_sessions": int(len(calendar)),
        "bar_available_rows": int(panel["bar_available"].eq(1).sum()),
        "horizons_in_market_sessions": list(HORIZONS),
        "future_price_cohort": "PIT TOP50 membership at t with bar_available=1 and positive adjusted_close at t",
        "future_endpoint_rule": "adjusted_close at t+h on the full TQBR/EQBR market-session calendar; missing endpoints are not filled or bridged",
        "price_board_rule": "complete OHLC row first, then TQBR, then EQBR",
        "numtrades_analyzed": False,
        "target_defined": False,
        "model_selected": False,
        "features_created": False,
        "ic_calculated": False,
        "portfolio_metrics_calculated": False,
        "source_databases_modified": False,
    }
    write_outputs(
        OUTPUT_DIR, distribution, distribution_by_year, by_secid,
        temporal_yearly, temporal_detail, consistency, future_summary,
        future_by_year, future_by_secid, metadata,
    )
    print(f"[EDA] Complete. Report: {OUTPUT_DIR / 'EDA_REPORT.md'}", flush=True)


if __name__ == "__main__":
    main()
