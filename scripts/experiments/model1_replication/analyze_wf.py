from __future__ import annotations

import argparse
import json
import math
import statistics
from pathlib import Path

METRICS = ("roc_auc", "pr_auc", "logloss", "brier", "precision", "recall", "pos_rate")
TARGETS = ("tp", "sl")
VERSIONS = ("raw", "calibrated")


def finite(values):
    return [float(x) for x in values if isinstance(x, (int, float)) and math.isfinite(float(x))]


def quantile(values, q):
    values = sorted(values)
    if not values:
        return None
    if len(values) == 1:
        return values[0]
    pos = (len(values) - 1) * q
    lo = int(pos)
    hi = min(lo + 1, len(values) - 1)
    weight = pos - lo
    return values[lo] * (1 - weight) + values[hi] * weight


def summarize(values):
    x = finite(values)
    if not x:
        return None
    return {
        "n_folds": len(x),
        "mean": statistics.mean(x),
        "median": statistics.median(x),
        "std": statistics.stdev(x) if len(x) > 1 else 0.0,
        "min": min(x),
        "p10": quantile(x, 0.10),
        "p25": quantile(x, 0.25),
        "p75": quantile(x, 0.75),
        "p90": quantile(x, 0.90),
        "max": max(x),
    }


def main():
    parser = argparse.ArgumentParser(description="Aggregate model1 replication WF statistics.")
    parser.add_argument(
        "input",
        nargs="?",
        default="data/interim/model1_replication/wf_results.json",
    )
    parser.add_argument(
        "--out",
        default="data/interim/model1_replication/wf_statistical_summary.json",
    )
    args = parser.parse_args()

    source = Path(args.input)
    output = Path(args.out)
    payload = json.loads(source.read_text(encoding="utf-8"))
    folds = payload.get("folds")
    if not isinstance(folds, list) or not folds:
        raise ValueError(f"{source}: expected non-empty 'folds' list")

    valid_folds = [f for f in folds if not f.get("skipped")]
    summary = {
        "source": str(source),
        "n_folds": len(valid_folds),
        "test_rows_total": sum(int(f.get("test_rows", 0)) for f in valid_folds),
        "test_period": {
            "start": min((f["test_start"] for f in valid_folds if f.get("test_start")), default=None),
            "end": max((f["test_end"] for f in valid_folds if f.get("test_end")), default=None),
        },
        "fold_metrics": {},
        "raw_vs_calibrated": {},
        "aggregate_oos": payload.get("aggregate_oos", {}),
    }

    for target in TARGETS:
        for version in VERSIONS:
            for metric in METRICS:
                key = f"{target}_{version}_{metric}"
                values = [
                    f.get(target, {}).get(version, {}).get(metric)
                    for f in valid_folds
                ]
                stats = summarize(values)
                if stats is not None:
                    summary["fold_metrics"][key] = stats

    # LogLoss and Brier are proper scoring rules: lower is better.
    # ROC-AUC and PR-AUC measure ranking/discrimination: higher is better.
    for target in TARGETS:
        for metric, lower_is_better in (("logloss", True), ("brier", True),
                                        ("roc_auc", False), ("pr_auc", False)):
            pairs = []
            for f in valid_folds:
                raw = f.get(target, {}).get("raw", {}).get(metric)
                cal = f.get(target, {}).get("calibrated", {}).get(metric)
                if isinstance(raw, (int, float)) and isinstance(cal, (int, float)):
                    if math.isfinite(float(raw)) and math.isfinite(float(cal)):
                        pairs.append((float(raw), float(cal)))
            raw_better = sum((r < c) if lower_is_better else (r > c) for r, c in pairs)
            cal_better = sum((c < r) if lower_is_better else (c > r) for r, c in pairs)
            summary["raw_vs_calibrated"][f"{target}_{metric}"] = {
                "n_compared_folds": len(pairs),
                "raw_better": raw_better,
                "calibrated_better": cal_better,
                "ties": len(pairs) - raw_better - cal_better,
                "raw_better_share": raw_better / len(pairs) if pairs else None,
            }

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")

    print(f"WF folds: {summary['n_folds']}")
    print(f"Test rows: {summary['test_rows_total']:,}")
    print(f"Test period: {summary['test_period']['start']} .. {summary['test_period']['end']}")
    print("\nFold-level mean / median / std:")
    for key, stats in summary["fold_metrics"].items():
        if key.endswith(("_roc_auc", "_pr_auc", "_logloss", "_brier")):
            print(f"{key:28s} {stats['mean']:.4f} / {stats['median']:.4f} / {stats['std']:.4f}")
    print("\nRaw vs calibrated (raw better / compared):")
    for key, result in summary["raw_vs_calibrated"].items():
        print(f"{key:18s} {result['raw_better']}/{result['n_compared_folds']}")
    print(f"\nAggregate JSON: {output}")


if __name__ == "__main__":
    main()
