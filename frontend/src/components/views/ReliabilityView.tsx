import React, { useState, useEffect } from 'react';
import {
  Gauge,
  AlertTriangle,
  CheckCircle2,
  RefreshCw,
  ShieldCheck,
  Activity
} from 'lucide-react';
import { api } from '../../services/api';

interface SLOEntry {
  service: string;
  sli: string;
  target_pct: number;
  current_pct: number;
  p95_ms: number;
  p95_target_ms: number;
  error_rate_pct: number;
  burn_rate_1h: number;
  error_budget_remaining_pct: number;
  status: 'HEALTHY' | 'BURNING' | 'EXHAUSTED' | 'ERROR' | string;
  error?: string;
}

export const ReliabilityView: React.FC = () => {
  const [slos, setSlos] = useState<SLOEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date());

  const fetchSLOs = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getSLOSummary();
      setSlos(data.slos ?? []);
      setLastRefresh(new Date());
    } catch (e: any) {
      setError(e.message ?? 'Failed to load SLO data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSLOs();
    const interval = setInterval(fetchSLOs, 15000);
    return () => clearInterval(interval);
  }, []);

  const burning = slos.filter(s => s.status === 'BURNING' || s.status === 'EXHAUSTED').length;
  const healthy = slos.filter(s => s.status === 'HEALTHY').length;
  const globalCompliance = slos.length > 0
    ? ((slos.reduce((sum, s) => sum + (s.current_pct ?? 0), 0) / slos.length)).toFixed(2)
    : '—';

  return (
    <div className="flex-1 p-6 space-y-6 overflow-y-auto bg-[#09090b] text-[#fafafa] font-mono">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-[#27272a] pb-5">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-[#fafafa] flex items-center gap-2.5">
            <Gauge className="w-5 h-5 text-sky-400" />
            SLO & Error Budget Burn Management
          </h2>
          <p className="text-xs text-[#a1a1aa] mt-1 font-sans">
            Multi-window multi-burn-rate alerting. Data refreshes every 15 s from live telemetry.
          </p>
        </div>

        <div className="flex items-center gap-2 text-xs">
          {!loading && (
            <span className={`px-2.5 py-1 rounded border text-xs font-mono ${
              burning > 0
                ? 'bg-amber-950 text-amber-400 border-amber-800'
                : 'bg-emerald-950 text-emerald-400 border-emerald-800'
            }`}>
              GLOBAL SLO: {globalCompliance}%
            </span>
          )}
          <button
            onClick={fetchSLOs}
            disabled={loading}
            className="p-1.5 rounded bg-[#18181b] hover:bg-[#27272a] border border-[#27272a] text-[#a1a1aa] hover:text-[#fafafa] transition-colors"
            title="Refresh SLOs"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Method Banner */}
      <div className="p-4 rounded-lg bg-[#141418] border border-[#27272a] text-xs font-sans text-[#a1a1aa] flex items-center justify-between">
        <div>
          <span className="font-mono font-bold text-[#fafafa] block">Multi-Window Alerting Standard:</span>
          Burn rate &gt; 14.4× in 1 h consumes 2% of budget → Page on-call.
          Burn rate &gt; 6× in 6 h → Autonomous mitigation.
        </div>
        <span className="text-[10px] font-mono px-2 py-1 rounded bg-zinc-800 text-zinc-300 shrink-0 ml-4">
          GOOGLE SRE COMPLIANT
        </span>
      </div>

      {/* Summary Pills */}
      {!loading && slos.length > 0 && (
        <div className="flex items-center gap-3 text-xs font-mono">
          <span className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-emerald-950 border border-emerald-800 text-emerald-400">
            <CheckCircle2 className="w-3.5 h-3.5" />
            {healthy} HEALTHY
          </span>
          {burning > 0 && (
            <span className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-amber-950 border border-amber-800 text-amber-400 animate-pulse">
              <AlertTriangle className="w-3.5 h-3.5" />
              {burning} BURNING
            </span>
          )}
          <span className="text-[#71717a] text-[11px]">
            Last refresh: {lastRefresh.toLocaleTimeString()}
          </span>
        </div>
      )}

      {/* Error state */}
      {error && (
        <div className="p-4 rounded-lg bg-rose-950/30 border border-rose-800 text-rose-400 text-xs font-mono">
          ⚠ {error} — showing cached data if available.
        </div>
      )}

      {/* Loading skeleton */}
      {loading && slos.length === 0 && (
        <div className="space-y-2">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="h-12 rounded bg-[#141418] border border-[#27272a] animate-pulse" />
          ))}
        </div>
      )}

      {/* SLO Table */}
      {slos.length > 0 && (
        <div className="rounded-lg border border-[#27272a] bg-[#101014] overflow-hidden">
          <table className="w-full text-left text-xs">
            <thead className="bg-[#18181b] text-[#71717a] uppercase border-b border-[#27272a] text-[10px] tracking-wider">
              <tr>
                <th className="px-4 py-3">Service</th>
                <th className="px-4 py-3">SLI</th>
                <th className="px-4 py-3">Target</th>
                <th className="px-4 py-3">Availability</th>
                <th className="px-4 py-3">p95 ms</th>
                <th className="px-4 py-3">Error Rate</th>
                <th className="px-4 py-3">Budget Left</th>
                <th className="px-4 py-3">1h Burn</th>
                <th className="px-4 py-3 text-right">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#27272a]">
              {slos.map(slo => (
                <tr key={slo.service} className="hover:bg-[#18181b]/50 transition-colors">
                  <td className="px-4 py-3.5 font-bold text-[#fafafa] whitespace-nowrap">
                    {slo.service}
                  </td>
                  <td className="px-4 py-3.5 text-[#71717a] font-sans text-[10px] max-w-[180px] truncate">
                    {slo.sli}
                  </td>
                  <td className="px-4 py-3.5 text-[#71717a]">
                    {slo.target_pct?.toFixed(3)}%
                  </td>
                  <td className={`px-4 py-3.5 font-bold ${
                    (slo.current_pct ?? 100) < (slo.target_pct ?? 99.9)
                      ? 'text-amber-400'
                      : 'text-emerald-400'
                  }`}>
                    {slo.current_pct?.toFixed(4)}%
                  </td>
                  <td className={`px-4 py-3.5 ${
                    (slo.p95_ms ?? 0) > (slo.p95_target_ms ?? 200)
                      ? 'text-amber-400 font-bold'
                      : 'text-[#a1a1aa]'
                  }`}>
                    {slo.p95_ms?.toFixed(0)} ms
                  </td>
                  <td className={`px-4 py-3.5 ${
                    (slo.error_rate_pct ?? 0) > 1.0 ? 'text-rose-400 font-bold' : 'text-[#a1a1aa]'
                  }`}>
                    {slo.error_rate_pct?.toFixed(3)}%
                  </td>
                  <td className="px-4 py-3.5">
                    <div className="flex items-center gap-2">
                      <div className="w-16 bg-zinc-800 h-2 rounded-full overflow-hidden">
                        <div
                          className={`h-full ${
                            (slo.error_budget_remaining_pct ?? 100) < 20
                              ? 'bg-rose-500'
                              : (slo.error_budget_remaining_pct ?? 100) < 50
                              ? 'bg-amber-400'
                              : 'bg-emerald-400'
                          }`}
                          style={{ width: `${Math.min(100, slo.error_budget_remaining_pct ?? 100)}%` }}
                        />
                      </div>
                      <span className="text-[10px]">
                        {slo.error_budget_remaining_pct?.toFixed(0)}%
                      </span>
                    </div>
                  </td>
                  <td className={`px-4 py-3.5 ${
                    (slo.burn_rate_1h ?? 0) > 1.0 ? 'text-amber-400 font-bold' : 'text-[#a1a1aa]'
                  }`}>
                    {slo.burn_rate_1h?.toFixed(2)}×
                  </td>
                  <td className="px-4 py-3.5 text-right">
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                      slo.status === 'EXHAUSTED'
                        ? 'bg-rose-950 text-rose-300 border border-rose-800 animate-pulse'
                        : slo.status === 'BURNING'
                        ? 'bg-amber-950 text-amber-300 border border-amber-800 animate-pulse'
                        : slo.status === 'ERROR'
                        ? 'bg-zinc-800 text-zinc-400 border border-zinc-700'
                        : 'bg-emerald-950 text-emerald-400 border border-emerald-800'
                    }`}>
                      {slo.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Empty state */}
      {!loading && slos.length === 0 && !error && (
        <div className="flex flex-col items-center justify-center py-20 text-[#71717a] text-sm font-mono gap-2">
          <Activity className="w-8 h-8 opacity-30" />
          <span>No SLO data available. Start the backend to see live data.</span>
        </div>
      )}
    </div>
  );
};
