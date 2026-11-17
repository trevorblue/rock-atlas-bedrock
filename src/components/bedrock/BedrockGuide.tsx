import React from 'react';
import { BedrockData } from '../../bedrock/types';
import { num, pct } from '../../bedrock/data';
import { DataTable, PageHead, Panel, PanelTitle, Pill, PillTone } from './kit';

const GLOSSARY: Array<[string, string]> = [
  ['Days to sell (days to exit)', 'Trading days needed to sell a holding if you sell at most 20% of a normal day\'s trading.'],
  ['20% of daily trading', 'The most you sell in one day, so your own selling does not crash the price.'],
  ['Liquidity, depth', 'How easily a share can be bought or sold without moving its price.'],
  ['Net foreign flow', 'Foreign investors\' buying minus their selling. Negative means they sold more than they bought.'],
  ['Heavy selling', 'A month in the worst quarter of all months for net foreign outflows.'],
  ['HIGH RISK, NO CALL', 'HIGH RISK is a warning. NO CALL means no reliable signal either way; it is not an all-clear.'],
  ['Tested on data it never saw', 'Every prediction was made using only data from before that date, then checked against what really happened, as if the model had been running live.'],
  ['Hit rate', 'How often a warning came true.'],
  ['Normal rate, average', 'How often the event happens anyway, with no model at all.'],
  ['Chance it is luck (p-value)', 'How likely the result is a fluke. Under 5% is usually treated as real.'],
  ['Ranking score (AUC)', 'How well a model puts risky stocks above safe ones. 0.5 is random, 1.0 is perfect, so 0.6 is modest skill.'],
  ['t (t-statistic)', 'How many times bigger a result is than its own normal wobble. Above 2 usually counts as proven.'],
  ['Volatility', 'How much a price jumps around. Higher means riskier.'],
  ['GARCH', 'A standard financial time-series model that forecasts volatility, knowing that calm and stormy spells come in runs.'],
  ['Crash', 'A fall of 15% or more over the next 21 trading days (about a month).'],
  ['Risk group', 'Stocks split into ten equal groups each month, from 1 (safest) to 10 (riskiest).'],
  ['Momentum', 'How much the price rose over the last year.'],
  ['Resilience', 'How a stock did compared with the whole market in months when the market fell.'],
  ['Exit check', 'Could you sell the position within 20 trading days? An opportunity has to pass it.'],
  ['XGBoost', 'A machine-learning method that combines many small decision trees into one prediction.'],
  ['Isolation Forest', 'A machine-learning method that spots unusual days because they are easy to separate from normal ones.'],
  ['Square-root price impact', 'A standard rule of thumb: selling four times more moves the price about twice as much.'],
  ['Trapped, strained, absorbed', 'Stress-test outcomes: stuck for more than four times the selling window, up to four times, or within it.'],
  ['Block deal', 'One huge pre-arranged trade, such as a takeover stake. Counted at most 10× a normal day so it does not make a stock look liquid.'],
  ['Challenger model', 'A newer model run beside the live one. It replaces the live model only if it keeps winning on new data.'],
  ['Synthetic, demo data', 'Made-up numbers used only to show how a feature works. Never used as a finding, and always behind a "(demo)" label.'],
];

