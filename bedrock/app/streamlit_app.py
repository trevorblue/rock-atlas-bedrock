"""Bedrock dashboard.  Run:  streamlit run app/streamlit_app.py
Reads the outputs written by `python -m bedrock.pipeline` (or the committed app/snapshot/ when deployed).
"""
from __future__ import annotations

import json
import sys
from html import escape
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from scipy.stats import binomtest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from bedrock import stress  # noqa: E402
from bedrock.config import (DEFAULT_SCENARIO_DAYS, DEFAULT_SCENARIO_KES, HIGH_RISK_PROB,  # noqa: E402
                            PARTICIPATION, POSITION_KES, PROCESSED, STRATEGIC_CUTOFF)

OUT = PROCESSED / "outputs"
if not (OUT / "headline.json").exists():          # deployed (Streamlit Cloud): use the committed snapshot
    OUT = ROOT / "app" / "snapshot"
st.set_page_config(page_title="Bedrock · NSE fragility monitor", page_icon="🪨", layout="wide",
                   initial_sidebar_state="collapsed")

# ---------------------------------------------------------------- design tokens
INK, MUTED, FAINT, LINE, GRID, CARD = "#1B2420", "#5F6662", "#9AA09C", "#E5E1D8", "#EFECE5", "#FFFFFF"
ACCENT = "#B83A2B"                               # UI accent: risk badge, eyebrows
BLUE, RED = "#2a78d6", "#e34948"                 # chart series (validated reference palette)
STATUS = {"good": "#0ca30c", "warning": "#fab219", "serious": "#ec835a", "critical": "#d03b3b"}
TIER_COLORS = {"1 Deep": STATUS["good"], "2 Moderate": STATUS["warning"], "3 Thin": STATUS["serious"],
               "4 Frozen": STATUS["critical"]}
STRESS_COLORS = {"absorbed": STATUS["good"], "strained": STATUS["warning"], "trapped": STATUS["critical"]}
FONT = "Inter, 'Segoe UI', system-ui, -apple-system, sans-serif"

CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');
html, body, .stApp, .stMarkdown, button, input {{ font-family: {FONT}; }}
header[data-testid="stHeader"] {{ display: none; }}
.block-container {{ padding-top: 1.4rem; padding-bottom: 2.5rem; max-width: 1320px; }}
.bd-top {{ display: flex; align-items: center; justify-content: space-between; gap: 16px; flex-wrap: wrap; }}
.bd-brand {{ display: flex; align-items: center; gap: 10px; font-family: 'Space Grotesk', {FONT};
             font-weight: 700; font-size: 21px; color: {INK}; }}
.bd-mark {{ width: 24px; height: 24px; border-radius: 6px; background: {INK};
            box-shadow: inset 0 -7px 0 {ACCENT}; display: inline-block; }}
.bd-tagline {{ font-family: {FONT}; font-weight: 500; font-size: 14px; color: {MUTED}; margin-left: 4px; }}
.bd-asof {{ font-size: 13px; color: {MUTED}; }}
.bd-eyebrow {{ font-size: 12px; font-weight: 700; letter-spacing: .12em; color: {ACCENT}; margin: 30px 0 10px;
               display: flex; align-items: center; gap: 12px; }}
.bd-h1 {{ font-family: 'Space Grotesk', {FONT}; font-size: 34px; line-height: 1.14; font-weight: 600;
          color: {INK}; margin: 0 0 8px; max-width: 1180px; letter-spacing: -0.01em; }}
.bd-sub {{ font-size: 16px; line-height: 1.5; color: {MUTED}; margin: 0 0 22px; max-width: 820px; }}
.bd-badge {{ display: inline-block; background: {ACCENT}; color: #fff; font-weight: 700; font-size: 13px;
             letter-spacing: .08em; border-radius: 999px; padding: 5px 13px; vertical-align: middle; margin-right: 10px; }}
.bd-badge.quiet {{ background: {FAINT}; }}
.bd-kpis {{ display: grid; gap: 14px; margin: 0 0 14px; }}
.bd-kpi {{ background: {CARD}; border: 1px solid {LINE}; border-radius: 16px; padding: 18px 20px 16px; }}
.bd-kpi .v {{ font-family: 'Space Grotesk', {FONT}; font-size: 34px; font-weight: 600; line-height: 1.05; color: {INK}; }}
.bd-kpi .v.risk {{ color: {ACCENT}; }}
.bd-kpi .l {{ font-size: 14px; line-height: 1.4; color: {MUTED}; margin-top: 8px; }}
.bd-model {{ display: flex; align-items: center; flex-wrap: wrap; gap: 6px 12px; font-size: 13.5px; color: {MUTED};
             border-top: 1px solid {LINE}; border-bottom: 1px solid {LINE}; padding: 10px 2px; margin: 4px 0 18px; }}
.bd-model .tag {{ font-size: 11px; font-weight: 700; letter-spacing: .1em; color: #fff; background: {INK};
                  border-radius: 5px; padding: 3px 8px; }}
.bd-model b {{ color: {INK}; font-weight: 600; }}
.bd-note {{ font-size: 14px; color: {MUTED}; margin: -4px 0 18px; }}
.bd-note b {{ color: {INK}; }}
.bd-cards {{ display: grid; gap: 14px; margin: 4px 0 18px; }}
.bd-card {{ background: {CARD}; border: 1px solid {LINE}; border-radius: 18px; padding: 20px 22px; }}
.bd-card .k {{ font-size: 11.5px; font-weight: 700; letter-spacing: .12em; color: {MUTED}; }}
.bd-card .v {{ font-family: 'Space Grotesk', {FONT}; font-size: 34px; font-weight: 600; line-height: 1.05;
               color: {INK}; margin: 12px 0 8px; }}
.bd-card .v.risk {{ color: {ACCENT}; }}
.bd-card .d {{ font-size: 14.5px; line-height: 1.45; color: {MUTED}; }}
.bd-stock {{ background: {CARD}; border: 1px solid {LINE}; border-radius: 14px; padding: 14px 18px; font-size: 15px;
             color: {MUTED}; line-height: 1.6; }}
.bd-stock b {{ color: {INK}; }}
.bd-foot {{ font-size: 12.5px; color: {FAINT}; margin-top: 30px; padding-top: 12px; border-top: 1px solid {LINE}; }}
.st-key-nav_sec button {{ font-weight: 600; }}
[class*="st-key-nav_p"] {{ margin-top: -6px; }}
[class*="st-key-nav_p"] button {{ background: transparent; }}
.bd-question {{ margin: 22px 0 0; padding: 12px 16px; background: {CARD}; border: 1px solid {LINE};
                border-left: 4px solid {ACCENT}; border-radius: 10px; font-size: 15.5px; color: {INK}; }}
.bd-question span {{ font-size: 11.5px; font-weight: 700; letter-spacing: .1em; color: {MUTED}; margin-right: 8px; }}
.bd-demo {{ border: 2px dashed {ACCENT}; border-radius: 14px; padding: 14px 18px; margin: 18px 0 4px;
            background: rgba(184,58,43,0.06); color: {INK}; font-size: 15px; line-height: 1.5; }}
.bd-demo b {{ color: {ACCENT}; letter-spacing: .06em; }}
.bd-table {{ width: 100%; border-collapse: collapse; background: {CARD}; border: 1px solid {LINE}; border-radius: 14px;
             overflow: hidden; font-size: 14.5px; margin: 4px 0 18px; }}
.bd-table th {{ text-align: left; font-size: 11.5px; letter-spacing: .08em; color: {MUTED}; font-weight: 700;
                padding: 11px 14px; border-bottom: 1px solid {LINE}; text-transform: uppercase; }}
