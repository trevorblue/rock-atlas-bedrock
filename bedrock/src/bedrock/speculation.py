"""Module C - Speculation Watch: which price moves look like speculation rather than news?

For every stock-day with a trade, compare the day with the stock's own previous
ANOMALY_WINDOW trading days:
  z_ret     return vs its normal return (std units)
  z_value   log value traded vs its normal
  ex_ret    return minus the NASI market return
  range     (day high - day low) / previous close
An Isolation Forest scores how unusual each stock-day is. The watch list keeps
flagged days that also had abnormal volume (z_value > 1) and a move the market
did not share (|ex_ret| > 3%).

There is no official list of manipulated stocks, so the flags are validated by
what happens next (forward returns at FWD_HORIZONS days), split by size and
direction. News checks are by hand in data/manual/news_checks.csv (see attach_news).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from .config import ANOMALY_CONTAMINATION, ANOMALY_WINDOW, FWD_HORIZONS, RANDOM_STATE

FEATURES = ["z_ret", "z_value", "ex_ret", "range"]
WATCH_Z_VALUE = 1.0
WATCH_EX_RET = 0.03


def build_features(stocks: pd.DataFrame, indices: pd.DataFrame, window: int = ANOMALY_WINDOW) -> pd.DataFrame:
    df = stocks.sort_values(["code", "date"]).copy()
    mkt = indices[indices["code"] == "^NASI"].set_index("date")["ret"].rename("mkt_ret")
    df = df.join(mkt, on="date")
    df["log_value"] = np.log1p(df["value_kes"])
    df["range"] = (df["day_high"] - df["day_low"]) / df["prev"]
    df["ex_ret"] = df["ret"] - df["mkt_ret"].fillna(0)

    g = df.groupby("code", group_keys=False)
    # shift(1): today is compared with the PREVIOUS window only (no look-ahead)
    for col, z in [("ret", "z_ret"), ("log_value", "z_value")]:
        prev = g[col].shift(1)
        roll = prev.groupby(df["code"]).rolling(window, min_periods=window // 2)
        mu = roll.mean().reset_index(level=0, drop=True)
        sd = roll.std().reset_index(level=0, drop=True)
        df[z] = (df[col] - mu) / sd.replace(0, np.nan)

    for h in FWD_HORIZONS:
        df[f"fwd_{h}d"] = g["close"].shift(-h) / df["close"] - 1
    return df


def detect(features: pd.DataFrame, contamination: float = ANOMALY_CONTAMINATION) -> pd.DataFrame:
    d = features[features["traded"]].dropna(subset=FEATURES).copy()
    X = d[FEATURES].clip(-20, 20)
    model = IsolationForest(n_estimators=300, contamination=contamination, random_state=RANDOM_STATE, n_jobs=-1)
    model.fit(X)
    d["anomaly_score"] = -model.score_samples(X)          # higher = more unusual
    d["flag"] = model.predict(X) == -1
    d["watch"] = d["flag"] & (d["z_value"] > WATCH_Z_VALUE) & (d["ex_ret"].abs() > WATCH_EX_RET)
    d["direction"] = np.where(d["ret"] > 0, "up", "down")
    d["news"] = ""
    fwd = [f"fwd_{h}d" for h in FWD_HORIZONS]
    cols = ["date", "code", "name", "close", "ret", "ex_ret", "value_kes", "z_ret", "z_value", "range",
            "anomaly_score", "flag", "watch", "direction", *fwd, "news"]
    return d[cols].sort_values(["date", "anomaly_score"], ascending=[True, False]).reset_index(drop=True)


def validation(scored: pd.DataFrame, size_by_code: pd.Series) -> pd.DataFrame:
    """Average forward returns after big moves (|ret| > 5%): watch-listed vs the rest,
    by stock size (small = below-median average value traded) and direction."""
    fwd = [f"fwd_{h}d" for h in FWD_HORIZONS]
    big = scored[(scored["ret"].abs() > 0.05) & scored[fwd[-1]].notna()].copy()
    small = set(size_by_code[size_by_code < size_by_code.median()].index)
    big["size"] = np.where(big["code"].isin(small), "small", "large")
    big["group"] = np.where(big["watch"], "watch list", "other big moves")
    out = big.groupby(["group", "size", "direction"])[fwd].agg(["mean", "count"])
    out.columns = [f"{a}_{b}" for a, b in out.columns]
    return out.reset_index()


# ------------------------------------------------------------------ news checks (manual)
NEWS_COLS = ["date", "code", "news_found", "headline", "source_url", "checked_on"]


def attach_news(scored: pd.DataFrame, path) -> pd.DataFrame:
    """Fill the 'news' column from the hand-checked file data/manual/news_checks.csv.

    news_found: 'yes' (a public announcement or press story explains the move), 'no' (nothing found:
    the speculation candidate) or blank (not checked yet). A check covers the flagged day and the
    two trading days before it, since news often leaks a day early."""
    from pathlib import Path
    path = Path(path)
    if not path.exists():
        return scored
    nc = pd.read_csv(path, parse_dates=["date"], dtype={"news_found": str, "headline": str}).fillna("")
    nc = nc[nc["news_found"].str.lower().isin(["yes", "no"])]
    if nc.empty:
        return scored
    lab = nc["news_found"].str.lower().map({"yes": "yes: ", "no": "no news found"}) +         np.where(nc["news_found"].str.lower() == "yes", nc["headline"], "")
    key = dict(zip(zip(nc["date"], nc["code"]), lab))
    out = scored.copy()
    out["news"] = [key.get((d, c), n) for d, c, n in zip(out["date"], out["code"], out["news"])]
    return out


def to_check(scored: pd.DataFrame, path, n_recent: int = 15, since_days: int = 180) -> pd.DataFrame:
    """Write the most unusual recent watch-list days that still need a news check (appends, never overwrites)."""
    from pathlib import Path
    path = Path(path)
    w = scored[scored["watch"] & (scored["date"] >= scored["date"].max() - pd.Timedelta(days=since_days))]
    w = w.nlargest(n_recent, "anomaly_score")[["date", "code"]]
    old = pd.read_csv(path, dtype=str, keep_default_na=False) if path.exists() else pd.DataFrame(columns=NEWS_COLS)
    if len(old):
        old["date"] = pd.to_datetime(old["date"])
    new = w.merge(old[["date", "code"]], how="left", indicator=True)
    new = new[new["_merge"] == "left_only"].drop(columns="_merge")
    out = pd.concat([old, new.reindex(columns=NEWS_COLS)], ignore_index=True).sort_values(["date", "code"])
    out["date"] = pd.to_datetime(out["date"]).dt.strftime("%Y-%m-%d")
    out.to_csv(path, index=False)
    return out
