# Bedrock: plan, layout and steps

## 1. What we are building

**Bedrock** answers one question: *when the next sell-off comes, where does Kenya's market break?*

| Deliverable | What it is | Status |
|---|---|---|
| **Dashboard** (Streamlit, 4 screens) | Market Depth · Sell-off Alert · Speculation Watch · Stress Test | ✅ working on public data |
| **Research note** (2–4 pages) | Headline first, key charts, method in plain language, limits | ⬜ write after the brief |
| **GitHub repo** | Clean code and a notebook anyone can rerun | ✅ structure ready |
| **Slides** (~8) | Only if there is a presentation round | ⬜ |
| Bonds screen (optional 5th) | Yield curve and corporate spreads | ⬜ method stub only |

Who it is for: Rock's research team (a weekly "market fragility" section), fund managers (can I exit before I buy?) and retail investors (warning before buying a stock that is hard to sell or looks pumped).

## 2. Repo layout

```
BEDROCK/
├── README.md                  public overview + quick start
├── PLAN.md                    this file          BUILD_LOG.md   what was built, step by step
├── requirements.txt, requirements-ocr.txt, pyproject.toml, .gitignore
├── .github/workflows/ci.yml   GitHub Actions: tests + dashboard smoke test on every push
├── src/bedrock/
│   ├── config.py              every tunable number (position size, 20% participation, thresholds ...)
│   ├── download.py            fetches all public data          → python -m bedrock.download
│   ├── nse_ocr.py             NSE daily price lists (scanned) → prices Jul–Nov 2026   → python -m bedrock.nse_ocr
│   ├── clean.py               raw files → tidy tables; Rock override hooks; NASI rebuild for OCR days
│   ├── depth.py               Module A  Market Depth
│   ├── selloff.py             Module B  Sell-off Alert (walk-forward tested)
│   ├── speculation.py         Module C  Speculation Watch (+ hand-checked news)
│   ├── stress.py              Screen 4  Stress Test
│   ├── robustness.py          sensitivity, binomial test, calibration, bootstrap
│   ├── bonds.py               Module D  (optional, method only)
│   ├── pipeline.py            runs everything, saves outputs   → python -m bedrock.pipeline
│   ├── figures.py             charts for the note / slides     → python -m bedrock.figures
│   └── publish.py             outputs → app/snapshot/ for Streamlit Cloud (blocks Rock data) → python -m bedrock.publish
├── app/streamlit_app.py       the dashboard                    → streamlit run app/streamlit_app.py
├── app/snapshot/              committed public-data outputs the deployed app reads
├── notebooks/bedrock_walkthrough.ipynb   reruns every number in the note
├── reports/bedrock_note.md    research note draft;  reports/figures/  its charts
├── tests/test_core.py         unit tests                       → pytest -q
└── data/                      (git-ignored except data/rock/README.md and data/manual/)
    ├── raw/        mendeley/ (NSE prices) · nse/ (daily price-list PDFs + OCR) · cma/ · cbk/ · fred/
    ├── processed/  tidy parquet tables + outputs/ for the dashboard
    ├── manual/     news_checks.csv: hand-checked news for speculation flags (committed)
    └── rock/       drop Rock Data Plus CSVs here → they replace the public data
```

## 3. Data: what we have and what Rock should fill

| Need | Have now (public) | Gap Rock should fill |
|---|---|---|
| Daily prices and volumes | ✅ 2013 – Jun 2026 (Mendeley) + **Jul – Nov 2026 (NSE price lists, OCR)** | official VWAP / value traded; a clean feed |
| Foreign flows | ✅ **monthly** net flows 2015 – Sep 2026 (CMA) | **weekly or daily** buys/sells: the biggest upgrade for Module B |
| Ownership / shares in issue | ✅ per company, Aug 2026 (CMA) | history of foreign ownership |
| Macro (FX, CBR, T-bills, inflation) | ✅ monthly, to Nov 2026 | daily FX and T-bill yields (nice to have) |
| Global (oil, US yields, USD, VIX) | ✅ FRED daily | – |
| Company announcements | ❌ | needed to confirm "no news" on speculation flags |
| Government and corporate bond yields | ❌ (NSE bond lists are scanned PDFs) | needed only for the optional Bonds screen |

## 4. Results (data to 16 Nov 2026)

