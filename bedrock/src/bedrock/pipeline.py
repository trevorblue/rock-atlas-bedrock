"""Run the whole analysis and save everything the dashboard and the note need.

    python -m bedrock.pipeline              # clean raw data, then run modules A, C, B, stress test, E
    python -m bedrock.pipeline --skip-clean # reuse data/processed/*.parquet

Outputs go to data/processed/outputs/.
"""
from __future__ import annotations

import argparse
import json

import numpy as np
import pandas as pd

from . import clean, crash, demo, depth, radar, robustness, selloff, speculation, stress
from .config import MANUAL, PROCESSED, ROCK

OUT = PROCESSED / "outputs"


def _load(name: str) -> pd.DataFrame:
    return pd.read_parquet(PROCESSED / f"{name}.parquet")


def _json(obj, path):
    def conv(o):
        if isinstance(o, (pd.Timestamp,)):
            return str(o.date())
        if isinstance(o, (np.integer,)):
            return int(o)
        if isinstance(o, (np.floating,)):
            return None if np.isnan(o) else float(o)
        if isinstance(o, pd.DataFrame):
            return o.to_dict("records")
        return str(o)
    path.write_text(json.dumps(obj, default=conv, indent=2))


def depth_history(stocks, shareholding, sectors) -> pd.DataFrame:
    """Headline numbers at each quarter-end, to show how depth changed over time."""
    cal = depth.trading_calendar(stocks)
    qends = pd.Series(cal).groupby(pd.Series(cal).dt.to_period("Q")).max()
    rows = []
    for d in qends[qends >= cal[0] + pd.Timedelta(days=200)]:
        snap = depth.depth_snapshot(stocks, shareholding, sectors, as_of=d)
        rows.append(depth.headline(snap))
    return pd.DataFrame(rows)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-clean", action="store_true")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    if not a.skip_clean:
        clean.build_all()
    stocks, indices = _load("stocks"), _load("indices")
    sectors, share = _load("sectors"), _load("shareholding")
    flows, macro = _load("foreign_flows"), _load("macro")

    print("Module A  Market Depth ...")
    snap = depth.depth_snapshot(stocks, share, sectors)
    snap.to_parquet(OUT / "depth_snapshot.parquet", index=False)
    head = depth.headline(snap)
    depth.concentration_monthly(stocks).to_parquet(OUT / "concentration.parquet", index=False)
    hist = depth_history(stocks, share, sectors)
    hist.to_parquet(OUT / "depth_history.parquet", index=False)
    print(f"  {head['pct_over_20d']:.0%} of {head['n_stocks']} listed shares need >20 days to exit KES 10m; "
          f"top-5 stocks = {head['top5_share_of_value']:.0%} of value traded")

    print("Module C  Speculation Watch ...")
    feats = speculation.build_features(stocks, indices)
    scored = speculation.detect(feats)
    news_file = MANUAL / "news_checks.csv"
    speculation.to_check(scored, news_file)          # adds new candidates to check by hand
    scored = speculation.attach_news(scored, news_file)
    scored[scored["flag"]].to_parquet(OUT / "speculation_flags.parquet", index=False)
    size = stocks.groupby("code")["value_kes_adj"].mean()
    val = speculation.validation(scored, size)
    val.to_parquet(OUT / "speculation_validation.parquet", index=False)
    print(f"  {int(scored['flag'].sum()):,} unusual stock-days, {int(scored['watch'].sum()):,} on the watch list")

    print("Module B  Sell-off Alert ...")
    sb = selloff.run(flows, macro, stocks, indices)
    sb["dataset"].reset_index().to_parquet(OUT / "selloff_dataset.parquet", index=False)
    sb["walk_forward"].to_parquet(OUT / "selloff_walk_forward.parquet", index=False)
    sb["evaluation"].to_parquet(OUT / "selloff_evaluation.parquet", index=False)
    live = sb["live"]
    live["drivers"].to_parquet(OUT / "selloff_drivers.parquet", index=False)
    _json({k: v for k, v in live.items() if k != "drivers"} | {"freq": sb["freq"]}, OUT / "selloff_live.json")
    print(f"  {live['period']:%b %Y}: P(heavy foreign selling next period) = {live['probability']:.0%} -> {live['signal']}"
          f"  [model: {live['model']}]")

    print("Stress test (default scenario) ...")
    recent = scored[(scored["watch"]) & (scored["date"] >= scored["date"].max() - pd.Timedelta(days=60))]
    res = stress.run_scenario(snap, speculative_codes=set(recent["code"]))
    summ = stress.summarize(res, res["sell_kes"].sum())
    print(f"  KES 2bn over 5 days: {summ['n_trapped']} stocks trapped, value-weighted impact {summ['weighted_impact']:.1%}")

    print("Module E  Crash Risk (stock by stock) ...")
    cr = crash.run(stocks, indices, flows, sectors)
    for k in ("compare", "by_year", "deciles", "robust", "live", "importance"):
        cr[k].to_parquet(OUT / f"crash_{k}.parquet", index=False)
    cmp_ = cr["compare"].set_index("model")
    mdl, rule = cmp_.iloc[0], cmp_.loc["Rule: most volatile stocks"]
    dec = cr["deciles"].set_index("decile")["crash_rate"]
    crash_summary = {"crash_drop": crash.CRASH_DROP, "horizon_days": crash.HORIZON, "n_test": int(mdl["n"]),
                     "n_samples": cr["n_samples"], "n_stocks": cr["n_stocks"], "first_test_year": crash.FIRST_TEST_YEAR,
                     "base_rate": mdl["base_rate"], "top10_rate": mdl["top10_crash_rate"], "lift": mdl["lift"],
                     "p_value_top10": mdl["p_value_top10"], "safest10_rate": dec.loc[1],
                     "rule_top10_rate": rule["top10_crash_rate"], "auc_model": mdl["auc"], "auc_rule": rule["auc"],
                     "auc_gap_vs_rule": cr["auc_gap_vs_volatility"],
                     "riskiest_now": cr["live"].head(5)["code"].tolist(), "as_of": cr["live"]["date"].max()}
    _json(crash_summary, OUT / "crash_summary.json")
    _json(cr["garch_eval"], OUT / "garch_eval.json")
    print(f"  riskiest 10% crashed {mdl['top10_crash_rate']:.1%} of the time vs {mdl['base_rate']:.1%} average "
          f"(volatility rule {rule['top10_crash_rate']:.1%}); riskiest now: {', '.join(crash_summary['riskiest_now'])}")

    print("Module F  Opportunity Radar + Resilience ...")
    ra = radar.run(cr["panel"], indices)
    ra["monthly_radar"].to_parquet(OUT / "radar_monthly.parquet", index=False)
    ra["monthly_resilience"].to_parquet(OUT / "radar_resilience_monthly.parquet", index=False)
    ra["live"].to_parquet(OUT / "radar_live.parquet", index=False)
    _json(ra["summary"] | {"exit_days": radar.EXIT_DAYS, "test_position_kes": radar.TEST_POSITION},
          OUT / "radar_summary.json")
    s_ = ra["summary"]
    print(f"  top third beat bottom third by {s_['spread_avg']:+.2%} a month (t = {s_['spread_t']:.1f}); "
          f"{s_['paper_fail_share_1m']:.0%} of paper top picks fail the exit check at KES 1m")
    demo.fundamentals_demo().to_parquet(OUT / "demo_fundamentals.parquet", index=False)
    demo.foreign_flows_demo().to_parquet(OUT / "demo_foreign_flows.parquet", index=False)
    wk = demo.selloff_weekly_demo()
    wk_wf, wk_live = demo.selloff_demo_results(wk)
    wk.reset_index().to_parquet(OUT / "demo_selloff_flows.parquet", index=False)
    wk_wf.to_parquet(OUT / "demo_selloff_walk_forward.parquet", index=False)
    _json(wk_live, OUT / "demo_selloff_live.json")
    demo.opportunities_demo().to_parquet(OUT / "demo_opportunities.parquet", index=False)

    print("Robustness checks ...")
    rb = robustness.run_all(stocks, share, sectors, sb["walk_forward"], sb["best_model"], scored, sb["dataset"])
    for k, v in rb.items():
        v.to_parquet(OUT / f"robustness_{k}.parquet", index=False)
    sig = rb["selloff_significance"].set_index("model").loc[sb["best_model"]]
    print(f"  HIGH RISK calls: {int(sig['hits'])}/{int(sig['high_risk_calls'])} hit vs base {sig['base_rate']:.0%}"
          f" (p = {sig['p_value_vs_base']:.3f})")

    _json({"depth": head, "selloff": {k: live[k] for k in ("period", "probability", "signal", "model")},
           "stress_default": summ,
           "crash": {k: crash_summary[k] for k in ("top10_rate", "base_rate", "safest10_rate", "rule_top10_rate",
                                                   "riskiest_now")},
           "uses_rock_data": any((ROCK / f).exists() for f in ("prices.csv", "foreign_flows.csv")),
           "data_as_of": {"stocks": stocks["date"].max(), "flows": flows["period"].max(), "macro": macro["period"].max()}},
          OUT / "headline.json")
    print(f"\nSaved outputs to {OUT}\nNext: streamlit run app/streamlit_app.py")


if __name__ == "__main__":
    main()
