import React, { useState, useEffect } from 'react';
import {
  Leaf,
  Zap,
  TrendingDown,
  RefreshCw,
  Activity
} from 'lucide-react';
import { api } from '../../services/api';

// Static regional data — these are infrastructure-level constants, not telemetry
const REGIONS = [
  { name: 'eu-north-1 (Stockholm)', carbonIntensity: 22, energySource: 'Hydro / Nuclear', status: 'ULTRA_CLEAN' },
  { name: 'us-west-2 (Oregon)', carbonIntensity: 110, energySource: 'Hydro / Wind', status: 'CLEAN' },
  { name: 'eu-west-1 (Ireland)', carbonIntensity: 280, energySource: 'Wind / Gas', status: 'MODERATE' },
  { name: 'us-east-1 (N. Virginia)', carbonIntensity: 390, energySource: 'Gas / Coal Grid', status: 'HIGH_CARBON' },
];

const STATUS_LABEL: Record<string, string> = {
  ULTRA_CLEAN: 'PREFERRED BATCH TARGET',
  CLEAN: 'NORMAL TRAFFIC',
  MODERATE: 'RESTRICTED TO USER EDGE',
  HIGH_CARBON: 'CARBON OFFSET REQUIRED',
};

export const SustainabilityView: React.FC = () => {
  const [greenOpt, setGreenOpt] = useState<any>(null);
  const [services, setServices] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date());

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      // Run optimizer in GREEN mode to get real energy/carbon numbers
      const [opt, svc] = await Promise.allSettled([
        api.getOptimizer('GREEN', 6, 480),
        api.getServices(),
      ]);

      if (opt.status === 'fulfilled') setGreenOpt(opt.value);
      if (svc.status === 'fulfilled') setServices(svc.value?.services ?? []);
      setLastRefresh(new Date());
    } catch (e: any) {
      setError(e.message ?? 'Failed to load sustainability data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, []);

  // Pull real values from the GREEN optimizer result
  const selected = greenOpt?.selected_candidate;
  const totalReplicas = services.reduce((s: number, r: any) => s + (r.replicas ?? 1), 0);
  const wattPerReplica = 22; // ~22W per active pod
  const pue = 1.15;
  const carbonIntensityUsEast = 390; // gCO2/kWh

  const energyKwh = selected?.energy_kwh_per_hr
    ?? ((totalReplicas * wattPerReplica * pue) / 1000);
  const carbonGco2 = selected?.carbon_gco2_per_hr
    ?? (energyKwh * carbonIntensityUsEast);

  // Compare GREEN vs BALANCED mode to show avoided carbon
  const candidates: any[] = greenOpt?.candidates ?? [];
  const balancedCandidate = candidates.find((c: any) => !c.name?.includes('Current')) ?? null;
  const carbonAvoided = balancedCandidate
    ? Math.max(0, balancedCandidate.carbon_gco2_per_hr - (selected?.carbon_gco2_per_hr ?? carbonGco2))
    : null;

  return (
    <div className="flex-1 p-6 space-y-6 overflow-y-auto bg-[#09090b] text-[#fafafa] font-mono">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-[#27272a] pb-5">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-[#fafafa] flex items-center gap-2.5">
            <Leaf className="w-5 h-5 text-emerald-400" />
            Green Cloud Carbon Modeling
          </h2>
          <p className="text-xs text-[#a1a1aa] mt-1 font-sans">
            Real-time energy (kWh), regional grid carbon intensity, and GREEN mode optimizer results.
          </p>
        </div>
        <div className="flex items-center gap-2">
          {!loading && carbonAvoided != null && (
            <span className="px-2.5 py-1 rounded bg-emerald-950 text-emerald-400 border border-emerald-800 text-xs font-mono">
              GREEN MODE SAVES {carbonAvoided.toFixed(0)} gCO₂/hr
            </span>
          )}
          <button
            onClick={fetchData}
            disabled={loading}
            className="p-1.5 rounded bg-[#18181b] hover:bg-[#27272a] border border-[#27272a] text-[#a1a1aa] hover:text-[#fafafa] transition-colors"
            title="Refresh"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4 text-xs">
        <div className="p-4 rounded-lg bg-[#141418] border border-[#27272a]">
          <div className="text-[11px] text-[#71717a]">HOURLY ENERGY (GREEN MODE)</div>
          <div className="text-2xl font-bold text-emerald-400 mt-1">
            {loading ? '…' : `${energyKwh.toFixed(3)} kWh`}
          </div>
          <div className="text-[10px] text-[#a1a1aa] mt-1">
            {totalReplicas} active replicas · PUE {pue}
          </div>
        </div>
        <div className="p-4 rounded-lg bg-[#141418] border border-[#27272a]">
          <div className="text-[11px] text-[#71717a]">CARBON EMISSION</div>
          <div className="text-2xl font-bold text-[#fafafa] mt-1">
            {loading ? '…' : `${carbonGco2.toFixed(0)} gCO₂/hr`}
          </div>
          <div className="text-[10px] text-emerald-400 mt-1">
            {greenOpt ? 'GREEN optimizer active' : 'Estimated from telemetry'}
          </div>
        </div>
        <div className="p-4 rounded-lg bg-[#141418] border border-[#27272a]">
          <div className="text-[11px] text-[#71717a]">GREEN REPLICAS SELECTED</div>
          <div className="text-2xl font-bold text-sky-400 mt-1">
            {loading ? '…' : (selected?.replicas ?? totalReplicas)}
          </div>
          <div className="text-[10px] text-sky-400 mt-1">Pareto-optimal for carbon + cost</div>
        </div>
        <div className="p-4 rounded-lg bg-[#141418] border border-[#27272a]">
          <div className="text-[11px] text-[#71717a]">PUE FACTOR</div>
          <div className="text-2xl font-bold text-emerald-400 mt-1">{pue}</div>
          <div className="text-[10px] text-emerald-400 mt-1">Datacenter efficiency coefficient</div>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="p-4 rounded-lg bg-rose-950/30 border border-rose-800 text-rose-400 text-xs font-mono">
          ⚠ {error} — static regional data shown below.
        </div>
      )}

      {/* GREEN Optimizer Candidates Table */}
      {candidates.length > 0 && (
        <div className="rounded-lg border border-[#27272a] bg-[#101014] overflow-hidden">
          <div className="p-4 border-b border-[#27272a] text-xs font-bold font-sans text-[#fafafa]">
            GREEN Mode Pareto Candidates — Carbon vs Cost Trade-offs
          </div>
          <table className="w-full text-left text-xs">
            <thead className="bg-[#18181b] text-[#71717a] uppercase border-b border-[#27272a] text-[10px] tracking-wider">
              <tr>
                <th className="px-4 py-3">Config</th>
                <th className="px-4 py-3">Replicas</th>
                <th className="px-4 py-3">Energy kWh/hr</th>
                <th className="px-4 py-3">Carbon gCO₂/hr</th>
                <th className="px-4 py-3">Cost $/hr</th>
                <th className="px-4 py-3">p95 ms</th>
                <th className="px-4 py-3 text-right">Selection</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#27272a]">
              {candidates.map((c: any, i: number) => {
                const isSelected = selected?.replicas === c.replicas;
                return (
                  <tr key={i} className={`transition-colors ${isSelected ? 'bg-emerald-950/20' : 'hover:bg-[#18181b]/50'}`}>
                    <td className="px-4 py-3.5 font-bold text-[#fafafa]">{c.name}</td>
                    <td className="px-4 py-3.5 text-[#a1a1aa]">{c.replicas}</td>
                    <td className="px-4 py-3.5 text-emerald-400">{c.energy_kwh_per_hr?.toFixed(3)}</td>
                    <td className="px-4 py-3.5 text-emerald-400">{c.carbon_gco2_per_hr?.toFixed(0)}</td>
                    <td className="px-4 py-3.5 text-[#a1a1aa]">${c.estimated_cost_per_hr?.toFixed(2)}</td>
                    <td className={`px-4 py-3.5 ${c.expected_p95_ms > 200 ? 'text-amber-400' : 'text-[#a1a1aa]'}`}>
                      {c.expected_p95_ms?.toFixed(0)} ms
                    </td>
                    <td className="px-4 py-3.5 text-right">
                      {isSelected ? (
                        <span className="px-2 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-800 text-[10px] font-bold">
                          ✓ SELECTED
                        </span>
                      ) : c.is_pareto ? (
                        <span className="px-2 py-0.5 rounded bg-sky-950 text-sky-400 border border-sky-800 text-[10px]">
                          PARETO
                        </span>
                      ) : (
                        <span className="text-[#52525b] text-[10px]">—</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Regional Carbon Intensity Table — static infrastructure data */}
      <div className="rounded-lg border border-[#27272a] bg-[#101014] overflow-hidden">
        <div className="p-4 border-b border-[#27272a] text-xs font-bold font-sans text-[#fafafa]">
          Carbon Intensity Across Deployment Regions
        </div>
        <table className="w-full text-left text-xs">
          <thead className="bg-[#18181b] text-[#71717a] uppercase border-b border-[#27272a] text-[10px] tracking-wider">
            <tr>
              <th className="px-4 py-3">Cloud Region</th>
              <th className="px-4 py-3">Carbon Intensity (gCO₂/kWh)</th>
              <th className="px-4 py-3">Primary Energy Mix</th>
              <th className="px-4 py-3 text-right">Workload Policy</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#27272a]">
            {REGIONS.map(r => (
              <tr key={r.name} className="hover:bg-[#18181b]/50 transition-colors">
                <td className="px-4 py-3.5 font-bold text-[#fafafa]">{r.name}</td>
                <td className="px-4 py-3.5 font-bold" style={{
                  color: r.carbonIntensity < 50 ? '#34d399' : r.carbonIntensity < 200 ? '#38bdf8' : '#f59e0b'
                }}>
                  {r.carbonIntensity} gCO₂/kWh
                </td>
                <td className="px-4 py-3.5 text-[#a1a1aa] font-sans">{r.energySource}</td>
                <td className="px-4 py-3.5 text-right">
                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                    r.status === 'ULTRA_CLEAN'
                      ? 'bg-emerald-950 text-emerald-400 border border-emerald-800'
                      : r.status === 'CLEAN'
                      ? 'bg-sky-950 text-sky-400 border border-sky-800'
                      : r.status === 'MODERATE'
                      ? 'bg-amber-950 text-amber-400 border border-amber-800'
                      : 'bg-zinc-800 text-zinc-400 border border-zinc-700'
                  }`}>
                    {STATUS_LABEL[r.status] ?? r.status}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="text-[10px] text-[#52525b] font-sans">
        Carbon data sourced from WattTime / Electricity Maps regional averages. Last refresh: {lastRefresh.toLocaleTimeString()}
      </div>
    </div>
  );
};