- **Depth:** 67% of 64 ordinary shares need more than 20 days to exit KES 10m (80% need more than 5). Only 5 clear in 2 days; 34% need more than a year or never trade. The top 5 stocks are 74% of value traded. The thin share rose from 54% (2013) to 92% (Mar 2024) and the rally brought it to 67%. Robust: 62–72% under every assumption. Block deals (NCBA KES 100bn, KPC KES 41bn) are capped.
- **Foreign flows:** net sellers in 73% of months since 2019, KES 127bn out, through the rally.
- **Sell-off Alert:** 6 versions tested walk-forward (3 input sets × 2 models). The winner is XGBoost on flows only: HIGH RISK 10/17 = 59% vs 26% (p = 0.004; 0.023 adjusted), well calibrated, beats the base rate on Brier (+9%), AUC 0.64. Adding macro made it worse. Live reading for **October 2026: 53%, HIGH RISK**.
- **Stress:** KES 2bn in 5 days traps 16 stocks, including **Equity (22 days)**. Portland −25%, Crown −21%, NBV −18%, Kakuzi −17%, Britam −16%. Value-weighted impact −4.0%.
- **Speculation:** small caps +4.4% over 5 days after a spike (CI +1.4% to +7.8%), +10.7% over 20 days (CI only just excludes zero); large caps −3.3% over 20 days. Of 21 flags hand-checked, 12 had news and 9 had none. Examples: TCL (+230% in 13 days, no news); C&G (Business Daily: "speculator-driven" tenfold run, flagged twice).

## 5. Steps

### Done (16 Nov)
1. Found and downloaded every public source; built cleaning with Rock override hooks.
2. Built modules A, B and C, the stress test, the pipeline, the 4-screen dashboard and the notebook.

### At the event: questions for Rock
1. What is the brief or question, the format (note, dashboard, slides?) and the **deadline**?
2. Can MSc / postgraduate students win prizes?
3. Rock Data Plus: daily **volumes** for all stocks, and how many years back?
4. **Foreign buy/sell** figures: daily, weekly or monthly? Per stock or market-wide?
5. Bonds (government and corporate)? Company announcements?
6. Export as CSV or API? May we combine Rock data with public data, and publish code on GitHub?

### Event-day playbook: match the brief, don't force all four screens

| If Rock's brief is about… | Lead with | Supporting |
|---|---|---|
| Market fragility / risk monitor | All 4 screens | – |
| Liquidity, fund managers, "can I exit?" | 1 Market Depth + 4 Stress Test | 2 (why foreign selling matters) |
| Foreign investors / flows / prediction | 2 Sell-off Alert | 1 (why it hurts), 4 (where it breaks) |
| Retail investors / manipulation / protection | 3 Speculation Watch (TCL example) | 1 ("can I sell it later?") |
| Something we have not touched (bonds, a sector, an event) | Answer their question first | Reuse the pipeline, dashboard style and testing approach |

**How to present the sell-off model's weakness:** "With monthly public data, our HIGH RISK calls were followed by heavy selling
twice as often as normal (p = 0.03), but 140 monthly points is thin. Rock Data Plus has weekly foreign buy/sell data: 4×
more points and earlier warnings. Our code detects the frequency automatically, so it is one file drop away."

### After the brief
| Step | Work | Notes |
|---|---|---|
| 1 | Map the brief to the screens; drop what does not answer it | If a topic is assigned, the modules become tools for it |
| 2 | Load Rock data into `data/rock/`, rerun the pipeline | Check that numbers still make sense; compare with public data |
| 3 | Re-test Module B on weekly flows if Rock has them | Same code; frequency is detected automatically |
| 4 | Check the top speculation flags by hand against news | Fill the "News found?" column for the note's examples |
| 5 | Write the note: headline, 3–4 charts, method, limits | Leave ≥ 25% of the time for writing and polish |
| 6 | Deploy the dashboard (Streamlit Community Cloud from GitHub) | Public data only; never push Rock files |
| 7 | Slides if there is a presentation | Built from the note's charts |
| 8 | Bonds screen only if time allows **and** data exists | |

## 6. Research note outline (2–4 pages)

1. **Headline:** "The NSE is at record highs, but 65% of listed shares would take more than 20 days to exit a KES 10m position, and foreign selling is what exposes them."
2. **How shallow is the market?** Days-to-exit chart and concentration over time.
3. **When will foreigners sell?** Flow history, the current reading and the honest test result.
4. **Where does it break?** Stress test results and the hardest-hit stocks.
5. **Speculation in thin stocks:** small caps run for a week after a spike; large caps reverse. Two worked examples.
6. **Method and limits:** half a page, plain language.

## 7. Risks

- **Scope:** four thin modules lose to one strong one. If the deadline is under a week, ship A, the stress test and B, and present C as a supporting finding.
- **Module B is weak on monthly data.** Show the test, don't hide it; the NO CALL zone exists for this.
- **Data lag:** public prices end in June 2026. Rock data or NSE daily lists are needed for a live "this week" view.
- **Licensing:** Rock data stays out of GitHub (`data/rock/` is git-ignored). Cite Mendeley (CC BY 4.0), CMA, CBK and FRED.
