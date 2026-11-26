from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_MEMBERSHIP = ROOT / "data/processed/top50/top50_membership.parquet"
DEFAULT_CALENDAR = ROOT / "data/interim/top50_build/daily_summary.csv"
DEFAULT_OUTPUT = ROOT / "data/interim/eda2/block_06"
DEFAULT_DOCS = ROOT / "docs/research/eda2/results/block_06"
LAGS = (1, 5, 20, 60)
GROUPS = ("1-10", "11-25", "26-50")
PERIODS = (
    ("2005_2012", "2005-01-01", "2012-12-31"),
    ("2013_2019", "2013-01-01", "2019-12-31"),
    ("2020_2026", "2020-01-01", "2026-12-31"),
)


def parse_args():
    p = argparse.ArgumentParser(description="EDA2 Block 6: PIT membership and rank mobility.")
    p.add_argument("--membership", type=Path, default=DEFAULT_MEMBERSHIP)
    p.add_argument("--calendar", type=Path, default=DEFAULT_CALENDAR)
    p.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    p.add_argument("--docs-dir", type=Path, default=DEFAULT_DOCS)
    return p.parse_args()


def load_inputs(membership_path, calendar_path):
    membership = pd.read_parquet(
        membership_path, columns=["tradedate", "secid", "rank", "universe_size"]
    )
    membership["tradedate"] = pd.to_datetime(membership["tradedate"], errors="coerce")
    membership["secid"] = membership["secid"].astype(str).str.upper()
    for col in ("rank", "universe_size"):
        membership[col] = pd.to_numeric(membership[col], errors="coerce")
    membership = membership.dropna().copy()
    membership["rank"] = membership["rank"].astype(int)
    membership["universe_size"] = membership["universe_size"].astype(int)
    membership = membership.sort_values(["tradedate", "rank", "secid"]).reset_index(drop=True)
    if membership.empty:
        raise ValueError("PIT membership input is empty.")
    if membership.duplicated(["tradedate", "secid"]).any():
        raise ValueError("Duplicate (tradedate, secid) membership rows.")
    if membership.duplicated(["tradedate", "rank"]).any():
        raise ValueError("Duplicate rank within a date.")
    if not membership["rank"].between(1, 50).all():
        raise ValueError("Rank outside TOP50 range.")

    calendar = pd.read_csv(calendar_path, parse_dates=["tradedate"])
    calendar = calendar[["tradedate", "universe_size"]].copy()
    calendar["tradedate"] = pd.to_datetime(calendar["tradedate"], errors="coerce")
    calendar["universe_size"] = pd.to_numeric(calendar["universe_size"], errors="coerce")
    calendar = calendar.dropna(subset=["tradedate"]).drop_duplicates("tradedate")
    calendar = calendar.sort_values("tradedate").reset_index(drop=True)
    calendar = calendar.loc[
        calendar["tradedate"] <= membership["tradedate"].max()
    ].copy()
    if calendar.empty:
        raise ValueError("No calendar sessions overlap membership sample.")

    dates = pd.DatetimeIndex(calendar["tradedate"])
    actual = membership.groupby("tradedate")["secid"].nunique()
    expected = calendar.set_index("tradedate")["universe_size"]
    common = actual.index.intersection(expected.index)
    meta = {
        "membership_path": str(membership_path),
        "calendar_path": str(calendar_path),
        "membership_rows": int(len(membership)),
        "membership_dates": int(membership["tradedate"].nunique()),
        "calendar_sessions": int(len(dates)),
        "securities": int(membership["secid"].nunique()),
        "sample_start": str(dates.min().date()),
        "sample_end": str(dates.max().date()),
        "calendar_sessions_without_membership": int(len(dates.difference(actual.index))),
        "membership_calendar_count_mismatches": int((actual.loc[common] != expected.loc[common]).sum()),
        "calendar_definition": "Trading-session calendar from TOP50 builder daily_summary.csv; zero-universe sessions retained.",
    }
    return membership, calendar, dates, meta


