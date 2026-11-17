"""Module E - Crash Risk: which stocks are most likely to fall sharply next month?

Unit      one row per ordinary share per month-end, 2013 onwards (about 64 stocks x 160 months).
Target    crash = the stock's return over the next 21 trading days is CRASH_DROP (-15%) or worse.
Features  only data up to that day (no look-ahead):
          stock    momentum (1, 3, 12 months), volatility (20 and 60 days), distance from 1-year high,
                   value traded (60 days), share of no-trade days, Amihud illiquidity, recent unusual spikes
          market   NASI 1-month return and 60-day volatility, net foreign flow (latest month and 3 months,
                   as known by the previous month-end)
Eligible  ordinary shares with at least 5 trading days in the last 60 (frozen stocks cannot crash in price).
Models    logistic regression and shallow XGBoost, settings fixed in advance (no tuning on test years).
Baseline  rank stocks by 60-day volatility alone: the model only adds value if it beats this.
Testing   walk-forward by year: train on every earlier month whose 21-day outcome was already known
          (purged), predict each month of the test year. 2016 onwards.
Output    crash probability per stock today, model comparison, per-year results, risk-decile table.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import binomtest
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

from .config import RANDOM_STATE
from .depth import instrument_type

CRASH_DROP = -0.15
HORIZON = 21
MIN_TRADES_60 = 5
FIRST_TEST_YEAR = 2016
TOP_SHARE = 0.10                     # "riskiest 10% of stocks each month"

STOCK_FEATURES = ["mom_1m", "mom_3m", "mom_12m", "vol_20", "vol_60", "dd_1y", "log_adv", "zero_60",
                  "log_amihud", "spikes_60"]
MARKET_FEATURES = ["nasi_1m", "nasi_vol_60", "flow_lag", "flow3_lag"]
FEATURES = STOCK_FEATURES + MARKET_FEATURES
LABELS = {
    "mom_1m": "Return, last month", "mom_3m": "Return, last 3 months", "mom_12m": "Return, last 12 months",
    "vol_20": "Volatility, 20 days", "vol_60": "Volatility, 60 days", "dd_1y": "Distance below 1-year high",
    "log_adv": "Value traded per day", "zero_60": "Share of days with no trades", "log_amihud": "Price impact per KES",
    "spikes_60": "Unusual spikes, last 60 days", "nasi_1m": "Market (NASI) return, last month",
    "nasi_vol_60": "Market volatility", "flow_lag": "Net foreign flow, latest month",
    "flow3_lag": "Net foreign flow, last 3 months",
}


# ------------------------------------------------------------------ features
def _per_stock(g: pd.DataFrame) -> pd.DataFrame:
    r = g["ret"].fillna(0.0)                         # corporate-action days count as 0 (see clean.split_prices)
    lp = np.log1p(r).cumsum()
    v = g["value_kes_adj"].fillna(0.0)
    tr = g["traded"].astype(float)
    o = pd.DataFrame(index=g.index)
    o["mom_1m"] = np.expm1(lp - lp.shift(21))
    o["mom_3m"] = np.expm1(lp - lp.shift(63))
    o["mom_12m"] = np.expm1(lp - lp.shift(250))
    o["vol_20"] = r.rolling(20, min_periods=15).std()
    o["vol_60"] = r.rolling(60, min_periods=40).std()
    o["dd_1y"] = np.expm1(lp - lp.rolling(250, min_periods=120).max())
    o["log_adv"] = np.log1p(v.rolling(60, min_periods=40).mean())
    o["zero_60"] = 1 - tr.rolling(60, min_periods=40).mean()
    o["traded_60"] = tr.rolling(60, min_periods=40).sum()
    ill = (r.abs() / (v / 1e6)).where(v > 0)
    o["log_amihud"] = np.log1p(ill.rolling(60, min_periods=5).mean())
    sd_prev = o["vol_60"].shift(1)
    o["spikes_60"] = ((r.abs() > 3 * sd_prev) & (tr > 0)).astype(float).rolling(60, min_periods=40).sum()
    o["fwd"] = np.expm1(lp.shift(-HORIZON) - lp)    # outcome only: never used as a feature
    o["fwd_end"] = g["date"].shift(-HORIZON)
    return o


def build_panel(stocks: pd.DataFrame, indices: pd.DataFrame, flows: pd.DataFrame,
                sectors: pd.DataFrame | None = None) -> pd.DataFrame:
    """Daily stock panel with features and the 21-day forward return."""
    s = stocks.sort_values(["code", "date"]).reset_index(drop=True)
    feats = s.groupby("code", group_keys=False)[["date", "ret", "value_kes_adj", "traded"]].apply(_per_stock)
    p = pd.concat([s[["date", "code", "name", "close"]], feats], axis=1)

    sec = (sectors.dropna(subset=["code"]).drop_duplicates("code").set_index("code")["sector"]
           if sectors is not None and "sector" in sectors else None)
    codes = p["code"].unique()
    inst = dict(zip(codes, instrument_type(codes, sec)))
    p["instrument"] = p["code"].map(inst)

    nasi = indices[indices["code"] == "^NASI"].sort_values("date")[["date", "close", "ret"]].copy()
    nasi["nasi_1m"] = nasi["close"] / nasi["close"].shift(21) - 1
    nasi["nasi_vol_60"] = nasi["ret"].rolling(60, min_periods=40).std()
    p = p.merge(nasi[["date", "nasi_1m", "nasi_vol_60"]], on="date", how="left")

    # foreign flow as known at the previous month-end (CMA publishes with a lag)
    f = flows.rename(columns={"net_flow_kes_m": "flow"})[["period", "flow"]].sort_values("period").copy()
    f["flow3"] = f["flow"].rolling(3).sum()
    p["_key"] = (p["date"].dt.to_period("M") - 1).dt.to_timestamp("M")
    p = pd.merge_asof(p.sort_values("_key"), f.rename(columns={"period": "_key", "flow": "flow_lag",
                                                               "flow3": "flow3_lag"}),
                      on="_key", direction="backward").drop(columns="_key")
    return p.sort_values(["code", "date"]).reset_index(drop=True)


def month_end_samples(panel: pd.DataFrame) -> pd.DataFrame:
    """Rows at each month's last trading day, eligible stocks only, with the crash label."""
    cal = panel["date"].drop_duplicates().sort_values()
    ends = set(cal.groupby(cal.dt.to_period("M")).max())
    d = panel[panel["date"].isin(ends) & (panel["instrument"] == "Equity")
              & (panel["traded_60"] >= MIN_TRADES_60) & panel["vol_60"].notna()].copy()
    d["crash"] = np.where(d["fwd"].notna(), (d["fwd"] <= CRASH_DROP).astype(float), np.nan)
    return d.reset_index(drop=True)


