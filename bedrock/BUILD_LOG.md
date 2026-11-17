# Bedrock build log

What was built, in order, with the result of each step. Newest steps at the bottom.

| # | Step | Status |
|---|---|---|
| 0 | Base build: data download, cleaning, modules A/B/C, stress test, dashboard, notebook | ✅ 16 Nov 2026 |
| 1 | Prices to November 2026 (OCR of NSE daily price lists) | ✅ 17 Nov 2026 |
| 2 | Robustness checks (bootstrap, calibration, sensitivity) | ✅ 16 Nov 2026 |
| 3 | Chart export + research note draft | ✅ 17 Nov 2026 |
| 4 | Speculation news checks | ✅ 17 Nov 2026 |
| 5 | Deploy-ready + tests + CI | ✅ 17 Nov 2026 (push pending your OK) |

---

## Step 0: Base build (16 Nov 2026)

- Public data: NSE daily prices from Mendeley (2013 – Jun 2026), CMA bulletins (monthly foreign flows 2015 – Sep 2026, ownership per company), CBK macro, FRED.
- Modules: depth (A), sell-off alert (B, walk-forward tested), speculation (C), stress test; 4-screen Streamlit dashboard; walkthrough notebook.
- Headline: 65% of listed shares need more than 20 days to exit KES 10m; the top 5 stocks make up 69% of trading.
- See [PLAN.md](PLAN.md) for the full plan.

## Step 2: Robustness checks (16 Nov 2026) ✅

Do the findings survive other assumptions, and could they be chance? Code: `src/bedrock/robustness.py`, run by the pipeline,
saved as `data/processed/outputs/robustness_*.parquet`, shown in the dashboard's "Robustness" expanders.

**Depth: the headline holds.** Share of the 65 ordinary shares needing more than 20 days to exit KES 10m:

| Lookback | 10% of daily volume | 20% (base) | 30% |
|---|---|---|---|
| 60 days | 74% | 65% | 62% |
| 120 days (base) | 71% | **65%** | 60% |
| 250 days | 71% | 66% | 62% |

At KES 1m it is 26–49%; at KES 50m it is 74–92%. However you set it up, most of the market is hard to exit.

**Sell-off Alert: the signal is real but weak, and over-confident.**
- XGBoost HIGH RISK calls (≥ 45%): heavy selling followed 8 of 18 times (44%), against a 22% base rate. Binomial test p = 0.03.
- Logistic HIGH RISK calls: 4 of 15 (27%), p = 0.44. Not better than chance.
- Calibration (XGBoost): when it says ~62%, the real rate is 44%; when it says ~38%, the real rate is 14%. Treat the number as a ranking, not a probability.

**Speculation: one claim dropped, two kept.** Cluster bootstrap (resampling whole stocks, 2,000 draws), gap in forward
return after a watch-listed up-spike vs other > 5% up-days:

| Stocks | Horizon | Gap | 95% CI | Keep? |
|---|---|---|---|---|
| Small | 5 days | +4.4% | +1.4% to +8.3% | ✅ momentum in thin stocks |
| Small | 20 days | +10.7% | −0.4% to +29.0% | ❌ too noisy, dropped |
| Large | 5 days | +1.1% | −0.8% to +3.1% | ❌ |
| Large | 20 days | −3.3% | −5.2% to −1.3% | ✅ large caps partly reverse |

PLAN.md results section updated to match.

## Step 1: Prices to November 2026 (OCR of NSE daily price lists) ✅

**Why:** the public price history (Mendeley) stops on 30 Jun 2026. The NSE posts a daily price list as a
scanned PDF (`https://www.nse.co.ke/wp-content/uploads/DD-MMM-YY.pdf`), so we read those with OCR.

**How:** `python -m bedrock.nse_ocr` (code: `src/bedrock/nse_ocr.py`)
1. Download every trading day 22 Jun – 13 Nov 2026: 104 PDFs (20 Oct was a holiday).
2. OCR each page (RapidOCR; 4 parallel workers × 3 threads, ~1 hour, cached per day in `data/raw/nse/ocr/days/`).
3. Rebuild rows: each row is anchored on its ISIN box, and the five number columns (high, low, VWAP, previous, volume)
   are found by clustering box positions. Company names are matched to tickers.
4. **Official close** = the "previous" price on the next day's list (it can differ from VWAP because small trades
   do not set the price), used when the next list is the next trading day and the two agree within 15%.
5. Quality checks: close inside the day's range, no move > 30%, previous price = yesterday's close.
   Rows failing the first two are dropped in `clean.py`.

