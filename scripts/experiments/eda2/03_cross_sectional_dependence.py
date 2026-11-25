from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_PANEL = ROOT / "data" / "processed" / "top50" / "top50_panel.parquet"
DEFAULT_OUTPUT = ROOT / "data" / "interim" / "eda2" / "block_03"
DEFAULT_PROCESSED = ROOT / "data" / "processed" / "eda2" / "block_03"

WINDOWS = (60, 120, 240)
ROLLING_STEP = 20
MIN_PAIR_OBS = 60
MIN_ROLLING_PAIR_OBS = 40


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="EDA2 Block 3: cross-sectional dependence and co-movement."
    )
    parser.add_argument("--panel", type=Path, default=DEFAULT_PANEL)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--processed-dir", type=Path, default=DEFAULT_PROCESSED)
    parser.add_argument("--rolling-step", type=int, default=ROLLING_STEP)
    parser.add_argument("--min-pair-obs", type=int, default=MIN_PAIR_OBS)
    return parser.parse_args()


def load_returns(panel_path: Path) -> tuple[pd.DataFrame, dict]:
    if not panel_path.exists():
        raise FileNotFoundError(f"PIT panel not found: {panel_path}")

    columns = [
        "tradedate", "secid", "adjusted_close", "bar_available",
    ]
    panel = pd.read_parquet(panel_path, columns=columns)
    panel["tradedate"] = pd.to_datetime(panel["tradedate"], errors="coerce")
    panel["secid"] = panel["secid"].astype(str).str.upper()
    panel["adjusted_close"] = pd.to_numeric(panel["adjusted_close"], errors="coerce")
    panel["bar_available"] = pd.to_numeric(panel["bar_available"], errors="coerce")

    panel = panel.dropna(subset=["tradedate", "secid"])
    panel = panel.sort_values(["tradedate", "secid"])

    if panel.duplicated(["tradedate", "secid"]).any():
        raise ValueError("Duplicate (tradedate, secid) rows in PIT panel.")

    dates = pd.DatetimeIndex(sorted(panel["tradedate"].unique()))
    prices = panel.pivot(index="tradedate", columns="secid", values="adjusted_close")
    available = panel.pivot(index="tradedate", columns="secid", values="bar_available")
    prices = prices.reindex(index=dates)
    available = available.reindex(index=dates).fillna(0).eq(1)

    previous_prices = prices.shift(1)
    previous_available = available.shift(1)
    valid = (
        available
        & previous_available
        & prices.gt(0)
        & previous_prices.gt(0)
    )

    values = np.log(prices.to_numpy(dtype=np.float64) /
                    previous_prices.to_numpy(dtype=np.float64))
    values[~valid.to_numpy()] = np.nan

    returns = pd.DataFrame(values, index=dates, columns=prices.columns)
    returns = returns.iloc[1:].copy()

    metadata = {
        "panel_path": str(panel_path),
        "panel_rows_read": int(len(panel)),
        "panel_dates": int(len(dates)),
        "panel_tickers": int(panel["secid"].nunique()),
        "return_dates": int(len(returns)),
        "return_observations": int(np.isfinite(values[1:]).sum()),
        "return_definition": (
            "log(adjusted_close_t / adjusted_close_t-1); "
            "both observations must be PIT members with bar_available=1 "
            "on adjacent panel trading sessions"
        ),
        "forward_fill": False,
        "external_data_requests": 0,
    }
    return returns, metadata


