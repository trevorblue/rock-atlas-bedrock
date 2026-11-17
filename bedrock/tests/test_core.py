"""Fast unit tests on small synthetic data (no downloads needed).  Run:  pytest -q"""
import numpy as np
import pandas as pd
import pytest

from bedrock import clean, crash, demo, depth, garch, nse_ocr, radar, selloff, speculation, stress


# ------------------------------------------------------------------ helpers
def _stocks(n_days=150):
    """Three stocks: DEEP trades a lot, THIN a little, DEAD never."""
    dates = pd.bdate_range("2026-01-01", periods=n_days)
    rows = []
    rng = np.random.default_rng(0)
    for code, vol, px in [("DEEP", 1_000_000, 20.0), ("THIN", 2_000, 10.0), ("DEAD", 0, 5.0)]:
        close = px * np.cumprod(1 + rng.normal(0, 0.01, n_days)) if vol else np.full(n_days, px)
        for i, d in enumerate(dates):
            rows.append({"date": d, "code": code, "name": code, "close": close[i],
                         "prev": close[i - 1] if i else close[i], "day_low": close[i], "day_high": close[i],
                         "volume": float(vol)})
    st, _ = clean.split_prices(pd.DataFrame(rows))
    return st


def _shareholding():
    return pd.DataFrame({"code": ["DEEP", "THIN", "DEAD"], "shares_issued": [1e9, 1e8, 1e7],
                         "foreign_pct": [0.3, 0.2, 0.9]})


# ------------------------------------------------------------------ clean
def test_num_parsing():
    s = clean._num(pd.Series(["1,234.5", "-", "", "(12)", "7%"]))
    assert s.iloc[0] == 1234.5 and np.isnan(s.iloc[1]) and np.isnan(s.iloc[2])
    assert s.iloc[3] == -12 and s.iloc[4] == 7


def test_split_prices_drops_corporate_action_returns():
    df = pd.DataFrame({"date": pd.to_datetime(["2026-01-01", "2026-01-02"] * 2),
                       "code": ["AAA", "AAA", "^NASI", "^NASI"], "name": "x",
                       "close": [10.0, 30.0, 100.0, 101.0], "prev": [10.0, 10.0, 100.0, 100.0],
                       "day_low": np.nan, "day_high": np.nan, "volume": [100, np.nan, np.nan, np.nan]})
    st, ix = clean.split_prices(df)
    assert len(ix) == 2 and ix["ret"].iloc[1] == pytest.approx(0.01)
    assert np.isnan(st["ret"].iloc[1])                   # +200% treated as a split, not a return
    assert st["volume"].iloc[1] == 0 and not st["traded"].iloc[1]


def test_extend_nasi_chains_cap_weighted_returns():
    st = _stocks(5)
    ix = pd.DataFrame({"date": [st["date"].min()], "code": ["^NASI"], "name": ["NASI"],
                       "close": [100.0], "prev": [100.0], "ret": [0.0]})
    out = clean.extend_nasi(st, ix, _shareholding())
    nasi = out[out["code"] == "^NASI"].sort_values("date")
    assert len(nasi) == 5 and (nasi["name"].iloc[1:] == "NASI (rebuilt)").all()
    assert nasi["close"].iloc[-1] == pytest.approx(100 * (1 + nasi["ret"].iloc[1:]).prod())


# ------------------------------------------------------------------ depth
def test_tiers():
    t = depth.tier_from_days(pd.Series([1, 10, 100, 1000, np.inf]))
    assert list(t) == ["1 Deep", "2 Moderate", "3 Thin", "4 Frozen", "4 Frozen"]


def test_depth_snapshot_orders_liquidity():
    snap = depth.depth_snapshot(_stocks(), _shareholding()).set_index("code")
    assert snap.loc["DEEP", "days_to_exit"] < snap.loc["THIN", "days_to_exit"]
    assert np.isinf(snap.loc["DEAD", "days_to_exit"])
    assert snap.loc["DEAD", "zero_trade_share"] == 1.0


# ------------------------------------------------------------------ stress
def _snap():
    return pd.DataFrame({"code": ["A", "B", "C", "P"], "name": "x", "sector": "s", "tier": "t",
                         "instrument": "Equity", "foreign_pct": [0.2, 0.2, 0.2, 0.8],
                         "market_cap_kes": [100e9, 10e9, 1e9, 50e9], "adv_kes": [5e9, 1e6, 0, 10e6],
                         "volatility": [0.02, 0.03, 0.03, 0.02]})