**Checks against Mendeley on the overlap (22–30 Jun):** volumes match 98.9%, closing prices 95.7%. Most mismatches
are non-traded small caps where Mendeley's source carries a stale price (e.g. CABL 1.00 vs the NSE's 1.71).

**NASI for the new days:** the price lists cover stocks only, so NASI is rebuilt from stock prices (daily returns
weighted by market cap). Tested on 2024–26, where we have the real NASI: daily correlation 0.97, average daily error
6 bp, cumulative return 146% vs 147%. Rows are labelled "NASI (rebuilt)". Code: `clean.extend_nasi`.

## Step 3: Charts + research note draft ✅

- `python -m bedrock.figures` writes 6 print-ready charts to `reports/figures/` (PNG + SVG): exit bands, depth over
  time, foreign flows, sell-off out-of-sample test, stress test, speculation bootstrap.
- `reports/bedrock_note.md`: full first draft (headline, 4 sections, method and limits). Numbers are refreshed after the
  OCR rerun.
- New fact for the note, checked in the data: foreigners were **net sellers in 73% of months since 2019, a net KES 127bn
  out**, including through the 2025–26 rally.

## Step 4: Speculation news checks ✅

- `data/manual/news_checks.csv` (committed to GitHub): one row per flagged day, with `news_found` = yes / no, the headline
  and source link. The pipeline adds new candidates to check automatically, and fills the dashboard's "News found?" column.
- **Checked so far: the 8 most unusual watch-list days of 2025–26.** 6 had news (KQ return to trading, EABL–Asahi deal,
  NMG stake sale, Car & General results and dividend, Williamson Tea dividend). **2 had none: TCL (21 Jan 2025) and
  Eveready (7 May 2025).**
- Worked example for the note: **TCL** normally traded ~KES 64k/day; from 20 Jan 2025 it rose on 12 of 13 days,
  KES 0.50 → 1.65 (+230%), on 10–100× normal value, then fell 39% in 5 days, with no news found. Contrast: EABL
  rose 19% on the Asahi news and gave back 18% within a month.

## Step 5: Deploy-ready, tests, CI ✅

- `tests/test_core.py`: 10 unit tests on small synthetic data (parsing, tiers, depth ordering, stress statuses,
  NASI rebuild, news file, OCR row rebuild). All pass.
- `.github/workflows/ci.yml`: GitHub Actions runs the tests and a dashboard smoke test on every push.
- `python -m bedrock.publish`: copies outputs to `app/snapshot/` for Streamlit Cloud. **Refuses if the outputs were
  built from Rock data**, so licensed numbers can't be pushed by accident. `--check` opens all 4 screens.
- `requirements-ocr.txt` keeps the heavy OCR packages out of the deployed app.

## Final rerun on data to 16 Nov 2026 (17 Nov 2026)

**OCR result:** 105 trading days (22 Jun – 16 Nov; 20 Oct holiday), 7,374 rows, 70 stocks a day. The official close
comes from the next day's list for 98% of rows. 11 misreads (lost decimal points) were repaired from neighbouring days,
and only 4 new rows were dropped.

**Three problems found and fixed during the rerun:**
1. **Block deals distorted liquidity.** NCBA moved 1.09bn shares (KES 99.8bn, two-thirds of the company) on 3 Nov 2026
   after a 4-day halt, and Kenya Pipeline moved KES 41bn on 19 Oct. These made the top-5 share jump from 69% to 82%.
   Fix: for liquidity measures a day counts for at most 10× the stock's median traded day (`value_kes_adj`,
   `config.BLOCK_MULT`). Speculation still uses raw values (spikes are its signal).
2. **The sell-off model's result was fragile.** With full inputs, p moved from 0.03 to 0.05 to 0.22 as data and value
   measurement changed. We therefore compared 3 input sets × 2 models out-of-sample and report all of them
   (`robustness.selloff_feature_sets`, a dashboard expander). Flows-only XGBoost was clearly best: 10/17 = 59% vs 26%,
   p = 0.004 (0.023 after Bonferroni for 6 versions), Brier +9% vs base, calibrated. It is now the live model
   (`config.SELLOFF_FEATURES`). A no-model persistence rule gets 40% (p = 0.12).
3. **Chart theme hid reference lines** (simple_white sets shape width 0), so lines were invisible. Fixed and every chart
   re-checked by eye.

