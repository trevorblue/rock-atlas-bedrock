"""Module A - Market Depth: which NSE stocks can you actually sell?

Per stock, over the last LOOKBACK_DAYS trading days:
  adv_kes           average daily value traded (zero on no-trade days)
  zero_trade_share  share of trading days with no trade at all
  amihud            Amihud illiquidity: mean |daily return| per KES 1m traded (higher = a small trade moves price more)
  turnover_annual   value traded in a year / market capitalisation
  days_to_exit      POSITION_KES / (PARTICIPATION x adv_kes)
Tiers are rule-based on days_to_exit (TIER_BOUNDS) so they are easy to explain; a K-means
clustering of the traded stocks is kept alongside as a cross-check ("cluster" column).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

from .config import EXIT_THRESHOLDS, LOOKBACK_DAYS, N_CLUSTERS, PARTICIPATION, POSITION_KES, RANDOM_STATE, TIER_BOUNDS

TIER_NAMES = ["1 Deep", "2 Moderate", "3 Thin", "4 Frozen"]


def trading_calendar(stocks: pd.DataFrame) -> pd.DatetimeIndex:
    return pd.DatetimeIndex(sorted(stocks.loc[stocks["traded"], "date"].unique()))


def depth_snapshot(stocks: pd.DataFrame, shareholding: pd.DataFrame | None = None,
                   sectors: pd.DataFrame | None = None, as_of: pd.Timestamp | None = None,
                   lookback: int = LOOKBACK_DAYS) -> pd.DataFrame:
    cal = trading_calendar(stocks)
    as_of = cal[cal <= (as_of or cal[-1])][-1]
    window = cal[(cal <= as_of)][-lookback:]
    w = stocks[stocks["date"].isin(window)]
    listed = set(stocks.loc[stocks["date"] == as_of, "code"])   # still quoted on the as-of date
    w = w[w["code"].isin(listed)]

    # make the panel complete: a stock missing on a day counts as no trade
    full = pd.MultiIndex.from_product([sorted(listed), window], names=["code", "date"])
    p = (w.set_index(["code", "date"])[["value_kes_adj", "ret", "close"]].rename(columns={"value_kes_adj": "value_kes"})
         .reindex(full))                                  # block-adjusted value: see clean.split_prices
    p["value_kes"] = p["value_kes"].fillna(0.0)

    g = p.groupby(level="code")
    out = pd.DataFrame({
        "adv_kes": g["value_kes"].mean(),
        "median_value_kes": g["value_kes"].median(),
        "zero_trade_share": g["value_kes"].apply(lambda s: (s <= 0).mean()),
        "volatility": g["ret"].std(),
    })
    traded = p[p["value_kes"] > 0].copy()
    traded["illiq"] = traded["ret"].abs() / (traded["value_kes"] / 1e6)
    out["amihud"] = traded.groupby(level="code")["illiq"].mean()
    last = stocks[stocks["date"] == as_of].set_index("code")
    out["price"] = last["close"]
    out["name"] = last["name"]

    if shareholding is not None and len(shareholding):
        sh = shareholding.dropna(subset=["code"]).drop_duplicates("code").set_index("code")
        out["shares_issued"] = sh["shares_issued"]
        out["foreign_pct"] = sh["foreign_pct"]
        out["market_cap_kes"] = out["shares_issued"] * out["price"]
        out["turnover_annual"] = out["adv_kes"] * 250 / out["market_cap_kes"]
    if sectors is not None and len(sectors):
        out["sector"] = sectors.drop_duplicates("code").set_index("code")["sector"]

    out["days_to_exit"] = POSITION_KES / (PARTICIPATION * out["adv_kes"].replace(0, np.nan))
    out["days_to_exit"] = out["days_to_exit"].fillna(np.inf)
    out["instrument"] = instrument_type(out.index, out.get("sector"))
    out["tier"] = tier_from_days(out["days_to_exit"])
    out["cluster"] = cluster_traded(out)
    out["as_of"] = as_of
    return out.reset_index().sort_values("days_to_exit").reset_index(drop=True)


def instrument_type(codes, sector) -> list[str]:
    sector = pd.Series(sector, index=codes) if sector is not None else pd.Series(index=codes, dtype=object)
    out = []
    for c in codes:
        sec = str(sector.get(c, ""))
        if "-P" in c:
            out.append("Preference")
        elif "Exchange Traded" in sec:
            out.append("ETF")
        elif "Real Estate" in sec:
            out.append("REIT")
        else:
            out.append("Equity")
    return out


def tier_from_days(days: pd.Series, bounds=TIER_BOUNDS) -> pd.Series:
    edges = [-np.inf, *bounds, np.inf]
    return pd.cut(days, bins=edges, labels=TIER_NAMES, right=True).astype(str)


def cluster_traded(df: pd.DataFrame, k: int = N_CLUSTERS) -> pd.Series:
    """K-means on standardised log liquidity features, traded stocks only; 1 = most liquid cluster."""
    ok = (df["adv_kes"] > 0) & df["amihud"].notna()
    X = pd.DataFrame({"log_adv": np.log(df.loc[ok, "adv_kes"]),
                      "zero": df.loc[ok, "zero_trade_share"],
                      "log_amihud": np.log1p(df.loc[ok, "amihud"] * 1e3)})
    res = pd.Series(np.nan, index=df.index)
    if ok.sum() < k * 3:
        return res
    km = KMeans(n_clusters=k, n_init=20, random_state=RANDOM_STATE).fit(StandardScaler().fit_transform(X))
    order = X.assign(c=km.labels_).groupby("c")["log_adv"].mean().sort_values(ascending=False).index
    rank = {c: i + 1 for i, c in enumerate(order)}
    res.loc[ok] = [rank[c] for c in km.labels_]
    return res


def headline(snapshot: pd.DataFrame, thresholds=EXIT_THRESHOLDS) -> dict:
    """Headline numbers on ordinary shares only (ETFs, REITs and preference shares excluded)."""
    snapshot = snapshot[snapshot["instrument"] == "Equity"]
    n = len(snapshot)
    h = {"n_stocks": n, "as_of": str(pd.Timestamp(snapshot["as_of"].iloc[0]).date())}
    for y in thresholds:
        h[f"pct_over_{y}d"] = float((snapshot["days_to_exit"] > y).mean())
    h["pct_no_trade_in_window"] = float(np.isinf(snapshot["days_to_exit"]).mean())
    top5 = snapshot.nlargest(5, "adv_kes")["adv_kes"].sum() / snapshot["adv_kes"].sum()
    h["top5_share_of_value"] = float(top5)
    return h


def concentration_monthly(stocks: pd.DataFrame) -> pd.DataFrame:
    """Monthly market concentration: share of value traded in the top-5 stocks and HHI."""
    v = stocks.groupby([pd.Grouper(key="date", freq="ME"), "code"])["value_kes_adj"].sum().rename("v").reset_index()
    def agg(g):
        s = g["v"] / g["v"].sum()
        return pd.Series({"total_value_kes": g["v"].sum(), "top5_share": s.nlargest(5).sum(),
                          "hhi": (s ** 2).sum(), "n_traded": (g["v"] > 0).sum()})
    out = v.groupby("date").apply(agg, include_groups=False).reset_index().rename(columns={"date": "period"})
    return out
