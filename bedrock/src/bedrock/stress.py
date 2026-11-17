"""Screen 4 - Stress Test: if foreigners sell KES X over N days, which stocks break?

1. Allocate the total foreign sale across stocks in proportion to foreign-held value
   (foreign % of shares x shares in issue x price, from the CMA shareholding table).
2. Days to absorb = stock's share of the sale / (PARTICIPATION x average daily value traded).
3. Price impact from the square-root law:  impact = k x daily volatility x sqrt(sale / ADV).
   This is the standard rule of thumb for the cost of trading a block; it is an
   estimate, not a forecast, and is capped at -90%. Stocks with no trades in the window
   have no market at all: status "no market", impact left blank.
Strategic stakes: a stock whose foreign ownership is above STRATEGIC_CUTOFF (default 50%)
is assumed to be held by a foreign parent (e.g. Absa Group in ABSA Kenya) and not sold.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .config import DEFAULT_SCENARIO_DAYS, DEFAULT_SCENARIO_KES, IMPACT_K, PARTICIPATION, STRATEGIC_CUTOFF


def run_scenario(snapshot: pd.DataFrame, total_sell_kes: float = DEFAULT_SCENARIO_KES,
                 days: int = DEFAULT_SCENARIO_DAYS, participation: float = PARTICIPATION,
                 max_foreign_pct: float = STRATEGIC_CUTOFF, speculative_codes: set[str] | None = None) -> pd.DataFrame:
    d = snapshot[snapshot["instrument"] == "Equity"].copy()
    d = d[d["foreign_pct"].notna() & d["market_cap_kes"].notna()]
    # stakes above the cut-off are treated as strategic and not sold
    d["foreign_value_kes"] = np.where(d["foreign_pct"] <= max_foreign_pct, d["foreign_pct"] * d["market_cap_kes"], 0.0)
    total_fv = d["foreign_value_kes"].sum()
    d["weight"] = d["foreign_value_kes"] / total_fv if total_fv > 0 else 0.0
    d["sell_kes"] = d["weight"] * total_sell_kes
    d["sell_per_day_kes"] = d["sell_kes"] / days
    adv = d["adv_kes"].replace(0, np.nan)
    d["sell_vs_adv"] = d["sell_per_day_kes"] / adv
    d["days_to_absorb"] = (d["sell_kes"] / (participation * adv)).fillna(np.inf)
    vol = d["volatility"].fillna(d["volatility"].median())
    d["price_impact"] = -np.minimum(IMPACT_K * vol * np.sqrt(d["sell_kes"] / adv), 0.9)
    d.loc[d["sell_kes"] <= 0, "price_impact"] = 0.0
    d["speculative_recently"] = d["code"].isin(speculative_codes or set())
    d["status"] = np.select(
        [d["sell_kes"] <= 0, d["adv_kes"] <= 0, d["days_to_absorb"] <= days, d["days_to_absorb"] <= 4 * days],
        ["not hit", "no market", "absorbed", "strained"], default="trapped")
    cols = ["code", "name", "sector", "tier", "foreign_pct", "foreign_value_kes", "sell_kes", "adv_kes",
            "sell_vs_adv", "days_to_absorb", "price_impact", "status", "speculative_recently"]
    return d[cols].sort_values("price_impact").reset_index(drop=True)


def summarize(res: pd.DataFrame, total_sell_kes: float) -> dict:
    hit = res[res["sell_kes"] > 0]
    mk = hit[hit["status"] != "no market"]
    w = mk["sell_kes"] / mk["sell_kes"].sum()
    return {
        "total_sell_kes": total_sell_kes,
        "n_hit": len(hit),
        "n_trapped": int(hit["status"].isin(["trapped", "no market"]).sum()),
        "n_no_market": int((hit["status"] == "no market").sum()),
        "value_trapped_kes": float(hit.loc[hit["status"].isin(["trapped", "no market"]), "sell_kes"].sum()),
        "weighted_impact": float((w * mk["price_impact"]).sum()),
        "worst": mk.nsmallest(5, "price_impact")[["code", "price_impact", "days_to_absorb"]].to_dict("records"),
    }
