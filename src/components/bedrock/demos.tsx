/**
 * Bedrock's own demo pages. Every number on them is invented, to show what a feature would do once the data
 * exists. They are kept apart from the real-data pages and always carry the demo banner.
 */
import React, { useMemo, useState } from 'react';
import { BedrockData } from '../../bedrock/types';
import { kes, niceDate, niceMonth, num, pct, signedPct } from '../../bedrock/data';
import { ColumnChart, DataTable, DemoBanner, HBarChart, HowToRead, Kpi, KpiRow, ModelStrip, Note, PageHead, Panel, PanelTitle, Pill } from './kit';
import { MultiLineChart } from '../Charts';

// ---------------------------------------------------------------- Sell-off alert (demo): weekly flows
export const SelloffDemo: React.FC<{ data: BedrockData }> = ({ data }) => {
  const live = data.demo.selloffLive;
  const wf = data.demo.selloffWalkForward;
  const flows = data.demo.selloffFlows;
  const highRisk = data.meta.settings.highRiskProb;

  if (!live || wf.length === 0) {
    return (
      <Panel>
        <p className="text-sm text-slate-500">Demo data not exported. Run `python export_for_atlas.py`.</p>
      </Panel>
    );
  }

  const calls = wf.filter((w) => w.xgboost >= highRisk);
  const hits = calls.filter((w) => w.actual === 1).length;
  const heavy = wf.filter((w) => w.actual === 1).length;
  const recentFlows = flows.slice(-156);

  return (
    <div className="space-y-6">
      <DemoBanner>
        A copy of the real Sell-off Alert, run on made-up <strong>weekly</strong> foreign flows, to show what Rock's
        weekly data would add. The model code is the real one; the data, and therefore every number here, is invented.
        The real Sell-off Alert page is untouched.
      </DemoBanner>

      <PageHead
        eyebrow="Sell-off alert (demo)"
        question="What would the sell-off alert look like on weekly foreign flows, as Rock could provide?"
        title={`Demo: on weekly data the alert would update every week (${live.signal} this week)`}
        subtitle={`The model read ${pct(live.probability)} for next week, against ${pct(
          live.base_rate
        )} normally, and was tested on ${wf.length} weeks instead of 78 months.`}
        badge={{ text: live.signal, tone: live.signal === 'HIGH RISK' ? 'alert' : 'quiet' }}
      />

      <HowToRead
        purpose="Shows Rock the value of weekly foreign-flow data: the same tested model, updating five times as often and learning from five times as many periods."
        points={[
          'The model code is identical to the real alert; only the data is invented.',
          'The made-up data has built-in "exit waves", so the demo scores say nothing about real skill.',
          'What is real here is the mechanism: weekly data means weekly warnings.',
        ]}
      />

      <KpiRow>
        <Kpi value={String(wf.length)} label="test periods (weeks), against 78 months on real monthly data" alert />
        <Kpi value={`${hits} of ${calls.length}`} label="demo warnings followed by heavy selling" />
        <Kpi value={`${hits} of ${heavy}`} label="demo heavy-selling weeks warned about in advance" />
        <Kpi value="Weekly" label="how often the real alert could update with Rock's data, instead of monthly" />
      </KpiRow>

      <ModelStrip
        name="XGBoost classifier (the same code as the real alert)"
        facts={['inputs: net foreign flow this week and over three weeks', 'tested week by week on unseen data', 'data: synthetic']}
      />

      <div className="grid gap-6 lg:grid-cols-2">
        <Panel>
          <PanelTitle title="Demo: weekly net foreign flow" subtitle="Invented data, last three years · red = net selling" />
          <ColumnChart
            data={recentFlows.map((f) => ({
              label: niceMonth(f.period),
              value: f.flow / 1000,
              tone: f.flow < 0 ? 'bad' : 'muted',
            }))}
            height={240}
            width={560}
            valueFormatter={(v) => `${v.toFixed(1)}bn`}
          />
        </Panel>
        <Panel>
          <PanelTitle title="Demo: its warnings against what happened" subtitle="Each week predicted using only earlier weeks" />
          <MultiLineChart
            dates={wf.map((w) => w.period)}
            series={[
              { id: 'p', label: 'Predicted chance', color: '#CDB171', values: wf.map((w) => w.xgboost * 100) },
              {
                id: 'a',
                label: 'Heavy selling followed',
                color: '#D4654F',
                dashed: true,
                values: wf.map((w) => (w.actual === 1 ? 100 : 0)),
              },
            ]}
            height={240}
            valueFormatter={(v) => `${v.toFixed(0)}%`}
          />
        </Panel>
      </div>
    </div>
  );
};

