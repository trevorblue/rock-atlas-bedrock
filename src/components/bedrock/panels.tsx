/**
 * Bedrock blocks that sit inside ROCK ATLAS's own workspaces, so each page carries both projects' work:
 *   ExitCheckPanel   -> 02. Opportunity Radar   (can you actually get out of a pick?)
 *   StockSignalsPanel-> 03. Security Explorer   (every Bedrock signal for the selected stock)
 *   DepthRiskPanel   -> 04. Risk Laboratory     (days to exit + the foreign-selling stress test)
 *   ResilienceTestPanel -> 06. Resilience Index (does resilience repeat in the next fall?)
 *   PredictivePanel  -> 05. Predictive Models   (Bedrock's three tested models)
 *   HeadlinePanel    -> 01. Command Centre      (the five headline findings)
 *   ProvenancePanel  -> 08. Data Governance     (real sources and OCR quality)
 */
import React, { useMemo } from 'react';
import { BedrockData } from '../../bedrock/types';
import { days as fmtDays, kes, niceDate, num, pct, shortName, signedPct } from '../../bedrock/data';
import { daysToExit, runScenario, summarize } from '../../bedrock/stressModel';
import { DataTable, HBarChart, Kpi, ModelStrip, Note, Panel, PanelTitle, Pill } from './kit';

const BEDROCK_TAG = (
  <span className="bg-slate-900 dark:bg-slate-100 text-white dark:text-slate-900 px-2 py-0.5 text-[10px] font-mono font-bold tracking-wider">
    BEDROCK · REAL NSE DATA
  </span>
);

// ---------------------------------------------------------------- 01. Command Centre
export const HeadlinePanel: React.FC<{ data: BedrockData }> = ({ data }) => {
  const h = data.headline;
  const spec90 = data.speculation.recentFlags.filter((f) => {
    const d = new Date(`${data.speculation.recentFlags[0]?.date ?? f.date}T00:00:00Z`);
    d.setUTCDate(d.getUTCDate() - 90);
    return f.date >= d.toISOString().slice(0, 10);
  }).length;

  const cards = [
    { k: 'Market depth', v: pct(h.depth.pct_over_20d), d: `of shares take more than four weeks to sell ${kes(data.meta.settings.positionKes)}`, alert: false },
    { k: 'Sell-off alert', v: h.selloff.signal, d: `${pct(h.selloff.probability)} chance of heavy foreign selling next month`, alert: h.selloff.signal === 'HIGH RISK' },
    { k: 'Crash risk', v: h.crash ? `${(h.crash.top10_rate / h.crash.base_rate).toFixed(0)}×` : '—', d: 'how often our riskiest 10% of stocks crash, against the average', alert: false },
    { k: 'Stress test', v: `${h.stress_default.n_trapped} stocks`, d: `trapped if foreigners sell ${kes(h.stress_default.total_sell_kes)} in a week`, alert: false },
    { k: 'Speculation', v: String(spec90), d: 'unusual price jumps in the last 90 days, each one a lead to check', alert: false },
  ];

  return (
    <Panel className="border-l-2 border-l-red-700 dark:border-l-red-500">
      <PanelTitle
        title="Bedrock fragility findings on real NSE data"
        subtitle={`Six tested models on prices from 2013 to ${niceDate(h.data_as_of.stocks)} and CMA foreign flows to ${
          h.data_as_of.flows
        }. Each headline opens its own page in the sidebar.`}
        right={BEDROCK_TAG}
      />
      <div className="grid gap-3 grid-cols-1 sm:grid-cols-2 lg:grid-cols-5">
        {cards.map((c) => (
          <div key={c.k} className="border border-slate-200 dark:border-slate-800 p-4">
            <div className="text-[10px] font-mono font-semibold tracking-widest text-slate-500 dark:text-slate-400 uppercase">
              {c.k}
            </div>
            <div
              className={`font-display text-xl font-semibold mt-2 tabular-nums ${
                c.alert ? 'text-red-700 dark:text-red-400' : 'text-slate-900 dark:text-slate-100'
              }`}
            >
              {c.v}
            </div>
            <div className="text-[11px] text-slate-500 dark:text-slate-400 mt-1.5 leading-snug">{c.d}</div>
          </div>
        ))}
      </div>
    </Panel>
  );
};

