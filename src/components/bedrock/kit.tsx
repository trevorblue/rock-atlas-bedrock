/**
 * Shared building blocks for the Bedrock pages, written in ROCK ATLAS's visual language
 * (slate palette, square corners, bordered panels, mono tabular figures, dark-mode aware).
 */
import React from 'react';

// ---------------------------------------------------------------- layout
export const Panel: React.FC<{ children: React.ReactNode; className?: string }> = ({ children, className = '' }) => (
  <div className={`border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-6 ${className}`}>
    {children}
  </div>
);

export const PanelTitle: React.FC<{ title: string; subtitle?: string; right?: React.ReactNode }> = ({
  title,
  subtitle,
  right,
}) => (
  <div className="flex flex-wrap items-start justify-between gap-4 mb-4">
    <div>
      <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">{title}</h3>
      {subtitle && <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5 max-w-3xl">{subtitle}</p>}
    </div>
    {right}
  </div>
);

/** The question this page answers, then the headline finding. Every Bedrock page opens with one. */
export const PageHead: React.FC<{
  eyebrow: string;
  question: string;
  title: string;
  subtitle?: string;
  badge?: { text: string; tone: 'alert' | 'quiet' };
}> = ({ eyebrow, question, title, subtitle, badge }) => (
  <div className="space-y-3">
    <div className="border-l-2 border-red-700 dark:border-red-500 pl-3 py-1">
      <div className="text-[10px] font-mono font-semibold tracking-widest text-slate-500 dark:text-slate-400 uppercase">
        This page answers
      </div>
      <div className="text-sm text-slate-900 dark:text-slate-100 mt-0.5">{question}</div>
    </div>
    <div>
      <div className="flex flex-wrap items-center gap-3">
        <span className="text-[10px] font-mono font-semibold tracking-widest text-red-700 dark:text-red-400 uppercase">
          {eyebrow}
        </span>
        {badge && (
          <span
            className={`px-2.5 py-0.5 text-[10px] font-mono font-bold tracking-wider ${
              badge.tone === 'alert'
                ? 'bg-red-700 dark:bg-red-600 text-white'
                : 'bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-200'
            }`}
          >
            {badge.text}
          </span>
        )}
      </div>
      <h2 className="font-display text-xl md:text-2xl font-semibold text-slate-900 dark:text-slate-100 mt-1.5 max-w-4xl leading-snug">
        {title}
      </h2>
      {subtitle && <p className="text-xs text-slate-600 dark:text-slate-400 mt-1.5 max-w-3xl">{subtitle}</p>}
    </div>
  </div>
);

/** A short "what this is for / how to read it" block, collapsed by default. */
export const HowToRead: React.FC<{ purpose: string; points: string[] }> = ({ purpose, points }) => (
  <details className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900">
    <summary className="cursor-pointer px-4 py-2.5 text-xs font-medium text-slate-700 dark:text-slate-300 select-none">
      New here? What this page is for, and how to read it
    </summary>
    <div className="px-4 pb-4 pt-1 text-xs text-slate-600 dark:text-slate-400 space-y-2">
      <p>
        <span className="font-semibold text-slate-800 dark:text-slate-200">What it's for: </span>
        {purpose}
      </p>
      <ul className="list-disc pl-4 space-y-1">
        {points.map((p) => (
          <li key={p}>{p}</li>
        ))}
      </ul>
    </div>
  </details>
);

// ---------------------------------------------------------------- numbers
export const Kpi: React.FC<{ value: string; label: string; alert?: boolean }> = ({ value, label, alert }) => (
  <div className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-4">
    <div
      className={`font-display text-2xl font-semibold tabular-nums leading-tight ${
        alert ? 'text-red-700 dark:text-red-400' : 'text-slate-900 dark:text-slate-100'
      }`}
    >
      {value}
    </div>
    <div className="text-xs text-slate-500 dark:text-slate-400 mt-1.5 leading-snug">{label}</div>
  </div>
);

export const KpiRow: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <div className="grid gap-3 grid-cols-1 sm:grid-cols-2 lg:grid-cols-4">{children}</div>
);

/** Names the model behind a page, what it was fed and how it was tested. */
export const ModelStrip: React.FC<{ name: string; facts: string[] }> = ({ name, facts }) => (
  <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5 border-y border-slate-200 dark:border-slate-800 py-2.5 text-xs text-slate-500 dark:text-slate-400">
    <span className="bg-slate-900 dark:bg-slate-100 text-white dark:text-slate-900 px-2 py-0.5 text-[10px] font-mono font-bold tracking-wider">
      MODEL
    </span>
    <span className="font-semibold text-slate-800 dark:text-slate-200">{name}</span>
    {facts.map((f) => (
      <span key={f}>· {f}</span>
    ))}
  </div>
);

