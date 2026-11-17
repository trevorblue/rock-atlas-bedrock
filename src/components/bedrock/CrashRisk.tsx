import React from 'react';
import { BedrockData } from '../../bedrock/types';
import { niceDate, num, pct, shortName, signedPct } from '../../bedrock/data';
import { ColumnChart, DataTable, HBarChart, HowToRead, Kpi, KpiRow, ModelStrip, Note, PageHead, Panel, PanelTitle } from './kit';

export const CrashRisk: React.FC<{ data: BedrockData }> = ({ data }) => {
  const { summary, live, deciles, compare, byYear, robust, importance, garch } = data.crash;
  const drop = Math.abs(summary.crash_drop);
  const garchRow = compare.find((c) => c.model.includes('GARCH forecast'));
  const liveRow = compare[0];
  const ruleRow = compare.find((c) => c.model.includes('most volatile'));

  return (
    <div className="space-y-6">
      <PageHead
        eyebrow="Crash risk · Bedrock engine"
        question={`Which stocks are most likely to fall ${pct(drop)} or more next month?`}
        title="The stocks ranked riskiest crash twice as often as average"
        subtitle={`Every month each stock is ranked by its chance of falling ${pct(drop)} or more over the next ${
          summary.horizon_days
        } trading days. Trained year by year on earlier data only and tested on ${summary.n_test.toLocaleString(
          'en-US'
        )} stock-months it had never seen (${summary.first_test_year}–${new Date(summary.as_of).getFullYear()}).`}
      />

      <HowToRead
        purpose="A stock-by-stock watch list: which holdings to watch or trim, and which stocks a stress scenario would hurt most."
        points={[
          'Risk group 10 is the riskiest tenth of stocks that month; group 1 is the safest tenth.',
          'The score is a ranking, not an exact probability, so the table shows each stock\'s group and how often that group actually crashed.',
          'GARCH, a standard financial time-series model, runs beside it as a challenger (below).',
        ]}
      />

      <KpiRow>
        <Kpi value={pct(summary.top10_rate, 1)} label="of the riskiest 10% crashed the next month" alert />
        <Kpi value={pct(summary.base_rate, 1)} label="average crash rate across all stocks" />
        <Kpi value={pct(summary.safest10_rate, 1)} label="of the safest 10% crashed" />
        <Kpi value={pct(summary.rule_top10_rate, 1)} label="for a simple rule: the most volatile 10%" />
      </KpiRow>

      <Note>
        crash risk on the NSE is genuinely predictable (this is very unlikely to be luck), but it comes mostly from
        volatility: a simple "most volatile" rule gets {pct(summary.rule_top10_rate, 1)}. Per-stock foreign trading and
        order-book data from Rock are what would let machine learning add more.
      </Note>

      <ModelStrip
        name="XGBoost classifier"
        facts={[
          '14 inputs: momentum, volatility, liquidity, spikes, market, foreign flows',
          'retrained for each test year on earlier data only',
          `${summary.n_test.toLocaleString('en-US')} out-of-sample stock-months`,
        ]}
      />

      <div className="grid gap-6 lg:grid-cols-2">
        <Panel>
          <PanelTitle title={`Riskiest stocks on ${niceDate(summary.as_of)}`} subtitle="Model risk score, highest first" />
          <HBarChart
            data={live.slice(0, 12).map((r) => ({
              label: shortName(r.name),
              value: r.crash_prob,
              display: pct(r.crash_prob, 1),
              tone: 'bad',
              hint: `${shortName(r.name)}: risk score ${pct(r.crash_prob, 1)}, group ${r.risk_decile} of 10, which crashed ${pct(
                r.group_crash_rate,
                1
              )} of the time in testing`,
            }))}
            width={560}
            labelWidth={210}
          />
        </Panel>

        <Panel>
          <PanelTitle
            title="The higher the risk group, the more often stocks crashed"
            subtitle={`Share that fell ${pct(drop)}+ in the next month, by monthly risk group. Test years only.`}
          />
          <ColumnChart
            data={deciles.map((d) => ({
              label: d.decile === 1 ? '1 safest' : d.decile === 10 ? '10 riskiest' : String(d.decile),
              value: d.crash_rate * 100,
              tone: d.decile === 10 ? 'bad' : 'muted',
              hint: `Risk group ${d.decile}: ${pct(d.crash_rate, 1)} crashed`,
            }))}
            height={250}
            valueFormatter={(v) => `${v.toFixed(0)}%`}
            showEvery={1}
            width={560}
            reference={{ value: summary.base_rate * 100, label: `average ${pct(summary.base_rate, 1)}` }}
          />
        </Panel>
      </div>

      {garch && garchRow && (
        <Panel className="border-l-2 border-l-amber-500 dark:border-l-amber-400">
          <PanelTitle
            title="New stochastic model: GARCH volatility forecast"
            subtitle="Volatility is the strongest crash signal. GARCH, a standard financial time-series model, forecasts each stock's volatility for the next four weeks, knowing that calm and stormy spells come in runs. Refitted every year on earlier data only, and tested exactly like everything else."
          />
          <div className="grid gap-3 grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 mb-4">
            <Kpi value={pct(garchRow.top10_crash_rate, 1)} label="of the 10% GARCH expected to be most volatile crashed the next month" alert />
            <Kpi value={pct(liveRow.top10_crash_rate, 1)} label="for the live model's riskiest 10%" />
            <Kpi value={pct(ruleRow ? ruleRow.top10_crash_rate : 0, 1)} label="for the simple 60-day volatility rule" />
            <Kpi value={pct(1 - garch.failed_or_explosive / garch.fits)} label="of stock-years where weekly GARCH fitted" />
          </div>
          <Note>
            GARCH ranked crash risk best of all six methods tested, but the gain could still be chance: its ranking
            score is {num(garch.auc_gap_vs_last60_rule.gap, 3)} against the 60-day rule, with a likely range of{' '}
            {num(garch.auc_gap_vs_last60_rule.ci_low, 3)} to {num(garch.auc_gap_vs_last60_rule.ci_high, 3)}, which
            includes zero. So it runs as a <strong>challenger</strong> beside the live model and would replace it only
            after it kept winning on new months. On daily data GARCH broke down, because NSE prices move in small
            steps and many days have no trades at all, so it uses weekly returns.
          </Note>
          <div className="mt-4">
            <ModelStrip
              name="GARCH(1,1) on weekly returns"
              facts={[
                'Student-t daily version reported but not used',
                `${garch.fits} yearly fits`,
                `${garch.n.toLocaleString('en-US')} volatility forecasts tested`,
              ]}
            />
          </div>
        </Panel>
      )}

      <Panel>
        <PanelTitle title={`All ${live.length} stocks, riskiest first`} />
        <DataTable
          rows={live}
          maxHeight="420px"
          columns={[
            { key: 'rank', header: '#', align: 'right', width: '46px', render: (r) => String(r.risk_rank) },
            { key: 'name', header: 'Company', render: (r) => <span className="font-medium">{shortName(r.name)}</span> },
            { key: 'score', header: 'Risk score', align: 'right', render: (r) => pct(r.crash_prob, 1) },
            { key: 'group', header: 'Risk group', align: 'right', render: (r) => `${r.risk_decile} of 10` },
            { key: 'grate', header: 'Its group crashed', align: 'right', render: (r) => pct(r.group_crash_rate, 1) },
            { key: 'mom', header: 'Last 3 months', align: 'right', render: (r) => signedPct(r.mom_3m) },
            { key: 'dd', header: 'Below 1-year high', align: 'right', render: (r) => signedPct(r.dd_1y) },
          ]}
          caption="Raw scores run higher than the crash rates that followed, so read the risk group and the rate that group actually produced in testing."
        />
      </Panel>

      <div className="grid gap-6 lg:grid-cols-2">
        <Panel>
          <PanelTitle title="Every method we tested, on the same unseen months" />
          <DataTable
            rows={compare}
            columns={[
              { key: 'm', header: 'Method', render: (r) => r.model },
              { key: 'auc', header: 'Ranking score', align: 'right', render: (r) => num(r.auc, 3) },
              { key: 'rate', header: 'Riskiest 10% crashed', align: 'right', render: (r) => pct(r.top10_crash_rate, 1) },
              { key: 'lift', header: '× average', align: 'right', render: (r) => `${num(r.lift, 1)}×` },
              { key: 'p', header: 'p-value', align: 'right', render: (r) => (r.p_value_top10 < 0.0001 ? '< 0.0001' : num(r.p_value_top10, 4)) },
            ]}
            caption="A ranking score of 0.5 is random and 1.0 is perfect, so 0.6 is modest skill."
          />
        </Panel>

        <Panel>
          <PanelTitle title="Year by year, and under other crash definitions" />
          <DataTable
            rows={byYear}
            maxHeight="200px"
            columns={[
              { key: 'y', header: 'Year', align: 'right', render: (r) => String(r.year) },
              { key: 'n', header: 'Stock-months', align: 'right', render: (r) => r.stock_months.toLocaleString('en-US') },
              { key: 'c', header: 'Crashes', align: 'right', render: (r) => String(r.crashes) },
              { key: 'base', header: 'Average', align: 'right', render: (r) => pct(r.base_rate, 1) },
              { key: 'top', header: 'Riskiest 10% crashed', align: 'right', render: (r) => pct(r.top10_crash_rate, 1) },
            ]}
          />
          <div className="mt-4">
            <DataTable
              rows={robust}
              columns={[
                { key: 'd', header: 'Crash means', render: (r) => r.crash_definition },
                { key: 'b', header: 'Average', align: 'right', render: (r) => pct(r.base_rate, 1) },
                { key: 'am', header: 'Model ranking', align: 'right', render: (r) => num(r.auc_model, 3) },
                { key: 'av', header: 'Volatility rule', align: 'right', render: (r) => num(r.auc_volatility, 3) },
              ]}
              caption="Same picture at −10% and −20%, so the finding does not depend on where 'crash' is drawn."
            />
          </div>
        </Panel>
      </div>

      <Panel>
        <PanelTitle title="What the model leans on" subtitle="How much each input contributed, across all test years" />
        <HBarChart
          data={importance.slice(0, 14).map((f) => ({
            label: f.label ?? f.feature,
            value: f.importance,
            display: pct(f.importance, 1),
            tone: 'accent',
          }))}
          labelWidth={240}
        />
      </Panel>
    </div>
  );
};