// ---------------------------------------------------------------- 02. Opportunity Radar
export const ExitCheckPanel: React.FC<{ data: BedrockData }> = ({ data }) => {
  const { summary, live } = data.radar;
  const position = 10e6;
  const ok = live.filter((r) => r.exit_ok_10m);
  const paperTop = live.filter((r) => r.paper_rank <= 10);
  const blocked = paperTop.filter((r) => !r.exit_ok_10m);

  return (
    <Panel className="border-l-2 border-l-red-700 dark:border-l-red-500">
      <PanelTitle
        title="Can you actually get out? Bedrock's exit check on real NSE data"
        subtitle={`On the NSE a stock can look excellent on paper and still be impossible to sell. Bedrock tested this every month from ${summary.first.slice(
          0,
          4
        )} to ${summary.last.slice(0, 4)}: a pick only counts when the position can be sold within ${
          summary.exit_days
        } trading days.`}
        right={BEDROCK_TAG}
      />

      <div className="grid gap-3 grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 mb-5">
        <Kpi value={pct(summary.paper_fail_share_10m)} label={`of top picks on paper could not be sold within ${summary.exit_days} days (KES 10m)`} alert />
        <Kpi value={`${blocked.length} of 10`} label="of today's top 10 on paper fail the exit check" />
        <Kpi value={signedPct(summary.spread_avg)} label="a month: top third beat bottom third in testing" />
        <Kpi value={pct(summary.spread_win_share)} label="of months the top third won" />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <div>
          <h4 className="text-xs font-semibold text-slate-800 dark:text-slate-200 mb-2">
            Top opportunities you can get out of
          </h4>
          <HBarChart
            data={ok.slice(0, 10).map((r) => ({
              label: shortName(r.name),
              value: r.score,
              display: num(r.score, 2),
              tone: 'accent',
              hint: `${shortName(r.name)}: score ${num(r.score, 2)}, 12-month return ${signedPct(
                r.mom_12_1
              )}, sells ${kes(position)} in ${fmtDays(r.days_exit_10m)}`,
            }))}
            maxValue={1}
            labelWidth={190}
            width={520}
          />
        </div>
        <div>
          <h4 className="text-xs font-semibold text-slate-800 dark:text-slate-200 mb-2">
            Great on paper, but you cannot get out
          </h4>
          {blocked.length ? (
            <HBarChart
              data={blocked.map((r) => ({
                label: shortName(r.name),
                value: Math.log10(Math.max(2, r.days_exit_10m ?? 1e4)),
                display: fmtDays(r.days_exit_10m),
                tone: 'bad',
                hint: `${shortName(r.name)}: rank ${r.paper_rank} on paper, but ${fmtDays(
                  r.days_exit_10m
                )} to sell ${kes(position)}`,
              }))}
              labelWidth={190}
              width={520}
              reference={{ value: Math.log10(20), label: '20-day limit' }}
            />
          ) : (
            <p className="text-xs text-slate-500 dark:text-slate-400">
              All of today's top 10 on paper pass the exit check at {kes(position)}.
            </p>
          )}
        </div>
      </div>

      <div className="mt-4">
        <Note>
          the exit check is the proven part: without it, {pct(summary.paper_fail_share_1m)} of top picks could not be
          sold within {summary.exit_days} days even at KES 1m, and {pct(summary.paper_fail_share_10m)} at KES 10m. The
          score itself points the right way ({signedPct(summary.spread_avg)} a month, about{' '}
          {signedPct(summary.spread_avg * 12, 0)} a year) but a gap this size could still come from chance about one
          time in five (t = {num(summary.spread_t, 1)}), so treat it as a shortlist to research, not a buy signal.
        </Note>
      </div>

      <div className="mt-4">
        <ModelStrip
          name="Transparent scoring rule + exit check"
          facts={[
            'equal weights fixed in advance: momentum, stability, resilience',
            'exit check applied first',
            `tested on ${summary.months} months, ${summary.first.slice(0, 4)}–${summary.last.slice(0, 4)}`,
          ]}
        />
      </div>
    </Panel>
  );
};