def test_stress_allocation_and_status():
    res = stress.run_scenario(_snap(), total_sell_kes=1e9, days=5, participation=0.2, max_foreign_pct=0.5)
    r = res.set_index("code")
    assert r.loc["P", "sell_kes"] == 0 and r.loc["P", "status"] == "not hit"     # strategic stake
    assert res["sell_kes"].sum() == pytest.approx(1e9)
    assert r.loc["A", "status"] == "absorbed"
    assert r.loc["C", "status"] == "no market"
    assert r.loc["B", "status"] == "trapped"
    s = stress.summarize(res, 1e9)
    assert s["n_trapped"] == 2 and s["n_no_market"] == 1


# ------------------------------------------------------------------ sell-off
def test_signal_bands():
    assert selloff.signal(0.6) == "HIGH RISK"
    assert selloff.signal(0.05) == "NO CALL"         # no all-clear: low readings hit ~ the normal rate
    assert selloff.signal(0.3) == "NO CALL"


def test_infer_freq():
    assert selloff.infer_freq(pd.Series(pd.date_range("2025-01-31", periods=12, freq="ME"))) == "ME"
    assert selloff.infer_freq(pd.Series(pd.date_range("2025-01-03", periods=30, freq="W-FRI"))) != "ME"


# ------------------------------------------------------------------ speculation news file
def test_attach_news(tmp_path):
    scored = pd.DataFrame({"date": pd.to_datetime(["2026-07-01", "2026-07-02"]), "code": ["AAA", "BBB"], "news": ""})
    f = tmp_path / "news.csv"
    pd.DataFrame({"date": ["2026-07-01", "2026-07-02"], "code": ["AAA", "BBB"], "news_found": ["yes", "no"],
                  "headline": ["Profit warning", ""], "source_url": "", "checked_on": ""}).to_csv(f, index=False)
    out = speculation.attach_news(scored, f)
    assert out["news"].tolist() == ["yes: Profit warning", "no news found"]


# ------------------------------------------------------------------ OCR row parser
def test_parse_boxes_rebuilds_rows():
    W = 1000.0
    boxes = []
    for i, (isin, name, nums) in enumerate([("KE0000000001", "Alpha Bank", ["21.50", "20.00", "20.80", "20.40", "15,300"]),
                                            ("KE0000000002", "Beta Ltd", ["5.10", "5.00", "5.05", "5.00", "900"]),
                                            ("KE0000000003", "Gamma Plc", ["9.00", "8.80", "8.90", "8.95", "1,200"])]):
        y = 100 + 30 * i
        boxes += [(0, 10, 60, y, 12, "30.00"), (0, 70, 120, y, 12, "15.00"), (0, 130, 260, y, 12, name),
                  (0, 300, 420, y, 12, isin)]
        for x1, t in zip([600, 680, 760, 840, 940], nums):
            boxes.append((0, x1 - 40, x1, y + 1, 12, t))
    df = nse_ocr.parse_boxes(boxes, W)
    assert len(df) == 3
    a = df.iloc[0]
    assert a["name_raw"] == "Alpha Bank" and a["high_52w"] == 30.0
    assert (a["high"], a["low"], a["vwap"], a["prev"], a["volume"]) == (21.5, 20.0, 20.8, 20.4, 15300)


def test_to_check_keeps_existing_and_adds_new(tmp_path):
    f = tmp_path / "news.csv"
    pd.DataFrame({"date": ["2026-07-01"], "code": ["AAA"], "news_found": ["no"], "headline": [""],
                  "source_url": [""], "checked_on": ["2026-11-16"]}).to_csv(f, index=False)
    scored = pd.DataFrame({"date": pd.to_datetime(["2026-07-01", "2026-07-02", "2026-07-03"]),
                           "code": ["AAA", "BBB", "CCC"], "watch": [True, True, False],
                           "anomaly_score": [0.7, 0.6, 0.9]})
    out = speculation.to_check(scored, f)
    assert list(out["code"]) == ["AAA", "BBB"]
    assert out.loc[out["code"] == "AAA", "news_found"].iloc[0] == "no"       # hand check preserved
    again = speculation.to_check(scored, f)                                   # idempotent
    assert len(again) == 2