# ------------------------------------------------------------------ models
def _models() -> dict:
    return {
        "logistic": make_pipeline(SimpleImputer(strategy="median"), StandardScaler(),
                                  LogisticRegression(C=0.3, max_iter=3000)),
        "xgboost": XGBClassifier(n_estimators=300, max_depth=3, learning_rate=0.05, subsample=0.8,
                                 colsample_bytree=0.8, min_child_weight=5, reg_lambda=2.0,
                                 random_state=RANDOM_STATE, eval_metric="logloss", verbosity=0),
    }


def walk_forward(samples: pd.DataFrame, features: list[str] = FEATURES, models=("logistic", "xgboost"),
                 drop: float = CRASH_DROP) -> pd.DataFrame:
    """Out-of-sample predictions, one test year at a time. Training rows must have their outcome known
    before the test year starts (purge), so no label overlaps the test period."""
    lab = samples.dropna(subset=["fwd"]).copy()
    lab["crash"] = (lab["fwd"] <= drop).astype(int)
    out = []
    for year in range(FIRST_TEST_YEAR, lab["date"].dt.year.max() + 1):
        start = pd.Timestamp(year=year, month=1, day=1)
        train = lab[lab["fwd_end"] < start]
        test = lab[lab["date"].dt.year == year].copy()
        if test.empty or train["crash"].nunique() < 2:
            continue
        test["base_rate"] = train["crash"].mean()
        for name in models:
            m = _models()[name].fit(train[features], train["crash"])
            test[name] = m.predict_proba(test[features])[:, 1]
        out.append(test)
    return pd.concat(out, ignore_index=True)