// ---------------------------------------------------------------- 03. Security Explorer
export const StockSignalsPanel: React.FC<{ data: BedrockData; ticker: string }> = ({ data, ticker }) => {
  const depth = data.depth.find((r) => r.code === ticker);
  const crash = data.crash.live.find((r) => r.code === ticker);
  const radar = data.radar.live.find((r) => r.code === ticker);
  const flags = data.speculation.recentFlags.filter((f) => f.code === ticker);

  const stress = useMemo(() => {
    const rows = runScenario(data.depth, {
      totalSellKes: data.headline.stress_default.total_sell_kes,
      days: 5,
      participation: data.meta.settings.participation,
      maxForeignPct: data.meta.settings.strategicCutoff,
    });
    return rows.find((r) => r.code === ticker);
  }, [data, ticker]);

  if (!depth) {
    return (
      <Panel className="border-l-2 border-l-red-700 dark:border-l-red-500">
        <PanelTitle
          title="Bedrock signals"
          subtitle={`${ticker} is not in Bedrock's real-data universe (ordinary shares on the NSE with a liquidity history).`}
          right={BEDROCK_TAG}
        />
      </Panel>
    );
  }

  const d10 = daysToExit(depth.adv_kes, 10e6, data.meta.settings.participation);
  const exitOk = d10 !== null && d10 <= 20;
  const third = radar
    ? radar.score >= 0.667
      ? 'top third'
      : radar.score <= 0.333
      ? 'bottom third'
      : 'middle third'
    : null;

  interface Row {
    signal: string;
    reading: React.ReactNode;
    evidence: string;
    sure: React.ReactNode;
  }

  const rows: Row[] = [
    {
      signal: 'Can you get out?',
      reading: <Pill text={exitOk ? 'Yes' : 'No'} tone={exitOk ? 'good' : 'bad'} />,
      evidence: `Selling KES 10m takes ${fmtDays(d10)} at ${pct(
        data.meta.settings.participation
      )} of normal trading (about ${kes(depth.adv_kes)} a day).`,
      sure: <Pill text="Strong" tone="good" />,
    },
  ];

  if (radar && third) {
    rows.push({
      signal: 'Opportunity score',
      reading: <Pill text={third} tone={third === 'top third' ? 'good' : 'muted'} />,
      evidence: `Score ${num(radar.score, 2)} (rank ${radar.paper_rank} of ${
        data.radar.live.length
      } on paper): 12-month return ${signedPct(radar.mom_12_1)}, volatility ${pct(
        radar.vol_60 * Math.sqrt(250)
      )} a year, ${signedPct(radar.resilience)} against the market in falling months.`,
      sure: <Pill text="Not yet proven" tone="warn" />,
    });
  }

  if (crash) {
    rows.push({
      signal: 'Crash risk next month',
      reading: <Pill text={`group ${crash.risk_decile} of 10`} tone={crash.risk_decile >= 9 ? 'bad' : 'muted'} />,
      evidence: `Stocks in this group fell ${pct(Math.abs(data.crash.summary.crash_drop))}+ in the next month ${pct(
        crash.group_crash_rate,
        1
      )} of the time, against ${pct(data.crash.summary.base_rate, 1)} on average.`,
      sure: <Pill text="Medium" tone="warn" />,
    });
  }

  rows.push({
    signal: 'Speculation flags (last year)',
    reading: <Pill text={String(flags.length)} tone={flags.length ? 'bad' : 'good'} />,
    evidence: flags.length
      ? `Latest ${niceDate(flags[0].date)}. ${flags[0].news || 'News not checked yet.'}`
      : 'No unusual price jumps flagged.',
    sure: <Pill text="Lead to check" tone="muted" />,
  });

  if (stress && stress.sellKes > 0) {
    rows.push({
      signal: `If foreigners sell ${kes(data.headline.stress_default.total_sell_kes)} in a week`,
      reading: (
        <Pill
          text={stress.status}
          tone={stress.status === 'trapped' || stress.status === 'no market' ? 'bad' : stress.status === 'strained' ? 'warn' : 'good'}
        />
      ),
      evidence: `Its share: ${kes(stress.sellKes)}, about ${fmtDays(stress.daysToAbsorb)} to clear${
        stress.priceImpact === null ? '' : `, price ${signedPct(stress.priceImpact)}`
      }.`,
      sure: <Pill text="Scenario" tone="muted" />,
    });
  }

  const changes: string[] = [];
  if (!exitOk) {
    changes.push(
      `Trading rising to about ${kes(10e6 / (data.meta.settings.participation * 20))} a day would let KES 10m be sold within 20 days.`
    );
  }
  if (crash && crash.risk_decile >= 8) {
    changes.push('A calmer price, or the end of a recent run-up, would move it to a lower crash-risk group.');
  }
  if (radar) changes.push('Momentum fading or volatility rising would lower its opportunity score.');
  if (flags.length) changes.push('News that explains the recent jumps would turn a speculation lead into an explained move.');

  return (
    <Panel className="border-l-2 border-l-red-700 dark:border-l-red-500">
      <PanelTitle
        title={`Bedrock stock report — ${shortName(depth.name)}`}
        subtitle="Every signal Bedrock holds on this stock, with the evidence behind it and how sure we are. Rules, not opinions; not investment advice."
        right={BEDROCK_TAG}
      />
      <DataTable
        rows={rows}
        columns={[
          { key: 's', header: 'Signal', width: '22%', render: (r) => <span className="font-semibold">{r.signal}</span> },
          { key: 'r', header: 'Reading', width: '14%', render: (r) => r.reading },
          { key: 'e', header: 'Evidence', render: (r) => r.evidence },
          { key: 'c', header: 'How sure', width: '14%', render: (r) => r.sure },
        ]}
      />
      {changes.length > 0 && (
        <div className="mt-4 border border-slate-200 dark:border-slate-800 p-4">
          <div className="text-xs font-semibold text-slate-900 dark:text-slate-100 mb-1.5">
            What would change this view
          </div>
          <ul className="text-xs text-slate-600 dark:text-slate-400 space-y-1 list-disc pl-4">
            {changes.map((c) => (
              <li key={c}>{c}</li>
            ))}
          </ul>
        </div>
      )}
    </Panel>
  );
};