export const Note: React.FC<{ label?: string; children: React.ReactNode }> = ({ label = 'How sure', children }) => (
  <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
    <span className="font-semibold text-slate-900 dark:text-slate-100">{label}: </span>
    {children}
  </p>
);

export type PillTone = 'good' | 'warn' | 'bad' | 'muted';

export const Pill: React.FC<{ text: string; tone: PillTone }> = ({ text, tone }) => {
  const cls: Record<PillTone, string> = {
    good: 'bg-teal-50 text-teal-800 dark:bg-teal-950/50 dark:text-teal-300',
    warn: 'bg-amber-50 text-amber-800 dark:bg-amber-950/50 dark:text-amber-300',
    bad: 'bg-red-50 text-red-800 dark:bg-red-950/50 dark:text-red-300',
    muted: 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300',
  };
  return <span className={`inline-block px-2 py-0.5 text-[11px] font-medium whitespace-nowrap ${cls[tone]}`}>{text}</span>;
};

/** The red-dashed banner that marks every page built on invented numbers. */
export const DemoBanner: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <div className="border-2 border-dashed border-amber-500 dark:border-amber-600 bg-amber-50/70 dark:bg-amber-950/20 px-4 py-3 text-xs text-amber-950 dark:text-amber-200 leading-relaxed">
    <span className="font-mono font-bold tracking-wider">DEMO · SYNTHETIC DATA. </span>
    {children}
  </div>
);

// ---------------------------------------------------------------- tables
export interface Column<T> {
  key: string;
  header: string;
  align?: 'left' | 'right';
  width?: string;
  render: (row: T) => React.ReactNode;
}

