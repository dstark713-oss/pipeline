
import argparse
import csv
import json
import math
import statistics
from pathlib import Path


METRICS = (
    "n",
    "pos_rate",
    "logloss",
    "roc_auc",
    "pr_auc",
    "precision",
    "recall",
    "brier",
)


def summarize(values):
    values = [float(v) for v in values if v is not None and math.isfinite(float(v))]
    if not values:
        return None

    values.sort()
    n = len(values)

    def percentile(p):
        if n == 1:
            return values[0]
        pos = (n - 1) * p
        lo = int(pos)
        hi = min(lo + 1, n - 1)
        w = pos - lo
        return values[lo] * (1 - w) + values[hi] * w

    return {
        "n": n,
        "mean": statistics.mean(values),
        "median": statistics.median(values),
        "std": statistics.stdev(values) if n > 1 else 0.0,
        "min": values[0],
        "p10": percentile(0.10),
        "p25": percentile(0.25),
        "p75": percentile(0.75),
        "p90": percentile(0.90),
        "max": values[-1],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
    "input",
    nargs="?",
    default="data/interim/model1_replication/wf_results.json",
    )   
    parser.add_argument(
        "--out",
        default="data/interim/model1_replication/fold_analysis",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    with input_path.open("r", encoding="utf-8") as f:
        data = json.load(f)
        print("INPUT:", input_path.resolve())
        print("ROOT TYPE:", type(data).__name__)
        print("ROOT KEYS:", list(data.keys()) if isinstance(data, dict) else "not a dict")

        folds = data.get("folds") if isinstance(data, dict) else None

        print("FOLDS TYPE:", type(folds).__name__)
        print("FOLDS VALUE:", repr(folds)[:2000])

        if isinstance(folds, list):
            print("FOLDS LENGTH:", len(folds))
    if folds:
        print("FIRST FOLD:", json.dumps(
            folds[0], ensure_ascii=False, indent=2
        )[:3000])

    folds = data.get("folds")
    if not isinstance(folds, list) or not folds:
        raise ValueError("В JSON не найден непустой список folds.")

    rows = []

    for fold in folds:
        row = {
            "fold_id": fold.get("fold_id"),
            "train_rows": fold.get("train_rows"),
            "test_rows": fold.get("test_rows"),
            "train_start": fold.get("train_start"),
            "train_end": fold.get("train_end"),
            "test_start": fold.get("test_start"),
            "test_end": fold.get("test_end"),
            "n_star": fold.get("n_star"),
        }

        for target in ("tp", "sl"):
            for calibration in ("raw", "calibrated"):
                metrics = fold.get(target, {}).get(calibration, {})

                for metric in METRICS:
                    row[f"{target}_{calibration}_{metric}"] = metrics.get(metric)

        rows.append(row)

    csv_path = out_dir / "fold_metrics.csv"
    fields = list(rows[0].keys())

    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    aggregate = {
        "n_folds": len(rows),
        "folds": {},
    }

    metric_columns = [
        key for key in fields
        if key not in {
            "fold_id", "train_rows", "test_rows",
            "train_start", "train_end", "test_start",
            "test_end", "n_star",
        }
    ]

    for column in metric_columns:
        values = [row[column] for row in rows]
        stats = summarize(values)
        if stats is not None:
            aggregate["folds"][column] = stats

    # Direct comparison of raw vs calibrated LogLoss and Brier.
    comparisons = {}

    for target in ("tp", "sl"):
        for metric in ("logloss", "brier"):
            raw_key = f"{target}_raw_{metric}"
            cal_key = f"{target}_calibrated_{metric}"

            pairs = [
                (row[raw_key], row[cal_key])
                for row in rows
                if row[raw_key] is not None and row[cal_key] is not None
            ]

            comparisons[f"{target}_{metric}"] = {
                "n_compared": len(pairs),
                "raw_better_count": sum(raw < cal for raw, cal in pairs),
                "calibrated_better_count": sum(cal < raw for raw, cal in pairs),
                "ties": sum(raw == cal for raw, cal in pairs),
                "raw_better_share": (
                    sum(raw < cal for raw, cal in pairs) / len(pairs)
                    if pairs else None
                ),
                "mean_raw_minus_calibrated": (
                    statistics.mean(raw - cal for raw, cal in pairs)
                    if pairs else None
                ),
            }

    aggregate["raw_vs_calibrated"] = comparisons

    n_star_values = [
        row["n_star"] for row in rows
        if row["n_star"] is not None
    ]

    aggregate["n_star_distribution"] = {
        str(value): n_star_values.count(value)
        for value in sorted(set(n_star_values))
    }

    json_path = out_dir / "fold_aggregate.json"
    with json_path.open("w", encoding="utf-8") as f:
        json.dump(aggregate, f, ensure_ascii=False, indent=2, allow_nan=False)

    print(f"Фолдов обработано: {len(rows)}")
    print(f"CSV: {csv_path}")
    print(f"Aggregate JSON: {json_path}")

    print("\nRaw vs calibrated:")
    for name, result in comparisons.items():
        print(
            f"{name}: raw лучше в "
            f"{result['raw_better_count']}/{result['n_compared']} фолдах"
        )

    print("\nn_star:")
    print(aggregate["n_star_distribution"])


if __name__ == "__main__":
    main()