// ---------------------------------------------------------------- 04. Risk Laboratory
export const DepthRiskPanel: React.FC<{ data: BedrockData }> = ({ data }) => {
  const stress = useMemo(() => {
    const rows = runScenario(data.depth, {
      totalSellKes: data.headline.stress_default.total_sell_kes,
      days: 5,
      participation: data.meta.settings.participation,
      maxForeignPct: data.meta.settings.strategicCutoff,
    });
    return { rows, summary: summarize(rows, data.headline.stress_default.total_sell_kes) };
  }, [data]);

  const worst = stress.rows.filter((r) => r.sellKes > 0 && r.priceImpact !== null).slice(0, 8);

  return (
    <Panel className="border-l-2 border-l-red-700 dark:border-l-red-500">
      <PanelTitle
        title="Bedrock liquidity risk: days to exit, and a foreign-selling stress test"
        subtitle={`Risk here is not only volatility: it is whether a position can be sold at all. ${pct(
          data.headline.depth.pct_over_20d
        )} of ordinary shares need more than 20 trading days to sell ${kes(data.meta.settings.positionKes)}.`}
        right={BEDROCK_TAG}
      />
      <div className="grid gap-3 grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 mb-5">
        <Kpi value={pct(data.headline.depth.pct_over_20d)} label="of shares need more than 20 days to sell KES 10m" alert />
        <Kpi value={pct(data.headline.depth.top5_share_of_value)} label="of all trading is in five stocks" />
        <Kpi value={String(stress.summary.nTrapped)} label={`stocks trapped if foreigners sell ${kes(data.headline.stress_default.total_sell_kes)} in a week`} />
        <Kpi value={signedPct(stress.summary.weightedImpact)} label="index-level impact: the market looks calm" />
      </div>
      <h4 className="text-xs font-semibold text-slate-800 dark:text-slate-200 mb-2">
        Hardest-hit stocks in the default scenario
      </h4>
      <HBarChart
        data={worst.map((r) => ({
          label: shortName(r.name),
          value: Math.abs(r.priceImpact ?? 0),
          display: signedPct(r.priceImpact ?? 0, 0),
          tone: 'bad',
          hint: `${shortName(r.name)}: ${r.status}, about ${fmtDays(r.daysToAbsorb)} to clear`,
        }))}
        labelWidth={220}
      />
      <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-3">
        The full interactive scenario, with sliders for the amount, the window and the assumptions, is on the Stress
        Test page.
      </p>
    </Panel>
  );
};