def _top_hits(wf: pd.DataFrame, score: str, share: float = TOP_SHARE) -> pd.DataFrame:
    """Each month, the riskiest `share` of stocks by `score`."""
    def pick(g):
        k = max(1, int(np.ceil(share * len(g))))
        return g.nlargest(k, score)
    return wf.groupby("date", group_keys=False).apply(pick)


def evaluate(wf: pd.DataFrame, scores: dict[str, str]) -> pd.DataFrame:
    """Compare scores on the same out-of-sample rows. `scores` maps a display name to a column."""
    base = wf["crash"].mean()
    rows = []
    for name, col in scores.items():
        top = _top_hits(wf, col)
        top20 = _top_hits(wf, col, 0.20)
        k, n = int(top["crash"].sum()), len(top)
        p_col = wf[col] if wf[col].between(0, 1).all() and col != "vol_60" else None
        rows.append({
            "model": name, "auc": roc_auc_score(wf["crash"], wf[col]),
            "top10_crash_rate": k / n, "top10_n": n, "lift": (k / n) / base,
            "p_value_top10": binomtest(k, n, base, alternative="greater").pvalue,
            "caught_in_top20": top20["crash"].sum() / wf["crash"].sum(),
            "brier_skill": (1 - brier_score_loss(wf["crash"], p_col) / brier_score_loss(wf["crash"], wf["base_rate"]))
            if p_col is not None else np.nan,
            "base_rate": base, "n": len(wf),
        })
    return pd.DataFrame(rows)


def by_year(wf: pd.DataFrame, model: str = "xgboost") -> pd.DataFrame:
    rows = []
    for y, g in wf.groupby(wf["date"].dt.year):
        if g["crash"].nunique() < 2:
            continue
        top = _top_hits(g, model)
        rows.append({"year": int(y), "stock_months": len(g), "crashes": int(g["crash"].sum()),
                     "base_rate": g["crash"].mean(), "auc_model": roc_auc_score(g["crash"], g[model]),
                     "auc_volatility": roc_auc_score(g["crash"], g["vol_60"]),
                     "top10_crash_rate": top["crash"].mean()})
    return pd.DataFrame(rows)


def deciles(wf: pd.DataFrame, model: str = "xgboost") -> pd.DataFrame:
    """Crash rate by monthly risk decile (10 = riskiest)."""
    d = wf.copy()
    d["decile"] = d.groupby("date")[model].transform(lambda s: pd.qcut(s.rank(method="first"), 10, labels=False) + 1)
    return (d.groupby("decile").agg(stock_months=("crash", "size"), crash_rate=("crash", "mean"),
                                    avg_predicted=(model, "mean")).reset_index())


def auc_gap_ci(wf: pd.DataFrame, a: str, b: str, n_boot: int = 1000, seed: int = RANDOM_STATE) -> dict:
    """95% interval for AUC(a) - AUC(b), resampling whole months (rows within a month are related)."""
    rng = np.random.default_rng(seed)
    groups = [g for _, g in wf.groupby("date")]
    gaps = []
    for _ in range(n_boot):
        s = pd.concat([groups[i] for i in rng.integers(0, len(groups), len(groups))])
        if s["crash"].nunique() == 2:
            gaps.append(roc_auc_score(s["crash"], s[a]) - roc_auc_score(s["crash"], s[b]))
    lo, hi = np.percentile(gaps, [2.5, 97.5])
    return {"gap": roc_auc_score(wf["crash"], wf[a]) - roc_auc_score(wf["crash"], wf[b]),
            "ci_low": float(lo), "ci_high": float(hi)}