# ------------------------------------------------------------------ crash risk (module E)
def _crash_inputs(n=300, seed=1):
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2024-01-01", periods=n)
    rows = []
    for code in ["AAA", "BBB"]:
        r = rng.normal(0, 0.02, n)
        close = 10 * np.cumprod(1 + r)
        rows += [{"date": d, "code": code, "name": code, "close": close[i], "ret": r[i],
                  "value_kes_adj": 1e6, "traded": True} for i, d in enumerate(dates)]
    ix = pd.DataFrame({"date": dates, "code": "^NASI", "close": 100 * np.cumprod(1 + rng.normal(0, 0.01, n)),
                       "ret": rng.normal(0, 0.01, n)})
    fl = pd.DataFrame({"period": pd.date_range("2023-06-30", periods=24, freq="ME"),
                       "net_flow_kes_m": rng.normal(0, 1000, 24)})
    return pd.DataFrame(rows), ix, fl


def test_crash_features_use_no_future_data():
    st, ix, fl = _crash_inputs()
    cut = np.sort(st["date"].unique())[200]
    p1 = crash.build_panel(st, ix, fl)
    st2 = st.copy()
    future = st2["date"] > cut
    st2.loc[future, "ret"] = -0.05                     # a crash after the cut-off ...
    st2.loc[future, "value_kes_adj"] = 9e9
    p2 = crash.build_panel(st2, ix, fl)
    a = p1[p1["date"] == cut].set_index("code")[crash.FEATURES]
    b = p2[p2["date"] == cut].set_index("code")[crash.FEATURES]
    pd.testing.assert_frame_equal(a, b)                # ... leaves every feature on the cut-off day unchanged
    fwd = p2[p2["date"] == cut].set_index("code")["fwd"]
    assert (fwd <= crash.CRASH_DROP).all()             # but the outcome sees it


# ------------------------------------------------------------------ opportunity radar (module F) + demo
def test_radar_exit_check_blocks_thin_stocks():
    days = radar.days_to_exit(pd.Series([50e6, 1e6, 0.0]), 10e6)     # KES a day traded
    assert days.iloc[0] == pytest.approx(1.0)                        # 10m / (20% x 50m)
    assert days.iloc[1] == pytest.approx(50.0) and days.iloc[1] > radar.EXIT_DAYS
    assert np.isinf(days.iloc[2])                                    # never trades -> can't get out


def test_radar_resilience_uses_no_future_data():
    st, ix, fl = _crash_inputs(n=700)
    m1 = radar.monthly(crash.build_panel(st, ix, fl), ix)
    cut = m1["date"].drop_duplicates().sort_values().iloc[24]
    st2, ix2 = st.copy(), ix.copy()
    st2.loc[st2["date"] > cut, "ret"] = -0.05
    ix2.loc[ix2["date"] > cut, "ret"] = 0.04
    ix2.loc[ix2["date"] > cut, "close"] *= 3
    m2 = radar.monthly(crash.build_panel(st2, ix2, fl), ix2)
    cols = ["mom_12_1", "vol_60", "resilience"]
    a = m1[m1["date"] == cut].set_index("code")[cols]
    b = m2[m2["date"] == cut].set_index("code")[cols]
    assert a["resilience"].notna().all()
    pd.testing.assert_frame_equal(a, b)


def test_demo_data_is_labelled_and_fictional():
    d = demo.fundamentals_demo()
    assert d["company"].str.startswith("Demo Company").all()
    assert (d["data"] == demo.LABEL).all()


# ------------------------------------------------------------------ GARCH volatility forecast
def test_garch_forecast_uses_no_future_data():
    rng = np.random.default_rng(3)
    r = rng.standard_t(5, 600)
    params = (0.0, 0.1, 0.1, 0.85)                       # mu, omega, alpha, beta
    a = garch.forecast_path(r, params)
    r2 = r.copy()
    r2[400:] *= 10                                       # a storm after day 400 ...
    b = garch.forecast_path(r2, params)
    assert np.allclose(a[:400], b[:400])                 # ... cannot change any forecast made before it
    assert b[450] > a[450]                               # but forecasts after it react
    assert (a > 0).all()
