from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]
INPUT_PATH = PROJECT_ROOT / "data" / "interim" / "aggressive_market_snapshot" / "latest_snapshot.csv"
OUTPUT_DIR = PROJECT_ROOT / "data" / "interim" / "aggressive_name_signals"
REPORT_PATH = PROJECT_ROOT / "docs" / "aggressive_name_signals_report.md"

QUINTILE_COUNT = 5
TAIL_CUTOFF = 0.80
MIN_TURNOVER_RATIO = 0.50
MAX_NAMES_PER_SIDE = 10


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build current name-level aggressive signals from the PIT TOP50 snapshot."
    )
    parser.add_argument("--input", type=Path, default=INPUT_PATH)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    parser.add_argument("--report", type=Path, default=REPORT_PATH)
    return parser.parse_args()


def require_columns(frame: pd.DataFrame) -> None:
    required = {
        "tradedate", "secid", "rank", "bar_available", "adjusted_close",
        "return_5d", "return_20d", "rs_5d", "rs_20d",
        "realized_vol_20d_ann", "turnover_vs_20d_median", "value",
    }
    missing = required - set(frame.columns)
    if missing:
        raise RuntimeError(f"Snapshot is missing required columns: {sorted(missing)}")


def percentile_rank(series: pd.Series, ascending: bool = True) -> pd.Series:
    return series.rank(method="average", pct=True, ascending=ascending)


def build_candidates(snapshot: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, int]]:
    frame = snapshot.copy()
    frame["tradedate"] = pd.to_datetime(frame["tradedate"]).dt.normalize()
    if frame["tradedate"].nunique() != 1:
        raise RuntimeError("Input must contain exactly one snapshot date.")
    if frame["secid"].duplicated().any():
        raise RuntimeError("Duplicate ticker rows in current snapshot.")

    numeric = [
        "rank", "bar_available", "adjusted_close", "return_5d", "return_20d",
        "rs_5d", "rs_20d", "realized_vol_20d_ann",
        "turnover_vs_20d_median", "value",
    ]
    for column in numeric:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")

    frame["valid_bar"] = frame["bar_available"].eq(1) & frame["adjusted_close"].gt(0)
    frame["valid_features"] = frame[
        ["return_5d", "return_20d", "rs_5d", "rs_20d",
         "realized_vol_20d_ann", "turnover_vs_20d_median", "value"]
    ].notna().all(axis=1)
    frame["liquid_enough"] = (
        frame["turnover_vs_20d_median"].ge(MIN_TURNOVER_RATIO)
        & frame["value"].gt(0)
    )
    frame["eligible"] = frame["valid_bar"] & frame["valid_features"] & frame["liquid_enough"]

    # Compare RS20 inside the same RS5 quintile, reducing selection by the
    # very recent 5-session move alone.
    frame["rs5_pct"] = percentile_rank(frame["rs_5d"])
    frame["rs5_quintile"] = np.ceil(
        frame["rs5_pct"] * QUINTILE_COUNT
    ).clip(1, QUINTILE_COUNT)
    frame["rs20_pct_within_rs5"] = (
        frame.groupby("rs5_quintile", observed=False)["rs_20d"]
        .rank(method="average", pct=True)
    )

    # Long: positive RS20 and top quintile within its RS5 stratum.
    long_mask = (
        frame["eligible"]
        & frame["rs_20d"].gt(0)
        & frame["rs20_pct_within_rs5"].ge(TAIL_CUTOFF)
    )

    # Short: simultaneous bottom-quintile RS5 and RS20. This is deliberately
    # stricter and lower-confidence because F3 was regime-dependent.
    frame["rs20_pct"] = percentile_rank(frame["rs_20d"])
    short_mask = (
        frame["eligible"]
        & frame["rs_5d"].lt(0)
        & frame["rs_20d"].lt(0)
        & frame["rs5_pct"].le(1.0 - TAIL_CUTOFF)
        & frame["rs20_pct"].le(1.0 - TAIL_CUTOFF)
    )

    candidates = []
    for direction, mask in (("LONG", long_mask), ("SHORT", short_mask)):
        selected = frame.loc[mask].copy()
        if direction == "LONG":
            selected["signal_score"] = selected["rs20_pct_within_rs5"]
            selected["evidence_grade"] = "PRIMARY"
            selected["evidence_basis"] = (
                "Positive RS20; top quintile of RS20 within the same RS5 quintile. "
                "Matches the surviving F1 incremental-RS20 result."
            )
        else:
            selected["signal_score"] = (
                0.5 * (1.0 - selected["rs5_pct"])
                + 0.5 * (1.0 - selected["rs20_pct"])
            )
            selected["evidence_grade"] = "CONDITIONAL"
            selected["evidence_basis"] = (
                "Negative RS5 and RS20, both in the bottom quintile. "
                "F3 was regime-dependent and borderline after multiple-testing adjustment; "
                "treat as a conditional short candidate, not a confirmed short edge."
            )
        selected["direction"] = direction
        candidates.append(selected)

    if candidates:
        result = pd.concat(candidates, ignore_index=True)
        result = result.sort_values(
            ["direction", "signal_score", "rs_20d"],
            ascending=[True, False, False],
        )
        result["candidate_rank"] = result.groupby("direction").cumcount() + 1
        result = result.loc[result["candidate_rank"] <= MAX_NAMES_PER_SIDE].copy()
    else:
        result = pd.DataFrame()

    counts = {
        "universe": int(len(frame)),
        "valid_bar": int(frame["valid_bar"].sum()),
        "eligible": int(frame["eligible"].sum()),
        "long_before_cap": int(long_mask.sum()),
        "short_before_cap": int(short_mask.sum()),
    }

    columns = [
        "tradedate", "secid", "direction", "candidate_rank", "evidence_grade",
        "signal_score", "rank", "rs5_quintile", "return_5d", "rs_5d",
        "return_20d", "rs_20d", "rs20_pct_within_rs5",
        "realized_vol_20d_ann", "turnover_vs_20d_median", "value",
        "adjusted_close", "evidence_basis",
    ]
    if result.empty:
        result = pd.DataFrame(columns=columns)
    else:
        result = result[columns].reset_index(drop=True)

    return result, counts


