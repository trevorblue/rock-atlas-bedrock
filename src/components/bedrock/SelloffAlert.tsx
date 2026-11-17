import React from 'react';
import { BedrockData } from '../../bedrock/types';
import { kes, niceMonth, num, pct } from '../../bedrock/data';
import { ColumnChart, DataTable, HowToRead, Kpi, KpiRow, ModelStrip, Note, PageHead, Panel, PanelTitle } from './kit';
import { MultiLineChart } from '../Charts';

export const SelloffAlert: React.FC<{ data: BedrockData }> = ({ data }) => {
  const { live, walkForward, significance, featureSets, calibration, thresholds } = data.selloff;
  const best = significance.find((s) => s.model === live.model) ?? significance[0];
  const highRisk = data.meta.settings.highRiskProb;

  const nextPeriod = (() => {
    const d = new Date(`${live.period}T00:00:00Z`);
    d.setUTCMonth(d.getUTCMonth() + 1);
    return niceMonth(d.toISOString().slice(0, 10));
  })();

  const flows = data.flows.filter((f) => f.period >= '2019-01-01');
  const outflowShare = flows.filter((f) => f.flow < 0).length / Math.max(1, flows.length);
  const netTotal = flows.reduce((a, f) => a + f.flow, 0);

  const heavyMonths = walkForward.filter((w) => w.actual === 1).length;
  const caught = walkForward.filter((w) => w.actual === 1 && w.xgboost >= highRisk).length;
  const recent = walkForward.slice(-15);
  const recentHeavy = recent.filter((w) => w.actual === 1).length;
  const recentCaught = recent.filter((w) => w.actual === 1 && w.xgboost >= highRisk).length;

  return (
    <div className="space-y-6">
      <PageHead
        eyebrow="Sell-off alert · Bedrock engine"
        question="Will foreign investors sell heavily next month?"
        title={
          live.signal === 'HIGH RISK'
            ? `High risk of heavy foreign selling in ${nextPeriod}`
            : `No warning for ${nextPeriod}`
        }
        subtitle={`The model reads ${pct(live.probability)}, against ${pct(
          live.base_rate
        )} in a normal month. "Heavy" means a net foreign outflow worse than ${kes(
          Math.abs(live.threshold_kes_m) * 1e6
        )} in one month, which is the worst quarter of months so far.`}
        badge={{ text: live.signal, tone: live.signal === 'HIGH RISK' ? 'alert' : 'quiet' }}
      />

      <HowToRead
        purpose="An early warning, so investors can cut risk before heavy foreign selling hits the thin stocks on the Market Depth page."
        points={[
          'HIGH RISK means heavy foreign selling next month is more likely than usual. NO CALL means no reliable signal.',
          'It never says "safe": out of sample, the quietest readings were followed by heavy selling almost as often as normal.',
          'Every month below was predicted using only data from before that date, then checked against what really happened.',
        ]}
      />

      <KpiRow>
        <Kpi value={pct(best.hit_rate)} label={`of its warnings were followed by heavy selling (${pct(best.base_rate)} by chance)`} alert />
        <Kpi value={`${caught} of ${heavyMonths}`} label="heavy-selling months it warned about in advance" />
        <Kpi value={best.p_value_vs_base < 0.01 ? '< 1%' : pct(best.p_value_vs_base)} label="chance this record is luck" />
        <Kpi value={String(walkForward.length)} label="months tested, each one unseen when predicted" />
      </KpiRow>

      <Note>
        the warnings are real, but it catches about half of all sell-offs and only {recentCaught} of the last{' '}
        {recentHeavy}. Weekly foreign-flow data from Rock Data Plus is the upgrade that would close that gap: about
        four times more data points and an alert that updates every week.
      </Note>

      <ModelStrip
        name="XGBoost classifier"
        facts={[
          `inputs: ${live.features_used.join(', ')} (net foreign flow this month and over three months)`,
          `trained on ${live.n_train} months of CMA data`,
          `tested on ${walkForward.length} months it had never seen`,
        ]}
      />

      <div className="grid gap-6 lg:grid-cols-2">
        <Panel>
          <PanelTitle
            title={`Foreigners were net sellers in ${pct(outflowShare)} of months since 2019`}
            subtitle={`Net foreign flow into NSE equities, KES bn a month. Dashed line: heavy selling (worse than ${kes(
              Math.abs(live.threshold_kes_m) * 1e6
            )})`}
          />
          <ColumnChart
            data={flows.map((f) => ({
              label: niceMonth(f.period),
              value: f.flow / 1000,
              tone: f.flow < 0 ? 'bad' : 'muted',
              hint: `${niceMonth(f.period)}: ${f.flow < 0 ? '−' : '+'}KES ${Math.abs(f.flow / 1000).toFixed(2)}bn`,
            }))}
            height={250}
            valueFormatter={(v) => `${v.toFixed(0)}bn`}
            width={560}
            reference={{ value: live.threshold_kes_m / 1000, label: 'heavy selling' }}
          />
          <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-2">
            Net KES {Math.abs(netTotal / 1000).toFixed(0)}bn out since 2019, straight through the 2025–26 rally: local
            investors carried it.
          </p>
        </Panel>

        <Panel>
          <PanelTitle
            title="Its warnings against what actually happened"
            subtitle={`Each month predicted using only earlier data. Warning line at ${pct(highRisk)}`}
          />
          <MultiLineChart
            dates={walkForward.map((w) => niceMonth(w.period))}
            series={[
              {
                id: 'p',
                label: 'Predicted chance of heavy selling',
                color: '#CDB171',
                values: walkForward.map((w) => w.xgboost * 100),
              },
              {
                id: 'actual',
                label: 'Heavy selling did follow (100 = yes)',
                color: '#D4654F',
                dashed: true,
                values: walkForward.map((w) => (w.actual === 1 ? 100 : 0)),
              },
            ]}
            height={250}
            valueFormatter={(v) => `${v.toFixed(0)}%`}
          />
        </Panel>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Panel>
          <PanelTitle
            title="Does it depend on where the warning line is drawn?"
            subtitle="No: the result holds anywhere between 35% and 50%"
          />
          <DataTable
            rows={thresholds.filter((t) => String(t.months).startsWith('all'))}
            columns={[
              { key: 'line', header: 'Warning line', align: 'right', render: (r) => pct(Number(r.high_risk_line)) },
              { key: 'calls', header: 'Warnings', align: 'right', render: (r) => String(r.calls) },
              { key: 'hits', header: 'Right', align: 'right', render: (r) => String(r.hits) },
              { key: 'rate', header: 'Hit rate', align: 'right', render: (r) => pct(Number(r.hit_rate)) },
              { key: 'p', header: 'p-value', align: 'right', render: (r) => num(Number(r.p_value_vs_base), 3) },
            ]}
          />
        </Panel>

        <Panel>
          <PanelTitle
            title="When it says X%, how often did it happen?"
            subtitle="Read the bands, not the exact number"
          />
          <DataTable
            rows={calibration}
            columns={[
              { key: 'bin', header: 'Predicted range', render: (r) => r.bin },
              { key: 'n', header: 'Months', align: 'right', render: (r) => String(r.n) },
              { key: 'pred', header: 'Avg predicted', align: 'right', render: (r) => pct(r.predicted) },
              { key: 'act', header: 'Actually happened', align: 'right', render: (r) => pct(r.actual) },
            ]}
            caption="The lowest band was followed by heavy selling about as often as the normal rate, which is why the alert never says 'low risk'."
          />
        </Panel>
      </div>

      {featureSets.length > 0 && (
        <Panel>
          <PanelTitle
            title="All six versions we tested, plus a no-model rule"
            subtitle="We report every version, not only the one that won. The simplest, foreign flows alone, is the only one that beats quoting the normal rate."
          />
          <DataTable
            rows={featureSets}
            columns={[
              { key: 'inputs', header: 'Inputs', render: (r) => String(r.inputs) },
              { key: 'model', header: 'Model', render: (r) => String(r.model) },
              { key: 'calls', header: 'Warnings', align: 'right', render: (r) => String(r.high_risk_calls) },
              { key: 'hits', header: 'Right', align: 'right', render: (r) => String(r.hits) },
              { key: 'rate', header: 'Hit rate', align: 'right', render: (r) => pct(Number(r.hit_rate)) },
              { key: 'p', header: 'p-value', align: 'right', render: (r) => num(Number(r.p_value_vs_base), 3) },
              {
                key: 'padj',
                header: 'p, adjusted for 6 tries',
                align: 'right',
                render: (r) => (r.p_adjusted_bonferroni === null ? '—' : num(Number(r.p_adjusted_bonferroni), 3)),
              },
            ]}
            caption="With about 140 monthly data points, adding macro inputs (exchange rate, interest rates, oil, US yields) made the model worse: more noise than signal. That is the case for Rock's weekly data."
          />
        </Panel>
      )}
    </div>
  );
};