// ---------------------------------------------------------------- 05. Predictive Models
export const PredictivePanel: React.FC<{ data: BedrockData }> = ({ data }) => {
  const sig = data.selloff.significance.find((s) => s.model === data.selloff.live.model);
  const crash = data.crash.summary;
  const garchRow = data.crash.compare.find((c) => c.model.includes('GARCH forecast'));

  const models = [
    {
      name: 'Sell-off alert (XGBoost on foreign flows)',
      tested: `${data.selloff.walkForward.length} months, each predicted from earlier data only`,
      result: sig
        ? `Warnings were followed by heavy selling ${sig.hits} of ${sig.high_risk_calls} times (${pct(
            sig.hit_rate
          )}), against ${pct(sig.base_rate)} by chance`
        : '—',
      meaning: 'A useful warning that still misses about half of all sell-offs',
      grade: { text: 'Medium', tone: 'warn' as const },
    },
    {
      name: 'Crash risk (XGBoost, 14 inputs)',
      tested: `${crash.n_test.toLocaleString('en-US')} stock-months, ${crash.first_test_year} onwards`,
      result: `Riskiest 10% crashed ${pct(crash.top10_rate, 1)} of the time against ${pct(
        crash.base_rate,
        1
      )} on average; safest 10%: ${pct(crash.safest10_rate, 1)}`,
      meaning: 'Real, but driven mostly by volatility: a simple rule gets ' + pct(crash.rule_top10_rate, 1),
      grade: { text: 'Medium', tone: 'warn' as const },
    },
    {
      name: 'GARCH volatility forecast (stochastic time series)',
      tested: `${data.crash.garch ? data.crash.garch.n.toLocaleString('en-US') : '—'} forecasts, refitted yearly`,
      result: garchRow
        ? `As a crash ranking, its riskiest 10% crashed ${pct(garchRow.top10_crash_rate, 1)}: best of six methods`
        : '—',
      meaning: 'Promising, but the gain could be chance, so it runs as a challenger',
      grade: { text: 'Challenger', tone: 'muted' as const },
    },
  ];

  return (
    <Panel className="border-l-2 border-l-red-700 dark:border-l-red-500">
      <PanelTitle
        title="Bedrock's tested predictive models, on real NSE data"
        subtitle="Each one was trained only on data available at the time and scored on periods it had never seen. Every version tried is reported, not only the winner."
        right={BEDROCK_TAG}
      />
      <DataTable
        rows={models}
        columns={[
          { key: 'n', header: 'Model', width: '26%', render: (r) => <span className="font-semibold">{r.name}</span> },
          { key: 't', header: 'How it was tested', render: (r) => r.tested },
          { key: 'r', header: 'Result', render: (r) => r.result },
          { key: 'm', header: 'What that means', render: (r) => r.meaning },
          { key: 'g', header: 'Grade', width: '10%', render: (r) => <Pill text={r.grade.text} tone={r.grade.tone} /> },
        ]}
        caption="Full detail, including every alternative tested, is on the Sell-off Alert and Crash Risk pages."
      />
    </Panel>
  );
};