def live(samples_all: pd.DataFrame, panel: pd.DataFrame, features: list[str] = FEATURES) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Train on every labelled month and score each eligible stock on the latest date."""
    lab = samples_all.dropna(subset=["fwd"])
    m = _models()["xgboost"].fit(lab[features], (lab["fwd"] <= CRASH_DROP).astype(int))
    last = panel[panel["date"] == panel["date"].max()]
    now = last[(last["instrument"] == "Equity") & (last["traded_60"] >= MIN_TRADES_60) & last["vol_60"].notna()].copy()
    now["crash_prob"] = m.predict_proba(now[features])[:, 1]
    now["risk_rank"] = now["crash_prob"].rank(ascending=False, method="first").astype(int)
    imp = pd.DataFrame({"feature": features, "importance": m.feature_importances_})
    imp["label"] = imp["feature"].map(LABELS)
    keep = ["date", "code", "name", "close", "crash_prob", "risk_rank", "mom_1m", "mom_3m", "vol_60", "dd_1y",
            "zero_60", "spikes_60"] + (["garch_vol"] if "garch_vol" in now else [])
    return now[keep].sort_values("risk_rank").reset_index(drop=True), imp.sort_values("importance", ascending=False)


def run(stocks, indices, flows, sectors=None) -> dict:
    from . import garch
    panel = build_panel(stocks, indices, flows, sectors)
    gv, gstats = garch.forecasts_weekly(stocks)                 # stochastic volatility forecast (challenger input)
    panel = panel.merge(gv, on=["date", "code"], how="left").merge(garch.realized_forward(stocks),
                                                                   on=["date", "code"], how="left")
    samples = month_end_samples(panel)
    wf = walk_forward(samples)
    wf_stock = walk_forward(samples, STOCK_FEATURES, models=("xgboost",)).rename(columns={"xgboost": "xgb_stock_only"})
    wf_garch = walk_forward(samples, FEATURES + ["garch_vol"], models=("xgboost",)).rename(columns={"xgboost": "xgb_garch"})
    wf = (wf.merge(wf_stock[["date", "code", "xgb_stock_only"]], on=["date", "code"], how="left")
            .merge(wf_garch[["date", "code", "xgb_garch"]], on=["date", "code"], how="left"))
    wf["garch_rule"] = wf["garch_vol"].fillna(wf["vol_60"])     # GARCH forecast, or the 60-day figure where no fit
    compare = evaluate(wf, {"XGBoost, all inputs (live model)": "xgboost", "Logistic regression, all inputs": "logistic",
                            "XGBoost, stock inputs only": "xgb_stock_only",
                            "XGBoost + GARCH forecast (challenger)": "xgb_garch",
                            "Rule: most volatile stocks": "vol_60", "Rule: highest GARCH forecast": "garch_rule"})
    garch_eval = garch.evaluate(samples, FIRST_TEST_YEAR) | gstats
    robust = []
    for drop in (-0.10, -0.20):
        w = walk_forward(samples, models=("xgboost",), drop=drop)
        robust.append({"crash_definition": f"fall of {abs(drop):.0%} or more", "base_rate": w["crash"].mean(),
                       "auc_model": roc_auc_score(w["crash"], w["xgboost"]),
                       "auc_volatility": roc_auc_score(w["crash"], w["vol_60"])})
    now, imp = live(samples, panel)
    dec = deciles(wf)
    # raw probabilities run high (negative Brier skill), so report each stock's risk group and that
    # group's actual crash rate in the out-of-sample test instead
    now["risk_decile"] = 10 - ((now["risk_rank"] - 1) * 10 // len(now))
    now["group_crash_rate"] = now["risk_decile"].map(dec.set_index("decile")["crash_rate"])
    gap = auc_gap_ci(wf, "xgboost", "vol_60")
    garch_eval |= {"auc_gap_vs_last60_rule": auc_gap_ci(wf, "garch_rule", "vol_60"),
                   "auc_gap_vs_live_model": auc_gap_ci(wf, "garch_rule", "xgboost")}
    return {"panel": panel, "garch_eval": garch_eval, "walk_forward": wf, "compare": compare, "by_year": by_year(wf), "deciles": dec,
            "robust": pd.DataFrame(robust), "live": now, "importance": imp, "auc_gap_vs_volatility": gap,
            "n_samples": len(samples.dropna(subset=["fwd"])), "n_stocks": samples["code"].nunique()}