def pairwise_corr_numpy(
    frame: pd.DataFrame,
    min_obs: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Pairwise-complete Pearson/Spearman correlations using NumPy matrix algebra."""
    x = frame.to_numpy(dtype=np.float64)
    mask = np.isfinite(x)
    m = mask.astype(np.float64)
    z = np.where(mask, x, 0.0)

    n = m.T @ m
    sx = z.T @ m
    sy = sx.T
    sxx = (z * z).T @ m
    syy = sxx.T
    sxy = z.T @ z

    with np.errstate(divide="ignore", invalid="ignore"):
        cov_num = sxy - (sx * sy) / n
        var_x = sxx - (sx * sx) / n
        var_y = syy - (sy * sy) / n
        denom = np.sqrt(np.maximum(var_x, 0.0) * np.maximum(var_y, 0.0))
        corr = cov_num / denom

    corr[(n < min_obs) | (denom <= 0)] = np.nan
    np.fill_diagonal(corr, np.where(np.diag(n) >= min_obs, 1.0, np.nan))
    return corr, n.astype(np.int32), n


def rank_columns(frame: pd.DataFrame) -> pd.DataFrame:
    # Average ranks handle ties; ranking is performed independently per security.
    return frame.rank(axis=0, method="average", na_option="keep")


def matrix_to_long(
    matrix: np.ndarray,
    counts: np.ndarray,
    tickers: list[str],
    metric: str,
    period: str,
) -> pd.DataFrame:
    i, j = np.triu_indices(len(tickers), k=1)
    return pd.DataFrame({
        "period": period,
        "metric": metric,
        "secid_1": np.asarray(tickers)[i],
        "secid_2": np.asarray(tickers)[j],
        "correlation": matrix[i, j],
        "pair_observations": counts[i, j],
    })


def matrix_summary(matrix: np.ndarray) -> dict:
    upper = matrix[np.triu_indices_from(matrix, k=1)]
    upper = upper[np.isfinite(upper)]
    if not len(upper):
        return {"valid_pairs": 0}
    return {
        "valid_pairs": int(len(upper)),
        "mean": float(np.mean(upper)),
        "median": float(np.median(upper)),
        "q25": float(np.quantile(upper, 0.25)),
        "q75": float(np.quantile(upper, 0.75)),
        "q05": float(np.quantile(upper, 0.05)),
        "q95": float(np.quantile(upper, 0.95)),
        "negative_share": float(np.mean(upper < 0)),
    }


def rolling_dependence(
    returns: pd.DataFrame,
    windows: tuple[int, ...],
    step: int,
    min_obs: int,
) -> pd.DataFrame:
    rows: list[dict] = []
    n_dates = len(returns)

    for window in windows:
        if n_dates < window:
            continue
        for end in range(window, n_dates + 1, step):
            sample = returns.iloc[end - window:end]
            corr, counts, _ = pairwise_corr_numpy(sample, MIN_ROLLING_PAIR_OBS)
            stats = matrix_summary(corr)
            rows.append({
                "window_sessions": window,
                "window_start": sample.index[0].date().isoformat(),
                "window_end": sample.index[-1].date().isoformat(),
                "n_dates": int(len(sample)),
                "min_pair_observations": min_obs,
                **stats,
            })

    return pd.DataFrame(rows)


def eigen_spectrum(
    corr: np.ndarray,
    tickers: list[str],
    period: str,
) -> tuple[pd.DataFrame, dict]:
    # Pairwise deletion can yield a non-PSD matrix. Restrict spectral analysis
    # to securities with complete off-diagonal correlations, then use symmetric
    # eigendecomposition. The retained universe is explicitly reported.
    valid_counts = np.isfinite(corr).sum(axis=0)
    keep = valid_counts == len(tickers)
    indices = np.flatnonzero(keep)

    if len(indices) < 3:
        return pd.DataFrame(), {
            "period": period,
            "spectral_status": "insufficient_complete_correlation_universe",
            "complete_tickers": int(len(indices)),
        }

    sub = corr[np.ix_(indices, indices)]
    sub = (sub + sub.T) / 2.0
    eig = np.linalg.eigvalsh(sub)[::-1]
    eig = np.maximum(eig, 0.0)
    total = eig.sum()
    explained = eig / total if total > 0 else np.full_like(eig, np.nan)

    spectrum = pd.DataFrame({
        "period": period,
        "component": np.arange(1, len(eig) + 1),
        "eigenvalue": eig,
        "explained_share": explained,
        "cumulative_explained_share": np.cumsum(explained),
    })
    summary = {
        "period": period,
        "spectral_status": "ok",
        "complete_tickers": int(len(indices)),
        "top_1_explained_share": float(explained[0]),
        "top_3_explained_share": float(np.sum(explained[:3])),
        "top_5_explained_share": float(np.sum(explained[:5])),
        "eigenvalue_sum": float(total),
    }
    return spectrum, summary


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.processed_dir.mkdir(parents=True, exist_ok=True)

    returns, metadata = load_returns(args.panel)
    tickers = list(returns.columns)

    pearson, counts, _ = pairwise_corr_numpy(returns, args.min_pair_obs)
    spearman, _, _ = pairwise_corr_numpy(rank_columns(returns), args.min_pair_obs)

    pairwise = pd.concat([
        matrix_to_long(pearson, counts, tickers, "pearson", "full_sample"),
        matrix_to_long(spearman, counts, tickers, "spearman", "full_sample"),
    ], ignore_index=True)
    pairwise.to_csv(args.output_dir / "pairwise_correlations.csv", index=False)

    # Yearly cross-sectional dependence summaries and spectra.
    yearly_rows: list[dict] = []
    yearly_spectra: list[pd.DataFrame] = []
    for year, sample in returns.groupby(returns.index.year):
        if len(sample) < args.min_pair_obs:
            continue
        corr, year_counts, _ = pairwise_corr_numpy(sample, args.min_pair_obs)
        yearly_rows.append({
            "year": int(year),
            "n_dates": int(len(sample)),
            **matrix_summary(corr),
        })
        spectrum, _ = eigen_spectrum(corr, tickers, str(year))
        if not spectrum.empty:
            yearly_spectra.append(spectrum)

    pd.DataFrame(yearly_rows).to_csv(
        args.output_dir / "yearly_dependence_summary.csv", index=False
    )
    if yearly_spectra:
        pd.concat(yearly_spectra, ignore_index=True).to_csv(
            args.output_dir / "yearly_eigen_spectrum.csv", index=False
        )

    rolling = rolling_dependence(
        returns, WINDOWS, args.rolling_step, MIN_ROLLING_PAIR_OBS
    )
    rolling.to_csv(args.output_dir / "rolling_dependence_summary.csv", index=False)

    spectrum, spectral_summary = eigen_spectrum(pearson, tickers, "full_sample")
    if not spectrum.empty:
        spectrum.to_csv(args.output_dir / "full_sample_eigen_spectrum.csv", index=False)

    # Persist the pooled Pearson matrix for downstream inspection.
    pd.DataFrame(pearson, index=tickers, columns=tickers).to_csv(
        args.output_dir / "full_sample_pearson_matrix.csv"
    )

    metadata.update({
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "block": 3,
        "block_name": "Межбумажная зависимость и совместное движение",
        "windows": list(WINDOWS),
        "rolling_step_sessions": args.rolling_step,
        "min_pair_observations": args.min_pair_obs,
        "min_rolling_pair_observations": MIN_ROLLING_PAIR_OBS,
        "pearson_summary": matrix_summary(pearson),
        "spearman_summary": matrix_summary(spearman),
        "spectral_summary": spectral_summary,
        "method_notes": [
            "Pairwise-complete observations; no imputation or forward-fill.",
            "Spearman uses average ranks within each security over the analyzed sample.",
            "Rolling matrices are sampled every rolling_step_sessions to control runtime.",
            "Eigen analysis is restricted to the complete-correlation sub-universe.",
            "Pairwise deletion may make the full correlation matrix non-positive-semidefinite.",
            "No prediction target, IC ranking, model, trading rule, or portfolio metric is calculated.",
        ],
        "outputs": [
            "pairwise_correlations.csv",
            "yearly_dependence_summary.csv",
            "yearly_eigen_spectrum.csv",
            "rolling_dependence_summary.csv",
            "full_sample_eigen_spectrum.csv",
            "full_sample_pearson_matrix.csv",
        ],
    })
    (args.output_dir / "run_metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    report = [
        "# EDA2 — Блок 3. Межбумажная зависимость и совместное движение",
        "",
        "## Область анализа",
        f"- Дат доходностей: {len(returns):,}",
        f"- Бумаг в матрице: {len(tickers):,}",
        f"- Наблюдений доходности: {metadata['return_observations']:,}",
        f"- Средняя корреляция Пирсона: {metadata['pearson_summary'].get('mean', float('nan')):.6f}",
        f"- Медианная корреляция Пирсона: {metadata['pearson_summary'].get('median', float('nan')):.6f}",
        f"- Средняя корреляция Спирмена: {metadata['spearman_summary'].get('mean', float('nan')):.6f}",
        f"- Медианная корреляция Спирмена: {metadata['spearman_summary'].get('median', float('nan')):.6f}",
        "",
        "## Спектральное разложение",
        f"- Статус: {spectral_summary.get('spectral_status', 'not_available')}",
        f"- Бумаг в полном корреляционном подмножестве: {spectral_summary.get('complete_tickers', 0)}",
        f"- Доля первой компоненты: {spectral_summary.get('top_1_explained_share', float('nan')):.6f}",
        f"- Доля первых трёх компонент: {spectral_summary.get('top_3_explained_share', float('nan')):.6f}",
        "",
        "## Ограничения интерпретации",
        "- Корреляция описывает совместное линейное/ранговое движение, но не причинность.",
        "- Попарное исключение пропусков означает, что разные пары могут оцениваться на разных датах.",
        "- Спектр рассчитан только на подмножестве с полной матрицей попарных корреляций.",
        "- Скользящие оценки являются описательными срезами и не используются как прогноз.",
        "- Это исследование не выполняет отбор признаков, оценку IC или обучение модели.",
        "",
        "Числа в этом отчёте являются результатом фактического запуска только после выполнения скрипта на локальной панели.",
    ]
    (args.processed_dir / "EDA2_BLOCK_03_REPORT.md").write_text(
        "\n".join(report) + "\n", encoding="utf-8"
    )

    print(json.dumps(metadata, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
