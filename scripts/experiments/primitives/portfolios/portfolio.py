# Folder: scripts/experiments/primitives/portfolios/
# File: portfolio.py
# Purpose: Construct PIT portfolio weights and simulate daily open-to-open
#          portfolio returns with explicit breadth sizing and turnover costs.

from __future__ import annotations

import pandas as pd

from config import (
    BASELINE_WEIGHT, BREADTH_MULTIPLIERS, CORE_STRATEGIES,
    SELECTED_WEIGHT, TOP_N,
)


def build_target_weights(
    features: pd.DataFrame,
    breadth: pd.DataFrame,
) -> tuple[dict[str, pd.DataFrame], pd.DataFrame]:
    breadth_lookup = breadth.set_index("tradedate")
    dates = pd.DatetimeIndex(sorted(features["tradedate"].unique()))
    secids = sorted(features["secid"].unique())
    weight_frames: dict[str, pd.DataFrame] = {}
    strategy_specs = []

    for base_name, spec in CORE_STRATEGIES.items():
        for use_breadth in (False, True):
            strategy_name = f"{base_name}_breadth" if use_breadth else base_name
            weights = pd.DataFrame(0.0, index=dates, columns=secids, dtype=float)

            for date, group in features.groupby("tradedate", sort=True):
                selected = group.copy()

                if spec["kind"] == "rank":
                    feature = spec["feature"]
                    selected = selected.dropna(subset=[feature])
                    selected = selected.sort_values(
                        [feature, "secid"],
                        ascending=[spec["ascending"], True],
                        kind="mergesort",
                    ).head(TOP_N)
                    base_weight = SELECTED_WEIGHT
                else:
                    selected = selected.sort_values(
                        ["rank", "secid"], ascending=[True, True],
                        kind="mergesort",
                    )
                    base_weight = BASELINE_WEIGHT

                if selected.empty:
                    continue

                multiplier = 1.0
                if use_breadth:
                    if date not in breadth_lookup.index:
                        continue
                    regime = breadth_lookup.at[date, "breadth_regime"]
                    if not isinstance(regime, str):
                        continue
                    multiplier = BREADTH_MULTIPLIERS.get(regime)
                    if multiplier is None:
                        continue

                weights.loc[date, selected["secid"].tolist()] = (
                    base_weight * multiplier
                )

            weight_frames[strategy_name] = weights
            strategy_specs.append({
                "strategy": strategy_name,
                "base_strategy": base_name,
                "uses_breadth": use_breadth,
                "kind": spec["kind"],
                "feature": spec["feature"],
                "ascending": spec["ascending"],
                "top_n": TOP_N if spec["kind"] == "rank" else 50,
                "base_weight": (
                    SELECTED_WEIGHT if spec["kind"] == "rank"
                    else BASELINE_WEIGHT
                ),
                "breadth_sizing": (
                    "100/75/50/25% by breadth regime"
                    if use_breadth else "None; full base sizing"
                ),
                "description": spec["description"],
            })

    return weight_frames, pd.DataFrame(strategy_specs)


def simulate_strategy(
    strategy: str,
    target_weights: pd.DataFrame,
    asset_returns: pd.DataFrame,
    date_map: pd.DataFrame,
    cost_bps: float,
) -> pd.DataFrame:
    dates = target_weights.index.intersection(asset_returns.index)
    weights = target_weights.reindex(dates).fillna(0.0)
    returns = asset_returns.reindex(index=dates, columns=weights.columns)

    previous_weights = pd.Series(0.0, index=weights.columns, dtype=float)
    previous_cash = 1.0
    equity_gross = 1.0
    equity_net = 1.0
    rows = []

    for date in dates:
        target = weights.loc[date].astype(float).clip(lower=0.0)
        target_exposure = float(target.sum())
        if target_exposure > 1.0000001:
            raise RuntimeError(
                f"{strategy}: target exposure exceeds 100% on {date}: {target_exposure:.6f}"
            )
        target_cash = max(0.0, 1.0 - target_exposure)

        # Missing forward OPEN observations are not forward-filled.
        # The affected allocation is treated as cash and reported.
        daily_returns = returns.loc[date]
        valid = daily_returns.notna() & daily_returns.map(
            lambda value: pd.notna(value) and abs(value) < float("inf")
        )
        missing_return_weight = float(target.loc[~valid].sum())
        safe_returns = daily_returns.where(valid, 0.0)

        # One-way turnover includes the cash leg.
        turnover = 0.5 * (
            float((target - previous_weights).abs().sum())
            + abs(target_cash - previous_cash)
        )
        cost_rate = turnover * float(cost_bps) / 10000.0
        gross_return = float((target * safe_returns).sum())
        net_return = (1.0 + gross_return) * (1.0 - cost_rate) - 1.0

        if gross_return <= -1.0 or net_return <= -1.0:
            raise RuntimeError(f"Invalid portfolio return for {strategy} on {date}.")

        equity_gross *= 1.0 + gross_return
        equity_net *= 1.0 + net_return

        # Mark holdings to market before the next rebalance.
        growth = 1.0 + gross_return
        if growth > 0:
            drifted = target * (1.0 + safe_returns) / growth
            drifted_cash = target_cash / growth
        else:
            drifted = pd.Series(0.0, index=target.index)
            drifted_cash = 1.0

        previous_weights = drifted
        previous_cash = float(drifted_cash)

        mapping = date_map.loc[date]
        rows.append({
            "strategy": strategy,
            "signal_date": date,
            "execution_date": mapping["execution_date"],
            "exit_date": mapping["exit_date"],
            "gross_return": gross_return,
            "net_return": net_return,
            "turnover_one_way": turnover,
            "transaction_cost_bps": float(cost_bps),
            "target_exposure": target_exposure,
            "missing_return_weight": missing_return_weight,
            "equity_gross": equity_gross,
            "equity_net": equity_net,
            "constituents": int((target > 0).sum()),
        })

    result = pd.DataFrame(rows)
    return result.dropna(subset=["execution_date", "exit_date"]).copy()


def run_portfolios(
    weight_frames: dict[str, pd.DataFrame],
    asset_returns: pd.DataFrame,
    date_map: pd.DataFrame,
    cost_bps: tuple[float, ...],
) -> pd.DataFrame:
    daily_results = []
    for strategy, weights in weight_frames.items():
        print(f"Simulating {strategy}...", flush=True)
        for cost in cost_bps:
            daily_results.append(
                simulate_strategy(
                    strategy, weights, asset_returns, date_map, cost
                )
            )

    daily = pd.concat(daily_results, ignore_index=True)
    daily = daily.dropna(subset=["exit_date"]).copy()
    for column in ("signal_date", "execution_date", "exit_date"):
        daily[column] = pd.to_datetime(daily[column])
    return daily
