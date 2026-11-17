"""GARCH volatility forecasts: a stochastic time-series model feeding the crash-risk model (module E).

Why: volatility is the strongest crash signal, and the crash model used to assume the last 60 days' volatility
simply repeats. Financial volatility clusters (calm and stormy spells) and has fat tails, which is exactly what a
GARCH(1,1) model with Student-t shocks describes (Bollerslev 1986).

How, with no look-ahead:
- For each stock and each calendar year Y, the model is fitted once on daily returns BEFORE 1 January of Y
  (at least 250 days). Through year Y those fitted parameters update the volatility day by day from new returns.
- At every date it forecasts the average daily volatility over the next 21 trading days (`garch_vol`).
- A fit that fails or is explosive (persistence >= 0.999) gives no forecast for that year, and the share of such
  cases is reported. Days with no trades count as 0% returns, as in the 60-day volatility it is compared with.

Test: at each month-end from 2016, compare the forecast with the volatility that actually followed (next 21 days)
against the simple rule "the last 60 days repeat", and report the error of each.

Two versions, both reported:
- V1 daily: GARCH(1,1), Student-t shocks, on daily returns. On the NSE most stocks have many unchanged-price days
  (tick sizes, thin trading), so fits are often explosive and the model over-reacts to one-tick jumps.
- V2 weekly (the live version): the standard remedy for thin, discrete trading. GARCH(1,1), normal (quasi-maximum
  likelihood) on weekly returns; the forecast for the next 4 weeks is converted to a daily volatility. At any date
  only weeks that ended on or before it are used.
"""
from __future__ import annotations

import warnings

import numpy as np
import pandas as pd

HORIZON = 21
MIN_OBS = 250


def fit_params(r_pct: np.ndarray, dist: str = "t", min_obs: int = MIN_OBS) -> tuple | None:
    """Fit GARCH(1,1), constant mean, on returns in %. None if it fails or is explosive."""
    from arch import arch_model
    if len(r_pct) < min_obs or np.nanstd(r_pct) == 0:
        return None
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            res = arch_model(r_pct, mean="Constant", vol="GARCH", p=1, q=1, dist=dist, rescale=False).fit(
                disp="off", show_warning=False)
        except Exception:  # noqa: BLE001 - any numerical failure means "no forecast this year"
            return None
    p = res.params
    mu, om, a, b = float(p["mu"]), float(p["omega"]), float(p["alpha[1]"]), float(p["beta[1]"])
    if not np.isfinite([mu, om, a, b]).all() or om <= 0 or a < 0 or b < 0 or a + b >= 0.999:
        return None
    return mu, om, a, b


def forecast_path(r_pct: np.ndarray, params: tuple, horizon: int = HORIZON) -> np.ndarray:
    """At each day t (using returns up to t only): average daily volatility expected over t+1..t+horizon,
    as a decimal. Starts from the model's own long-run variance, so no data from the window is peeked at."""
    mu, om, a, b = params
    phi, long_run = a + b, om / (1 - a - b)
    e = r_pct - mu
    s2_next = np.empty(len(e))
    s2 = long_run
    for t in range(len(e)):                          # s2 = variance for day t, known before day t
        s2 = om + a * e[t] ** 2 + b * s2             # variance for day t+1, known at the close of day t
        s2_next[t] = s2
    avg = long_run + (s2_next - long_run) * (1 - phi ** horizon) / ((1 - phi) * horizon)
    return np.sqrt(np.maximum(avg, 0)) / 100