**News checks on Jul–Nov 2026 flags:** 13 more checked. With news: KQ (USD 350m government loan, 12 Oct), C&G (H1 profit
×4, 13 Aug; Business Daily calls the tenfold run "speculator-driven"), Kapchorua (dividend), SMWF (global ETF, 3 days).
No news: UNGA (24 Jul), CTUM, TPSE, KQ (17 Aug), CARB, NMG (5 Oct, 1,700× normal value), NSE plc (26 Oct, 225×).
The largest no-news days look like negotiated block deals, so a no-news flag is a lead, not proof. UNGA 31 Aug is
unchecked (results date unclear).

**Final numbers:** see PLAN.md section 4. Checks run: 11 unit tests pass; all 4 dashboard screens OK on local outputs
**and** on the committed snapshot alone (deployed mode); walkthrough notebook re-executed with 0 errors.

**Not done (needs your decision):** commit and push to GitHub, and deploy on Streamlit Cloud.

## Model review, PDF note, slide deck and presentation check (17 Nov 2026)

**Honest model review (what the numbers really say).**
- *Sell-off alert:* HIGH RISK calls hit 10/17 (59% vs 26%), p = 0.004, and this holds with the line anywhere from
  35% to 50% (52–59%, all p < 0.03). But it catches only 10 of 20 heavy months, its hits cluster in 2020 and 2022,
  and from Jul 2025 to Sep 2026 it caught 1 of 6. Its AUC (0.64) is no better than the running base rate (0.635),
  so its value is only in the HIGH RISK calls.
- *Fix:* the **LOW RISK label was misleading** (heavy selling followed 6 of 28 low readings = 21%, close to the 26%
  normal rate; it said LOW RISK before the Aug 2025, Jan 2026 and Aug 2026 outflows). Removed: the signal is now
  HIGH RISK or NO CALL (`selloff.signal`, `config.py`, test updated).
- *New checks* (`robustness.selloff_thresholds`, `robustness.block_cap_sensitivity`, both in the dashboard):
  the depth headline is 66–67% with block caps from 5× to 50× and 62% with no cap; the cap mainly moves the top-5
  share (70–82%).
- Note, README and slide outline now state the limits plainly. No new model versions were tried (that would be
  tuning on the test months).

**Dashboard for presenting:** checked by screenshot at 1366×768 and 1600×900. Fixed cut-off labels on the Sell-off
screen (signal now a red badge) and Stress Test screen; added a "Track record" expander; `.streamlit/config.toml`
hides the developer "Deploy" menu. Pipeline rerun reproduced the same numbers; snapshot republished (18 files).

**Research note PDF:** `python -m bedrock.note_pdf` → `reports/bedrock_note.pdf`, 4 A4 pages with all six charts.
The header still has the placeholder `github.com/<your-account>/bedrock` (rerun with `--repo` once the repo exists).

**Slides:** 8-slide deck built as a private Claude artifact (downloadable as PowerPoint or PDF), with speaker notes
and judge Q&A answers. Charts exported title-free with larger text for projection (`reports/figures/slides/`).
Placeholders to fill: your name, programme/university, repo link.

**Checks:** 11 unit tests pass; all 4 screens OK.
**Still not done (needs your decision):** commit, push to GitHub, deploy on Streamlit Cloud.

## Dashboard redesign and project briefing (17 Nov 2026)

**Dashboard redesigned** (`app/streamlit_app.py`): top navigation instead of a sidebar, a new **Overview** screen
(four headline cards + two charts), one headline sentence per screen, number cards, a "MODEL" strip naming the model
and how it was tested, charts as clean cards with no toolbar, and all method detail moved into collapsible sections.
New interactions: position size on Market depth (KES 1m–100m), stock look-up, time window on Speculation, sliders on
Stress test. Theme in `.streamlit/config.toml`; Streamlit pinned to 1.56.0 so the styling matches what was tested.
Checked by screenshot at 1440×900; `publish --check` now tests all 5 screens (all OK).

**Briefing page** (private Claude artifact): the question, why it matters, the four answers, the models in plain words
with grades, what is done / not done, the honest case for and against winning, upgrades in order of payoff, a 60-second
script and judge Q&A. Made to share with a second reviewer.

**Slides:** last slide now shows the new dashboard Overview screenshot.

## Module E: stock-by-stock crash risk (17 Nov 2026)

**Built** `src/bedrock/crash.py`, run by the pipeline, shown on a new dashboard screen "Crash risk", in the note
(section 5, fig 7) and on a new slide. Design fixed before looking at results: crash = a fall of 15%+ over the next
21 trading days; 14 inputs known on the day; ordinary shares with at least 5 trades in the last 60 days; logistic and
XGBoost with preset settings; walk-forward by year with purging (no training label overlaps the test year); baseline =
rank by 60-day volatility. A test proves changing future prices leaves every feature unchanged.

