# Folder: scripts/experiments/primitives/portfolios/
# File: summarize_audit_for_assistant.py
# Purpose: Compress audit CSV outputs into a short, decision-oriented report.
#
# Run from repository root:
#   python scripts/experiments/primitives/portfolios/summarize_audit_for_assistant.py
#
# Reads audit CSVs and daily_equity_curves.csv. Does not modify source outputs.

from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
OUTPUT_DIR = ROOT / "data/interim/primitive_research/portfolios"
AUDIT_DIR = OUTPUT_DIR / "audit"
OUT_PATH = AUDIT_DIR / "assistant_summary.md"

KEY_STRATEGIES = [
    "baseline_top50",
    "drawdown60_top10",
    "drawdown60_top10_breadth",
    "zscore_top10",
    "zscore_top10_breadth",
    "realized_vol60_top10",
    "realized_vol60_top10_breadth",
]
FILES = {
    "extremes": AUDIT_DIR / "daily_extremes_top20.csv",
    "concentration": AUDIT_DIR / "daily_concentration.csv",
    "stress": AUDIT_DIR / "best_day_removal_stress.csv",
    "years": AUDIT_DIR / "calendar_year_diagnostics.csv",
    "tickers": AUDIT_DIR / "ticker_contribution_diagnostics.csv",
    "daily": OUTPUT_DIR / "daily_equity_curves.csv",
}


def read_csv(key: str, required: bool = True) -> pd.DataFrame:
    path = FILES[key]
    if not path.exists():
        if required:
            raise FileNotFoundError(f"Missing {path}. Run audit_results.py first.")
        return pd.DataFrame()
    return pd.read_csv(path)


def fmt_pct(x) -> str:
    if pd.isna(x):
        return "NA"
    return f"{float(x) * 100:.2f}%"


def fmt_num(x, digits: int = 3) -> str:
    if pd.isna(x):
        return "NA"
    return f"{float(x):,.{digits}f}"