def make_spells(membership, dates):
    tickers = sorted(membership["secid"].unique())
    flags = (membership.assign(member=1)
             .pivot(index="tradedate", columns="secid", values="member")
             .reindex(index=dates, columns=tickers).fillna(0).astype("int8"))
    spell_rows, security_rows = [], []
    n_dates = len(dates)
    for ticker in tickers:
        x = flags[ticker].to_numpy(dtype=bool)
        edges = np.diff(np.r_[False, x, False].astype("int8"))
        starts, ends = np.flatnonzero(edges == 1), np.flatnonzero(edges == -1) - 1
        for num, (a, b) in enumerate(zip(starts, ends), 1):
            left, right = a == 0, b == n_dates - 1
            status = "both" if left and right else "left" if left else "right" if right else "complete"
            spell_rows.append({
                "secid": ticker, "spell_number": num,
                "start_date": dates[a], "end_date": dates[b],
                "duration_sessions": int(b - a + 1),
                "left_censored": left, "right_censored": right,
                "censoring_status": status,
            })
        durations = ends - starts + 1
        security_rows.append({
            "secid": ticker, "spell_count": int(len(starts)),
            "total_membership_sessions": int(x.sum()),
            "membership_share": float(x.mean()),
            "mean_spell_duration": float(durations.mean()) if len(durations) else np.nan,
            "max_spell_duration": int(durations.max()) if len(durations) else 0,
        })
    spells = pd.DataFrame(spell_rows)
    if not spells.empty:
        starts = pd.to_datetime(spells["start_date"])
        spells["start_period"] = "outside_defined_periods"
        for name, lo, hi in PERIODS:
            spells.loc[starts.between(lo, hi), "start_period"] = name
    return spells, pd.DataFrame(security_rows)


def summarize_spells(spells):
    if spells.empty:
        return pd.DataFrame()
    rows = []
    for (status, period), g in spells.groupby(["censoring_status", "start_period"]):
        x = g["duration_sessions"]
        rows.append({
            "censoring_status": status, "start_period": period, "spell_count": len(x),
            "mean_duration_sessions": x.mean(), "median_duration_sessions": x.median(),
            "q25_duration_sessions": x.quantile(.25), "q75_duration_sessions": x.quantile(.75),
            "q90_duration_sessions": x.quantile(.90), "max_duration_sessions": x.max(),
        })
    return pd.DataFrame(rows).sort_values(["start_period", "censoring_status"])


def make_composition(membership, calendar):
    members = {d: set(g["secid"]) for d, g in membership.groupby("tradedate")}
    rows, previous, baseline_set = [], set(), False
    for row in calendar.itertuples(index=False):
        date = pd.Timestamp(row.tradedate)
        current = members.get(date, set())
        # The first non-empty universe establishes the comparison baseline.
        # Its initial population is not misclassified as daily turnover.
        baseline = bool(current) and not baseline_set
        if baseline:
            retained, entrants, exits = set(), set(), set()
            previous_size = 0
            baseline_set = True
        else:
            retained = previous & current
            entrants = current - previous
            exits = previous - current
            previous_size = len(previous)
        union = previous | current
        rows.append({
            "tradedate": date, "universe_size": len(current),
            "previous_universe_size": previous_size,
            "retained_count": len(retained), "entry_count": len(entrants), "exit_count": len(exits),
            "retention_of_previous": len(retained) / previous_size if previous_size and not baseline else np.nan,
            "retention_of_current": len(retained) / len(current) if current and not baseline else np.nan,
            "jaccard_similarity": len(retained) / len(union) if union and not baseline else np.nan,
            "composition_changed": bool(entrants or exits) if not baseline else False,
            "is_initial_baseline": baseline,
            "entry_tickers": ";".join(sorted(entrants)),
            "exit_tickers": ";".join(sorted(exits)),
        })
        if current or baseline_set:
            previous = current
    return pd.DataFrame(rows)


