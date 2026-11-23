# Folder: scripts/experiments/primitives/portfolios/
# File: run_experiment.py
# Purpose: Single entry point for the primitive portfolio application experiment.
#
# Run from repository root:
#   python scripts/experiments/primitives/portfolios/run_experiment.py

from __future__ import annotations

import json

from config import OUTPUT_DIR, TRANSACTION_COST_BPS
from data import load_inputs
from portfolio import build_target_weights, run_portfolios
from reporting import build_metrics, plot_curves, write_assistant_report


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 72, flush=True)
    print("PRIMITIVE PORTFOLIO APPLICATION EXPERIMENT", flush=True)
    print("=" * 72, flush=True)

    features, breadth, asset_returns, date_map = load_inputs()

    print("Building PIT target portfolios...", flush=True)
    weight_frames, specs = build_target_weights(features, breadth)

    print("Simulating daily portfolio paths...", flush=True)
    daily = run_portfolios(
        weight_frames=weight_frames,
        asset_returns=asset_returns,
        date_map=date_map,
        cost_bps=TRANSACTION_COST_BPS,
    )
    if daily.empty:
        raise RuntimeError("No daily portfolio observations were produced.")

    overall, annual = build_metrics(daily)

    daily.to_csv(
        OUTPUT_DIR / "daily_equity_curves.csv",
        index=False,
        encoding="utf-8-sig",
    )
    overall.to_csv(
        OUTPUT_DIR / "full_sample_metrics.csv",
        index=False,
        encoding="utf-8-sig",
    )
    annual.to_csv(
        OUTPUT_DIR / "annual_metrics.csv",
        index=False,
        encoding="utf-8-sig",
    )
    specs.to_csv(
        OUTPUT_DIR / "strategy_specs.csv",
        index=False,
        encoding="utf-8-sig",
    )
    breadth.to_csv(
        OUTPUT_DIR / "breadth_daily.csv",
        index=False,
        encoding="utf-8-sig",
    )

    plot_curves(daily, OUTPUT_DIR)
    write_assistant_report(
        output_path=OUTPUT_DIR / "report_for_assistant.md",
        daily=daily,
        overall=overall,
        annual=annual,
        specs=specs,
        breadth=breadth,
    )

    metadata = {
        "experiment": "primitive_portfolio_application",
        "strategies": int(specs["strategy"].nunique()),
        "cost_scenarios_bps": list(TRANSACTION_COST_BPS),
        "daily_rows": int(len(daily)),
        "signal_start": str(daily["signal_date"].min().date()),
        "exit_end": str(daily["exit_date"].max().date()),
        "focus_years": [2024, 2025, 2026],
        "source_features": "data/interim/primitive_research/primitive_features.parquet",
        "source_prices": "data/processed/moex_daily_adjusted.sqlite",
        "source_databases_modified": False,
        "execution_model": "Signal after close T; entry OPEN T+1; exit/rebalance OPEN T+2.",
        "outputs": [
            "daily_equity_curves.csv",
            "full_sample_metrics.csv",
            "annual_metrics.csv",
            "strategy_specs.csv",
            "breadth_daily.csv",
            "report_for_assistant.md",
            "figures/equity_full_sample.png",
            "figures/equity_2024.png",
            "figures/equity_2025.png",
            "figures/equity_2026.png",
        ],
    }
    (OUTPUT_DIR / "run_metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("=" * 72, flush=True)
    print("EXPERIMENT COMPLETE", flush=True)
    print(f"Output directory: {OUTPUT_DIR}", flush=True)
    print(f"Assistant report: {OUTPUT_DIR / 'report_for_assistant.md'}", flush=True)
    print(f"Figures: {OUTPUT_DIR / 'figures'}", flush=True)
    print("=" * 72, flush=True)


if __name__ == "__main__":
    main()