export function DataTable<T>({
  rows,
  columns,
  maxHeight,
  caption,
}: {
  rows: T[];
  columns: Array<Column<T>>;
  maxHeight?: string;
  caption?: string;
}): React.ReactElement {
  return (
    <div>
      <div className="overflow-auto" style={maxHeight ? { maxHeight } : undefined}>
        <table className="w-full text-xs border-collapse">
          <thead className="sticky top-0 bg-slate-50 dark:bg-slate-800/90 backdrop-blur">
            <tr>
              {columns.map((c) => (
                <th
                  key={c.key}
                  style={c.width ? { width: c.width } : undefined}
                  className={`px-3 py-2 font-medium text-slate-500 dark:text-slate-400 border-b border-slate-200 dark:border-slate-700 whitespace-nowrap ${
                    c.align === 'right' ? 'text-right' : 'text-left'
                  }`}
                >
                  {c.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (
              <tr key={i} className="border-b border-slate-100 dark:border-slate-800/70 last:border-0">
                {columns.map((c) => (
                  <td
                    key={c.key}
                    className={`px-3 py-2 text-slate-700 dark:text-slate-300 align-top ${
                      c.align === 'right' ? 'text-right tabular-nums font-mono' : ''
                    }`}
                  >
                    {c.render(row)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {caption && <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-2 leading-relaxed">{caption}</p>}
    </div>
  );
}

// ---------------------------------------------------------------- charts
export interface HBarDatum {
  label: string;
  value: number;
  display?: string;
  tone?: 'accent' | 'muted' | 'good' | 'warn' | 'bad';
  hint?: string;
}

const TONE_FILL: Record<string, string> = {
  accent: '#1D4ED8',
  muted: '#94A3B8',
  good: '#0F766E',
  warn: '#D97706',
  bad: '#DC2626',
};

/** Horizontal bars with the name on the left and the value at the end: rankings, impacts, scores. */
export const HBarChart: React.FC<{
  data: HBarDatum[];
  maxValue?: number;
  labelWidth?: number;
  rowHeight?: number;
  reference?: { value: number; label: string };
  /** viewBox width. Use a smaller value in half-width panels so the labels do not scale down. */
  width?: number;
}> = ({ data, maxValue, labelWidth = 190, rowHeight = 26, reference, width = 820 }) => {
  if (data.length === 0) return null;
  const padRight = 70;
  const plotW = width - labelWidth - padRight;
  const height = data.length * rowHeight + (reference ? 24 : 12);
  const max = maxValue ?? Math.max(...data.map((d) => Math.abs(d.value)), 1e-9);
  const w = (v: number) => Math.max(1, (Math.abs(v) / max) * plotW);

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-auto select-none">
      {reference && (
        <g>
          <line
            x1={labelWidth + w(reference.value)}
            x2={labelWidth + w(reference.value)}
            y1={4}
            y2={height - 8}
            className="stroke-slate-400 dark:stroke-slate-500"
            strokeWidth={1.25}
            strokeDasharray="4 3"
          />
          <text
            x={labelWidth + w(reference.value)}
            y={height - 1}
            textAnchor="middle"
            className="fill-slate-500 dark:fill-slate-400 text-[10px] font-mono"
          >
            {reference.label}
          </text>
        </g>
      )}
      {data.map((d, i) => {
        const y = i * rowHeight + 6;
        const bw = w(d.value);
        return (
          <g key={d.label}>
            <title>{d.hint ?? `${d.label}: ${d.display ?? d.value}`}</title>
            <text
              x={labelWidth - 8}
              y={y + rowHeight / 2 - 1}
              textAnchor="end"
              dominantBaseline="middle"
              className="fill-slate-700 dark:fill-slate-300 text-[11px]"
            >
              {d.label}
            </text>
            <rect
              x={labelWidth}
              y={y}
              width={bw}
              height={rowHeight - 10}
              fill={TONE_FILL[d.tone ?? 'accent']}
              opacity={0.85}
            />
            <text
              x={labelWidth + bw + 6}
              y={y + (rowHeight - 10) / 2}
              dominantBaseline="middle"
              className="fill-slate-700 dark:fill-slate-300 text-[10px] font-mono tabular-nums"
            >
              {d.display ?? d.value.toFixed(2)}
            </text>
          </g>
        );
      })}
    </svg>
  );
};

/** Vertical columns about a zero line: monthly flows, crash rate by risk group. */
export const ColumnChart: React.FC<{
  data: Array<{ label: string; value: number; tone?: 'accent' | 'muted' | 'good' | 'warn' | 'bad'; hint?: string }>;
  height?: number;
  valueFormatter?: (v: number) => string;
  showEvery?: number;
  reference?: { value: number; label: string };
  barLabels?: boolean;
  /** viewBox width. Use a smaller value in half-width panels so the labels do not scale down. */
  width?: number;
}> = ({ data, height = 240, valueFormatter = (v) => v.toFixed(1), showEvery, reference, barLabels, width = 820 }) => {
  if (data.length === 0) return null;
  const padLeft = 56;
  const padRight = 16;
  const padTop = barLabels ? 22 : 12;
  const padBottom = 28;
  const plotW = width - padLeft - padRight;
  const plotH = height - padTop - padBottom;

  const values = data.map((d) => d.value);
  const refV = reference?.value;
  const hi = Math.max(0, ...values, ...(refV !== undefined ? [refV] : []));
  const lo = Math.min(0, ...values, ...(refV !== undefined ? [refV] : []));
  const span = hi - lo || 1;
  const y = (v: number) => padTop + ((hi - v) / span) * plotH;
  const band = plotW / data.length;
  const bw = Math.max(1.2, band * 0.7);
  const every = showEvery ?? Math.max(1, Math.ceil(data.length / 10));

  const ticks = [hi, lo + span * 0.5, lo].filter((t, i, a) => a.indexOf(t) === i);

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-auto select-none">
      {ticks.map((t, i) => (
        <g key={i}>
          <line
            x1={padLeft}
            x2={width - padRight}
            y1={y(t)}
            y2={y(t)}
            className="stroke-slate-200 dark:stroke-slate-800"
            strokeWidth={1}
          />
          <text
            x={padLeft - 8}
            y={y(t) + 4}
            textAnchor="end"
            className="fill-slate-500 dark:fill-slate-400 text-[10px] font-mono tabular-nums"
          >
            {valueFormatter(t)}
          </text>
        </g>
      ))}
      <line x1={padLeft} x2={width - padRight} y1={y(0)} y2={y(0)} className="stroke-slate-400 dark:stroke-slate-600" />

      {reference !== undefined && (
        <g>
          <line
            x1={padLeft}
            x2={width - padRight}
            y1={y(reference.value)}
            y2={y(reference.value)}
            className="stroke-slate-500 dark:stroke-slate-400"
            strokeWidth={1.25}
            strokeDasharray="4 3"
          />
          <text x={padLeft + 4} y={y(reference.value) - 4} className="fill-slate-500 dark:fill-slate-400 text-[10px] font-mono">
            {reference.label}
          </text>
        </g>
      )}

      {data.map((d, i) => {
        const x = padLeft + i * band + (band - bw) / 2;
        const top = Math.min(y(d.value), y(0));
        const h = Math.max(1, Math.abs(y(d.value) - y(0)));
        return (
          <g key={`${d.label}-${i}`}>
            <title>{d.hint ?? `${d.label}: ${valueFormatter(d.value)}`}</title>
            <rect x={x} y={top} width={bw} height={h} fill={TONE_FILL[d.tone ?? 'accent']} opacity={0.85} />
            {barLabels && (
              <text
                x={x + bw / 2}
                y={top - 5}
                textAnchor="middle"
                className="fill-slate-700 dark:fill-slate-300 text-[10px] font-mono tabular-nums"
              >
                {valueFormatter(d.value)}
              </text>
            )}
            {i % every === 0 && (
              <text
                x={x + bw / 2}
                y={height - 9}
                textAnchor="middle"
                className="fill-slate-500 dark:fill-slate-400 text-[10px] font-mono"
              >
                {d.label}
              </text>
            )}
          </g>
        );
      })}
    </svg>
  );
};

/** A point with its 95% range: used where a result may still be chance. */
export const DotIntervalChart: React.FC<{
  data: Array<{ label: string; value: number; low: number; high: number; certain: boolean; display?: string }>;
  height?: number;
}> = ({ data, height }) => {
  if (data.length === 0) return null;
  const width = 820;
  const labelW = 210;
  const padRight = 150;
  const rowH = 46;
  const h = height ?? data.length * rowH + 30;
  const plotW = width - labelW - padRight;

  const lo = Math.min(0, ...data.map((d) => d.low));
  const hi = Math.max(0, ...data.map((d) => d.high));
  const span = hi - lo || 1;
  const x = (v: number) => labelW + ((v - lo) / span) * plotW;

  return (
    <svg viewBox={`0 0 ${width} ${h}`} className="w-full h-auto select-none">
      <line x1={x(0)} x2={x(0)} y1={6} y2={h - 22} className="stroke-slate-400 dark:stroke-slate-600" strokeWidth={1.25} />
      <text x={x(0)} y={h - 8} textAnchor="middle" className="fill-slate-500 dark:fill-slate-400 text-[10px] font-mono">
        0
      </text>
      {data.map((d, i) => {
        const cy = 16 + i * rowH;
        const colour = !d.certain ? '#94A3B8' : d.value >= 0 ? '#1D4ED8' : '#DC2626';
        return (
          <g key={d.label}>
            <title>{`${d.label}: ${d.display ?? d.value.toFixed(3)} (95% range ${(d.low * 100).toFixed(1)}% to ${(d.high * 100).toFixed(1)}%)`}</title>
            <text
              x={labelW - 10}
              y={cy}
              textAnchor="end"
              dominantBaseline="middle"
              className="fill-slate-700 dark:fill-slate-300 text-[11px]"
            >
              {d.label}
            </text>
            <line x1={x(d.low)} x2={x(d.high)} y1={cy} y2={cy} stroke={colour} strokeWidth={2} opacity={0.5} />
            <line x1={x(d.low)} x2={x(d.low)} y1={cy - 5} y2={cy + 5} stroke={colour} strokeWidth={2} opacity={0.5} />
            <line x1={x(d.high)} x2={x(d.high)} y1={cy - 5} y2={cy + 5} stroke={colour} strokeWidth={2} opacity={0.5} />
            <circle cx={x(d.value)} cy={cy} r={5} fill={colour} />
            <text
              x={x(d.high) + 10}
              y={cy}
              dominantBaseline="middle"
              className="fill-slate-700 dark:fill-slate-300 text-[11px] font-mono tabular-nums"
            >
              {d.display ?? d.value.toFixed(2)}
              {!d.certain && <tspan className="fill-slate-500"> (could be chance)</tspan>}
            </text>
          </g>
        );
      })}
    </svg>
  );
};

export const LoadingPanel: React.FC<{ error: string | null }> = ({ error }) =>
  error ? (
    <Panel>
      <p className="text-sm text-red-700 dark:text-red-400">{error}</p>
    </Panel>
  ) : (
    <Panel>
      <p className="text-sm text-slate-500 dark:text-slate-400">Loading Bedrock results…</p>
    </Panel>
  );