// ---------------------------------------------------------------- Opportunities (demo): radar + financials
export const OpportunitiesDemo: React.FC<{ data: BedrockData }> = ({ data }) => {
  const rowsAll = data.demo.opportunities as Array<Record<string, number | string | boolean>>;
  const ok = rowsAll.filter((r) => Boolean(r.exit_ok));
  const blocked = rowsAll.filter((r) => !r.exit_ok);
  const changed = useMemo(() => {
    const byFull = [...rowsAll].sort((a, b) => Number(b.score_full) - Number(a.score_full)).map((r) => String(r.company));
    const byPrice = [...rowsAll].sort((a, b) => Number(b.score_price_only) - Number(a.score_price_only)).map((r) => String(r.company));
    return byFull.filter((c, i) => byPrice[i] !== c).length;
  }, [rowsAll]);

  return (
    <div className="space-y-6">
      <DemoBanner>
        A copy of the real Opportunity Radar for <strong>fictional companies</strong>, with value and quality from
        invented financial statements added to the score. Nothing here is real. The real Opportunity Radar page is
        untouched.
      </DemoBanner>

      <PageHead
        eyebrow="Opportunities (demo)"
        question="What would the Opportunity Radar look like with company financials added?"
        title={`Demo: with financials, ${ok.length} of ${rowsAll.length} companies pass the exit check and are ranked on five ingredients`}
        subtitle="Momentum, stability and resilience, as on the real page, plus value and quality from financial statements. The exit check still comes first."
      />

      <HowToRead
        purpose="Shows Rock what company financials would add: a score that rates the business, not only the share price."
        points={[
          'Everything here is made-up data for fictional companies.',
          'Full score = momentum, stability, resilience (available today) plus value and quality (needs financials).',
          'The exit check is applied exactly as on the real page: a company that cannot be sold is not an opportunity.',
        ]}
      />

      <KpiRow>
        <Kpi value={`${ok.length} of ${rowsAll.length}`} label="demo companies pass the exit check (KES 10m in 20 days)" />
        <Kpi value={`${changed} of ${rowsAll.length}`} label="demo companies change rank once financials are added" alert />
        <Kpi value={String(ok[0]?.company ?? '—')} label="top demo opportunity you can get out of" />
        <Kpi value="5" label="ingredients in the full score, against 3 on real data today" />
      </KpiRow>

      <ModelStrip
        name="Opportunity score with financials (demo)"
        facts={['five equal ingredients', 'the same exit check as the real radar', 'not tested: needs real data']}
      />

      <div className="grid gap-6 lg:grid-cols-2">
        <Panel>
          <PanelTitle title="Demo: top opportunities you can get out of" subtitle="Fictional companies · full five-part score" />
          <HBarChart
            data={ok.slice(0, 8).map((r) => ({
              label: String(r.company),
              value: Number(r.score_full),
              display: num(Number(r.score_full), 2),
              tone: 'accent',
            }))}
            maxValue={1}
            width={560}
          />
        </Panel>
        <Panel>
          <PanelTitle title="Demo: good on paper, but you cannot get out" subtitle="Fictional companies · trading days to sell KES 10m" />
          <HBarChart
            data={blocked.slice(0, 6).map((r) => ({
              label: String(r.company),
              value: Number(r.days_to_exit_10m),
              display: `${Math.round(Number(r.days_to_exit_10m)).toLocaleString('en-US')} days`,
              tone: 'bad',
            }))}
            width={560}
          />
        </Panel>
      </div>

      <Panel>
        <PanelTitle title="Demo company detail" />
        <DataTable
          rows={rowsAll}
          columns={[
            { key: 'c', header: 'Company (demo)', render: (r) => <span className="font-medium">{String(r.company)}</span> },
            { key: 'sec', header: 'Sector', render: (r) => String(r.sector) },
            { key: 'sf', header: 'Full score', align: 'right', render: (r) => num(Number(r.score_full), 2) },
            { key: 'sp', header: 'Price-only score', align: 'right', render: (r) => num(Number(r.score_price_only), 2) },
            { key: 'v', header: 'Value', align: 'right', render: (r) => num(Number(r.value_score), 2) },
            { key: 'q', header: 'Quality', align: 'right', render: (r) => num(Number(r.quality_score), 2) },
            { key: 'd', header: 'Days to sell KES 10m', align: 'right', render: (r) => num(Number(r.days_to_exit_10m), 0) },
            { key: 'e', header: 'Exit check', render: (r) => <Pill text={r.exit_ok ? 'passes' : 'fails'} tone={r.exit_ok ? 'good' : 'bad'} /> },
          ]}
        />
      </Panel>
    </div>
  );
};

