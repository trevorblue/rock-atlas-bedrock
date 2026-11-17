"""Module F - Opportunity Radar and Resilience: which stocks look attractive, and can you actually get out?

The exit check comes first. On the NSE a stock can look like a great buy on paper yet trade too thinly to
buy or sell, so a stock only counts as an opportunity if a position can be sold within EXIT_DAYS trading
days while selling at most 20% of a normal day's trading (config.PARTICIPATION).

Score      equal-weight average of three percentile ranks (weights fixed in advance, never tuned):
           momentum    return over the last 12 months, skipping the latest month
           stability   low 60-day volatility
           resilience  the stock's return minus the market's, averaged over the months the market fell
                       (last 3 years, at least 6 such months) - the "Kenyan Market Resilience Index"
Testing    every month-end from 2016: stocks that pass the exit check are split into thirds by score and
           the next 21 trading days' returns of the top and bottom thirds are compared. The same split
           without the exit check ("on paper") shows how many top picks could not actually be sold.
           Resilience is tested on its own: do stocks that held up in past falls hold up in the next one?
Only data known at each month-end is used (features come from crash.build_panel, which is tested for
look-ahead).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .config import PARTICIPATION
from .crash import FIRST_TEST_YEAR, HORIZON, MIN_TRADES_60

EXIT_DAYS = 20
TEST_POSITION = 1e6          # KES 1m: enough stocks pass each month to split them into thirds
LIVE_POSITIONS = (1e6, 10e6, 50e6)
RES_WINDOW, RES_MIN = 36, 6  # resilience: last 36 month-ends, at least 6 falling months


def monthly(panel: pd.DataFrame, indices: pd.DataFrame) -> pd.DataFrame:
    """Month-end rows of ordinary shares with momentum, resilience and the market's next-month return."""
    cal = panel["date"].drop_duplicates().sort_values()
    ends = set(cal.groupby(cal.dt.to_period("M")).max())
    m = panel[panel["date"].isin(ends) & (panel["instrument"] == "Equity")].sort_values(["code", "date"]).copy()
    m["mom_12_1"] = (1 + m["mom_12m"]) / (1 + m["mom_1m"]) - 1
    m["adv"] = np.expm1(m["log_adv"])
    excess = (m["mom_1m"] - m["nasi_1m"]).where(m["nasi_1m"] < 0)
    m["resilience"] = excess.groupby(m["code"]).transform(lambda s: s.rolling(RES_WINDOW, min_periods=RES_MIN).mean())
    nasi = indices[indices["code"] == "^NASI"].sort_values("date")[["date", "close"]]
    nasi = nasi.assign(nasi_fwd=nasi["close"].shift(-HORIZON) / nasi["close"] - 1)[["date", "nasi_fwd"]]
    m = m.merge(nasi, on="date", how="left")
    m["base"] = (m["traded_60"] >= MIN_TRADES_60) & m[["vol_60", "mom_12_1", "resilience"]].notna().all(axis=1)
    return m


def days_to_exit(adv: pd.Series, position: float) -> pd.Series:
    return (position / (PARTICIPATION * adv.replace(0, np.nan))).fillna(np.inf)


def score(g: pd.DataFrame) -> pd.Series:
    """Equal-weight average of percentile ranks within one month (higher = more attractive)."""
    return pd.concat([g["mom_12_1"].rank(pct=True), g["vol_60"].rank(pct=True, ascending=False),
                      g["resilience"].rank(pct=True)], axis=1).mean(axis=1)


def _thirds(s: pd.Series) -> pd.Series:
    return pd.qcut(s.rank(method="first"), 3, labels=False)


