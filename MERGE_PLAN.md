# ROCK ATLAS × Bedrock — merge plan

**Written before any code was changed: 17 November 2026.**
This folder is a **new clone**. Neither original project is touched:

| Project | Where the original lives | Status |
|---|---|---|
| Rock Atlas (partner's front end) | `github.com/ObiwanKenobee/rock-atlas` | untouched; cloned here as the base |
| Bedrock (our engine) | `c:\Users\Admin\OneDrive\Desktop\BEDROCK` and `github.com/trevorblue/bedrock` | untouched; copied in, not moved |

---

## 1. The rule this merge follows

**Nothing is deleted from either project.**

1. **Atlas supplies the look**: its sidebar, page names, numbering, typography, dark theme and layout.
2. **Every Atlas page and feature stays**, working exactly as it does today.
3. **Every Bedrock page, model and line of code stays**, restyled to look like Atlas.
4. **Where both projects do the same job**, the two become one page under the Atlas name, carrying *both* sets of
   content side by side. Neither version is dropped.
5. **Where Bedrock has a page Atlas does not**, that page is simply added to the sidebar.
6. **Atlas's current pages, which run on made-up data, are cloned exactly as they are** into a `(demo)` group, so
   the partner's original work is preserved and can still be demonstrated.

## 2. Why this shape

| | Atlas | Bedrock |
|---|---|---|
| Strength | The product: 8 workspaces, upload, sliders, guided demo, dark theme, polished React UI | The evidence: real NSE data 2013–2026, six tested models, out-of-sample testing, a research note and 16 tests |
| Weakness | Runs on synthetic data for 10 fictional price paths; its own status page lists real-data validation as pending | Streamlit UI, plainer, fewer interactive tools |

Merged, Atlas becomes the shop window and Bedrock the engine room. Judges see a polished platform whose numbers
are real and tested.

## 3. Navigation in the merged app

Two groups in the Atlas sidebar. The first runs on **real NSE data**, the second is the partner's original
**demo** work, untouched.

### Group A — Real data (Bedrock engine)

| # | Page | Atlas content kept | Bedrock content added |
|---|---|---|---|
| 01 | Command Centre | breadth, sector table, index chart, movement monitor, unusual-activity alerts | headline cards (67% hard to sell, KES 127bn outflow, HIGH RISK, 16 trapped), depth history and foreign-flow charts |
| 02 | Opportunity Radar | 5-factor score, weight sliders, evidence, invalidation criteria | the exit check ("can you get out?"), Bedrock's tested score (129 months), "great on paper, can't get out" |
| 03 | Security Explorer | price + SMA chart, volume, drawdown, fundamentals panel | Bedrock's Stock Report rows: days to sell, crash-risk group, speculation flags, stress result, confidence, what would change the view |
| 04 | Risk Laboratory | Sharpe, VaR, drawdowns, correlation matrix, portfolio allocator, 3 stress scenarios | market depth (days to exit per stock, decade history) and the ownership-based foreign-selling stress test as a 4th scenario |
| 05 | Predictive Models | Ridge forecast, baselines, walk-forward backtest with transaction costs | sell-off alert (59% vs 26%), crash-risk model (10.9% vs 5.5%), GARCH challenger (11.8%), each with its test record |
| 06 | Resilience Index | KMRI, weight sliders, stress-cohort test, rank stability | Bedrock's out-of-sample test of whether resilience repeats in the *next* fall |
| 07 | Research Studio | 22-section brief generator, markdown export, AI narrative | Bedrock's research note (4 pages), slide deck, headline findings in the brief |
| 08 | Data Governance | provenance card, 10-point validation suite, status ledger | real data sources, OCR quality (99% volumes / 96% closes), the market-ready roadmap |
| 09 | Market Depth | — | **new**: days to exit per stock, tiers, decade history, block-deal cap, robustness table |
| 10 | Sell-off Alert | — | **new**: monthly foreign-selling warning, track record, all 6 versions tested |
| 11 | Crash Risk | — | **new**: per-stock crash probability, risk groups, GARCH challenger block |
| 12 | Speculation Watch | — | **new**: Isolation Forest flags, news checks, what happens after a flag |
| 13 | Stress Test | — | **new**: interactive foreign-selling scenario, trapped stocks |
| 14 | Market-Ready | — | **new**: data upgrades, user features, production-grade model roadmap |
| 15 | Guide | — | **new**: what each page answers, every model's score in plain English, glossary |

### Group B — Demo (made-up data)

Exact clones of the partner's current pages, running on his synthetic generator, plus Bedrock's four demo pages.
Every number here is invented and labelled as such.

| Page | Origin |
|---|---|
| Command Centre (demo) … Data Governance (demo), all 8 | Atlas, unchanged components on the synthetic dataset |
| Sell-off Alert (demo) | Bedrock: the real model code on synthetic weekly flows |
| Opportunities (demo) | Bedrock: the radar with synthetic company financials |
| Fundamentals (demo) | Bedrock: value-and-quality screen, fictional companies |
| Foreign Flows by Stock (demo) | Bedrock: daily per-stock foreign selling |

## 4. How the two code bases join

```
ROCK-ATLAS-MERGED/
  src/                     <- Atlas React app (his code, unchanged except nav + new pages)
    components/workspaces/ <- his 8 workspaces, untouched
    components/bedrock/    <- NEW: the Bedrock pages, styled like Atlas
    engines/               <- his 6 TypeScript engines, untouched
  bedrock/                 <- NEW: Bedrock's complete Python engine, copied in
    src/bedrock/           <- clean, depth, selloff, crash, garch, radar, speculation, stress, demo …
    tests/                 <- the 16 tests
    reports/               <- research note, figures, slides outline
  public/data/             <- NEW: real data + model results exported from Bedrock as JSON/CSV
  export_for_atlas.py      <- NEW: writes public/data from Bedrock's pipeline outputs
```

**Data flow:** Bedrock's Python pipeline (unchanged) → `export_for_atlas.py` → static JSON/CSV in `public/data/`
→ read by the React pages. No server needed, so it deploys on Vercel as a static site. Later, the same JSON can
come from a small Python API refreshed daily.

**Why the models are not rewritten in TypeScript:** XGBoost, Isolation Forest and GARCH are Python libraries.
Rewriting them would throw away the tests and the out-of-sample results that make Bedrock credible.

## 5. Conflicts, and how each is settled

Decision taken: **his display wins; our data and findings win; anything of his that needs data we do not have is
cloned exactly into the `(demo)` group rather than deleted.**

| Conflict | Settlement |
|---|---|
| Opportunity score: his 5 factors include fundamentals and valuation (45% of the weight), which need company financials we do not have for real NSE stocks | Real page shows his slider UI driven by the factors real data supports (momentum, risk, liquidity) plus our exit check and tested score. His full 5-factor version, including fundamentals, is kept exactly as-is in **Opportunity Radar (demo)**. |
| Resilience index: his cohort test is scored inside the same stress window it tests (his screen notes the overlap) | Both shown: his KMRI and cohort test on real data, beside Bedrock's out-of-sample test (does resilience repeat in the *next* fall? On real data, not reliably). |
| Predictive models: on synthetic data his Ridge model trails a naive baseline and the strategy loses money after costs | Rerun on real data and reported honestly, alongside Bedrock's tested models. The synthetic result stays in **Predictive Models (demo)**. |
| Fundamentals: no real company financials | Real pages mark fundamentals "unavailable" (his app already does this); the full fundamentals experience stays in the demo group. |
| Product name | ROCK ATLAS is the product. Bedrock is named as the engine ("Intelligence engine: Bedrock"). Team can change this in one constant. |

## 6. Known issues in the Atlas MVP, to fix here

1. `/api/*` returns 404 on the deployed Vercel site, so saving datasets/reports and the AI brief do not work there.
   Fix: those features degrade gracefully and the deterministic brief (which needs no server) stays primary.
2. His synthetic demo uses **real company names with invented financials** ("Equity Group Holdings (Modeled)",
   P/E 4.1x). Kept in the demo group only, and the demo banner says every figure is invented.
3. `package.json` still carries the template name `react-example`. Cosmetic; renamed here.

## 7. Order of work

1. ✅ New clone created, originals untouched.
2. ✅ This plan written.
3. Copy Bedrock's Python engine into `bedrock/`.
4. Write `export_for_atlas.py`; export real NSE prices (his CSV column format) and all model results as JSON.
5. Rebuild the sidebar: Group A (real) and Group B (demo), with a data-mode switch. His components are reused
   unchanged for both groups.
6. Build the 7 new Bedrock pages as React components in Atlas's visual language.
7. Add Bedrock's blocks to his 8 existing pages.
8. Check it builds, runs and type-checks; screenshot every page.
9. Write `MERGE_LOG.md` recording what was done, and keep this plan as the record of intent.

## 8. What is explicitly NOT done

- No page, feature or file from either project is removed.
- Neither original repository is modified.
- No invented numbers on real-data pages; every demo figure stays behind a `(demo)` label and a banner.