// ---------------------------------------------------------------- Fundamentals (demo)
export const FundamentalsDemo: React.FC<{ data: BedrockData }> = ({ data }) => {
  const rowsAll = data.demo.fundamentals as Array<Record<string, number | string | boolean>>;
  const passing = rowsAll.filter((r) => Boolean(r.exit_ok));

  return (
    <div className="space-y-6">
      <DemoBanner>
        Fictional companies and invented numbers, made only to show how a value-and-quality screen would work once
        real company financials are added (for example from Rock Data Plus). Nothing here is real, and no other page
        uses it.
      </DemoBanner>

      <PageHead
        eyebrow="Fundamentals (demo)"
        question="How would a value-and-quality screen work once company financials are added?"
        title="Demo: rating the business, not only the share price"
        subtitle="Each company is scored on value (price to earnings, dividend yield) and quality (return on equity, debt, earnings growth), and must still pass the same exit check."
      />

      <HowToRead
        purpose="Shows judges and Rock what the platform will do once company financials are available for NSE stocks."
        points={[
          'Everything here is made-up data for fictional companies.',
          'Value means a cheap price relative to earnings and dividends; quality means profitable, low debt and growing.',
          'Grey bars fail the exit check, even in the demo.',
        ]}
      />

      <KpiRow>
        <Kpi value={String(rowsAll.length)} label="fictional demo companies" />
        <Kpi value={String(passing.length)} label="pass the exit check (demo)" />
        <Kpi value={String(rowsAll[0]?.company ?? '—')} label="highest demo score" />
        <Kpi value="0" label="real figures on this page" alert />
      </KpiRow>

      <ModelStrip
        name="Value + quality score (demo)"
        facts={['equal weights across five measures', 'the same exit check as the radar', 'not tested: needs real data']}
      />

      <div className="grid gap-6 lg:grid-cols-2">
        <Panel>
          <PanelTitle title="Demo: value + quality score" subtitle="Fictional companies · blue passes the exit check" />
          <HBarChart
            data={rowsAll.map((r) => ({
              label: String(r.company),
              value: Number(r.score),
              display: num(Number(r.score), 2),
              tone: r.exit_ok ? 'accent' : 'muted',
            }))}
            maxValue={1}
            width={560}
          />
        </Panel>
        <Panel>
          <PanelTitle title="Demo financial detail" />
          <DataTable
            rows={rowsAll}
            maxHeight="360px"
            columns={[
              { key: 'c', header: 'Company (demo)', render: (r) => String(r.company) },
              { key: 'pe', header: 'P/E', align: 'right', render: (r) => num(Number(r.pe_ratio), 1) },
              { key: 'dy', header: 'Dividend yield', align: 'right', render: (r) => pct(Number(r.dividend_yield), 1) },
              { key: 'roe', header: 'Return on equity', align: 'right', render: (r) => pct(Number(r.return_on_equity), 1) },
              { key: 'de', header: 'Debt / equity', align: 'right', render: (r) => num(Number(r.debt_to_equity), 2) },
              { key: 'g', header: 'Earnings growth', align: 'right', render: (r) => signedPct(Number(r.earnings_growth)) },
            ]}
          />
        </Panel>
      </div>

      <Note label="Why this page exists">
        with real financials this becomes the fourth and fifth ingredient of the Opportunity Radar score, so the
        platform can rate the business as well as the share price. See the Market-Ready page for the data it needs.
      </Note>
    </div>
  );
};