**Results (7,154 out-of-sample stock-months, 2016–2026):** riskiest 10% crashed 10.9% vs 5.5% average (lift 2.0,
p < 0.001), safest 10% 2.7%. A "most volatile 10%" rule gets 9.2%. Ranking power: model AUC 0.60, volatility 0.61;
difference −0.01 (95% range −0.05 to +0.02, months resampled). Same picture at −10% and −20% crash definitions.
Raw probabilities run high (Brier skill −5%), so the dashboard reports each stock's risk group and that group's real
crash rate. Riskiest on 16 Nov 2026: AMAC, CGEN, OCH, SKL, EVRD. No further versions were tried.

**Checks:** 12 unit tests pass; all 6 screens OK; note PDF 4 pages; deck 9 slides.

## Opportunity Radar, Stock report, demo page, market-ready roadmap (17 Nov 2026)

Merged the team's Rock Atlas ideas into Bedrock (nothing removed):
- **Opportunity Radar** (`radar.py`): exit check first ("can you get out?": sell the position within 20 trading
  days at 20% of daily trading), then an equal-weight score of momentum, stability and resilience (the team's
  Kenyan Market Resilience Index). Weights fixed before testing. Results, 129 months 2016–2026: top third
  +0.87%/month vs bottom third +0.19% (difference +0.68%, t = 1.3, top won 56% of months: points the right way,
  not yet proven). Without the exit check, 42% (KES 1m) and 67% (KES 10m) of "top picks" could not be sold.
  Resilience test (54 falling months): +0.2%, t = 0.3, so past resilience does not reliably repeat.
- **Stock report**: one page per stock combining every module, with evidence, how sure, and what would change the view.
- **Fundamentals (demo)** (`demo.py`): synthetic data for fictional companies, clearly labelled, used nowhere else.
- **Market-ready** screen: data upgrades (per-stock foreign trading first), user-ready features, and the model
  upgrades that would make Bedrock production-grade (GARCH volatility, regime-switching, Hawkes, tail risk,
  calibration, monitoring and governance).
- Tests: 15 pass (new: exit check, resilience has no look-ahead, demo is labelled). All 10 screens OK.

## GARCH challenger, plain-English guide, second demo page, slides (17 Nov 2026)

**GARCH volatility forecast** (`garch.py`), a stochastic time-series model, refitted each year on earlier data only.
- V1, daily GARCH(1,1) with Student-t shocks: fitted for only 28% of stock-years (NSE prices move in ticks and many
  days have no trades, so daily returns are lumpy and fits explode). Reported, not used.
- V2, weekly GARCH(1,1) (normal QMLE), the standard thin-trading remedy: fits 84% of stock-years. Volatility
  forecasts track reality as well as "the last 60 days repeat" (correlation 0.49 both; median error 37% vs 32%).
- As a crash ranking, the riskiest 10% by GARCH crashed 11.8% of the time: best of six methods (live XGBoost 10.9%,
  60-day rule 9.2%, XGBoost + GARCH 10.6%). Gain vs the 60-day rule: AUC +0.009 (95% range -0.011 to +0.029), so not
  proven: GARCH runs as a challenger next to the live model. Test: future returns never change past forecasts.

**Dashboard (12 screens):** every screen opens with "This screen answers: ..." and a "New here?" explainer; new
**Guide** screen (all questions, every model with its result and what it means, glossary); GARCH block on Crash
risk; second demo page **Foreign flows by stock (demo)** (synthetic, fictional companies, labelled).
**Slides:** 13, adding GARCH, Opportunities, Stock report and Market-ready; last slide shows the new dashboard.
**Checks:** 16 tests pass; all 12 screens OK.

## Two-level navigation and demo copies of data-limited screens (17 Nov 2026)

- Navigation rebuilt as sections (Overview · Market · Stocks · Demo (made-up data) · Plan & guide), with that
  section's screens on a second row. 14 screens; the smoke check walks every section and screen.
- Demo copies of the screens that richer data would improve, real screens untouched:
  **Sell-off alert (demo)** runs the real sell-off model code on synthetic weekly flows (413 test weeks vs 78
  months) and **Opportunities (demo)** adds value and quality from (synthetic) financials to the radar for
  fictional companies. Both carry the red synthetic-data banner; their scores are not evidence of real skill.
- The dashboard now reloads automatically when the pipeline writes new outputs.
