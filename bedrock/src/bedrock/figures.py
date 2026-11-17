"""Static figures for the research note and slides, built from the pipeline outputs.

    python -m bedrock.figures            # -> reports/figures/fig*.png  (+ .svg)
                                         #    and reports/figures/slides/*.png (no title, larger text)

Same colours as the dashboard; white background and larger text so they print well.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from . import stress
from .config import HIGH_RISK_PROB, POSITION_KES, PROCESSED, ROOT

OUT = PROCESSED / "outputs"
FIG = ROOT / "reports" / "figures"

BLUE, RED = "#2a78d6", "#e34948"
STATUS = {"good": "#0ca30c", "warning": "#fab219", "serious": "#ec835a", "critical": "#d03b3b"}
STRESS_COLORS = {"absorbed": STATUS["good"], "strained": STATUS["warning"], "trapped": STATUS["critical"]}
INK, MUTED, GRID = "#1f1f1f", "#6b6b66", "#e6e6e3"
W = 900                                     # px at scale 1; exported at scale 2


def _style(fig: go.Figure, title: str, subtitle: str = "", height: int = 420) -> go.Figure:
    t = f"<b>{title}</b>" + (f"<br><span style='font-size:13px;color:{MUTED}'>{subtitle}</span>" if subtitle else "")
    legend = len(fig.data) > 1 and any(getattr(d, "showlegend", True) is not False for d in fig.data)
    fig.update_layout(width=W, height=height, template="simple_white", font=dict(size=14, color=INK, family="Arial"),
                      title=dict(text=t, x=0, xanchor="left", xref="paper", y=1, yref="container", yanchor="top",
                                 pad=dict(t=14), font=dict(size=18)),
                      margin=dict(l=10, r=30, t=118 if legend else 82, b=10), showlegend=legend,
                      legend=dict(orientation="h", x=0, y=1.0, yanchor="bottom", title_text=""),
                      # simple_white gives shapes a 0-width line: make reference lines visible
                      shapedefaults=dict(line=dict(width=1.5, color=MUTED), opacity=1))
    fig.update_xaxes(gridcolor=GRID, linecolor=MUTED, automargin=True, ticks="")
    fig.update_yaxes(gridcolor=GRID, linecolor=MUTED, automargin=True, ticks="")
    return fig


def _r(name: str) -> pd.DataFrame:
    return pd.read_parquet(OUT / f"{name}.parquet")


# ------------------------------------------------------------------ figures
def fig_exit_bands(snap: pd.DataFrame, head: dict) -> go.Figure:
    """How many ordinary shares fall in each days-to-exit band."""
    eq = snap[snap["instrument"] == "Equity"]
    bands = [("≤ 2 days", 0, 2, STATUS["good"]), ("2–5 days", 2, 5, STATUS["warning"]),
             ("5–20 days", 5, 20, STATUS["warning"]), ("20–250 days", 20, 250, STATUS["serious"]),
             ("> 250 days or no trades", 250, np.inf, STATUS["critical"])]
    cut = pd.cut(eq["days_to_exit"], [-np.inf] + [b[2] for b in bands], labels=[b[0] for b in bands])
    n = cut.value_counts().reindex([b[0] for b in bands]).fillna(0).astype(int)
    d = pd.DataFrame({"band": n.index, "n": n.values, "share": n.values / len(eq), "color": [b[3] for b in bands]})
    fig = go.Figure(go.Bar(x=d["band"], y=d["n"], marker_color=d["color"], marker_line_width=0,
                           text=[f"{n} ({s:.0%})" for n, s in zip(d["n"], d["share"])], textposition="outside",
                           textfont_color=INK, cliponaxis=False))
    fig.update_yaxes(title=None, showgrid=True, range=[0, d["n"].max() * 1.2])
    fig.update_xaxes(title=None)
    return _style(fig, f"{head['pct_over_20d']:.0%} of NSE shares need more than 20 trading days to exit KES 10m",
                  f"{len(eq)} ordinary shares, number of stocks by days to exit, selling ≤ 20% of average daily value "
                  f"(120 days to {head['as_of']})", 400)


def fig_depth_history(hist: pd.DataFrame) -> go.Figure:
    h = hist.copy()
    h["as_of"] = pd.to_datetime(h["as_of"])
    fig = go.Figure(go.Scatter(x=h["as_of"], y=h["pct_over_20d"], mode="lines", line=dict(color=BLUE, width=2.5)))
    for i, (shift, anchor) in zip([0, h["pct_over_20d"].idxmax(), len(h) - 1],
                                  [(16, "left"), (16, "center"), (-20, "right")]):
        r = h.loc[i]
        fig.add_annotation(x=r["as_of"], y=r["pct_over_20d"], text=f"<b>{r['pct_over_20d']:.0%}</b> ({r['as_of']:%b %Y})",
                           showarrow=False, yshift=shift, xanchor=anchor, font=dict(size=13, color=INK))
    fig.update_yaxes(tickformat=".0%", range=[0, 1], title=None)
    fig.update_xaxes(title=None)
    return _style(fig, "The market has thinned over a decade; the 2025–26 rally only partly reversed it",
                  "Share of ordinary shares needing more than 20 trading days to exit KES 10m, each quarter", 380)


def fig_flows(sb: pd.DataFrame, live: dict) -> go.Figure:
    fl = sb[["period", "flow"]].dropna()
    fl = fl[fl["period"] >= "2019-01-01"]
    fig = go.Figure(go.Bar(x=fl["period"], y=fl["flow"] / 1e3, marker_color=np.where(fl["flow"] < 0, RED, BLUE),
                           marker_line_width=0))
    thr = live["threshold_kes_m"] / 1e3
    fig.add_hline(y=thr, line_dash="dash", line_color=INK, line_width=1, layer="above")
    fig.update_yaxes(title=None, ticksuffix="bn", zeroline=True, zerolinecolor=MUTED)
    fig.update_xaxes(title=None)
    share, total = (fl["flow"] < 0).mean(), fl["flow"].sum() / 1e3
    return _style(fig, f"Foreigners were net sellers in {share:.0%} of months since 2019: KES {-total:,.0f}bn out",
                  f"Net foreign flow into NSE equities, KES bn per month (CMA). Dashed line: heavy selling "
                  f"(worse than KES {thr:,.1f}bn, the worst 25% of months)", 380)


def fig_walk_forward(wf: pd.DataFrame, sig: pd.Series, model: str) -> go.Figure:
    fig = go.Figure()
    fig.add_scatter(x=wf["period"], y=wf[model], mode="lines", name="predicted chance of heavy selling",
                    line=dict(color=BLUE, width=2))
    hit = wf[wf["actual"] == 1]
    fig.add_scatter(x=hit["period"], y=hit[model], mode="markers", name="heavy selling did follow",
                    marker=dict(color=RED, size=9, line=dict(color="white", width=2)))
    fig.add_hline(y=HIGH_RISK_PROB, line_dash="dash", line_color=INK, line_width=1, layer="below",
                  annotation_text="HIGH RISK line (45%)", annotation_position="top right",
                  annotation_font=dict(size=12, color=INK))
    fig.update_yaxes(tickformat=".0%", title=None, range=[0, 1])
    fig.update_xaxes(title=None)
    p = sig["p_value_vs_base"]
    return _style(fig, f"HIGH RISK calls were followed by heavy selling {int(sig['hits'])} of "
                       f"{int(sig['high_risk_calls'])} times ({sig['hit_rate']:.0%}) vs {sig['base_rate']:.0%} normally",
                  "Out-of-sample: each month predicted using only earlier data. Binomial p = "
                  + (f"{p:.3f}" if p < 0.01 else f"{p:.2f}"), 400)


def fig_stress(snap: pd.DataFrame, flags: pd.DataFrame) -> tuple[go.Figure, dict]:
    recent = flags[flags["watch"] & (flags["date"] >= flags["date"].max() - pd.Timedelta(days=60))]
    res = stress.run_scenario(snap, speculative_codes=set(recent["code"]))
    sm = stress.summarize(res, res["sell_kes"].sum())
    top = res[(res["sell_kes"] > 0) & res["price_impact"].notna()].nsmallest(15, "price_impact").iloc[::-1]
    fig = go.Figure()
    for status, col in STRESS_COLORS.items():
        t = top[top["status"] == status]
        if len(t):
            fig.add_bar(x=t["price_impact"], y=t["code"], orientation="h", name=status, marker_color=col,
                        marker_line_width=0)
    fig.update_layout(barmode="overlay", yaxis=dict(categoryorder="array", categoryarray=list(top["code"])))
    fig.update_xaxes(tickformat=".0%", title=None)
    fig.update_yaxes(title=None)
    return _style(fig, f"KES 2bn of foreign selling in a week would trap {sm['n_trapped']} stocks",
                  f"Estimated price impact, 15 hardest-hit stocks (selling split by foreign holdings; stakes > 50% "
                  f"treated as strategic).<br>Value-weighted impact across all {sm['n_hit']} stocks hit: "
                  f"{sm['weighted_impact']:.1%}", 540), sm


def fig_speculation(bs: pd.DataFrame) -> go.Figure:
    b = bs.copy()
    b["label"] = b["size"].str.capitalize() + " caps, next " + b["horizon"].str.extract(r"(\d+)")[0] + " days"
    b = b.iloc[::-1]
    col = np.where(~b["ci_excludes_zero"], MUTED, np.where(b["gap"] > 0, BLUE, RED))
    fig = go.Figure(go.Scatter(
        x=b["gap"], y=b["label"], mode="markers", marker=dict(color=col, size=12, line=dict(color="white", width=2)),
        error_x=dict(type="data", symmetric=False, array=b["ci_high"] - b["gap"], arrayminus=b["gap"] - b["ci_low"],
                     color=MUTED, thickness=2, width=6)))
    fig.add_vline(x=0, line_color=INK, line_width=1)
    for _, r in b.iterrows():
        fig.add_annotation(x=r["ci_high"], y=r["label"], text=f"{r['gap']:+.1%}" + ("" if r["ci_excludes_zero"] else " (could be chance)"),
                           showarrow=False, xanchor="left", xshift=8, font=dict(size=13, color=INK))
    fig.update_xaxes(tickformat="+.0%", title=None, range=[b["ci_low"].min() - 0.03, b["ci_high"].max() + 0.12])
    fig.update_yaxes(title=None)
    return _style(fig, "After an unexplained spike, small caps keep rising for a week; large caps fall back",
                  "Return after a watch-listed up-spike minus other >5% up-days, with 95% interval (2013–2026)", 360)


def fig_crash_deciles(dec: pd.DataFrame, cs: dict) -> go.Figure:
    """Crash rate by monthly risk group, out-of-sample."""
    shades = [f"rgba(184,58,43,{0.18 + 0.82 * i / 9:.2f})" for i in range(10)]
    fig = go.Figure(go.Bar(x=dec["decile"].astype(str), y=dec["crash_rate"], marker_color=shades, marker_line_width=0,
                           text=[f"{v:.0%}" for v in dec["crash_rate"]], textposition="outside", cliponaxis=False,
                           textfont_color=INK))
    fig.add_hline(y=cs["base_rate"], line_dash="dash", line_color=INK, line_width=1,
                  annotation_text=f"average {cs['base_rate']:.1%}", annotation_position="top left",
                  annotation_font=dict(size=12, color=INK))
    fig.update_yaxes(tickformat=".0%", range=[0, dec["crash_rate"].max() * 1.25], title=None)
    fig.update_xaxes(title=None, tickvals=list(dec["decile"].astype(str)),
                     ticktext=["1 safest"] + [str(i) for i in range(2, 10)] + ["10 riskiest"])
    return _style(fig, f"Stocks ranked riskiest crashed {cs['top10_rate']:.0%} of the time, twice the average",
                  f"Share falling {abs(cs['crash_drop']):.0%}+ over the next {cs['horizon_days']} trading days, by monthly "
                  f"risk group. Out-of-sample, {cs['first_test_year']}–2026 ({cs['n_test']:,} stock-months)", 380)


def export(formats=("png", "svg")) -> dict:
    FIG.mkdir(parents=True, exist_ok=True)
    head = json.loads((OUT / "headline.json").read_text())
    live = json.loads((OUT / "selloff_live.json").read_text())
    snap, flags = _r("depth_snapshot"), _r("speculation_flags")
    sig = _r("robustness_selloff_significance").set_index("model").loc[live["model"]]
    stress_fig, sm = fig_stress(snap, flags)
    figs = {
        "fig1_exit_bands": fig_exit_bands(snap, head["depth"]),
        "fig2_depth_history": fig_depth_history(_r("depth_history")),
        "fig3_foreign_flows": fig_flows(_r("selloff_dataset"), live),
        "fig4_selloff_test": fig_walk_forward(_r("selloff_walk_forward"), sig, live["model"]),
        "fig5_stress_test": stress_fig,
        "fig6_speculation": fig_speculation(_r("robustness_speculation_bootstrap")),
    }
    if (OUT / "crash_summary.json").exists():
        figs["fig7_crash_risk"] = fig_crash_deciles(_r("crash_deciles"), json.loads((OUT / "crash_summary.json").read_text()))
    for name, f in figs.items():
        for fmt in formats:
            f.write_image(FIG / f"{name}.{fmt}", scale=2 if fmt == "png" else 1)
        print(f"  {name}")
    print(f"Saved {len(figs)} figures to {FIG}")
    export_slides(figs)
    return figs


def for_slide(fig: go.Figure, width: int = 1000, height: int = 560) -> go.Figure:
    """Copy of a note figure for a 16:9 slide: the slide carries the title, so drop it and enlarge all text."""
    f = go.Figure(fig)
    legend = f.layout.showlegend
    f.update_layout(title_text="", width=width, height=height, font=dict(size=21),
                    margin=dict(l=10, r=30, t=56 if legend else 16, b=10))
    for a in f.layout.annotations:
        a.font.size = round((a.font.size or 14) * 1.5)
    return f


def export_slides(figs: dict) -> None:
    out = FIG / "slides"
    out.mkdir(parents=True, exist_ok=True)
    for name, f in figs.items():
        for_slide(f).write_image(out / f"{name}.png", scale=2)
    print(f"Saved {len(figs)} slide versions to {out}")


if __name__ == "__main__":
    export()