def pct(value: object) -> str:
    number = pd.to_numeric(value, errors="coerce")
    return f"{number:.2%}" if pd.notna(number) else "n/a"


def render_report(candidates: pd.DataFrame, counts: dict[str, int], report_path: Path) -> None:
    date = (
        pd.to_datetime(candidates["tradedate"].iloc[0]).date()
        if not candidates.empty else "see input snapshot"
    )
    lines = [
        "# Aggressive Agent: Name-Level Signal Packet",
        "",
        f"- Snapshot date: **{date}**",
        f"- PIT TOP50 universe rows: **{counts['universe']}**",
        f"- Current bars available: **{counts['valid_bar']}**",
        f"- Eligible after data/liquidity filters: **{counts['eligible']}**",
        f"- Long candidates before cap: **{counts['long_before_cap']}**",
        f"- Short candidates before cap: **{counts['short_before_cap']}**",
        "- Intended horizon: **10–20 trading sessions**",
        "- This packet provides directions and evidence, not position sizes.",
        "",
        "## Selection logic",
        "",
        "- Long: positive RS20 and top-quintile RS20 within the same RS5 quintile. "
        "This operationalizes the surviving F1 result while controlling for the shorter RS5 stratum.",
        "- Short: negative RS5 and RS20, both in their cross-sectional bottom quintiles. "
        "This is conditional because F3 was regime-dependent and borderline after multiple-testing adjustment.",
        f"- Both sides require a current adjusted close, complete core features, positive current traded value, "
        f"and turnover/current 20D-median ratio at least **{MIN_TURNOVER_RATIO:.2f}**.",
        f"- Maximum **{MAX_NAMES_PER_SIDE}** names per side. No parameter fitting or threshold optimization.",
        "- No sector labels, news assumptions, or unsupported catalysts are added.",
        "",
        "## Long candidates",
        "",
    ]

    long_rows = candidates.loc[candidates["direction"] == "LONG"]
    if long_rows.empty:
        lines.append("No qualifying Long names on this snapshot.")
    else:
        lines.extend([
            "| Rank | Ticker | RS20 | RS5 | Return 20D | Vol20 ann. | Turnover / median |",
            "|---:|---|---:|---:|---:|---:|---:|",
        ])
        for row in long_rows.itertuples(index=False):
            lines.append(
                f"| {row.candidate_rank} | **{row.secid}** | {pct(row.rs_20d)} | "
                f"{pct(row.rs_5d)} | {pct(row.return_20d)} | "
                f"{pct(row.realized_vol_20d_ann)} | {row.turnover_vs_20d_median:.2f}x |"
            )

    lines.extend(["", "## Short candidates", ""])
    short_rows = candidates.loc[candidates["direction"] == "SHORT"]
    if short_rows.empty:
        lines.append("No qualifying Short names on this snapshot.")
    else:
        lines.extend([
            "| Rank | Ticker | RS20 | RS5 | Return 20D | Vol20 ann. | Turnover / median |",
            "|---:|---|---:|---:|---:|---:|---:|",
        ])
        for row in short_rows.itertuples(index=False):
            lines.append(
                f"| {row.candidate_rank} | **{row.secid}** | {pct(row.rs_20d)} | "
                f"{pct(row.rs_5d)} | {pct(row.return_20d)} | "
                f"{pct(row.realized_vol_20d_ann)} | {row.turnover_vs_20d_median:.2f}x |"
            )

    lines.extend([
        "",
        "## Handoff notes for Sizing Agent",
        "",
        "- LONG candidates are the primary evidence-backed side.",
        "- SHORT candidates are conditional research signals with weaker evidence. "
        "Sizing Agent should independently check short permission, borrow/implementation constraints, "
        "portfolio risk, and risk budget; reject them if unsupported.",
        "- Volatility and turnover are context for sizing and implementation, not instructions "
        "to derive a target weight from this packet.",
        "- Empty side means no signal on that side. Do not fill the list by relaxing filters.",
        "",
        "## Output files",
        "",
        f"- CSV: {OUTPUT_DIR / 'name_level_signals.csv'}",
        f"- Report: {report_path}",
        "",
    ])
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    args = parse_args()
    if not args.input.is_file():
        raise FileNotFoundError(
            f"Latest market snapshot not found: {args.input}. "
            "Run the aggressive market snapshot builder first."
        )

    snapshot = pd.read_csv(args.input)
    require_columns(snapshot)
    candidates, counts = build_candidates(snapshot)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = args.output_dir / "name_level_signals.csv"
    candidates.to_csv(csv_path, index=False, encoding="utf-8-sig")
    render_report(candidates, counts, args.report)

    print("\nAGGRESSIVE NAME-LEVEL SIGNALS")
    print("=" * 64)
    print(f"Snapshot date:       {pd.to_datetime(snapshot['tradedate']).max().date()}")
    print(f"PIT universe:        {counts['universe']}")
    print(f"Eligible names:      {counts['eligible']}")
    print(f"Long candidates:     {counts['long_before_cap']}")
    print(f"Short candidates:    {counts['short_before_cap']}")
    print(f"CSV:                 {csv_path}")
    print(f"Report:              {args.report}")
    print("=" * 64)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