def summarize_composition(composition):
    dates = pd.to_datetime(composition["tradedate"])
    rows = []
    for name, lo, hi in PERIODS:
        g = composition.loc[dates.between(lo, hi)]
        if g.empty:
            continue
        rows.append({
            "period": name, "sessions": len(g),
            "mean_universe_size": g["universe_size"].mean(),
            "median_universe_size": g["universe_size"].median(),
            "mean_retained_count": g["retained_count"].mean(),
            "mean_entry_count": g["entry_count"].mean(),
            "mean_exit_count": g["exit_count"].mean(),
            "mean_retention_of_previous": g["retention_of_previous"].mean(),
            "mean_jaccard_similarity": g["jaccard_similarity"].mean(),
            "composition_change_share": g["composition_changed"].mean(),
        })
    return pd.DataFrame(rows)


def group_name(rank):
    return "1-10" if rank <= 10 else "11-25" if rank <= 25 else "26-50"


def rank_analysis(membership, dates):
    ranks = membership.pivot(index="tradedate", columns="secid", values="rank").reindex(index=dates)
    present = ranks.notna()
    pair_frames, transition_rows, daily_corr_rows = [], [], []
    for lag in LAGS:
        continuous = present.astype("int8").rolling(lag + 1, min_periods=lag + 1).sum().eq(lag + 1)
        prior = ranks.shift(lag)
        valid = continuous & ranks.notna() & prior.notna()
        cur_long = ranks.where(valid).stack().rename("rank_current").reset_index()
        prev_long = prior.where(valid).stack().rename("rank_prior").reset_index()
        pairs = cur_long.merge(prev_long, on=["tradedate", "secid"], validate="one_to_one")
        if pairs.empty:
            continue
        pairs["lag_sessions"] = lag
        pairs["rank_change"] = pairs["rank_current"] - pairs["rank_prior"]
        pairs["abs_rank_change"] = pairs["rank_change"].abs()
        pairs["group_prior"] = pairs["rank_prior"].astype(int).map(group_name)
        pairs["group_current"] = pairs["rank_current"].astype(int).map(group_name)
        pair_frames.append(pairs)
        for old in GROUPS:
            for new in GROUPS:
                transition_rows.append({
                    "lag_sessions": lag, "group_prior": old, "group_current": new,
                    "transition_count": int(((pairs["group_prior"] == old) & (pairs["group_current"] == new)).sum()),
                })
        for date, daily in pairs.groupby("tradedate"):
            if len(daily) >= 3:
                daily_corr_rows.append({
                    "tradedate": date, "lag_sessions": lag, "continuous_members": len(daily),
                    "pearson_rank_corr": daily["rank_prior"].corr(daily["rank_current"], method="pearson"),
                    "spearman_rank_corr": daily["rank_prior"].corr(daily["rank_current"], method="spearman"),
                })

    pairs = pd.concat(pair_frames, ignore_index=True) if pair_frames else pd.DataFrame()
    transitions = pd.DataFrame(transition_rows)
    if not transitions.empty:
        totals = transitions.groupby("lag_sessions")["transition_count"].transform("sum")
        row_totals = transitions.groupby(["lag_sessions", "group_prior"])["transition_count"].transform("sum")
        transitions["share_all_transitions"] = transitions["transition_count"] / totals.replace(0, np.nan)
        transitions["conditional_share"] = transitions["transition_count"] / row_totals.replace(0, np.nan)

    daily_corr = pd.DataFrame(daily_corr_rows)
    summaries = []
    if not pairs.empty:
        for lag, g in pairs.groupby("lag_sessions"):
            summaries.append({
                "lag_sessions": lag, "continuous_pairs": len(g),
                "mean_signed_rank_change": g["rank_change"].mean(),
                "median_signed_rank_change": g["rank_change"].median(),
                "median_absolute_rank_change": g["abs_rank_change"].median(),
                "q75_absolute_rank_change": g["abs_rank_change"].quantile(.75),
                "q90_absolute_rank_change": g["abs_rank_change"].quantile(.90),
                "share_abs_change_le_5": g["abs_rank_change"].le(5).mean(),
                "share_abs_change_gt_10": g["abs_rank_change"].gt(10).mean(),
                "pooled_pearson_rank_corr": g["rank_prior"].corr(g["rank_current"], method="pearson"),
                "pooled_spearman_rank_corr": g["rank_prior"].corr(g["rank_current"], method="spearman"),
            })
    summary = pd.DataFrame(summaries)
    if not daily_corr.empty:
        daily_summary = daily_corr.groupby("lag_sessions").agg(
            dates=("tradedate", "count"),
            median_daily_spearman=("spearman_rank_corr", "median"),
            q25_daily_spearman=("spearman_rank_corr", lambda x: x.quantile(.25)),
            q75_daily_spearman=("spearman_rank_corr", lambda x: x.quantile(.75)),
            median_continuous_members=("continuous_members", "median"),
        ).reset_index()
        summary = summary.merge(daily_summary, on="lag_sessions", how="left")
    return pairs, transitions, summary, daily_corr