def backtest(m: pd.DataFrame, position: float = TEST_POSITION) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Monthly results: radar (exit check first) and resilience in falling months."""
    d = m[m["base"] & m["fwd"].notna() & (m["date"].dt.year >= FIRST_TEST_YEAR)]
    radar, resil = [], []
    for date, g in d.groupby("date"):
        g = g.assign(sc=score(g), exit_ok=days_to_exit(g["adv"], position) <= EXIT_DAYS)
        paper_top = g[_thirds(g["sc"]) == 2]
        ok = g[g["exit_ok"]]
        if len(ok) >= 9:
            t = _thirds(ok["sc"])
            radar.append({"date": date, "n_ok": len(ok), "top": ok.loc[t == 2, "fwd"].mean(),
                          "bottom": ok.loc[t == 0, "fwd"].mean(), "all_ok": ok["fwd"].mean(),
                          "market": g["nasi_fwd"].iloc[0],
                          "paper_top_fail_share": 1 - paper_top["exit_ok"].mean(),
                          "paper_top_fail_share_10m": (days_to_exit(paper_top["adv"], 10e6) > EXIT_DAYS).mean()})
        if g["nasi_fwd"].iloc[0] < 0 and len(g) >= 9:
            t = _thirds(g["resilience"])
            resil.append({"date": date, "market": g["nasi_fwd"].iloc[0], "top": g.loc[t == 2, "fwd"].mean(),
                          "bottom": g.loc[t == 0, "fwd"].mean()})
    return pd.DataFrame(radar), pd.DataFrame(resil)


def _t(x: pd.Series) -> float:
    return float(x.mean() / (x.std(ddof=1) / np.sqrt(len(x)))) if len(x) > 2 and x.std() > 0 else np.nan


def summarize(radar: pd.DataFrame, resil: pd.DataFrame) -> dict:
    spread, vs_all = radar["top"] - radar["bottom"], radar["top"] - radar["all_ok"]
    rs = resil["top"] - resil["bottom"]
    return {
        "months": len(radar), "first": radar["date"].min(), "last": radar["date"].max(),
        "avg_ok_stocks": float(radar["n_ok"].mean()),
        "top_avg": float(radar["top"].mean()), "bottom_avg": float(radar["bottom"].mean()),
        "spread_avg": float(spread.mean()), "spread_t": _t(spread), "spread_win_share": float((spread > 0).mean()),
        "top_vs_all_avg": float(vs_all.mean()), "top_vs_all_t": _t(vs_all),
        "paper_fail_share_1m": float(radar["paper_top_fail_share"].mean()),
        "paper_fail_share_10m": float(radar["paper_top_fail_share_10m"].mean()),
        "res_months": len(resil), "res_top_avg": float(resil["top"].mean()), "res_bottom_avg": float(resil["bottom"].mean()),
        "res_spread_avg": float(rs.mean()), "res_spread_t": _t(rs), "res_win_share": float((rs > 0).mean()),
    }


def live(m: pd.DataFrame) -> pd.DataFrame:
    """Today's radar: every eligible stock with its score, components and exit check at several sizes."""
    last = m[(m["date"] == m["date"].max()) & m["base"]].copy()
    last["score"] = score(last)
    last["paper_rank"] = last["score"].rank(ascending=False, method="first").astype(int)
    for pos in LIVE_POSITIONS:
        tag = f"{int(pos / 1e6)}m"
        last[f"days_exit_{tag}"] = days_to_exit(last["adv"], pos)
        last[f"exit_ok_{tag}"] = last[f"days_exit_{tag}"] <= EXIT_DAYS
    keep = ["date", "code", "name", "score", "paper_rank", "mom_12_1", "vol_60", "resilience", "adv"] + \
           [c for c in last.columns if c.startswith(("days_exit_", "exit_ok_"))]
    return last[keep].sort_values("paper_rank").reset_index(drop=True)


def run(panel: pd.DataFrame, indices: pd.DataFrame) -> dict:
    m = monthly(panel, indices)
    radar, resil = backtest(m)
    return {"monthly_radar": radar, "monthly_resilience": resil, "summary": summarize(radar, resil), "live": live(m)}