export const BedrockGuide: React.FC<{ data: BedrockData }> = ({ data }) => {
  const sig = data.selloff.significance.find((s) => s.model === data.selloff.live.model);
  const crash = data.crash.summary;
  const radar = data.radar.summary;
  const garchRow = data.crash.compare.find((c) => c.model.includes('GARCH forecast'));

  const models: Array<{ model: string; how: string; result: string; meaning: string; grade: [string, PillTone] }> = [
    {
      model: 'Market depth — days to sell + K-means tiers',
      how: 'Measured on 120 trading days per stock, then rechecked under every assumption',
      result: `${pct(data.headline.depth.pct_over_20d)} of shares need more than 20 days to sell KES 10m; 62–72% under every assumption tested`,
      meaning: 'A solid measurement: most of the market is hard to sell',
      grade: ['Strong', 'good'],
    },
    {
      model: 'Sell-off alert — XGBoost on foreign flows',
      how: `${data.selloff.walkForward.length} months, each predicted using only earlier data`,
      result: sig
        ? `Warnings came true ${sig.hits} of ${sig.high_risk_calls} times (${pct(sig.hit_rate)}) against ${pct(
            sig.base_rate
          )} by chance; under 1% chance of luck`
        : '—',
      meaning: 'A useful warning that misses about half of all sell-offs; weekly data would sharpen it',
      grade: ['Medium', 'warn'],
    },
    {
      model: 'Crash risk — XGBoost, 14 inputs',
      how: `${crash.n_test.toLocaleString('en-US')} stock-months it had never seen`,
      result: `Riskiest 10% crashed ${pct(crash.top10_rate, 1)} of the time against ${pct(
        crash.base_rate,
        1
      )} average; safest 10%: ${pct(crash.safest10_rate, 1)}`,
      meaning: `Real, but mostly driven by volatility: a simple rule gets ${pct(crash.rule_top10_rate, 1)}`,
      grade: ['Medium', 'warn'],
    },
    {
      model: 'GARCH volatility forecast — stochastic time series',
      how: `${data.crash.garch ? data.crash.garch.fits : '—'} yearly fits, refitted on earlier data only`,
      result: garchRow
        ? `As a crash ranking, its riskiest 10% crashed ${pct(
            garchRow.top10_crash_rate,
            1
          )}: best of six methods, though the gain could be chance`
        : '—',
      meaning: 'Promising; runs as a challenger until it keeps winning on new months',
      grade: ['Promising', 'warn'],
    },
    {
      model: 'Speculation watch — Isolation Forest',
      how: 'Flags checked by hand against NSE announcements and the press',
      result: `${data.speculation.newsChecked - data.speculation.noNews} of ${
        data.speculation.newsChecked
      } checked flags had real news; after a flag, small stocks rose about 4.4% more over the next week`,
      meaning: 'Finds real events; the no-news flags are leads, not proof',
      grade: ['Good', 'good'],
    },
    {
      model: 'Stress test — square-root price impact',
      how: 'A scenario built on CMA ownership data, run live in the browser',
      result: `KES 2bn of foreign selling in a week traps ${data.headline.stress_default.n_trapped} stocks, even Equity`,
      meaning: 'A scenario, not a forecast, so it has no accuracy score',
      grade: ['Scenario', 'muted'],
    },
    {
      model: 'Exit check — can you get out?',
      how: `${radar.months} months, applied before any pick counts as an opportunity`,
      result: `Without it, ${pct(radar.paper_fail_share_1m)} (KES 1m) to ${pct(
        radar.paper_fail_share_10m
      )} (KES 10m) of top picks could not be sold within 20 days`,
      meaning: 'Proven, and the most useful new idea: always ask whether you can get out',
      grade: ['Strong', 'good'],
    },
    {
      model: 'Opportunity radar — transparent scoring rule',
      how: `${radar.months} months, weights fixed before testing and never tuned`,
      result: `Top third beat bottom third by ${(radar.spread_avg * 100).toFixed(1)}% a month in ${pct(
        radar.spread_win_share
      )} of months (t = ${num(radar.spread_t, 1)})`,
      meaning: 'Points the right way but not yet proven: a shortlist, not a buy signal',
      grade: ['Not yet proven', 'warn'],
    },
    {
      model: 'Resilience index (KMRI)',
      how: `${radar.res_months} months when the market actually fell`,
      result: `Stocks that had held up before did only ${(radar.res_spread_avg * 100).toFixed(
        1
      )}% better in the next fall (t = ${num(radar.res_spread_t, 1)})`,
      meaning: 'Describes the past; it does not reliably repeat',
      grade: ['History only', 'muted'],
    },
    {
      model: 'Fundamentals (demo)',
      how: 'Not tested: synthetic data for fictional companies',
      result: 'No result claimed',
      meaning: 'Shows what real company financials would add once Rock provides them',
      grade: ['Demo', 'muted'],
    },
  ];

  const pages: Array<[string, string, string]> = [
    ['01. Command Centre', 'What is the market doing right now, and where is it fragile?', 'A 30-second summary for a meeting or the start of a demo.'],
    ['02. Opportunity Radar', 'Which stocks look attractive, and can you actually get out of them?', 'A shortlist for investors, already filtered for whether a position can be sold.'],
    ['03. Security Explorer', 'What does every signal say about one stock?', 'A one-page brief before a decision.'],
    ['04. Risk Laboratory', 'How risky is this portfolio, and what would a shock do to it?', 'Portfolio risk, plus whether the holdings can be sold at all.'],
    ['05. Predictive Models', 'What do the models expect, and how well have they done?', 'The honest track record behind every prediction.'],
    ['06. Resilience Index', 'Which stocks hold up when the market falls?', 'Research into what makes an NSE stock resilient.'],
    ['07. Research Studio', 'Can I get this as a written research brief?', 'Turns the numbers into a report you can export.'],
    ['08. Data Governance', 'Where does the data come from, and can it be trusted?', 'Provenance, validation and limitations for every dataset.'],
    ['09. Market Depth', 'How easy is it to sell a share without crashing its price?', 'The core fragility measure: days to exit for every stock.'],
    ['10. Sell-off Alert', 'Will foreign investors sell heavily next month?', 'An early warning, with its full track record.'],
    ['11. Crash Risk', 'Which stocks are most likely to fall 15% or more next month?', 'A stock-by-stock watch list, plus the GARCH challenger.'],
    ['12. Speculation Watch', 'Which price jumps have no news behind them?', 'Leads for analysts and regulators.'],
    ['13. Stress Test', 'If foreigners sell a large amount quickly, which stocks break?', 'An interactive scenario for risk managers.'],
    ['14. Market-Ready', 'What would make this ready for real clients?', 'The data and model roadmap.'],
  ];

  return (
    <div className="space-y-6">
      <PageHead
        eyebrow="Guide"
        question="What does each page answer, how good is each model, and what do the words mean?"
        title="Plain English, for anyone seeing this platform for the first time"
        subtitle="Every figure quoted here comes from a model tested on data it had never seen. Pages marked (demo) in the sidebar run on invented numbers and are labelled as such."
      />

      <Panel>
        <PanelTitle title="What each page answers" />
        <DataTable
          rows={pages.map(([page, question, forWhat]) => ({ page, question, forWhat }))}
          columns={[
            { key: 'p', header: 'Page', width: '20%', render: (r) => <span className="font-semibold">{r.page}</span> },
            { key: 'q', header: 'The question it answers', width: '40%', render: (r) => r.question },
            { key: 'f', header: "What it's for", render: (r) => r.forWhat },
          ]}
        />
      </Panel>

      <Panel>
        <PanelTitle
          title="Every model, how well it did, and what that means"
          subtitle="Tested on data the model never saw at the time it made the call"
        />
        <DataTable
          rows={models}
          columns={[
            { key: 'm', header: 'Model', width: '22%', render: (r) => <span className="font-semibold">{r.model}</span> },
            { key: 'h', header: 'How it was tested', width: '18%', render: (r) => r.how },
            { key: 'r', header: 'Result', render: (r) => r.result },
            { key: 'w', header: 'What that means', width: '22%', render: (r) => r.meaning },
            { key: 'g', header: 'Grade', width: '10%', render: (r) => <Pill text={r.grade[0]} tone={r.grade[1]} /> },
          ]}
        />
      </Panel>

      <Panel>
        <PanelTitle title="Glossary" subtitle="Every term used on the pages, in plain words" />
        <DataTable
          rows={GLOSSARY.map(([word, meaning]) => ({ word, meaning }))}
          columns={[
            { key: 'w', header: 'Word', width: '26%', render: (r) => <span className="font-semibold">{r.word}</span> },
            { key: 'm', header: 'What it means', render: (r) => r.meaning },
          ]}
        />
      </Panel>
    </div>
  );
};