def write_report(path, meta, spell_summary, security_summary, composition_summary, mobility, transitions):
    lines = [
        "# EDA2 — Блок 6. Динамика PIT membership и мобильность рангов", "",
        "## Выборка",
        f"- Календарных торговых сессий: {meta['calendar_sessions']:,}",
        f"- Дат с membership: {meta['membership_dates']:,}",
        f"- Бумаг: {meta['securities']:,}; строк membership: {meta['membership_rows']:,}",
        f"- Период: {meta['sample_start']} — {meta['sample_end']}",
        "- Используется готовый PIT rank из top50_membership.parquet; повторное ранжирование не выполняется.",
        "- Лаги измеряются по полному календарю торговых сессий TOP50 builder от начала панели, включая начальные сессии с нулевым universe."); "",
        "## Длительность членства",
        "Spell включает обе граничные сессии. Начало/конец наблюдаемого окна помечаются как левое/правое цензурирование.",
        "",
        "| Цензурирование | Когорта начала | Spells | Median | Q25 | Q75 | Q90 | Max |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for r in spell_summary.itertuples(index=False):
        lines.append(f"| {r.censoring_status} | {r.start_period} | {r.spell_count} | {r.median_duration_sessions:.1f} | {r.q25_duration_sessions:.1f} | {r.q75_duration_sessions:.1f} | {r.q90_duration_sessions:.1f} | {r.max_duration_sessions} |")
    lines += [
        "", f"- Бумаг с хотя бы одним spell: {security_summary['secid'].nunique() if not security_summary.empty else 0:,}.",
        "- Индивидуальные числа spell, суммарные сессии и доли присутствия находятся в security_spell_summary.csv.",
        "- Длительность цензурированных spell не является полной длительностью членства.", "",
        "## Мобильность рангов внутри непрерывного членства",
        "Для лага L бумага должна присутствовать на каждой сессии от t-L до t включительно. Выходы и повторные входы не получают искусственный ранг.",
        "",
        "| Лаг | Пар | Median abs Δrank | Q90 abs Δrank | Share ≤5 | Share >10 | Pooled Spearman | Daily median Spearman |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in mobility.itertuples(index=False):
        daily = f"{r.median_daily_spearman:.4f}" if pd.notna(r.median_daily_spearman) else "NA"
        lines.append(f"| {r.lag_sessions} | {r.continuous_pairs:,} | {r.median_absolute_rank_change:.2f} | {r.q90_absolute_rank_change:.2f} | {r.share_abs_change_le_5:.1%} | {r.share_abs_change_gt_10:.1%} | {r.pooled_spearman_rank_corr:.4f} | {daily} |")
    lines += [
        "", "### Переходы между ранговыми группами",
        "Переходы условны на непрерывном присутствии. Доли нормированы по исходной группе; события входа/выхода анализируются отдельно.",
        "", "| Лаг | Исходная | 1–10 | 11–25 | 26–50 |",
        "|---:|---|---:|---:|---:|",
    ]
    for lag in LAGS:
        for old in GROUPS:
            g = transitions.loc[(transitions["lag_sessions"] == lag) & (transitions["group_prior"] == old)]
            if not g.empty:
                vals = g.set_index("group_current")["conditional_share"]
                cells = [f"{vals.get(k, np.nan):.1%}" if pd.notna(vals.get(k, np.nan)) else "NA" for k in GROUPS]
                lines.append(f"| {lag} | {old} | " + " | ".join(cells) + " |")
    lines += [
        "", "## Оборот состава universe",
        "| Период | Сессий | Mean N | Retained | Entries | Exits | Retention prev | Jaccard | Changed share |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in composition_summary.itertuples(index=False):
        lines.append(f"| {r.period} | {r.sessions:,} | {r.mean_universe_size:.2f} | {r.mean_retained_count:.2f} | {r.mean_entry_count:.2f} | {r.mean_exit_count:.2f} | {r.mean_retention_of_previous:.1%} | {r.mean_jaccard_similarity:.1%} | {r.composition_change_share:.1%} |")
    lines += [
        "", "- Retention(prev) = retained / previous universe; Jaccard = retained / union(previous, current).",
        "- Первая непустая выборка universe используется как baseline и не считается дневным входом/выходом; последующие изменения сравниваются с предыдущей торговой сессией.",
        "- Точные тикеры входов/выходов сохранены в daily_composition.csv.", "",
        "## Ограничения",
        "- Только описательная динамика PIT membership: без моделей, IC, прогнозов, торговых правил и портфельных выводов.",
        "- Ранговая мобильность условна на непрерывном членстве и не описывает выбывшие бумаги.",
        "- Период 2020–2026 неполный; периодные сравнения описательные.",
        "- Исходное ранжирование: rolling VALUE за 60 сессий с лагом в одну сессию.",
        "", "## Outputs",
        "- membership_spells.csv; security_spell_summary.csv; membership_duration_summary.csv",
        "- daily_composition.csv; universe_composition_summary.csv",
        "- rank_lag_pairs.csv; rank_group_transitions.csv; rank_mobility_summary.csv; daily_rank_autocorrelation.csv",
        "- EDA2_BLOCK_06_REPORT.md",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.docs_dir.mkdir(parents=True, exist_ok=True)
    membership, calendar, dates, meta = load_inputs(args.membership, args.calendar)
    spells, security_summary = make_spells(membership, dates)
    spell_summary = summarize_spells(spells)
    composition = make_composition(membership, calendar)
    composition_summary = summarize_composition(composition)
    rank_pairs, transitions, mobility, daily_corr = rank_analysis(membership, dates)

    spells.to_csv(args.output_dir / "membership_spells.csv", index=False)
    rank_pairs.to_csv(args.output_dir / "rank_lag_pairs.csv", index=False)
    composition.to_csv(args.output_dir / "daily_composition.csv", index=False)
    metadata = {
        **meta, "created_at_utc": datetime.now(timezone.utc).isoformat(), "block": 6,
        "rank_lags_sessions": list(LAGS), "rank_groups": list(GROUPS),
        "rank_source": "rank column from top50_membership.parquet; no re-ranking.",
        "rank_pair_rule": "Security is present on every calendar session from t-lag through t inclusive.",
        "spell_rule": "Inclusive session count; left/right censoring flagged at observed sample boundaries.",
    }
    (args.output_dir / "run_metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    security_summary.to_csv(args.docs_dir / "security_spell_summary.csv", index=False)
    spell_summary.to_csv(args.docs_dir / "membership_duration_summary.csv", index=False)
    composition_summary.to_csv(args.docs_dir / "universe_composition_summary.csv", index=False)
    transitions.to_csv(args.docs_dir / "rank_group_transitions.csv", index=False)
    mobility.to_csv(args.docs_dir / "rank_mobility_summary.csv", index=False)
    daily_corr.to_csv(args.docs_dir / "daily_rank_autocorrelation.csv", index=False)
    write_report(args.docs_dir / "EDA2_BLOCK_06_REPORT.md", meta, spell_summary,
                 security_summary, composition_summary, mobility, transitions)
    print("EDA2 Block 6 completed.")
    print(f"Membership spells: {len(spells):,}; rank lag pairs: {len(rank_pairs):,}")
    print(f"Calendar sessions: {len(dates):,}")
    print(f"Machine outputs: {args.output_dir}")
    print(f"Research outputs: {args.docs_dir}")


if __name__ == "__main__":
    main()
