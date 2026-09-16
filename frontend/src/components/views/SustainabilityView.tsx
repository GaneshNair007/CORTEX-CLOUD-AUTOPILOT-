import React from 'react';
import {
  Leaf,
  Globe,
  Zap,
  TrendingDown,
  CheckCircle2,
  Sparkles,
  Layers
} from 'lucide-react';

export const SustainabilityView: React.FC = () => {
  const regions = [
    { name: 'eu-north-1 (Stockholm)', carbonIntensity: 22, energySource: 'Hydro / Nuclear', status: 'ULTRA_CLEAN' },
    { name: 'us-west-2 (Oregon)', carbonIntensity: 110, energySource: 'Hydro / Wind', status: 'CLEAN' },
    { name: 'eu-west-1 (Ireland)', carbonIntensity: 280, energySource: 'Wind / Gas', status: 'MODERATE' },
    { name: 'us-east-1 (N. Virginia)', carbonIntensity: 390, energySource: 'Gas / Coal Grid', status: 'HIGH_CARBON' },
  ];

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
            Real-time energy consumption (kWh), regional grid carbon intensity, and carbon-aware workload scheduling.
          </p>
        </div>

        <div className="flex items-center gap-2 text-xs">
          <span className="px-2.5 py-1 rounded bg-emerald-950 text-emerald-400 border border-emerald-800">
            CARBON AVOIDED: 420 KG CO2EQ (-31%)
          </span>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4 text-xs">
        <div className="p-4 rounded-lg bg-[#141418] border border-[#27272a]">
          <div className="text-[11px] text-[#71717a]">HOURLY ENERGY USAGE</div>
          <div className="text-2xl font-bold text-emerald-400 mt-1">4.2 kWh</div>
          <div className="text-[10px] text-[#a1a1aa] mt-1">Across 48 vCPUs</div>
        </div>
        <div className="p-4 rounded-lg bg-[#141418] border border-[#27272a]">
          <div className="text-[11px] text-[#71717a]">AVG CARBON INTENSITY</div>
          <div className="text-2xl font-bold text-[#fafafa] mt-1">164 gCO2/kWh</div>
          <div className="text-[10px] text-emerald-400 mt-1">-42% via Green Mode routing</div>
        </div>
        <div className="p-4 rounded-lg bg-[#141418] border border-[#27272a]">
          <div className="text-[11px] text-[#71717a]">BATCH SHED EFFICIENCY</div>
          <div className="text-2xl font-bold text-sky-400 mt-1">94.2%</div>
          <div className="text-[10px] text-sky-400 mt-1">Aligned with solar peak</div>
        </div>
        <div className="p-4 rounded-lg bg-[#141418] border border-[#27272a]">
          <div className="text-[11px] text-[#71717a]">PUE FACTOR</div>
          <div className="text-2xl font-bold text-emerald-400 mt-1">1.12</div>
          <div className="text-[10px] text-emerald-400 mt-1">Tier-IV Datacenter rating</div>
        </div>
      </div>

      {/* Regional Carbon Intensity Table */}
      <div className="rounded-lg border border-[#27272a] bg-[#101014] overflow-hidden">
        <div className="p-4 border-b border-[#27272a] text-xs font-bold font-sans text-[#fafafa]">
          Carbon Intensity Across Deployment Regions
        </div>
        <table className="w-full text-left text-xs">
          <thead className="bg-[#18181b] text-[#71717a] uppercase border-b border-[#27272a] text-[10px] tracking-wider">
            <tr>
              <th className="px-4 py-3">Cloud Region</th>
              <th className="px-4 py-3">Carbon Intensity (gCO2/kWh)</th>
              <th className="px-4 py-3">Primary Grid Energy Mix</th>
              <th className="px-4 py-3 text-right">Workload Scheduling Policy</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#27272a]">
            {regions.map(r => (
              <tr key={r.name} className="hover:bg-[#18181b]/50 transition-colors">
                <td className="px-4 py-3.5 font-bold text-[#fafafa]">
                  {r.name}
                </td>
                <td className="px-4 py-3.5 text-emerald-400 font-bold">
                  {r.carbonIntensity} gCO2/kWh
                </td>
                <td className="px-4 py-3.5 text-[#a1a1aa] font-sans">
                  {r.energySource}
                </td>
                <td className="px-4 py-3.5 text-right">
                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                    r.status === 'ULTRA_CLEAN' ? 'bg-emerald-950 text-emerald-400 border border-emerald-800' :
                    r.status === 'CLEAN' ? 'bg-sky-950 text-sky-400 border border-sky-800' :
                    'bg-zinc-800 text-zinc-300 border border-zinc-700'
                  }`}>
                    {r.status === 'ULTRA_CLEAN' ? 'PREFERRED BATCH TARGET' : r.status === 'CLEAN' ? 'NORMAL TRAFFIC' : 'RESTRICTED TO USER EDGE'}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
