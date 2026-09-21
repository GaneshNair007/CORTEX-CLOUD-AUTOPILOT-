import React, { useState, useEffect } from 'react';
import {
  DollarSign,
  TrendingDown,
  Server,
  RefreshCw,
  Activity
} from 'lucide-react';
import { api } from '../../services/api';

export const CostView: React.FC = () => {
  const [costData, setCostData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date());

  const fetchCost = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getCostSummary();
      setCostData(data);
      setLastRefresh(new Date());
    } catch (e: any) {
      setError(e.message ?? 'Failed to load cost data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCost();
    const interval = setInterval(fetchCost, 30000);
    return () => clearInterval(interval);
  }, []);

  const totalHourly = costData?.total_hourly_usd ?? 0;
  const totalMonthly = costData?.total_monthly_usd ?? 0;
  const dynamicServices: any[] = costData?.dynamic_services ?? [];
  const fixedInfra: any[] = costData?.fixed_infrastructure ?? [];
  const allItems = [
    ...dynamicServices.map((s: any) => ({
      category: `${s.service} (${s.replicas} replicas)`,
      hourly: s.hourly_usd,
      monthly: s.monthly_usd,
      pct: totalHourly > 0 ? Math.round((s.hourly_usd / totalHourly) * 100) : 0,
      detail: `CPU: ${s.cpu_percent ?? '—'}%`,
    })),
    ...fixedInfra.map((f: any) => ({
      category: f.category,
      hourly: f.hourly_usd,
      monthly: f.monthly_usd,
      pct: totalHourly > 0 ? Math.round((f.hourly_usd / totalHourly) * 100) : 0,
      detail: 'Fixed infrastructure',
    })),
  ];

  return (
    <div className="flex-1 p-6 space-y-6 overflow-y-auto bg-[#09090b] text-[#fafafa] font-mono">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-[#27272a] pb-5">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-[#fafafa] flex items-center gap-2.5">
            <DollarSign className="w-5 h-5 text-emerald-400" />
            Cloud Cost Intelligence & FinOps
          </h2>
          <p className="text-xs text-[#a1a1aa] mt-1 font-sans">
            Real-time run rate derived from live replica counts. Refreshes every 30 s.
          </p>
        </div>
        <div className="flex items-center gap-2">
          {!loading && costData && (
            <span className="px-2.5 py-1 rounded bg-emerald-950 text-emerald-400 border border-emerald-800 text-xs font-mono">
              ${totalHourly.toFixed(2)}/hr · ${totalMonthly.toLocaleString()}/mo
            </span>
          )}
          <button
            onClick={fetchCost}
            disabled={loading}
            className="p-1.5 rounded bg-[#18181b] hover:bg-[#27272a] border border-[#27272a] text-[#a1a1aa] hover:text-[#fafafa] transition-colors"
            title="Refresh costs"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4 text-xs">
        <div className="p-4 rounded-lg bg-[#141418] border border-[#27272a]">
          <div className="text-[11px] text-[#71717a]">HOURLY RUN RATE</div>
          <div className="text-2xl font-bold text-[#fafafa] mt-1">
            {loading ? '…' : `$${totalHourly.toFixed(2)}/hr`}
          </div>
          <div className="text-[10px] text-[#a1a1aa] mt-1">
            {dynamicServices.length} dynamic + {fixedInfra.length} fixed resources
          </div>
        </div>
        <div className="p-4 rounded-lg bg-[#141418] border border-[#27272a]">
          <div className="text-[11px] text-[#71717a]">PROJECTED MONTHLY</div>
          <div className="text-2xl font-bold text-[#fafafa] mt-1">
            {loading ? '…' : `$${totalMonthly.toLocaleString()}`}
          </div>
          <div className="text-[10px] text-[#a1a1aa] mt-1">Based on current replica count</div>
        </div>
        <div className="p-4 rounded-lg bg-[#141418] border border-[#27272a]">
          <div className="text-[11px] text-[#71717a]">ACTIVE REPLICAS</div>
          <div className="text-2xl font-bold text-sky-400 mt-1">
            {loading ? '…' : dynamicServices.reduce((s: number, r: any) => s + (r.replicas ?? 0), 0)}
          </div>
          <div className="text-[10px] text-sky-400 mt-1">Across {dynamicServices.length} dynamic services</div>
        </div>
        <div className="p-4 rounded-lg bg-[#141418] border border-[#27272a]">
          <div className="text-[11px] text-[#71717a]">LAST REFRESHED</div>
          <div className="text-lg font-bold text-emerald-400 mt-1">
            {lastRefresh.toLocaleTimeString()}
          </div>
          <div className="text-[10px] text-emerald-400 mt-1">Live from sandbox telemetry</div>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="p-4 rounded-lg bg-rose-950/30 border border-rose-800 text-rose-400 text-xs font-mono">
          ⚠ {error}
        </div>
      )}

      {/* Loading skeleton */}
      {loading && !costData && (
        <div className="space-y-2">
          {[...Array(8)].map((_, i) => (
            <div key={i} className="h-11 rounded bg-[#141418] border border-[#27272a] animate-pulse" />
          ))}
        </div>
      )}

      {/* Breakdown Table */}
      {allItems.length > 0 && (
        <div className="rounded-lg border border-[#27272a] bg-[#101014] overflow-hidden">
          <div className="p-4 border-b border-[#27272a] text-xs font-bold font-sans text-[#fafafa] flex items-center justify-between">
            <span>FinOps Cost Allocation by Resource</span>
            <span className="text-[10px] text-[#71717a] font-mono">{costData?.region ?? 'us-east-1'} • AWS on-demand est.</span>
          </div>
          <table className="w-full text-left text-xs">
            <thead className="bg-[#18181b] text-[#71717a] uppercase border-b border-[#27272a] text-[10px] tracking-wider">
              <tr>
                <th className="px-4 py-3">Resource</th>
                <th className="px-4 py-3">Hourly</th>
                <th className="px-4 py-3">Monthly (est.)</th>
                <th className="px-4 py-3">% of Total</th>
                <th className="px-4 py-3">Detail</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#27272a]">
              {allItems.map((item, i) => (
                <tr key={i} className="hover:bg-[#18181b]/50 transition-colors">
                  <td className="px-4 py-3.5 font-bold text-[#fafafa]">{item.category}</td>
                  <td className="px-4 py-3.5 text-[#fafafa]">${item.hourly?.toFixed(2)}/hr</td>
                  <td className="px-4 py-3.5 text-[#a1a1aa]">${(item.monthly ?? 0).toLocaleString()}</td>
                  <td className="px-4 py-3.5">
                    <div className="flex items-center gap-2">
                      <div className="w-16 bg-zinc-800 h-2 rounded-full overflow-hidden">
                        <div className="h-full bg-sky-500" style={{ width: `${item.pct}%` }} />
                      </div>
                      <span>{item.pct}%</span>
                    </div>
                  </td>
                  <td className="px-4 py-3.5 text-[#71717a] text-[10px] font-sans">{item.detail}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="px-4 py-3 bg-[#0c0c0e] border-t border-[#27272a] text-[11px] text-[#71717a] font-sans">
            {costData?.note}
          </div>
        </div>
      )}

      {/* Empty */}
      {!loading && allItems.length === 0 && !error && (
        <div className="flex flex-col items-center justify-center py-20 text-[#71717a] text-sm font-mono gap-2">
          <Activity className="w-8 h-8 opacity-30" />
          <span>No cost data available. Start the backend to see live estimates.</span>
        </div>
      )}
    </div>
  );
};
