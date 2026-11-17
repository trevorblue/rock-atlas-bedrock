import { useEffect, useState } from 'react';
import { BedrockData } from './types';

const BASE = `${import.meta.env.BASE_URL || '/'}data/bedrock`.replace(/\/+/g, '/');

const FILES: Record<keyof BedrockData, string> = {
  meta: 'meta',
  headline: 'headline',
  depth: 'depth_snapshot',
  depthHistory: 'depth_history',
  concentration: 'concentration',
  robustnessDepth: 'robustness_depth',
  selloff: 'selloff',
  flows: 'flows',
  crash: 'crash',
  speculation: 'speculation',
  radar: 'radar',
  demo: 'demo',
  pricesMeta: 'prices_meta',
};

export interface BedrockState {
  data: BedrockData | null;
  loading: boolean;
  error: string | null;
}

/**
 * Loads every Bedrock result file once. They are static JSON written by the Python pipeline, so this works on
 * a plain static host with no server.
 */
export function useBedrockData(): BedrockState {
  const [state, setState] = useState<BedrockState>({ data: null, loading: true, error: null });

  useEffect(() => {
    let cancelled = false;
    const keys = Object.keys(FILES) as Array<keyof BedrockData>;

    Promise.all(
      keys.map(async (key) => {
        const res = await fetch(`${BASE}/${FILES[key]}.json`);
        if (!res.ok) throw new Error(`${FILES[key]}.json (HTTP ${res.status})`);
        return [key, await res.json()] as const;
      })
    )
      .then((entries) => {
        if (cancelled) return;
        const data = Object.fromEntries(entries) as unknown as BedrockData;
        setState({ data, loading: false, error: null });
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        const message = err instanceof Error ? err.message : 'unknown error';
        setState({
          data: null,
          loading: false,
          error: `Could not load Bedrock results: ${message}. Run "python export_for_atlas.py" to rebuild public/data/bedrock/.`,
        });
      });

    return () => {
      cancelled = true;
    };
  }, []);

  return state;
}

/** Real NSE prices in Atlas's own CSV format, so his six engines run on them unchanged. */
export async function fetchRealPricesCsv(): Promise<string> {
  const url = `${import.meta.env.BASE_URL || '/'}data/nse_prices.csv`.replace(/\/+/g, '/');
  const res = await fetch(url);
  if (!res.ok) throw new Error(`nse_prices.csv (HTTP ${res.status})`);
  return res.text();
}

// ---------------------------------------------------------------- formatting shared by the Bedrock pages
export const pct = (v: number | null | undefined, dp = 0): string =>
  v === null || v === undefined || !Number.isFinite(v) ? '—' : `${(v * 100).toFixed(dp)}%`;

export const signedPct = (v: number | null | undefined, dp = 1): string =>
  v === null || v === undefined || !Number.isFinite(v) ? '—' : `${v >= 0 ? '+' : '−'}${(Math.abs(v) * 100).toFixed(dp)}%`;

export const kes = (v: number | null | undefined): string => {
  if (v === null || v === undefined || !Number.isFinite(v)) return '—';
  const abs = Math.abs(v);
  if (abs >= 1e9) return `KES ${(v / 1e9).toFixed(1)}bn`;
  if (abs >= 1e6) return `KES ${(v / 1e6).toFixed(1)}m`;
  if (abs >= 1e3) return `KES ${(v / 1e3).toFixed(1)}k`;
  return `KES ${v.toFixed(0)}`;
};

export const num = (v: number | null | undefined, dp = 1): string =>
  v === null || v === undefined || !Number.isFinite(v) ? '—' : v.toLocaleString('en-US', { minimumFractionDigits: dp, maximumFractionDigits: dp });

export const days = (v: number | null | undefined): string => {
  if (v === null || v === undefined || !Number.isFinite(v)) return 'no trades';
  if (v < 1) return 'under 1 day';
  return `${Math.round(v).toLocaleString('en-US')} days`;
};

export const shortName = (name: string): string =>
  name.replace(/\s+(Ltd|Plc|PLC|Limited|Company)\.?$/i, '').trim();

export const niceDate = (iso: string): string => {
  const d = new Date(`${iso}T00:00:00Z`);
  if (Number.isNaN(d.getTime())) return iso;
  return `${d.getUTCDate()} ${['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'][d.getUTCMonth()]} ${d.getUTCFullYear()}`;
};

export const niceMonth = (iso: string): string => {
  const d = new Date(`${iso.slice(0, 10)}T00:00:00Z`);
  if (Number.isNaN(d.getTime())) return iso;
  return `${['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'][d.getUTCMonth()]} ${d.getUTCFullYear()}`;
};