def forecasts(stocks: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """garch_vol for every stock-day (refitted each year on earlier data only) + fit statistics."""
    s = stocks.sort_values(["code", "date"])[["date", "code", "ret"]].copy()
    out, fits, failed = [], 0, 0
    for code, g in s.groupby("code"):
        r = g["ret"].fillna(0.0).to_numpy() * 100
        years = g["date"].dt.year.to_numpy()
        vol = np.full(len(g), np.nan)
        for y in np.unique(years)[1:]:
            past = r[years < y]
            if len(past) < MIN_OBS:
                continue
            params = fit_params(past)
            fits += 1
            if params is None:
                failed += 1
                continue
            path = forecast_path(r, params)
            vol[years == y] = path[years == y]
        out.append(pd.DataFrame({"date": g["date"].to_numpy(), "code": code, "garch_vol": vol}))
    return pd.concat(out, ignore_index=True), {"fits": fits, "failed_or_explosive": failed}


def forecasts_weekly(stocks: pd.DataFrame, min_weeks: int = 104) -> tuple[pd.DataFrame, dict]:
    """V2: GARCH(1,1) on weekly returns (normal QMLE), refitted each year on earlier weeks only. The 4-week
    forecast is turned into a daily volatility and carried to each day from the last week that had ended."""
    s = stocks.sort_values(["code", "date"])[["date", "code", "ret"]].copy()
    s["lr"] = np.log1p(s["ret"].fillna(0.0))
    out, fits, failed = [], 0, 0
    for code, g in s.groupby("code"):
        wk = g.set_index("date")["lr"].resample("W-FRI").sum(min_count=1).dropna()
        if len(wk) < min_weeks + 10:
            continue
        r = (np.expm1(wk.to_numpy())) * 100
        years = wk.index.year.to_numpy()
        vol_w = np.full(len(wk), np.nan)
        for y in np.unique(years)[1:]:
            past = r[years < y]
            if len(past) < min_weeks:
                continue
            params = fit_params(past, dist="normal", min_obs=min_weeks)
            fits += 1
            if params is None:
                failed += 1
                continue
            path = forecast_path(r, params, horizon=4)          # average weekly volatility, decimal
            vol_w[years == y] = path[years == y] / np.sqrt(5)  # as a daily volatility
        wv = pd.Series(vol_w, index=wk.index)
        daily = wv.reindex(g["date"].to_numpy(), method="ffill")  # last week ending on or before each day
        out.append(pd.DataFrame({"date": g["date"].to_numpy(), "code": code, "garch_vol": daily.to_numpy()}))
    return pd.concat(out, ignore_index=True), {"fits": fits, "failed_or_explosive": failed}


def realized_forward(stocks: pd.DataFrame, horizon: int = HORIZON) -> pd.DataFrame:
    """The volatility that actually followed: std of daily returns over t+1..t+horizon (an outcome, never a feature)."""
    s = stocks.sort_values(["code", "date"])[["date", "code", "ret"]].copy()
    r = s["ret"].fillna(0.0)
    s["rv_fwd"] = r.groupby(s["code"]).transform(lambda x: x[::-1].rolling(horizon, min_periods=horizon).std()[::-1].shift(-1))
    return s[["date", "code", "rv_fwd"]]


def evaluate(samples: pd.DataFrame, first_year: int) -> dict:
    """Forecast accuracy at month-ends: GARCH vs 'the last 60 days repeat', against what actually happened."""
    d = samples[(samples["date"].dt.year >= first_year)].dropna(subset=["garch_vol", "vol_60", "rv_fwd"])
    d = d[d["rv_fwd"] > 0]
    err_g = (np.log(d["garch_vol"]) - np.log(d["rv_fwd"])).abs()
    err_h = (np.log(d["vol_60"].clip(lower=1e-6)) - np.log(d["rv_fwd"])).abs()
    return {"n": len(d), "median_error_garch": float(np.expm1(err_g.median())),
            "median_error_last60": float(np.expm1(err_h.median())),
            "garch_closer_share": float((err_g < err_h).mean()),
            "corr_garch": float(np.corrcoef(np.log(d["garch_vol"]), np.log(d["rv_fwd"]))[0, 1]),
            "corr_last60": float(np.corrcoef(np.log(d["vol_60"].clip(lower=1e-6)), np.log(d["rv_fwd"]))[0, 1])}
