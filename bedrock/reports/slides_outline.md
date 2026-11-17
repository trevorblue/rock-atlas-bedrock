# Bedrock: slide outline (8 slides, ~5 minutes)

Build only if there is a presentation round. Reorder to match the brief (see PLAN.md "Event-day playbook").
Every chart is in `reports/figures/`; every number comes from `data/processed/outputs/headline.json`.

| # | Slide title (the takeaway, not the topic) | Visual | What to say (≈ 30–40 s) |
|---|---|---|---|
| 1 | **The NSE is at record highs. What is actually holding it up?** | Title + one-line headline | "Bedrock answers one question: when the next sell-off comes, where does Kenya's market break?" |
| 2 | **67% of listed shares need more than 20 days to exit KES 10m** | fig1_exit_bands | Only 5 stocks clear in 2 days, and 5 stocks are 74% of all trading. Robust: 62–72% under every assumption. |
| 3 | **The rally lifted prices, not depth** | fig2_depth_history | Thin share rose from 54% (2013) to 92% (Mar 2024); the rally only brought it back to 67%. |
| 4 | **Foreigners pulled out a net KES 127bn since 2019, through the rally** | fig3_foreign_flows | Net sellers in 73% of months. Locals carried the rally; foreigners used it to exit. |
| 5 | **Our early warning: 59% hit rate vs 26% normal** | fig4_selloff_test | 10 of 17 HIGH RISK calls hit (p = 0.004, survives correction for 6 versions). The simplest model won, since more inputs added noise. Honest limit: it catches about half of heavy months and missed most of 2026's. Current reading: **HIGH RISK for October**. Rock's weekly flows are the upgrade. |
| 5b | **Stock by stock: the ones we rank riskiest crash twice as often** | fig7_crash_risk | Riskiest 10% crashed 10.9% vs 5.5% average (2.7% for the safest 10%), tested on 7,154 stock-months. Honest: a "most volatile" rule gets 9.2%, so crash risk is mostly volatility. Riskiest now: Africa Mega Agricorp, Car & General, Olympia. |
| 6 | **KES 2bn of foreign selling in a week would trap 16 stocks, even Equity** | fig5_stress_test | Equity needs 22 days to absorb its share; Portland, Crown, NBV, Kakuzi and Britam would fall 16–25%. The index looks calm (−4%) while smaller stocks freeze. |
| 7 | **TransCentury: +230% in 13 days on no news** | fig6_speculation + TCL price line | Small caps run for a week after spikes (+4.4%); large caps reverse (−3.3%). Of 21 flags checked, 9 had no news. Business Daily called C&G's tenfold run "speculator-driven", and we flagged it twice. |
| 8 | **Built for Rock: a weekly fragility section, ready for Rock Data Plus** | Dashboard screenshot + GitHub/QR link | Who uses it: Rock research (weekly section), Nabo fund managers (exit check), retail (warning). Drop Rock files into `data/rock/` and everything reruns. |

**Live demo (if allowed, 60 s):** Screen 4: move the slider from KES 2bn to KES 5bn, then show the trapped count rise.

**Likely judge questions, with short answers**
- *Is the sell-off model overfit?* It was tested walk-forward: each month predicted only from earlier data. We tested 6 versions and show all of them. The winner is the simplest, and its p-value survives correction for those 6 tries (0.023).
- *How has it done recently?* Badly, and we say so: from July 2025 to September 2026 it caught 1 of 6 heavy months. It works in long exit waves (2020, 2022) and misses selling that starts from a calm month. That is the gap weekly data from Rock would close. It never says "low risk", because low readings were not reliable.
- *Why 20% participation?* It's a common block-trading rule of thumb. The result holds at 10% and 30% (slide 2).
- *Where do prices after June come from?* The NSE's own daily price lists, read with OCR and checked against Mendeley on the overlap (98.9% of volumes and 95.7% of closes match); only 4 of 6,904 rows were dropped.
- *Is speculation proven?* No. Flags are leads. A move with no news is a candidate, not a verdict.
- *Why cap block deals?* NCBA moved KES 100bn in one day on 3 Nov 2026 (two-thirds of the company). Counting it would make NCBA look like the most liquid stock on the NSE, which it isn't for an ordinary seller.