.bd-table td {{ padding: 11px 14px; border-bottom: 1px solid {LINE}; vertical-align: top; color: {INK}; line-height: 1.45; }}
.bd-table tr:last-child td {{ border-bottom: none; }}
.bd-pill {{ display: inline-block; font-size: 12px; font-weight: 700; border-radius: 999px; padding: 2px 10px; white-space: nowrap; }}
.bd-pill.good {{ color: #1F7A4D; background: #E3F2E9; }} .bd-pill.ok {{ color: #8A5A00; background: #FBEFD5; }}
.bd-pill.bad {{ color: {ACCENT}; background: #F7E4E0; }} .bd-pill.na {{ color: {MUTED}; background: #ECEAE4; }}
[data-testid="stPlotlyChart"] {{ background: {CARD}; border: 1px solid {LINE}; border-radius: 16px; padding: 0;
                                 overflow: hidden; }}
[data-testid="stExpander"] details {{ border: 1px solid {LINE}; border-radius: 12px; background: transparent; }}
[data-testid="stExpander"] summary p {{ font-size: 14.5px; font-weight: 500; color: {INK}; }}
@media (max-width: 1000px) {{
  .bd-cards {{ grid-template-columns: repeat(2, minmax(0, 1fr)) !important; }}
  .bd-kpis {{ grid-template-columns: repeat(2, minmax(0, 1fr)) !important; }}
  .bd-h1 {{ font-size: 28px; }}
}}
</style>
"""


# ---------------------------------------------------------------- helpers
def kes(x: float) -> str:
    if x is None or not np.isfinite(x):
        return "-"
    for d, s in [(1e9, "bn"), (1e6, "m"), (1e3, "k")]:
        if abs(x) >= d:
            v = x / d
            return f"KES {v:,.1f}{s}".replace(".0" + s, s)
    return f"KES {x:,.0f}"


def html(s: str) -> None:
    st.markdown(s, unsafe_allow_html=True)


def hero(eyebrow: str, title: str, sub: str = "", badge: str = "") -> None:
    b = f"<span class='bd-badge{'' if badge == 'HIGH RISK' else ' quiet'}'>{badge}</span>" if badge else ""
    html(f"<div class='bd-eyebrow'>{eyebrow}{b}</div><div class='bd-h1'>{title}</div>"
         + (f"<div class='bd-sub'>{sub}</div>" if sub else ""))


def kpis(items: list[tuple[str, str, bool]]) -> None:
    cells = "".join(f"<div class='bd-kpi'><div class='v{' risk' if r else ''}'>{v}</div><div class='l'>{l}</div></div>"
                    for v, l, r in items)
    html(f"<div class='bd-kpis' style='grid-template-columns:repeat({len(items)},minmax(0,1fr))'>{cells}</div>")


def model(name: str, *facts: str) -> None:
    html("<div class='bd-model'><span class='tag'>MODEL</span><b>" + name + "</b>"
         + "".join(f"<span>· {f}</span>" for f in facts) + "</div>")


def chart(fig: go.Figure, title: str = "", sub: str = "", height: int = 360, legend: bool = False,
          hbar: bool = False) -> None:
    t = (f"<b>{title}</b>" + (f"<br><span style='font-size:12.5px;color:{MUTED}'>{sub}</span>" if sub else "")) if title else None
    top = (16 + (40 if sub else 22) + (28 if legend else 0)) if title else 8
    fig.update_layout(
        height=height, template="none", paper_bgcolor=CARD, plot_bgcolor=CARD,
        font=dict(family=FONT, size=13, color=INK), showlegend=legend,
        title=dict(text=t, x=0, xref="container", xanchor="left", y=1, yref="container", yanchor="top",
                   pad=dict(t=16, l=20), font=dict(size=15, color=INK)) if t else None,
        margin=dict(l=20, r=22, t=top + 10, b=16),
        legend=dict(orientation="h", x=0, xanchor="left", y=1.0, yanchor="bottom", font=dict(size=12.5, color=MUTED),
                    title_text=""),
        hoverlabel=dict(bgcolor=INK, bordercolor=INK, font=dict(color="#fff", family=FONT, size=13)),
        shapedefaults=dict(line=dict(color=FAINT, width=1.5)), bargap=0.25)
    grid_x, grid_y = (True, False) if hbar else (False, True)
    fig.update_xaxes(showgrid=grid_x, gridcolor=GRID, zeroline=False, showline=not hbar, linecolor=LINE, ticks="",
                     tickfont=dict(color=MUTED), automargin=True, title=None)
    fig.update_yaxes(showgrid=grid_y, gridcolor=GRID, zeroline=False, showline=False, ticks="",
                     tickfont=dict(color=MUTED), automargin=True, title=None)
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})


def keep(key: str, fallback):
    """on_change callback: if the active option is clicked again (value None), keep the previous choice."""
    def _cb():
        if st.session_state.get(key) is None:
            st.session_state[key] = st.session_state.get(f"_{key}_last", fallback)
        st.session_state[f"_{key}_last"] = st.session_state[key]
    return _cb


def short(name: str) -> str:
    import re
    return re.sub(r"\s+(Ltd|Plc|Limited|PLC|Holdings Ltd|Group Plc)\.?$", "", str(name)).strip()


def pill(text: str, tone: str) -> str:
    return f"<span class='bd-pill {tone}'>{escape(text)}</span>"


def table(head: list[str], rows: list[list[str]]) -> None:
    th = "".join(f"<th>{h}</th>" for h in head)
    tr = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    html(f"<table class='bd-table'><thead><tr>{th}</tr></thead><tbody>{tr}</tbody></table>")


def nice_date(s: str, fmt: str = "%d %b %Y") -> str:
    return pd.Timestamp(s).strftime(fmt).lstrip("0")


QUESTIONS = {
    "Overview": "When the next sell-off comes, where does Kenya’s stock market break?",
    "Market depth": "How easy is it to sell a share on the NSE without crashing its price?",
    "Sell-off alert": "Will foreign investors sell heavily next month?",
    "Crash risk": "Which stocks are most likely to fall 15% or more next month?",
    "Speculation": "Which price jumps have no news behind them, and might be speculation?",
    "Stress test": "If foreign investors sell a large amount quickly, which stocks break?",
    "Opportunities": "Which stocks look attractive, and can you actually get out of them?",
    "Stock report": "What does every Bedrock signal say about one stock, and how sure are we?",
    "Sell-off alert (demo)": "What would the sell-off alert look like on weekly foreign flows, as Rock could provide?",
    "Opportunities (demo)": "What would the Opportunity Radar look like with company financials added?",
    "Fundamentals (demo)": "How would a value-and-quality screen work once company financials are added?",
    "Foreign flows by stock (demo)": "What would a daily, stock-by-stock foreign selling alert look like with Rock’s data?",
    "Market-ready": "What would make Bedrock better, and ready for real clients?",
    "Guide": "What does each screen do, how good is each model, and what do the words mean?",
}
USED_FOR = {
    "Overview": ("A 30-second summary for a meeting or the start of a demo.",
                 ["Each card is the headline answer of one screen.", "Click a screen name at the top to see the evidence."]),
    "Market depth": ("Fund managers check how long it would take to sell a holding before they buy it; Rock’s research "
                     "team tracks whether the market is getting deeper or thinner.",
                     ["Days to sell = how many trading days you need to sell your holding if you sell at most 20% of a "
                      "normal day’s trading, so your own selling doesn’t crash the price.",
                      "More than 20 trading days (about four weeks) counts as hard to sell.",
                      "Change the position size to see how bigger holdings get stuck."]),
    "Sell-off alert": ("An early warning, so investors can reduce risk before heavy foreign selling hits.",
                       ["HIGH RISK = heavy foreign selling next month is more likely than usual. NO CALL = no reliable "
                        "signal. It never says “safe”.",
                        "Heavy selling = a month in the worst quarter of all months for foreign outflows.",
                        "The track record shows how often its past warnings came true, on months it had never seen."]),
    "Crash risk": ("A stock-by-stock watch list: which holdings to watch or trim.",
                   ["Each month every stock is ranked from safest to riskiest. The riskiest tenth historically crashed "
                    "about twice as often as average.",
                    "Risk group 10 = the riskiest tenth of stocks; 1 = the safest tenth.",
                    "The score is a ranking, not an exact probability. GARCH is a second, newer model shown below."]),
    "Speculation": ("Leads for analysts and regulators: unusual price jumps to check against company news.",
                    ["A flag = price and trading both jumped far above the stock’s normal while the market stayed calm.",
                     "“No news found” makes it a lead worth checking. A flag is not proof of wrongdoing."]),
    "Stress test": ("A “what if” for risk managers: what happens to each stock if foreigners sell a given amount quickly.",
                    ["Absorbed = can be sold within the time window; strained = takes up to 4 times longer; trapped = "
                     "takes longer still, or has no buyers.",
                     "Bigger sales in thinner stocks move the price more (a standard rule of thumb).",
                     "Move the sliders to try other amounts and speeds."]),
    "Opportunities": ("A shortlist for investors and Rock’s research team, already filtered for whether you can get out.",
                      ["Score 0 to 1 = the average of three ranks: momentum (rose over the last year), stability (calm "
                       "price) and resilience (held up when the market fell).",
                       "Exit check = could you sell the position within 20 trading days? If not, it is not an opportunity.",
                       "The right-hand chart shows stocks that look great on paper but would be hard to sell."]),
    "Stock report": ("A one-page brief on any stock, before a decision.",
                     ["Each row is one Bedrock signal, with its evidence and how sure we are.",
                      "“What would change this view” lists what to watch. It is not investment advice."]),
    "Fundamentals (demo)": ("Shows judges and Rock what the platform will do once company financials are added.",
                            ["Everything here is made-up data for fictional companies.",
                             "Value = a cheap price relative to earnings and dividends; quality = profitable, low debt, "
                             "growing. Grey bars fail the exit check, even in the demo."]),
    "Sell-off alert (demo)": ("A copy of the real Sell-off alert screen, run on made-up weekly data, to show what "
                              "Rock’s weekly foreign flows would add. The real screen is unchanged.",
                              ["The model code is the same as the real alert; only the data is made up.",
                               "With weekly data the alert updates every week and is tested on about five times more "
                               "periods.", "Its scores here come from made-up data, so they are not evidence of real skill."]),
    "Opportunities (demo)": ("A copy of the real Opportunity Radar, run on fictional companies, showing the full score "
                             "once company financials are added. The real screen is unchanged.",
                             ["Full score = momentum, stability, resilience (as now) plus value and quality from "
                              "financial statements.", "The exit check still comes first, exactly as on the real screen."]),
    "Foreign flows by stock (demo)": ("Shows Rock the #1 upgrade: daily foreign buying and selling for each stock "
                                      "would turn the monthly, market-wide alert into a daily alert per stock.",
                                      ["Everything here is made-up data for fictional companies.",
                                       "Net foreign flow = foreign buying minus foreign selling; red bars mean "
                                       "foreigners sold more than they bought that day.",
                                       "The demo rule flags a company when foreigners were net sellers of more than "
                                       "15% of its trading over the last 10 days. It is not tested."]),
    "Market-ready": ("The plan to turn the prototype into a product clients use every week.",
                     ["Priority shows what to add first. “Most needed” is daily foreign buying and selling for each stock."]),
}
GLOSSARY = [
    ("Days to sell (days to exit)", "Trading days needed to sell a holding if you sell at most 20% of a normal day’s trading."),
    ("20% of daily trading", "The most you sell in one day, so your own selling doesn’t crash the price."),
    ("Liquidity, depth", "How easily a share can be bought or sold without moving its price."),
    ("Net foreign flow", "Foreign investors’ buying minus their selling. Negative means they sold more than they bought."),
    ("Heavy selling", "A month in the worst quarter of all months for net foreign outflows."),
    ("HIGH RISK, NO CALL", "HIGH RISK is a warning. NO CALL means no reliable signal either way."),
    ("Tested on months it never saw", "Every prediction was made using only data from before that date, then checked "
     "against what really happened, as if it had been running live."),
    ("Hit rate", "How often a warning came true."),
    ("Normal rate, average", "How often the event happens anyway, with no model at all."),
    ("Chance it’s luck (p-value)", "How likely the result is a fluke. Under 5% is usually treated as real."),
    ("Ranking score (AUC)", "How well a model puts risky stocks above safe ones. 0.5 = random, 1.0 = perfect; 0.6 = modest skill."),
    ("t (t-statistic)", "How many times bigger a result is than its normal wobble. Above 2 usually counts as proven."),
    ("Volatility", "How much a price jumps around. Higher means riskier."),
    ("GARCH", "A standard financial time-series model that forecasts volatility, knowing calm and stormy spells come in runs."),
    ("Crash", "A fall of 15% or more over the next 21 trading days (about a month)."),
    ("Risk group", "Stocks split into ten equal groups each month, from 1 (safest) to 10 (riskiest)."),
    ("Momentum", "How much the price rose over the last year."),
    ("Resilience", "How a stock did compared with the whole market in months the market fell."),
    ("Exit check", "Could you sell the position within 20 trading days? Opportunities must pass it."),
    ("XGBoost", "A machine-learning method that combines many small decision trees into one prediction."),
    ("Isolation Forest", "A machine-learning method that spots unusual days because they are easy to separate from normal ones."),
    ("Square-root price impact", "A standard rule of thumb: selling 4 times more moves the price about 2 times more."),
    ("Trapped, strained, absorbed", "Stress-test outcomes: stuck for more than 4 times the window, up to 4 times, or within it."),
    ("Block deal", "One huge pre-arranged trade, such as a takeover stake. Counted at most 10 times a normal day."),
    ("Challenger model", "A newer model run next to the live one. It replaces the live model only if it keeps winning on new data."),
    ("Synthetic, demo data", "Made-up numbers used only to show how a feature works. Never used as a finding."),
]


# ---------------------------------------------------------------- data
@st.cache_data
def load(stamp: float = 0.0):
    """Read every output once; `stamp` (newest file time) makes a rerun of the pipeline reload automatically."""
    need = OUT / "headline.json"
    if not need.exists():
        return None
    r = lambda n: pd.read_parquet(OUT / f"{n}.parquet")  # noqa: E731
    opt = lambda n: r(n) if (OUT / f"{n}.parquet").exists() else pd.DataFrame()  # noqa: E731
    return dict(
        head=json.loads(need.read_text()), live=json.loads((OUT / "selloff_live.json").read_text()),
        snap=r("depth_snapshot"), hist=r("depth_history"), flags=r("speculation_flags"),
        sb_data=r("selloff_dataset"), wf=r("selloff_walk_forward"),
        rb_depth=r("robustness_depth_sensitivity"), rb_sig=r("robustness_selloff_significance"),
        rb_cal=r("robustness_selloff_calibration"), rb_spec=r("robustness_speculation_bootstrap"),
        rb_sets=opt("robustness_selloff_feature_sets"), rb_block=opt("robustness_block_cap"),
        crash_sum=json.loads((OUT / "crash_summary.json").read_text()) if (OUT / "crash_summary.json").exists() else None,
        crash_live=opt("crash_live"), crash_dec=opt("crash_deciles"), crash_cmp=opt("crash_compare"),
        crash_year=opt("crash_by_year"), crash_rob=opt("crash_robust"), crash_imp=opt("crash_importance"),
        radar_sum=json.loads((OUT / "radar_summary.json").read_text()) if (OUT / "radar_summary.json").exists() else None,
        radar_live=opt("radar_live"), demo=opt("demo_fundamentals"), demo_ff=opt("demo_foreign_flows"),
        demo_sf=opt("demo_selloff_flows"), demo_swf=opt("demo_selloff_walk_forward"), demo_opp=opt("demo_opportunities"),
        demo_slive=json.loads((OUT / "demo_selloff_live.json").read_text()) if (OUT / "demo_selloff_live.json").exists() else None,
        garch=json.loads((OUT / "garch_eval.json").read_text()) if (OUT / "garch_eval.json").exists() else None,
    )


D = load(max((f.stat().st_mtime for f in OUT.iterdir()), default=0.0) if OUT.exists() else 0.0)
if D is None:
    st.error("No outputs yet. Run `python -m bedrock.download` then `python -m bedrock.pipeline`.")
    st.stop()
H, LIVE, SNAP = D["head"], D["live"], D["snap"]
EQ = SNAP[SNAP["instrument"] == "Equity"].copy()
ASOF = H["data_as_of"]
BEST = LIVE["model"]
SIG = D["rb_sig"].set_index("model").loc[BEST]
WF = D["wf"]
FLAGS = D["flags"][D["flags"]["watch"]].copy()
PER = pd.Timestamp(LIVE["period"])
NXT = PER + (pd.offsets.MonthEnd(1) if LIVE.get("freq", "ME") == "ME" else pd.offsets.Week(1))
FLOWS = D["sb_data"][["period", "flow", "flow_3"]].dropna(subset=["flow"])


def stress_run(amount_bn=DEFAULT_SCENARIO_KES / 1e9, days=DEFAULT_SCENARIO_DAYS, part=PARTICIPATION,
               cut=STRATEGIC_CUTOFF):
    recent = FLAGS[FLAGS["date"] >= FLAGS["date"].max() - pd.Timedelta(days=60)]
    res = stress.run_scenario(SNAP, amount_bn * 1e9, days, part, cut, set(recent["code"]))
    return res, stress.summarize(res, amount_bn * 1e9)


def depth_history_fig() -> go.Figure:
    h = D["hist"].copy()
    h["as_of"] = pd.to_datetime(h["as_of"])
    f = go.Figure(go.Scatter(x=h["as_of"], y=h["pct_over_20d"], mode="lines", line=dict(color=BLUE, width=2.5),
                             fill="tozeroy", fillcolor="rgba(42,120,214,0.07)",
                             hovertemplate="%{x|%b %Y}: %{y:.0%}<extra></extra>"))
    for i, anchor, shift in [(0, "left", -18), (h["pct_over_20d"].idxmax(), "center", 16), (len(h) - 1, "right", -18)]:
        r = h.loc[i]
        f.add_annotation(x=r["as_of"], y=r["pct_over_20d"], text=f"<b>{r['pct_over_20d']:.0%}</b> {r['as_of']:%Y}",
                         showarrow=False, yshift=shift, xanchor=anchor, xshift=6 if anchor == "left" else 0,
                         font=dict(size=13, color=INK))
    f.update_yaxes(tickformat=".0%", range=[0, 1.05])
    return f


def flows_fig(since: str = "2019-01-01") -> go.Figure:
    fl = FLOWS[FLOWS["period"] >= since]
    f = go.Figure(go.Bar(x=fl["period"], y=fl["flow"] / 1e3, marker_color=np.where(fl["flow"] < 0, RED, BLUE),
                         marker_line_width=0, hovertemplate="%{x|%b %Y}: KES %{y:,.1f}bn<extra></extra>"))
    f.add_hline(y=LIVE["threshold_kes_m"] / 1e3, line_dash="dash", line_color=INK, line_width=1)
    f.update_yaxes(ticksuffix="bn")
    return f


# ---------------------------------------------------------------- page chrome
html(CSS)
html(f"<div class='bd-top'><div class='bd-brand'><span class='bd-mark'></span>Bedrock"
     f"<span class='bd-tagline'>NSE fragility monitor</span></div>"
     f"<div class='bd-asof'>Prices to {nice_date(ASOF['stocks'])} · foreign flows to "
     f"{nice_date(ASOF['flows'], '%b %Y')}</div></div>")
SCREENS = ["Overview", "Market depth", "Sell-off alert", "Crash risk", "Speculation", "Stress test", "Opportunities",
           "Stock report", "Sell-off alert (demo)", "Opportunities (demo)", "Fundamentals (demo)",
           "Foreign flows by stock (demo)", "Market-ready", "Guide"]
for s_, need in [("Crash risk", D["crash_sum"]), ("Opportunities", D["radar_sum"]), ("Stock report", D["radar_sum"]),
                 ("Fundamentals (demo)", len(D["demo"]) or None),
                 ("Foreign flows by stock (demo)", len(D["demo_ff"]) or None),
                 ("Sell-off alert (demo)", D["demo_slive"]), ("Opportunities (demo)", len(D["demo_opp"]) or None)]:
    if need is None:
        SCREENS.remove(s_)
NAV = {"Overview": ["Overview"],
       "Market": ["Market depth", "Sell-off alert", "Stress test"],
       "Stocks": ["Crash risk", "Speculation", "Opportunities", "Stock report"],
       "Demo (made-up data)": ["Sell-off alert (demo)", "Opportunities (demo)", "Fundamentals (demo)",
                               "Foreign flows by stock (demo)"],
       "Plan & guide": ["Market-ready", "Guide"]}
NAV = {sec_: [s_ for s_ in pages_ if s_ in SCREENS] for sec_, pages_ in NAV.items()}
NAV = {sec_: pages_ for sec_, pages_ in NAV.items() if pages_}
section = st.segmented_control("Section", list(NAV), default="Overview", key="nav_sec", label_visibility="collapsed",
                               on_change=keep("nav_sec", "Overview")) or "Overview"
pages = NAV[section]
if len(pages) > 1:
    pkey = f"nav_p{list(NAV).index(section)}"
    screen = st.segmented_control(f"{section} screens", pages, default=pages[0], key=pkey,
                                  label_visibility="collapsed", on_change=keep(pkey, pages[0])) or pages[0]
else:
    screen = pages[0]
html(f"<div class='bd-question'><span>THIS SCREEN ANSWERS</span>{QUESTIONS.get(screen, '')}</div>")
if screen in USED_FOR:
    with st.expander("New here? What this screen is for, and how to read it"):
        used, how = USED_FOR[screen]
        st.markdown(f"**What it’s for:** {used}")
        st.markdown("\n".join(f"- {h}" for h in how))

# ================================================================= OVERVIEW
if screen == "Overview":
    res0, sm = stress_run()
    n90 = int((FLAGS["date"] >= FLAGS["date"].max() - pd.Timedelta(days=90)).sum())
    eq_trapped = "EQTY" in set(res0.loc[res0["status"] == "trapped", "code"])
    hero("NSE FRAGILITY MONITOR", "The NSE is near record highs. Could you actually sell?",
         "Five checks on where Kenya’s stock market would break in the next sell-off.")
    sig = LIVE["signal"]
    cards = [
        ("MARKET DEPTH", f"{H['depth']['pct_over_20d']:.0%}", False,
         f"of shares take more than four weeks to sell {kes(POSITION_KES)}"),
        ("SELL-OFF ALERT", sig, sig == "HIGH RISK",
         f"{LIVE['probability']:.0%} chance of heavy foreign selling in {NXT:%B %Y}"),
        ("STRESS TEST", f"{sm['n_trapped']} stocks", False,
         f"trapped if foreigners sell {kes(DEFAULT_SCENARIO_KES)} in a week" + (", even Equity" if eq_trapped else "")),
        ("SPECULATION", f"{n90}", False, "unusual price jumps in the last 90 days, each one a lead to check"),
    ]
    CS = D["crash_sum"]
    if CS:
        top_name = D["crash_live"].iloc[0]["name"] if len(D["crash_live"]) else ""
        cards.insert(2, ("CRASH RISK", f"{CS['top10_rate'] / CS['base_rate']:.0f}×", False,
                         f"how often our riskiest 10% of stocks crash, vs the average. Riskiest now: "
                         f"{escape(short(top_name))}"))
    html(f"<div class='bd-cards' style='grid-template-columns:repeat({len(cards)},minmax(0,1fr))'>" + "".join(
        f"<div class='bd-card'><div class='k'>{k}</div><div class='v{' risk' if r else ''}'>{v}</div>"
        f"<div class='d'>{d}</div></div>" for k, v, r, d in cards) + "</div>")
    a, b = st.columns(2, gap="medium")
    with a:
        chart(depth_history_fig(), "The rally lifted prices, not depth",
              "Share of shares needing more than 20 trading days to sell KES 10m", 340)
    with b:
        fl = FLOWS[FLOWS["period"] >= "2019-01-01"]
        chart(flows_fig(), f"Foreigners have pulled out KES {-fl['flow'].sum() / 1e3:,.0f}bn since 2019",
              "Net foreign flow into NSE shares, KES bn a month · dashed line = heavy selling", 340)

# ================================================================= MARKET DEPTH
elif screen == "Market depth":
    pos = st.session_state.get("pos") or POSITION_KES
    eq = EQ.copy()
    eq["days"] = (pos / (PARTICIPATION * eq["adv_kes"].replace(0, np.nan))).fillna(np.inf)
    pct20 = (eq["days"] > 20).mean()
    hero("MARKET DEPTH", f"{pct20:.0%} of NSE shares take more than four weeks to sell {kes(pos)}",
         f"{len(eq)} ordinary shares, selling no more than {PARTICIPATION:.0%} of a normal day’s trading.")
    st.segmented_control("Position to sell", [1e6, 10e6, 50e6, 100e6], default=POSITION_KES, format_func=kes,
                         key="pos", on_change=keep("pos", POSITION_KES))
    kpis([(f"{pct20:.0%}", "need more than 20 trading days", True),
          (f"{int((eq['days'] <= 2).sum())}", "stocks can be sold within 2 days", False),
          (f"{H['depth']['top5_share_of_value']:.0%}", "of all trading is in just 5 stocks", False),
          (f"{np.isinf(eq['days']).mean():.0%}", "of shares had no trades in 6 months", False)])
    model("Days-to-exit + K-means tiers", "120 days of trading per stock",
          "result holds at 62–72% under every assumption tested")

    a, b = st.columns([1, 1], gap="medium")
    with a:
        bands = [("≤ 2 days", 2, STATUS["good"]), ("2–5", 5, STATUS["warning"]), ("5–20", 20, STATUS["warning"]),
                 ("20–250", 250, STATUS["serious"]), ("> 250 or none", np.inf, STATUS["critical"])]
        cut = pd.cut(eq["days"], [-np.inf] + [x[1] for x in bands], labels=[x[0] for x in bands])
        n = cut.value_counts().reindex([x[0] for x in bands]).fillna(0).astype(int)
        f = go.Figure(go.Bar(x=n.index, y=n.values, marker_color=[x[2] for x in bands], marker_line_width=0,
                             text=[f"{v}" for v in n.values], textposition="outside", cliponaxis=False,
                             textfont=dict(color=INK, size=14),
                             hovertemplate="%{x} days: %{y} stocks<extra></extra>"))
        f.update_yaxes(showticklabels=False, showgrid=False, range=[0, n.max() * 1.18])
        chart(f, "Most shares take weeks or months to sell", f"Number of stocks by trading days to sell {kes(pos)}", 360)
    with b:
        chart(depth_history_fig(), "The market thinned for a decade",
              "Share needing more than 20 days to sell KES 10m, each quarter", 360)

    names = eq.sort_values("name")
    c1, c2 = st.columns([1, 2], gap="medium")
    pick = c1.selectbox("Look up a stock", names["code"], format_func=lambda c: f"{names.set_index('code').loc[c, 'name']} ({c})",
                        index=int(np.argmax(names["code"].values == "SCOM")) if "SCOM" in names["code"].values else 0)
    r = eq.set_index("code").loc[pick]
    d_txt = "no trades in 6 months" if np.isinf(r["days"]) else (
        "under a day" if r["days"] < 1 else f"{r['days']:,.0f} trading days")
    c2.markdown(f"<div class='bd-stock'><b>{escape(r['name'])}</b> · {escape(str(r['sector']))}<br>"
                f"Selling {kes(pos)} takes <b>{d_txt}</b> · trades about <b>{kes(r['adv_kes'])}</b> a day · "
                f"<b>{'n/a' if pd.isna(r['foreign_pct']) else format(r['foreign_pct'], '.0%')}</b> foreign-owned · tier <b>{r['tier'][2:]}</b></div>",
                unsafe_allow_html=True)

    with st.expander(f"All {len(eq)} stocks"):
        t = eq.sort_values("days")[["name", "sector", "tier", "days", "adv_kes", "foreign_pct"]].copy()
        t["tier"] = t["tier"].str[2:]
        st.dataframe(t, hide_index=True, width="stretch", column_config={
            "name": "Company", "sector": "Sector", "tier": "Tier",
            "days": st.column_config.NumberColumn("Days to sell", format="%.1f"),
            "adv_kes": st.column_config.NumberColumn("Trades a day (KES)", format="%,.0f"),
            "foreign_pct": st.column_config.NumberColumn("Foreign-owned", format="percent")})
    with st.expander("How we measure this, and does it hold?"):
        st.markdown("**Days to sell** = position ÷ (20% × the stock’s average daily value traded, last 120 days). "
                    "Tiers: Deep ≤ 2 days · Moderate ≤ 20 · Thin ≤ 250 · Frozen > 250 or no trades. "
                    "One-off block deals (e.g. NCBA’s KES 100bn transfer on 3 Nov 2026) count for at most 10× a "
                    "normal day.")
        rd = D["rb_depth"]
        piv = rd.pivot_table(index=["lookback_days", "participation"], columns="position_kes", values="pct_over_20d")
        piv.columns = [kes(c) for c in piv.columns]
        piv.index = [f"{lb}-day window, sell ≤ {p:.0%} a day" for lb, p in piv.index]
        st.dataframe(piv.style.format("{:.0%}"), width="stretch")
        if len(D["rb_block"]):
            bc = D["rb_block"][["block_cap", "pct_over_20d", "top5_share_of_value"]]
            st.dataframe(bc, hide_index=True, width="stretch", column_config={
                "block_cap": "Block deals counted at most",
                "pct_over_20d": st.column_config.NumberColumn("Need > 20 days", format="percent"),
                "top5_share_of_value": st.column_config.NumberColumn("Top-5 share", format="percent")})

# ================================================================= SELL-OFF ALERT
elif screen == "Sell-off alert":
    p, sig = LIVE["probability"], LIVE["signal"]
    last = FLOWS.set_index("period").loc[PER]
    title = (f"High risk of heavy foreign selling in {NXT:%B %Y}" if sig == "HIGH RISK"
             else f"No warning for {NXT:%B %Y}")
    hero("SELL-OFF ALERT", title,
         f"The model puts it at <b>{p:.0%}</b>, against {LIVE['base_rate']:.0%} in a normal month. Trigger: "
         f"{kes(-last['flow'] * 1e6)} net foreign outflow in {PER:%B} ({kes(-last['flow_3'] * 1e6)} over 3 months)."
         if last["flow"] < 0 else f"The model puts it at <b>{p:.0%}</b>, against {LIVE['base_rate']:.0%} normally.",
         badge=sig)
    hits, calls = int(SIG["hits"]), int(SIG["high_risk_calls"])
    a_ = WF["actual"].astype(bool)
    kpis([(f"{SIG['hit_rate']:.0%}", f"of its warnings were followed by heavy selling ({SIG['base_rate']:.0%} by chance)", True),
          (f"{hits} of {int(a_.sum())}", "heavy-selling months it warned about in advance", False),
          ("< 1%" if SIG["p_value_vs_base"] < 0.01 else f"{SIG['p_value_vs_base']:.0%}", "chance this record is luck", False)])
    rec = WF.tail(15)
    caught = int((rec["actual"].astype(bool) & (rec[BEST] >= HIGH_RISK_PROB)).sum())
    html(f"<div class='bd-note'><b>Weak spot:</b> it misses about half of all sell-offs, and caught {caught} of the last "
         f"{int(rec['actual'].sum())}. Weekly data from Rock is the fix.</div>")
    model("XGBoost classifier", "inputs: net foreign flow this month and over 3 months",
          f"trained on {LIVE['n_train']} months", f"tested on {len(WF)} months it had never seen")

    a, b = st.columns([1, 1], gap="medium")
    with a:
        chart(flows_fig(), "Foreign investors keep selling",
              "Net foreign flow into NSE shares, KES bn a month · dashed line = heavy selling", 380)
    with b:
        f = go.Figure()
        f.add_scatter(x=WF["period"], y=WF[BEST], mode="lines", name="predicted chance",
                      line=dict(color=BLUE, width=2), hovertemplate="%{x|%b %Y}: %{y:.0%}<extra></extra>")
        hit = WF[WF["actual"] == 1]
        f.add_scatter(x=hit["period"], y=hit[BEST], mode="markers", name="heavy selling followed",
                      marker=dict(color=RED, size=9, line=dict(color="white", width=2)),
                      hovertemplate="%{x|%b %Y}: heavy selling next month<extra></extra>")
        f.add_hline(y=HIGH_RISK_PROB, line_dash="dash", line_color=INK, line_width=1,
                    annotation_text="warning line (45%)", annotation_position="top right",
                    annotation_font=dict(size=12, color=MUTED))
        f.update_yaxes(tickformat=".0%", range=[0, 1])
        chart(f, "Its warnings against what happened", "Each month predicted using only earlier data", 380, legend=True)

    with st.expander("Full test results"):
        rows = []
        for thr in [0.35, 0.40, 0.45, 0.50]:
            m = WF[BEST] >= thr
            k, n = int(a_[m].sum()), int(m.sum())
            rows.append({"Warning line": f"{thr:.0%}", "Warnings": n, "Right": k, "Hit rate": k / n if n else np.nan,
                         "p-value": binomtest(k, n, a_.mean(), alternative="greater").pvalue if n else np.nan})
        st.markdown("**Does it depend on where the warning line is drawn?** No:")
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch", column_config={
            "Hit rate": st.column_config.NumberColumn(format="percent"),
            "p-value": st.column_config.NumberColumn(format="%.3f")})
        if len(D["rb_sets"]):
            st.markdown("**All six versions we tested** (we report every one, not just the best):")
            rs = D["rb_sets"][["inputs", "model", "high_risk_calls", "hits", "hit_rate", "p_value_vs_base",
                               "p_adjusted_bonferroni"]]
            st.dataframe(rs, hide_index=True, width="stretch", column_config={
                "inputs": "Inputs", "model": "Model", "high_risk_calls": "Warnings", "hits": "Right",
                "hit_rate": st.column_config.NumberColumn("Hit rate", format="percent"),
                "p_value_vs_base": st.column_config.NumberColumn("p-value", format="%.3f"),
                "p_adjusted_bonferroni": st.column_config.NumberColumn("p, adjusted for 6 tries", format="%.3f")})
        st.markdown("**When it says X%, how often did it happen?**")
        st.dataframe(D["rb_cal"], hide_index=True, width="stretch", column_config={
            "bin": "Predicted", "n": "Months",
            "predicted": st.column_config.NumberColumn("Avg predicted", format="percent"),
            "actual": st.column_config.NumberColumn("Happened", format="percent")})
        st.caption("Low readings were followed by heavy selling almost as often as normal, so the alert never says "
                   "“low risk”: only HIGH RISK or NO CALL. With about 140 monthly data points, adding economic inputs "
                   "made it worse, so the live model uses foreign flows only.")

# ================================================================= CRASH RISK
elif screen == "Crash risk":
    CS, CL, CD = D["crash_sum"], D["crash_live"], D["crash_dec"]
    drop = abs(CS["crash_drop"])
    hero("CRASH RISK", "The stocks Bedrock ranks riskiest crash twice as often as average",
         f"Each month every stock is ranked by its chance of falling {drop:.0%} or more over the next "
         f"{CS['horizon_days']} trading days. Tested on {CS['n_test']:,} stock-months it had never seen "
         f"({CS['first_test_year']}–{pd.Timestamp(CS['as_of']).year}).")
    kpis([(f"{CS['top10_rate']:.1%}", "of the riskiest 10% crashed the next month", True),
          (f"{CS['base_rate']:.1%}", "average crash rate across all stocks", False),
          (f"{CS['safest10_rate']:.1%}", "of the safest 10% crashed", False),
          (f"{CS['rule_top10_rate']:.1%}", "for a simple rule: the most volatile 10%", False)])
    html("<div class='bd-note'><b>Honest result:</b> crash risk is predictable, but mostly from volatility, so a "
         "simple rule does almost as well. Richer data from Rock (foreign trading per stock, order books) is "
         "where machine learning can add more.</div>")
    model("XGBoost classifier", "14 inputs: momentum, volatility, liquidity, spikes, market, foreign flows",
          f"trained year by year, tested on {CS['n_test']:,} stock-months")

    a, b = st.columns([1, 1], gap="medium")
    with a:
        top = CL.head(10).iloc[::-1].copy()
        top["label"] = top["name"].map(short)
        f = go.Figure(go.Bar(
            x=top["crash_prob"], y=top["label"], orientation="h", marker_color=RED, marker_line_width=0,
            customdata=np.c_[top["mom_3m"], top["vol_60"] * np.sqrt(250), top["group_crash_rate"]],
            hovertemplate="<b>%{y}</b><br>risk score %{x:.0%}<br>last 3 months %{customdata[0]:+.0%}"
                          "<br>volatility (yearly) %{customdata[1]:.0%}<br>its group crashed %{customdata[2]:.0%} "
                          "of the time<extra></extra>"))
        f.update_xaxes(tickformat=".0%")
        chart(f, f"Riskiest stocks on {nice_date(CS['as_of'])}", "Model risk score · hover for the evidence",
              400, hbar=True)
    with b:
        d = CD.copy()
        shades = [f"rgba(184,58,43,{0.18 + 0.82 * i / 9:.2f})" for i in range(10)]
        f = go.Figure(go.Bar(x=d["decile"].astype(str), y=d["crash_rate"], marker_color=shades, marker_line_width=0,
                             text=[f"{v:.0%}" for v in d["crash_rate"]], textposition="outside", cliponaxis=False,
                             textfont=dict(color=INK, size=12.5),
                             hovertemplate="risk group %{x}: %{y:.1%} crashed<extra></extra>"))
        f.add_hline(y=CS["base_rate"], line_dash="dash", line_color=INK, line_width=1,
                    annotation_text="average", annotation_position="top left",
                    annotation_font=dict(size=12, color=MUTED))
        f.update_yaxes(tickformat=".0%", range=[0, d["crash_rate"].max() * 1.25])
        f.update_xaxes(title=None, tickvals=list(d["decile"].astype(str)),
                       ticktext=["1<br>safest"] + [str(i) for i in range(2, 10)] + ["10<br>riskiest"])
        chart(f, "The higher the risk group, the more often stocks crashed",
              f"Share that fell {drop:.0%}+ in the next month, by monthly risk group (test years only)", 400)

    GE = D["garch"]
    if GE and "Rule: highest GARCH forecast" in set(D["crash_cmp"]["model"]):
        cm = D["crash_cmp"].set_index("model")
        g_rule, live_m = cm.loc["Rule: highest GARCH forecast"], cm.iloc[0]
        v_rule = cm.loc["Rule: most volatile stocks"]
        gap = GE["auc_gap_vs_last60_rule"]
        html("<div class='bd-eyebrow'>NEW · STOCHASTIC MODEL: GARCH VOLATILITY FORECAST</div><div class='bd-sub'>"
             "Volatility is the strongest crash signal. GARCH, a standard financial time-series model, forecasts each "
             "stock’s volatility for the next four weeks, knowing that calm and stormy spells come in runs. It was "
             "refitted every year using only earlier data, and tested the same way as everything else.</div>")
        kpis([(f"{g_rule['top10_crash_rate']:.1%}", "of the 10% GARCH expected to be most volatile crashed the next month",
               True),
              (f"{live_m['top10_crash_rate']:.1%}", "for the live model’s riskiest 10%", False),
              (f"{v_rule['top10_crash_rate']:.1%}", "for the simple “last 60 days” volatility rule", False),
              (f"{1 - GE['failed_or_explosive'] / GE['fits']:.0%}", "of stock-years where weekly GARCH fitted", False)])
        html(f"<div class='bd-note'><b>How sure:</b> GARCH ranked crash risk best of all six methods tested, but the gain "
             f"could still be chance (its ranking score is {gap['gap']:+.3f} vs the 60-day rule, likely range "
             f"{gap['ci_low']:+.3f} to {gap['ci_high']:+.3f}). So it runs as a <b>challenger</b> next to the live model "
             "and replaces it only if it keeps winning on new months. On daily data GARCH failed (NSE prices move in "
             "small steps and many days have no trades), so it uses weekly returns.</div>")
        model("GARCH(1,1) on weekly returns", "refitted each year on earlier data only", "forecasts the next 4 weeks",
              f"{GE['fits']} yearly fits, {GE['n']:,} forecasts tested")
    with st.expander(f"All {len(CL)} stocks, ranked"):
        tb = CL[["risk_rank", "name", "crash_prob", "group_crash_rate", "mom_3m", "dd_1y"]].copy()
        tb["name"] = tb["name"].map(short)
        st.dataframe(tb, hide_index=True, width="stretch", column_config={
            "risk_rank": "Rank", "name": "Company",
            "crash_prob": st.column_config.NumberColumn("Risk score", format="percent"),
            "group_crash_rate": st.column_config.NumberColumn("Its group crashed", format="percent"),
            "mom_3m": st.column_config.NumberColumn("Last 3 months", format="percent"),
            "dd_1y": st.column_config.NumberColumn("Below 1-year high", format="percent")})
    with st.expander("Full test results"):
        st.markdown("**Model against simple alternatives** (same test months):")
        st.dataframe(D["crash_cmp"][["model", "auc", "top10_crash_rate", "lift", "caught_in_top20", "p_value_top10"]],
                     hide_index=True, width="stretch", column_config={
                         "model": "Method", "auc": st.column_config.NumberColumn("AUC (ranking)", format="%.3f"),
                         "top10_crash_rate": st.column_config.NumberColumn("Riskiest 10% crashed", format="percent"),
                         "lift": st.column_config.NumberColumn("× average", format="%.1f"),
                         "caught_in_top20": st.column_config.NumberColumn("Crashes caught in riskiest 20%",
                                                                          format="percent"),
                         "p_value_top10": st.column_config.NumberColumn("p-value", format="%.4f")})
        g = CS["auc_gap_vs_rule"]
        st.caption(f"Ranking power (AUC) of the model minus the volatility rule: {g['gap']:+.3f}, 95% range "
                   f"{g['ci_low']:+.3f} to {g['ci_high']:+.3f}. That range includes zero: the model is not clearly "
                   "better than the rule at ranking, though its riskiest 10% crashed somewhat more often.")
        st.markdown("**Year by year:**")
        st.dataframe(D["crash_year"], hide_index=True, width="stretch", column_config={
            "year": st.column_config.NumberColumn("Year", format="%d"), "stock_months": "Stock-months",
            "crashes": "Crashes", "base_rate": st.column_config.NumberColumn("Average", format="percent"),
            "auc_model": st.column_config.NumberColumn("AUC model", format="%.2f"),
            "auc_volatility": st.column_config.NumberColumn("AUC rule", format="%.2f"),
            "top10_crash_rate": st.column_config.NumberColumn("Riskiest 10% crashed", format="percent")})
        st.markdown("**Other crash definitions:**")
        st.dataframe(D["crash_rob"], hide_index=True, width="stretch", column_config={
            "crash_definition": "Crash means", "base_rate": st.column_config.NumberColumn("Average", format="percent"),
            "auc_model": st.column_config.NumberColumn("AUC model", format="%.3f"),
            "auc_volatility": st.column_config.NumberColumn("AUC rule", format="%.3f")})
        st.caption("Raw model scores run higher than the crash rates that followed, so the dashboard reports each "
                   "stock’s risk group and that group’s real crash rate, not the score as a probability.")

# ================================================================= SPECULATION
elif screen == "Speculation":
    days = st.session_state.get("win") or 90
    last = FLAGS["date"].max()
    recent = FLAGS[FLAGS["date"] >= last - pd.Timedelta(days=days)].sort_values("date", ascending=False)
    news = FLAGS["news"].fillna("")
    n_yes, n_no = int(news.str.startswith("yes").sum()), int((news == "no news found").sum())
    bs = D["rb_spec"].set_index(["size", "horizon"])
    hero("SPECULATION", f"{len(recent)} unusual price jumps in the last {days} days",
         "Price and trading both broke sharply from the stock’s own normal while the market stayed calm. "
         "Each one is a lead to check, not proof.")
    st.segmented_control("Window", [30, 90, 180, 365], default=90, format_func=lambda d: f"Last {d} days", key="win",
                         on_change=keep("win", 90))
    kpis([(f"{len(recent)}", f"flags across {recent['code'].nunique()} stocks", False),
          (f"{n_no} of {n_yes + n_no}", "flags we checked had no news behind them", True),
          (f"{bs.loc[('small', 'fwd_5d'), 'gap']:+.1%}", "extra gain for small caps in the week after a flag", False),
          (f"{bs.loc[('large', 'fwd_20d'), 'gap']:+.1%}", "large caps give back over the next month", False)])
    model("Isolation Forest anomaly detector", "each stock against its own last 60 days",
          "market-wide moves removed", "flags checked by hand against news")

    a, b = st.columns([1.35, 1], gap="medium")
    with a:
        t = recent[["date", "name", "ret", "value_kes", "news"]].copy()
        t["news"] = t["news"].fillna("").replace("", "not checked yet")
        t["ret"] = t["ret"] * 100
        st.dataframe(t, hide_index=True, width="stretch", height=420, column_config={
            "date": st.column_config.DateColumn("Date", format="D MMM YYYY"), "name": "Company",
            "ret": st.column_config.NumberColumn("Day’s move", format="%+.1f%%"),
            "value_kes": st.column_config.NumberColumn("Traded (KES)", format="%,.0f"),
            "news": "News found?"})
    with b:
        g = D["rb_spec"].copy()
        g["label"] = g["size"].str.capitalize() + " caps, " + g["horizon"].str.extract(r"(\d+)")[0] + " days"
        g = g.iloc[::-1]
        col = np.where(~g["ci_excludes_zero"], FAINT, np.where(g["gap"] > 0, BLUE, RED))
        f = go.Figure(go.Scatter(
            x=g["gap"], y=g["label"], mode="markers",
            marker=dict(color=col, size=13, line=dict(color="white", width=2)),
            error_x=dict(type="data", symmetric=False, array=g["ci_high"] - g["gap"], arrayminus=g["gap"] - g["ci_low"],
                         color=FAINT, thickness=2, width=5),
            hovertemplate="%{y}: %{x:+.1%}<extra></extra>"))
        f.add_vline(x=0, line_color=INK, line_width=1)
        f.update_xaxes(tickformat="+.0%")
        chart(f, "After a flag, small caps keep running",
              "Extra return vs other big up-days · grey = could be chance", 420, hbar=True)

    with st.expander("How it works"):
        st.markdown("Every trading day since 2013, each stock’s return and value traded are compared with its own "
                    "previous 60 days, after removing the market’s move. An Isolation Forest scores how unusual each "
                    "day is; the most extreme go on the watch list. We then check the top flags against NSE "
                    "announcements and the press. Example: TransCentury rose 230% in 13 days in early 2025 with no "
                    "news; Bedrock flagged it on the second day.")

# ================================================================= STRESS TEST
elif screen == "Stress test":
    ss = st.session_state
    amount, days = ss.get("amt", DEFAULT_SCENARIO_KES / 1e9), ss.get("days", DEFAULT_SCENARIO_DAYS)
    part, cut = ss.get("part", PARTICIPATION), ss.get("cut", STRATEGIC_CUTOFF)
    res, sm = stress_run(amount, days, part, cut)
    trapped = set(res.loc[res["status"] == "trapped", "code"])
    hero("STRESS TEST", f"Selling {kes(amount * 1e9)} in {days} days would trap {sm['n_trapped']} stocks"
         + (", even Equity" if "EQTY" in trapped else ""),
         "Trapped = needs more than four times the selling window to clear, or has no buyers at all.")
    c1, c2, c3 = st.columns([1, 1, 0.8], gap="large")
    c1.slider("Foreign selling (KES bn)", 0.5, 10.0, DEFAULT_SCENARIO_KES / 1e9, 0.5, key="amt")
    c2.slider("Over how many trading days", 1, 20, DEFAULT_SCENARIO_DAYS, key="days")
    with c3.expander("Advanced assumptions"):
        st.slider("Most you can sell in a day (share of normal trading)", 0.05, 0.5, PARTICIPATION, 0.05,
                  format="%.2f", key="part")
        st.slider("Foreign stakes above this are strategic and not sold", 0.3, 1.0, STRATEGIC_CUTOFF, 0.05,
                  format="%.2f", key="cut")
    kpis([(f"{sm['n_hit']}", "stocks hit by the selling", False),
          (f"{sm['n_trapped']}", "trapped: can’t be sold in time", True),
          (kes(sm["value_trapped_kes"]), "of selling stuck in trapped stocks", False),
          (f"{sm['weighted_impact']:.1%}", "average price fall, weighted by size: the index looks calm", False)])
    model("Square-root market-impact model", "selling split by foreign ownership (CMA, Aug 2026)",
          f"stakes above {cut:.0%} treated as strategic")

    top = res[(res["sell_kes"] > 0) & res["price_impact"].notna()].nsmallest(15, "price_impact").iloc[::-1]
    f = go.Figure()
    for s_, col in STRESS_COLORS.items():
        t = top[top["status"] == s_]
        if len(t):
            f.add_bar(x=t["price_impact"], y=t["name"].str.replace(r"\s+(Ltd|Plc|Limited|PLC)\.?$", "", regex=True),
                      orientation="h", name=s_, marker_color=col, marker_line_width=0,
                      customdata=np.c_[t["sell_kes"], t["days_to_absorb"]],
                      hovertemplate="<b>%{y}</b><br>price impact %{x:.1%}<br>sold KES %{customdata[0]:,.0f}"
                                    "<br>days to clear %{customdata[1]:,.0f}<extra></extra>")
    names = top["name"].str.replace(r"\s+(Ltd|Plc|Limited|PLC)\.?$", "", regex=True)
    f.update_layout(barmode="overlay", yaxis=dict(categoryorder="array", categoryarray=list(names)))
    f.update_xaxes(tickformat=".0%")
    chart(f, "The 15 hardest-hit stocks", "Estimated price fall from the selling", 540, legend=True, hbar=True)

    with st.expander("All stocks in this scenario"):
        st.dataframe(res[["name", "status", "foreign_pct", "sell_kes", "days_to_absorb", "price_impact"]],
                     hide_index=True, width="stretch", column_config={
                         "name": "Company", "status": "Status",
                         "foreign_pct": st.column_config.NumberColumn("Foreign-owned", format="percent"),
                         "sell_kes": st.column_config.NumberColumn("Sold (KES)", format="%,.0f"),
                         "days_to_absorb": st.column_config.NumberColumn("Days to clear", format="%.1f"),
                         "price_impact": st.column_config.NumberColumn("Price impact", format="percent")})
    with st.expander("How it works"):
        st.markdown("The selling is split across stocks by how much foreigners own (CMA ownership data). Each stock "
                    "can absorb at most the chosen share of its normal daily trading. Price impact uses the standard "
                    "square-root law: volatility × √(amount sold ÷ normal daily trading). Absorbed = clears within the "
                    "window · strained = within 4× · trapped = longer, or no trades in 120 days.")

# ================================================================= OPPORTUNITY RADAR
elif screen == "Opportunities":
    RS, RL = D["radar_sum"], D["radar_live"].copy()
    pos = st.session_state.get("rpos") or 10e6
    tag = f"{int(pos / 1e6)}m"
    ok = RL[RL[f"exit_ok_{tag}"]]
    paper_top = RL[RL["paper_rank"] <= 10]
    blocked = paper_top[~paper_top[f"exit_ok_{tag}"]]
    hero("OPPORTUNITY RADAR", f"{len(ok)} of {len(RL)} stocks pass the “can you get out?” check for {kes(pos)}",
         "Each stock is scored on momentum, stability and resilience. It only counts as an opportunity if the "
         "position could be sold within 20 trading days: on the NSE, a stock can look great on paper and still be "
         "impossible to sell.")
    st.segmented_control("Position to sell", [1e6, 10e6, 50e6], default=10e6, format_func=kes, key="rpos",
                         on_change=keep("rpos", 10e6))
    kpis([(f"{RS['paper_fail_share_10m']:.0%}", "of top picks on paper could not be sold within 20 days "
           "(KES 10m, 2016–2026)", True),
          (f"{len(blocked)} of 10", f"of today’s top 10 on paper fail the exit check at {kes(pos)}", False),
          (f"{RS['spread_avg']:+.1%}", "a month: top third beat bottom third (about "
           f"{RS['spread_avg'] * 12:+.0%} a year)", False),
          (f"{RS['spread_win_share']:.0%}", "of months the top third beat the bottom third", False)])
    html("<div class='bd-note'><b>How sure:</b> the exit check is the proven part: without it, 2 in 3 “top picks” "
         "could not be sold. The score points the right way, but a gap this size could still come from chance "
         "about 1 time in 5, so treat it as a shortlist to research, not a buy signal.</div>")
    model("Transparent scoring rule", "equal weights fixed in advance: momentum, stability, resilience",
          "exit check first", f"tested on {RS['months']} months, 2016–2026")
    a, b = st.columns(2, gap="medium")
    with a:
        top = ok.head(10).iloc[::-1].copy()
        top["label"] = top["name"].map(short)
        f = go.Figure(go.Bar(x=top["score"], y=top["label"], orientation="h", marker_color=BLUE, marker_line_width=0,
                             customdata=np.c_[top["mom_12_1"], top["vol_60"] * np.sqrt(250), top[f"days_exit_{tag}"]],
                             hovertemplate="<b>%{y}</b><br>score %{x:.2f}<br>12-month return %{customdata[0]:+.0%}"
                                           "<br>volatility (yearly) %{customdata[1]:.0%}<br>days to sell "
                                           "%{customdata[2]:.1f}<extra></extra>"))
        f.update_xaxes(range=[0, 1])
        chart(f, "Top opportunities you can get out of", f"Score 0 to 1 · all can sell {kes(pos)} within 20 days",
              400, hbar=True)
    with b:
        if len(blocked):
            bl = blocked.iloc[::-1].copy()
            bl["label"] = bl["name"].map(short)
            dx = bl[f"days_exit_{tag}"].replace(np.inf, 1e4)
            f = go.Figure(go.Bar(x=dx, y=bl["label"], orientation="h", marker_color=RED,
                                 marker_line_width=0, customdata=np.c_[bl["paper_rank"], bl["score"]],
                                 text=["no trades" if np.isinf(d) else f"{d:,.0f} days" for d in bl[f"days_exit_{tag}"]],
                                 textposition="outside",
                                 cliponaxis=False,
                                 hovertemplate="<b>%{y}</b><br>rank %{customdata[0]} on paper (score "
                                               "%{customdata[1]:.2f})<br>%{x:,.0f} trading days to sell<extra></extra>"))
            f.add_scatter(x=[20] * len(bl), y=bl["label"], mode="markers", showlegend=False, hoverinfo="skip",
                          marker=dict(symbol="line-ns-open", size=28, color=INK, line=dict(width=2.5, color=INK)))
            f.update_xaxes(type="log", range=[np.log10(2), np.log10(dx.max() * 6)], tickvals=[2, 20, 200, 2000],
                           ticktext=["2", "20", "200", "2,000"])
            chart(f, "Great on paper, but you can’t get out", f"Trading days to sell {kes(pos)} · black tick = the 20-day limit", 400, hbar=True)
        else:
            html(f"<div class='bd-stock'>All of today’s top 10 on paper pass the exit check at {kes(pos)}. "
                 "Try a larger position to see which ones would be stuck.</div>")
    with st.expander("Resilience index: which stocks held up when the market fell"):
        rz = ok.sort_values("resilience", ascending=False).head(10)[["name", "resilience", "vol_60"]].copy()
        rz["name"] = rz["name"].map(short)
        rz["vol_60"] = rz["vol_60"] * np.sqrt(250)
        st.dataframe(rz, hide_index=True, width="stretch", column_config={
            "name": "Company", "resilience": st.column_config.NumberColumn(
                "Vs market in falling months (avg, last 3 years)", format="percent"),
            "vol_60": st.column_config.NumberColumn("Volatility (yearly)", format="percent")})
        st.caption(f"Honest test: in {RS['res_months']} months when the market fell, stocks that had held up before "
                   f"did only {RS['res_spread_avg']:+.1%} better than those that had not, which could be chance. "
                   "Use it as history, not as a forecast.")
    with st.expander("Full test results"):
        table(["Measure (each month, 2016–2026)", "Result", "What it means"], [
            ["Top third, next month (avg)", f"{RS['top_avg']:+.2%}", "stocks the radar liked"],
            ["Bottom third, next month (avg)", f"{RS['bottom_avg']:+.2%}", "stocks the radar disliked"],
            ["Difference", f"{RS['spread_avg']:+.2%} (t = {RS['spread_t']:.1f})",
             "points the right way; t below 2 means not yet proven"],
            ["Top third beat bottom third", f"{RS['spread_win_share']:.0%} of months", "50% would be a coin flip"],
            ["Top picks on paper that fail the exit check", f"{RS['paper_fail_share_1m']:.0%} at KES 1m · "
             f"{RS['paper_fail_share_10m']:.0%} at KES 10m", "why the exit check comes first"],
            ["Resilience: held-up stocks in the next falling month", f"{RS['res_spread_avg']:+.2%} "
             f"(t = {RS['res_spread_t']:.1f}, {RS['res_months']} months)", "no clear evidence it repeats"]])
        st.caption(f"Test position KES 1m so that about {RS['avg_ok_stocks']:.0f} stocks pass each month and can be "
                   "split into thirds. Weights were fixed before testing and never tuned.")

# ================================================================= STOCK REPORT
elif screen == "Stock report":
    RL, CL = D["radar_live"], D["crash_live"]
    names = EQ.sort_values("name")
    codes = list(names["code"])
    pick = st.selectbox("Choose a stock", codes, format_func=lambda c: f"{short(names.set_index('code').loc[c, 'name'])} ({c})",
                        index=codes.index("SCOM") if "SCOM" in codes else 0, key="rep")
    pos = st.session_state.get("reppos") or 10e6
    s = EQ.set_index("code").loc[pick]
    days = pos / (PARTICIPATION * s["adv_kes"]) if s["adv_kes"] > 0 else np.inf
    exit_ok = days <= 20
    rr = RL.set_index("code").loc[pick] if pick in set(RL["code"]) else None
    cr = CL.set_index("code").loc[pick] if pick in set(CL["code"]) else None
    fl = FLAGS[(FLAGS["code"] == pick) & (FLAGS["date"] >= FLAGS["date"].max() - pd.Timedelta(days=90))]
    res0, _ = stress_run()
    sr = res0.set_index("code").loc[pick] if pick in set(res0["code"]) else None
    third = None if rr is None else ("top" if rr["score"] >= RL["score"].quantile(2 / 3) else
                                     "bottom" if rr["score"] <= RL["score"].quantile(1 / 3) else "middle")
    if not exit_ok:
        verdict = f"Hard to get out of: selling {kes(pos)} would take {'forever (no trades)' if np.isinf(days) else f'about {days:,.0f} trading days'}"
    elif cr is not None and cr["risk_decile"] >= 9:
        verdict = "You can get out, but crash risk is high"
    elif third == "top":
        verdict = "You can get out, and it ranks in the top third of opportunities"
    else:
        verdict = "You can get out; no strong signal either way"
    hero("STOCK REPORT", f"{escape(short(s['name']))}: {verdict[0].lower() + verdict[1:]}",
         f"{escape(str(s['sector']))} · every signal Bedrock has on this stock, with the evidence and how sure we are.")
    st.segmented_control("Position to sell", [1e6, 10e6, 50e6], default=10e6, format_func=kes, key="reppos",
                         on_change=keep("reppos", 10e6))
    d_txt = "no trades" if np.isinf(days) else ("under 1 day" if days < 1 else f"{days:,.0f} days")
    rows = [[f"<b>Can you get out?</b>", pill("Yes" if exit_ok else "No", "good" if exit_ok else "bad"),
             f"Selling {kes(pos)} takes {d_txt} at 20% of normal trading (about {kes(s['adv_kes'])} a day).",
             pill("Strong", "good")]]
    if rr is not None:
        rows.append(["<b>Opportunity score</b>", pill(f"{third} third", "good" if third == "top" else "na"),
                     f"Score {rr['score']:.2f} (rank {int(rr['paper_rank'])} of {len(RL)} on paper): 12-month return "
                     f"{rr['mom_12_1']:+.0%}, volatility {rr['vol_60'] * np.sqrt(250):.0%} a year, "
                     f"{rr['resilience']:+.1%} vs market in falling months.", pill("Not yet proven", "ok")])
    if cr is not None:
        hi = cr["risk_decile"] >= 9
        rows.append(["<b>Crash risk next month</b>", pill(f"group {int(cr['risk_decile'])} of 10", "bad" if hi else "na"),
                     f"Stocks in this group fell 15%+ in the next month {cr['group_crash_rate']:.0%} of the time "
                     f"(average {D['crash_sum']['base_rate']:.1%}).", pill("Medium", "ok")])
    rows.append(["<b>Speculation flags (90 days)</b>", pill(str(len(fl)), "bad" if len(fl) else "good"),
                 ("Latest " + fl["date"].max().strftime("%d %b %Y") + ". " + (fl.sort_values("date")["news"].iloc[-1] or
                  "News not checked yet.")) if len(fl) else "No unusual price jumps.", pill("Lead to check", "na")])
    if sr is not None and sr["sell_kes"] > 0:
        rows.append(["<b>If foreigners sell KES 2bn in a week</b>", pill(str(sr["status"]),
                     "bad" if sr["status"] in ("trapped", "no market") else "ok" if sr["status"] == "strained" else "good"),
                     f"Its share: {kes(sr['sell_kes'])}, about {sr['days_to_absorb']:,.0f} days to clear"
                     + ("" if pd.isna(sr["price_impact"]) else f", price {sr['price_impact']:+.0%}") + ".",
                     pill("Scenario", "na")])
    table(["Signal", "Reading", "Evidence", "How sure"], rows)
    need = pos / (PARTICIPATION * 20)
    change = []
    if not exit_ok:
        change.append(f"Trading rising to about {kes(need)} a day would let {kes(pos)} be sold within 20 days.")
    if cr is not None and cr["risk_decile"] >= 8:
        change.append("A calmer price, or the end of a recent run-up, would move it to a lower crash-risk group.")
    if rr is not None:
        change.append("Momentum fading or volatility rising would lower its opportunity score.")
    if len(fl):
        change.append("News that explains the recent jumps would turn a speculation lead into an explained move.")
    if change:
        html("<div class='bd-stock'><b>What would change this view</b><br>" + "<br>".join(f"· {c}" for c in change)
             + "</div>")
    st.caption("Rules, not opinions: every line above is computed from the same tested models as the other screens. "
               "Not investment advice.")

# ================================================================= FUNDAMENTALS (DEMO)
elif screen == "Fundamentals (demo)":
    DM = D["demo"].copy()
    html("<div class='bd-demo'><b>DEMO · SYNTHETIC DATA.</b> Fictional companies and invented numbers, made only to "
         "show how this screen would work once real company financials are added (for example from Rock Data Plus). "
         "Nothing here is real, and no other screen uses it.</div>")
    hero("FUNDAMENTALS (DEMO)", "How a value-and-quality screen would work with real company financials",
         "Each company is scored on value (price to earnings, dividend yield) and quality (return on equity, debt, "
         "earnings growth), and must still pass the same “can you get out?” check.")
    kpis([(f"{len(DM)}", "fictional demo companies", False),
          (f"{int(DM['exit_ok'].sum())}", "pass the exit check (demo)", False),
          (escape(DM.iloc[0]["company"]), "highest demo score", False)])
    model("Value + quality score (demo)", "equal weights across five measures", "same exit check as the radar",
          "not tested: needs real data")
    a, b = st.columns([1, 1.2], gap="medium")
    with a:
        dd = DM.iloc[::-1]
        f = go.Figure(go.Bar(x=dd["score"], y=dd["company"], orientation="h", marker_line_width=0,
                             marker_color=np.where(dd["exit_ok"], BLUE, "#c9c6bd"),
                             hovertemplate="<b>%{y}</b> (demo)<br>score %{x:.2f}<extra></extra>"))
        f.update_xaxes(range=[0, 1])
        chart(f, "Demo: value + quality score", "Fictional companies · blue = passes the exit check", 440, hbar=True)
    with b:
        show = DM[["company", "pe_ratio", "dividend_yield", "return_on_equity", "debt_to_equity", "earnings_growth",
                   "days_to_exit_10m"]]
        st.dataframe(show, hide_index=True, width="stretch", height=440, column_config={
            "company": "Company (demo)", "pe_ratio": st.column_config.NumberColumn("P/E", format="%.1f"),
            "dividend_yield": st.column_config.NumberColumn("Dividend yield", format="percent"),
            "return_on_equity": st.column_config.NumberColumn("Return on equity", format="percent"),
            "debt_to_equity": st.column_config.NumberColumn("Debt / equity", format="%.2f"),
            "earnings_growth": st.column_config.NumberColumn("Earnings growth", format="percent"),
            "days_to_exit_10m": st.column_config.NumberColumn("Days to sell KES 10m", format="%.1f")})
    st.caption("With real financials this becomes the fourth part of the Opportunity Radar score, so it rates the "
               "business, not only the share price. See Market-ready for the data it needs.")

# ================================================================= SELL-OFF ALERT (DEMO)
elif screen == "Sell-off alert (demo)":
    SL, SW, SF = D["demo_slive"], D["demo_swf"].copy(), D["demo_sf"].copy()
    html("<div class='bd-demo'><b>DEMO · SYNTHETIC DATA.</b> A copy of the real Sell-off alert, run on made-up weekly "
         "foreign flows, to show what Rock’s weekly data would add. The model code is the real one; the data and "
         "therefore every number here are made up. The real Sell-off alert screen is unchanged.</div>")
    a_ = SW["actual"].astype(bool)
    calls = SW["xgboost"] >= HIGH_RISK_PROB
    k, n = int(a_[calls].sum()), int(calls.sum())
    hero("SELL-OFF ALERT (DEMO)", f"Demo: on weekly data the alert would update every week ({SL['signal']} this week)",
         f"The model read {SL['probability']:.0%} for next week, against {SL['base_rate']:.0%} normally. Tested on "
         f"{len(SW)} weeks instead of 78 months.", badge=SL["signal"])
    kpis([(f"{len(SW)}", "test periods (weeks), against 78 months on real monthly data", True),
          (f"{k} of {n}" if n else "0", "demo warnings followed by heavy selling", False),
          (f"{int(a_[calls].sum())} of {int(a_.sum())}", "demo heavy-selling weeks warned about in advance", False)])
    html("<div class='bd-note'><b>Read this right:</b> the made-up data has built-in “exit waves”, so the demo scores "
         "say nothing about real skill. What it shows is real: the same code runs on weekly data and is tested on "
         "about five times more periods.</div>")
    model("XGBoost classifier (same code as the real alert)", "inputs: net foreign flow this week and over 3 weeks",
          "tested week by week on data it had never seen", "data: synthetic")
    c1, c2 = st.columns(2, gap="medium")
    with c1:
        sf = SF[SF["period"] >= SF["period"].max() - pd.Timedelta(days=3 * 365)]
        f = go.Figure(go.Bar(x=sf["period"], y=sf["flow"] / 1e3, marker_line_width=0,
                             marker_color=np.where(sf["flow"] < 0, RED, BLUE),
                             hovertemplate="%{x|%d %b %Y}: KES %{y:,.2f}bn (demo)<extra></extra>"))
        f.update_yaxes(ticksuffix="bn")
        chart(f, "Demo: weekly net foreign flow", "Made-up data, last 3 years · red = net selling", 360)
    with c2:
        f = go.Figure()
        f.add_scatter(x=SW["period"], y=SW["xgboost"], mode="lines", name="predicted chance",
                      line=dict(color=BLUE, width=1.5), hovertemplate="%{x|%d %b %Y}: %{y:.0%}<extra></extra>")
        hit = SW[SW["actual"] == 1]
        f.add_scatter(x=hit["period"], y=hit["xgboost"], mode="markers", name="heavy selling followed",
                      marker=dict(color=RED, size=6), hovertemplate="%{x|%d %b %Y}<extra></extra>")
        f.update_yaxes(tickformat=".0%", range=[0, 1])
        chart(f, "Demo: its warnings against what happened", "Each week predicted using only earlier weeks", 360,
              legend=True)

# ================================================================= OPPORTUNITIES (DEMO)
elif screen == "Opportunities (demo)":
    OD = D["demo_opp"].copy()
    html("<div class='bd-demo'><b>DEMO · SYNTHETIC DATA.</b> A copy of the real Opportunity Radar for fictional "
         "companies, with value and quality from company financials added to the score. Nothing here is real. The real "
         "Opportunities screen is unchanged.</div>")
    ok = OD[OD["exit_ok"]]
    hero("OPPORTUNITIES (DEMO)", f"Demo: with company financials, {len(ok)} of {len(OD)} companies pass the exit check "
         "and are ranked on five ingredients", "Momentum, stability and resilience (as on the real screen) plus value "
         "and quality from financial statements. The exit check still comes first.")
    moved = int((OD["score_full"].rank(ascending=False) != OD["score_price_only"].rank(ascending=False)).sum())
    kpis([(f"{len(ok)} of {len(OD)}", "demo companies pass the exit check (KES 10m in 20 days)", False),
          (f"{moved} of {len(OD)}", "demo companies change rank once financials are added", True),
          (escape(ok.iloc[0]["company"]) if len(ok) else "-", "top demo opportunity you can get out of", False)])
    model("Opportunity score with financials (demo)", "five equal ingredients", "same exit check as the real radar",
          "not tested: needs real data")
    c1, c2 = st.columns(2, gap="medium")
    with c1:
        top = ok.head(8).iloc[::-1]
        f = go.Figure(go.Bar(x=top["score_full"], y=top["company"], orientation="h", marker_color=BLUE,
                             marker_line_width=0, hovertemplate="<b>%{y}</b> (demo)<br>score %{x:.2f}<extra></extra>"))
        f.update_xaxes(range=[0, 1])
        chart(f, "Demo: top opportunities you can get out of", "Fictional companies · full five-part score", 380,
              hbar=True)
    with c2:
        bl = OD[~OD["exit_ok"]].head(6).iloc[::-1]
        f = go.Figure(go.Bar(x=bl["days_to_exit_10m"], y=bl["company"], orientation="h", marker_color=RED,
                             marker_line_width=0, text=[f"{d:,.0f} days" for d in bl["days_to_exit_10m"]],
                             textposition="outside", cliponaxis=False,
                             hovertemplate="<b>%{y}</b> (demo)<br>%{x:,.0f} days to sell KES 10m<extra></extra>"))
        f.update_xaxes(range=[0, bl["days_to_exit_10m"].max() * 1.35])
        chart(f, "Demo: good on paper, but you can’t get out", "Fictional companies · trading days to sell KES 10m",
              380, hbar=True)

# ================================================================= FOREIGN FLOWS BY STOCK (DEMO)
elif screen == "Foreign flows by stock (demo)":
    from bedrock.demo import foreign_alert_demo
    FF = D["demo_ff"].copy()
    AL = foreign_alert_demo(FF)
    html("<div class='bd-demo'><b>DEMO · SYNTHETIC DATA.</b> Fictional companies and invented numbers, made only to "
         "show what Bedrock would do with daily foreign buying and selling for each stock (the #1 upgrade on the "
         "Market-ready screen). Nothing here is real, and no other screen uses it.</div>")
    hero("FOREIGN FLOWS BY STOCK (DEMO)", "With per-stock data, the sell-off alert would become daily and stock by stock",
         "Today Bedrock sees foreign selling only as one monthly total for the whole market. With Rock’s per-stock "
         "data it could warn about each stock, every day.")
    n_hi = int((AL["signal"] == "HIGH RISK (demo)").sum())
    kpis([(f"{FF['company'].nunique()}", "fictional demo companies, 60 trading days", False),
          (f"{n_hi}", "flagged by the demo rule (foreigners sold over 15% of trading, last 10 days)", True),
          ("Daily", "how often the real alert could update with Rock’s data, instead of monthly", False)])
    model("Per-stock foreign selling rule (demo)", "net foreign selling over the last 10 days, as a share of trading",
          "not tested: needs real data")
    a, b = st.columns([1.3, 1], gap="medium")
    with a:
        pick = st.selectbox("Demo company", sorted(FF["company"].unique()), key="ffpick")
        g = FF[FF["company"] == pick]
        f = go.Figure(go.Bar(x=g["date"], y=g["net_foreign_kes"] / 1e6, marker_line_width=0,
                             marker_color=np.where(g["net_foreign_kes"] < 0, RED, BLUE),
                             hovertemplate="%{x|%d %b}: KES %{y:,.1f}m (demo)<extra></extra>"))
        f.update_yaxes(ticksuffix="m")
        chart(f, f"Demo: daily net foreign flow, {pick}", "Fictional data · red = foreigners sold more than they bought",
              360)
    with b:
        st.dataframe(AL[["company", "net_share", "signal"]], hide_index=True, width="stretch", height=360,
                     column_config={"company": "Company (demo)",
                                    "net_share": st.column_config.NumberColumn("Net foreign flow, 10 days, share of "
                                                                               "trading", format="percent"),
                                    "signal": "Demo signal"})
    st.caption("With real per-stock data, this rule would be replaced by a model trained and tested the same way as "
               "the other screens, and joined to the exit check and stress test.")

# ================================================================= MARKET-READY
elif screen == "Market-ready":
    hero("WHAT MAKES IT MARKET-READY", "Six data upgrades would take Bedrock from prototype to a weekly tool for "
         "Rock’s clients", "Most of the gain is in data, and much of that data is what Rock Data Plus is built to "
         "provide. Compute is not the constraint: everything reruns on a laptop in a few minutes.")
    kpis([("#1 need", "daily foreign buying and selling for each stock: it improves the most models at once", True),
          ("About 20×", "more data points for the sell-off alert with daily instead of monthly flows", False),
          ("7", "analysis screens already working on public data, ready to rerun on Rock’s", False)])
    table(["Upgrade", "Makes better", "Why the models get better", "Priority"], [
        ["<b>Daily foreign buying and selling for each stock</b>", "Sell-off alert, crash risk, stress test",
         "Shows who is selling which stock, every day. The alert becomes per-stock and daily, with about 20 times "
         "more data points, and the stress test can use real foreign positions.", pill("Most needed", "bad")],
        ["<b>Weekly market-wide foreign flows</b>", "Sell-off alert",
         "About 600 data points instead of 140, so earlier warnings, and the economic inputs (exchange rate, "
         "interest rates) get enough data to start helping.", pill("High", "ok")],
        ["<b>Company financials</b> (earnings, dividends, balance sheets)", "Opportunity radar, Fundamentals",
         "Adds value and quality to the score, turning today’s demo page into a tested screen of real businesses.",
         pill("High", "ok")],
        ["<b>Bid-ask spreads, order book, block-trade flags</b>", "Market depth, stress test",
         "Measures the true cost of selling and separates one-off negotiated deals from everyday trading.",
         pill("Medium", "na")],
        ["<b>Dividends and corporate actions</b> (adjusted prices)", "Crash risk, speculation watch",
         "Removes false “crashes” on dividend days and false “jumps” on share splits.", pill("Medium", "na")],
        ["<b>Verified daily prices from Rock</b>", "Every screen",
         "Replaces our reading of scanned NSE price lists (very close, but not perfect) with the source data.",
         pill("Medium", "na")]])
    table(["To be user-ready", "What it means"], [
        ["Daily automatic refresh", "New data in every morning, no manual run"],
        ["Alerts", "Email or SMS when the sell-off alert turns HIGH RISK or a holding fails the exit check"],
        ["Watch-lists and stock reports", "Each client follows their own stocks"],
        ["An API for Rock’s research team", "Pull Bedrock’s numbers straight into weekly research notes"]])
    html("<div class='bd-eyebrow'>WHAT MAKES THE MODELS PRODUCTION-GRADE</div>"
         "<div class='bd-sub'>Financial data moves through time and has fat tails, so the next generation of Bedrock’s "
         "models adds dedicated time-series and stochastic methods on top of today’s tested machine learning. Each one "
         "will be tested the same honest way: trained only on the past, compared with a simple rule, reported in "
         "full.</div>")
    table(["Upgrade", "What it adds", "Improves"], [
        ["<b>Volatility forecasting</b> (GARCH family)", "First version built and running as a challenger (weekly "
         "GARCH): the best crash ranking in testing, not yet proven. Next: versions designed for thin trading, and "
         "daily data from Rock.", "Crash risk, stress test"],
        ["<b>Regime-switching models</b> (Markov)", "Detects when the market has moved into an “exit wave”, the "
         "periods where most past sell-offs clustered (2020, 2022).", "Sell-off alert"],
        ["<b>Self-exciting selling models</b> (Hawkes)", "Captures how one heavy selling day raises the chance of the "
         "next, using daily foreign flows.", "Sell-off alert"],
        ["<b>Tail-risk models</b> (extreme value theory)", "Estimates how big a rare crash could be, not only how "
         "likely it is.", "Crash risk, stress test"],
        ["<b>Probability calibration</b>", "Makes a reading of 53% mean a 53% chance, so scores can be used as "
         "probabilities in client reports.", "Crash risk, sell-off alert"],
        ["<b>Model monitoring and governance</b>", "Live tracking of hit rates, alerts when data or accuracy drifts, "
         "versioned models, documented validation, and new models tested against the current one before they "
         "replace it.", "Every model"]])

# ================================================================= GUIDE
elif screen == "Guide":
    hero("GUIDE", "What each screen answers, how good each model is, and what the words mean",
         "Plain English, for anyone seeing Bedrock for the first time.")
    table(["Screen", "The question it answers", "What it’s for"],
          [[f"<b>{escape(s_)}</b>", escape(QUESTIONS[s_]), escape(USED_FOR[s_][0])] for s_ in SCREENS if s_ in USED_FOR])
    html("<div class='bd-eyebrow'>EVERY MODEL, HOW WELL IT DID, AND WHAT THAT MEANS</div>")
    table(["Model", "How well it did (tested on data it never saw)", "What that means", "Grade"], [
        ["<b>Market depth</b><br>days to sell + K-means groups", "67% of shares need more than 20 days to sell KES 10m; "
         "62–72% under every assumption", "A solid measurement: most of the market is hard to sell", pill("Strong", "good")],
        ["<b>Sell-off alert</b><br>XGBoost on foreign flows", "Warnings came true 10 of 17 times (59%) vs 26% by chance; "
         "under 1% chance of luck. Caught 10 of 20 sell-offs; 1 of the last 6", "A useful warning that misses about "
         "half of sell-offs. Weekly data would sharpen it", pill("Medium", "ok")],
        ["<b>Crash risk</b><br>XGBoost, 14 inputs", "Riskiest 10% crashed 10.9% of the time vs 5.5% average (2x); "
         "safest 10%: 2.7%", "Real, but mostly driven by volatility: a simple rule gets 9.2%", pill("Medium", "ok")],
        ["<b>GARCH volatility forecast</b><br>stochastic time-series (new)", "As a crash ranking: riskiest 10% crashed "
         "11.8% of the time, best of six methods, but the gain could be chance. Volatility forecasts as accurate as "
         "the 60-day rule", "Promising; runs as a challenger until it keeps winning on new months", pill("Promising", "ok")],
        ["<b>Speculation watch</b><br>Isolation Forest", "12 of 21 checked flags had real news; after a flag small stocks "
         "rose 4.4% more the next week", "Finds real events; the no-news flags are leads, not proof", pill("Good", "good")],
        ["<b>Stress test</b><br>square-root price impact", "KES 2bn of foreign selling in a week traps 16 stocks, even "
         "Equity", "A scenario, not a forecast, so it has no accuracy score", pill("Scenario", "na")],
        ["<b>Exit check</b> (new)", "Without it, 42% (KES 1m) to 67% (KES 10m) of top picks could not be sold within "
         "20 days", "Proven, and the most useful new idea: always ask “can you get out?”", pill("Strong", "good")],
        ["<b>Opportunity radar</b><br>scoring rule (new)", "Top third beat bottom third by +0.7% a month (about +8% a "
         "year) in 56% of months; could be chance about 1 time in 5", "Points the right way, not yet proven: a "
         "shortlist, not a buy signal", pill("Not yet proven", "ok")],
        ["<b>Resilience index</b> (new)", "Stocks that held up before did only 0.2% better in the next fall, which could "
         "be chance", "Describes the past; it does not reliably repeat", pill("History only", "na")],
        ["<b>Fundamentals</b> (demo)", "Not tested: synthetic data", "Shows what real company financials would add",
         pill("Demo", "na")]])
    html("<div class='bd-eyebrow'>GLOSSARY</div>")
    table(["Word", "What it means"], [[f"<b>{escape(w)}</b>", escape(m)] for w, m in GLOSSARY])

html("<div class='bd-foot'>Sources: NSE daily prices (Mendeley Data, Wanjawa, CC BY 4.0; extended to "
     f"{nice_date(ASOF['stocks'])} from NSE daily price lists) · CMA Quarterly Statistical Bulletins · Central Bank of "
     "Kenya · FRED. Built to run on Rock Data Plus.</div>")