def select_strategies(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty or "strategy" not in frame:
        return frame
    present = [s for s in KEY_STRATEGIES if s in set(frame["strategy"])]
    return frame[frame["strategy"].isin(present)].copy()


def daily_summary(daily: pd.DataFrame) -> pd.DataFrame:
    d = daily.copy()
    d["transaction_cost_bps"] = pd.to_numeric(d["transaction_cost_bps"], errors="coerce")
    d = d[d["transaction_cost_bps"].eq(0)].copy()
    for c in ["net_return", "effective_exposure", "missing_return_weight", "turnover_one_way"]:
        d[c] = pd.to_numeric(d[c], errors="coerce")
    rows = []
    for strategy, g in d.groupby("strategy"):
        g = g.sort_values("exit_date")
        r = g["net_return"].dropna()
        wealth = float((1 + r).prod()) if len(r) else np.nan
        years = len(r) / 252 if len(r) else np.nan
        cagr = wealth ** (1 / years) - 1 if years and wealth > 0 else np.nan
        rows.append({
            "strategy": strategy,
            "cagr": cagr,
            "terminal_multiple": wealth,
            "mean_exposure": g["effective_exposure"].mean(),
            "mean_missing": g["missing_return_weight"].mean(),
            "max_missing": g["missing_return_weight"].max(),
            "mean_turnover": g["turnover_one_way"].mean(),
        })
    return pd.DataFrame(rows)


def build_report() -> str:
    extremes = select_strategies(read_csv("extremes"))
    concentration = select_strategies(read_csv("concentration"))
    stress = select_strategies(read_csv("stress"))
    years = select_strategies(read_csv("years"))
    tickers = select_strategies(read_csv("tickers"))
    daily = select_strategies(read_csv("daily"))
    core = daily_summary(daily)

    lines = [
        "# Краткая сводка аудита портфельного эксперимента",
        "",
        "Сформировано автоматически из audit CSV и daily_equity_curves.csv. Это навигационная сводка для дальнейшего разбора, а не подтверждение корректности backtest.",
        "",
        "## 1. Общая картина (0 bps)",
        "",
    ]

    if not core.empty:
        lines += [
            "| Strategy | CAGR | Конечный капитал | Exposure | Missing weight avg/max | Turnover |",
            "|---|---:|---:|---:|---:|---:|",
        ]
        for _, x in core.iterrows():
            lines.append(
                f"| {x['strategy']} | {fmt_pct(x['cagr'])} | {fmt_num(x['terminal_multiple'], 2)}x "
                f"| {fmt_pct(x['mean_exposure'])} | {fmt_pct(x['mean_missing'])} / {fmt_pct(x['max_missing'])} "
                f"| {fmt_num(x['mean_turnover'])} |"
            )
    else:
        lines.append("Нет данных для общей сводки.")

    lines += ["", "## 2. Зависимость от лучших дней", ""]
    if not stress.empty:
        stress["removed_best_days"] = pd.to_numeric(stress["removed_best_days"], errors="coerce")
        stress["cagr_252"] = pd.to_numeric(stress["cagr_252"], errors="coerce")
        stress["total_return"] = pd.to_numeric(stress["total_return"], errors="coerce")
        stress20 = stress[stress["removed_best_days"].eq(20)]
        lines += [
            "| Strategy | CAGR исходный | CAGR без 20 лучших дней | Return без 20 лучших дней |",
            "|---|---:|---:|---:|",
        ]
        base_cagr = stress[stress["removed_best_days"].eq(0)].set_index("strategy")["cagr_252"]
        for _, x in stress20.iterrows():
            original = base_cagr.get(x["strategy"], np.nan)
            lines.append(
                f"| {x['strategy']} | {fmt_pct(original)} | {fmt_pct(x['cagr_252'])} "
                f"| {fmt_pct(x['total_return'])} |"
            )
    else:
        lines.append("Нет данных для stress-test.")
    lines += ["", "## 3. Концентрация положительных дней", ""]
    if not concentration.empty:
        for c in ["top_1pct_positive_day_share", "top_5pct_positive_day_share", "top_10pct_positive_day_share"]:
            concentration[c] = pd.to_numeric(concentration[c], errors="coerce")
        lines += [
            "| Strategy | Top 1% days share | Top 5% days share | Top 10% days share |",
            "|---|---:|---:|---:|",
        ]
        for _, x in concentration.iterrows():
            lines.append(
                f"| {x['strategy']} | {fmt_pct(x['top_1pct_positive_day_share'])} "
                f"| {fmt_pct(x['top_5pct_positive_day_share'])} "
                f"| {fmt_pct(x['top_10pct_positive_day_share'])} |"
            )
    else:
        lines.append("Нет данных для concentration.")
    lines += ["", "## 4. Экстремальные дни", ""]
    if not extremes.empty:
        extremes["net_return"] = pd.to_numeric(extremes["net_return"], errors="coerce")
        for strategy in KEY_STRATEGIES:
            g = extremes[extremes["strategy"].eq(strategy)]
            if g.empty:
                continue
            best = g[g["extreme_type"].eq("best")].nlargest(3, "net_return")
            worst = g[g["extreme_type"].eq("worst")].nsmallest(3, "net_return")
            def day_rows(frame):
                out = []
                for _, z in frame.iterrows():
                    out.append(
                        f"{str(z.get('exit_date', ''))[:10]} {fmt_pct(z['net_return'])} "
                        f"(gross {fmt_pct(z.get('gross_return', np.nan))}, "
                        f"exposure {fmt_pct(z.get('effective_exposure', np.nan))}, "
                        f"missing {fmt_pct(z.get('missing_return_weight', np.nan))}; "
                        f"{str(z.get('constituents', ''))[:100]})"
                    )
                return "; ".join(out) if out else "нет"
            lines.append(f"**{strategy}**")
            lines.append(f"- Лучшие: {day_rows(best)}")
            lines.append(f"- Худшие: {day_rows(worst)}")
            lines.append("")
    else:
        lines.append("Нет данных.")

    lines += ["## 5. Годовая устойчивость", ""]
    if not years.empty:
        for c in ["year", "total_return", "cagr_252", "max_drawdown", "worst_day", "best_day"]:
            if c in years:
                years[c] = pd.to_numeric(years[c], errors="coerce")
        recent = years[years["year"].ge(2020)].copy()
        if recent.empty:
            recent = years.copy()
        lines += [
            "| Strategy | Годы в плюсе | Средняя годовая доходность | Лучший год | Худший год | Худший годовой MDD |",
            "|---|---:|---:|---:|---:|---:|",
        ]
        for strategy, g in recent.groupby("strategy"):
            best = g.loc[g["total_return"].idxmax()]
            worst = g.loc[g["total_return"].idxmin()]
            positive_years = int((g["total_return"] > 0).sum())
            lines.append(
                f"| {strategy} | {positive_years}/{len(g)} | {fmt_pct(g['total_return'].mean())} "
                f"| {int(best['year'])}: {fmt_pct(best['total_return'])} "
                f"| {int(worst['year'])}: {fmt_pct(worst['total_return'])} "
                f"| {fmt_pct(g['max_drawdown'].min())} |"
            )
        lines.append("")
        lines.append("Агрегировано по календарным годам с 2020; последний год может быть неполным.")
    else:
        lines.append("Нет данных.")

    lines += ["", "## 6. Концентрация на отдельных тикерах", ""]
    if not tickers.empty:
        tickers["summed_gross_contribution"] = pd.to_numeric(
            tickers["summed_gross_contribution"], errors="coerce"
        )
        for strategy in KEY_STRATEGIES:
            g = tickers[tickers["strategy"].eq(strategy)]
            if g.empty:
                continue
            top = g.nlargest(5, "summed_gross_contribution")
            bottom = g.nsmallest(5, "summed_gross_contribution")
            top_text = ", ".join(
                f"{r.secid} ({fmt_num(r.summed_gross_contribution, 3)})"
                for r in top.itertuples()
            )
            bottom_text = ", ".join(
                f"{r.secid} ({fmt_num(r.summed_gross_contribution, 3)})"
                for r in bottom.itertuples()
            )
            lines.append(f"**{strategy}**")
            lines.append(f"- Top contributors: {top_text}")
            lines.append(f"- Bottom contributors: {bottom_text}")
            lines.append("")
        lines.append("Ticker attribution approximate: un-compounded weighted contributions, before exact portfolio wealth reconciliation.")
    else:
        lines.append("Нет данных.")

    # Machine-generated flags: intentionally conservative; these identify what to inspect,
    # not proof of a bug.
    lines += ["", "## 7. Автоматические флаги для проверки", ""]
    flags = []
    if not core.empty:
        focus = core[core["strategy"].eq("drawdown60_top10")]
        base = core[core["strategy"].eq("baseline_top50")]
        if not focus.empty and not base.empty:
            a, b = focus.iloc[0], base.iloc[0]
            if pd.notna(a["cagr"]) and pd.notna(b["cagr"]) and a["cagr"] - b["cagr"] > 0.10:
                flags.append(
                    f"- CAGR drawdown60_top10 выше baseline на {fmt_pct(a['cagr'] - b['cagr'])}: проверить отбор, цены и исполнение."
                )
        if "mean_missing" in core and core["mean_missing"].max() > 0.05:
            flags.append("- Средний missing_return_weight превышает 5% хотя бы у одной стратегии: проверить treatment отсутствующих OPEN.")
        if "max_missing" in core and core["max_missing"].max() > 0.20:
            flags.append("- Максимальный missing_return_weight превышает 20%: изучить конкретные даты и составы.")
    if not extremes.empty and "missing_return_weight" in extremes:
        extremes["missing_return_weight"] = pd.to_numeric(extremes["missing_return_weight"], errors="coerce")
        suspect = extremes[
            extremes["extreme_type"].eq("best")
            & extremes["missing_return_weight"].gt(0.05)
        ]
        if not suspect.empty:
            flags.append(f"- Среди top-20 best days есть {len(suspect)} строк с missing_return_weight >5%: проверить, не связан ли высокий результат с пропущенными ценами.")
    if not flags:
        flags.append("- По заданным порогам явных автоматических флагов не обнаружено. Это не доказывает отсутствие ошибок.")
    lines.extend(flags)

    lines += [
        "",
        "## 8. Что эта сводка НЕ проверяет",
        "",
        "- Не сверяет adjusted OPEN с raw OHLC и corporate action register.",
        "- Не доказывает отсутствие lookahead и не реконструирует сделки независимо от исходного simulator.",
        "- Не проверяет исполнимость заявок, лимиты цены, suspension, lot size, spread и market impact.",
        "- CAGR рассчитан из net_return с 252 периодами в год; terminal multiple — произведение (1 + daily return).",
        "",
        "## Приоритет следующего аудита",
        "",
        "1. Сопоставить лучшие/худшие даты с missing_return_weight и constituents.",
        "2. Проверить ticker concentration: не создают ли несколько SECID основную часть результата.",
        "3. Сверить extreme daily returns с raw/adjusted OPEN вокруг corporate actions.",
        "4. Независимо восстановить несколько сделок вручную по цепочке signal T -> execution T+1 OPEN -> exit T+2 OPEN.",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    report = build_report()
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(report, encoding="utf-8")
    print(report)
    print(f"\nСохранено: {OUT_PATH}")


if __name__ == "__main__":
    main()