// ---------------------------------------------------------------- Foreign flows by stock (demo)
export const ForeignFlowsDemo: React.FC<{ data: BedrockData }> = ({ data }) => {
  const flows = data.demo.foreignFlows;
  const companies = useMemo(() => Array.from(new Set(flows.map((f) => f.company))).sort(), [flows]);
  const [pick, setPick] = useState(companies[0] ?? '');

  const alert = useMemo(() => {
    const dates = Array.from(new Set(flows.map((f) => f.date))).sort();
    const cutoff = dates[Math.max(0, dates.length - 10)];
    const last = flows.filter((f) => f.date >= cutoff);
    const byCompany = new Map<string, { net: number; turnover: number }>();
    for (const f of last) {
      const cur = byCompany.get(f.company) ?? { net: 0, turnover: 0 };
      cur.net += f.net_foreign_kes;
      cur.turnover += f.turnover_kes;
      byCompany.set(f.company, cur);
    }
    return Array.from(byCompany.entries())
      .map(([company, v]) => ({ company, share: v.turnover ? v.net / v.turnover : 0 }))
      .sort((a, b) => a.share - b.share);
  }, [flows]);

  const flagged = alert.filter((a) => a.share <= -0.15).length;
  const series = flows.filter((f) => f.company === pick);

  return (
    <div className="space-y-6">
      <DemoBanner>
        Fictional companies and invented numbers, made only to show what Bedrock would do with daily foreign buying
        and selling for each stock — the number one upgrade on the Market-Ready page. Nothing here is real.
      </DemoBanner>

      <PageHead
        eyebrow="Foreign flows by stock (demo)"
        question="What would a daily, stock-by-stock foreign selling alert look like with Rock's data?"
        title="Demo: with per-stock data, the sell-off alert becomes daily and stock by stock"
        subtitle="Today Bedrock sees foreign selling only as one monthly total for the whole market. With Rock's per-stock data it could warn about each stock, every day."
      />

      <HowToRead
        purpose="Shows Rock the single most valuable data upgrade, in the form it would actually take on screen."
        points={[
          'Everything here is made-up data for fictional companies.',
          'Net foreign flow is foreign buying minus foreign selling; red bars mean foreigners sold more than they bought that day.',
          'The demo rule flags a company when foreigners were net sellers of more than 15% of its trading over the last 10 days. It is not tested.',
        ]}
      />

      <KpiRow>
        <Kpi value={String(companies.length)} label="fictional demo companies, 60 trading days" />
        <Kpi value={String(flagged)} label="flagged by the demo rule (net selling over 15% of trading in 10 days)" alert />
        <Kpi value="Daily" label="how often the real alert could update with Rock's data" />
        <Kpi value="Per stock" label="instead of one number for the whole market" />
      </KpiRow>

      <ModelStrip
        name="Per-stock foreign selling rule (demo)"
        facts={['net foreign selling over the last 10 days as a share of trading', 'not tested: needs real data']}
      />

      <div className="grid gap-6 lg:grid-cols-5">
        <Panel className="lg:col-span-3">
          <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
            <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">Demo: daily net foreign flow</h3>
            <select
              value={pick}
              onChange={(e) => setPick(e.target.value)}
              className="px-2 py-1 text-xs border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-800 dark:text-slate-200"
            >
              {companies.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </div>
          <ColumnChart
            data={series.map((f) => ({
              label: niceDate(f.date).slice(0, 6),
              value: f.net_foreign_kes / 1e6,
              tone: f.net_foreign_kes < 0 ? 'bad' : 'accent',
              hint: `${niceDate(f.date)}: ${kes(f.net_foreign_kes)} (demo)`,
            }))}
            height={240}
            valueFormatter={(v) => `${v.toFixed(0)}m`}
          />
        </Panel>

        <Panel className="lg:col-span-2">
          <PanelTitle title="Demo alert, last 10 trading days" />
          <DataTable
            rows={alert}
            maxHeight="300px"
            columns={[
              { key: 'c', header: 'Company (demo)', render: (r) => r.company },
              { key: 's', header: 'Net foreign flow, share of trading', align: 'right', render: (r) => signedPct(r.share) },
              {
                key: 'sig',
                header: 'Demo signal',
                render: (r) => <Pill text={r.share <= -0.15 ? 'HIGH RISK (demo)' : 'NO CALL (demo)'} tone={r.share <= -0.15 ? 'bad' : 'muted'} />,
              },
            ]}
            caption="With real per-stock data this rule would be replaced by a model trained and tested the same way as the other pages, and joined to the exit check and the stress test."
          />
        </Panel>
      </div>
    </div>
  );
};