// ---------------------------------------------------------------- 06. Resilience Index
export const ResilienceTestPanel: React.FC<{ data: BedrockData }> = ({ data }) => {
  const s = data.radar.summary;
  return (
    <Panel className="border-l-2 border-l-red-700 dark:border-l-red-500">
      <PanelTitle
        title="Does resilience repeat? Bedrock's out-of-sample test on real NSE data"
        subtitle="The cohort test above is scored inside the same stress window it measures. Bedrock asks the harder question: do stocks that held up in past falls hold up in the NEXT one?"
        right={BEDROCK_TAG}
      />
      <div className="grid gap-3 grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 mb-4">
        <Kpi value={String(s.res_months)} label="months when the market actually fell, used as tests" />
        <Kpi value={signedPct(s.res_top_avg)} label="average return of previously resilient stocks in those falls" />
        <Kpi value={signedPct(s.res_bottom_avg)} label="average return of the least resilient stocks" />
        <Kpi value={signedPct(s.res_spread_avg)} label="the difference: too small to be relied on" alert />
      </div>
      <Note>
        on real NSE data, stocks that had held up before did only {signedPct(s.res_spread_avg)} better in the next
        falling month (t = {num(s.res_spread_t, 1)}, {pct(s.res_win_share)} of months), which could easily be chance.
        So the resilience index is sound as a description of the past, and should not be presented as a forecast.
        Resilience still earns its place as one of the three ingredients in Bedrock's opportunity score, where it is
        combined with momentum and stability rather than used alone.
      </Note>
    </Panel>
  );
};

// ---------------------------------------------------------------- 08. Data Governance
export const ProvenancePanel: React.FC<{ data: BedrockData }> = ({ data }) => (
  <Panel className="border-l-2 border-l-red-700 dark:border-l-red-500">
    <PanelTitle
      title="Bedrock data provenance"
      subtitle={`Real market data behind every figure on the real-data pages. Prices to ${niceDate(
        data.headline.data_as_of.stocks
      )}, foreign flows to ${data.headline.data_as_of.flows}, macro to ${data.headline.data_as_of.macro}.`}
      right={BEDROCK_TAG}
    />
    <ul className="text-xs text-slate-600 dark:text-slate-400 space-y-1.5 list-disc pl-4">
      {data.meta.sources.map((s) => (
        <li key={s}>{s}</li>
      ))}
    </ul>
    <div className="mt-4 grid gap-3 grid-cols-1 sm:grid-cols-3">
      <Kpi value={`${data.pricesMeta.rows.toLocaleString('en-US')}`} label={`real daily price rows loaded into Atlas (${data.pricesMeta.stocks} stocks, ${data.pricesMeta.start} to ${data.pricesMeta.end})`} />
      <Kpi value="99% / 96%" label="of volumes / closes from our OCR of NSE price lists match the published data on the overlap" />
      <Kpi value={data.headline.uses_rock_data ? 'Rock Data Plus' : 'Public sources'} label="data in use: Rock files dropped into data/rock/ replace these with no code changes" />
    </div>
    <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-3 leading-relaxed">
      {data.pricesMeta.note}
    </p>
  </Panel>
);
