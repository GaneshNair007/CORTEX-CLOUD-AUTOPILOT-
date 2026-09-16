import React from 'react';
import {
  DollarSign,
  TrendingDown,
  ArrowUpRight,
  Sliders,
  CheckCircle2,
  PieChart,
  Layers,
  Sparkles
} from 'lucide-react';

export const CostView: React.FC = () => {
  const costBreakdown = [
    { category: 'Kubernetes Worker Nodes (c6i.2xlarge)', hourly: 12.40, monthly: 8928, pct: 54 },
    { category: 'Managed PostgreSQL (db.r6g.xlarge)', hourly: 4.80, monthly: 3456, pct: 21 },
    { category: 'ElastiCache Redis Cluster', hourly: 2.10, monthly: 1512, pct: 9 },
    { category: 'Cross-AZ Network Egress & NAT Gateway', hourly: 2.60, monthly: 1872, pct: 11 },
    { category: 'CloudWatch & Prometheus Metrics Ingestion', hourly: 1.10, monthly: 792, pct: 5 }
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
            Real-time infrastructure run rate, autonomous right-sizing, and predictive scaling savings.
          </p>
        </div>

        <div className="flex items-center gap-2 text-xs">
          <span className="px-2.5 py-1 rounded bg-emerald-950 text-emerald-400 border border-emerald-800">
            TOTAL SAVINGS: $1,420 / MO (-24.2%)
          </span>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4 text-xs">
        <div className="p-4 rounded-lg bg-[#141418] border border-[#27272a]">
          <div className="text-[11px] text-[#71717a]">CURRENT HOURLY RUN RATE</div>
          <div className="text-2xl font-bold text-[#fafafa] mt-1">$23.00/hr</div>
          <div className="text-[10px] text-[#a1a1aa] mt-1">Across 8 active services</div>
        </div>
        <div className="p-4 rounded-lg bg-[#141418] border border-[#27272a]">
          <div className="text-[11px] text-[#71717a]">PROJECTED MONTHLY SPEND</div>
          <div className="text-2xl font-bold text-[#fafafa] mt-1">$16,560</div>
          <div className="text-[10px] text-emerald-400 mt-1">Down from $21,800 without CORTEX</div>
        </div>
        <div className="p-4 rounded-lg bg-[#141418] border border-[#27272a]">
          <div className="text-[11px] text-[#71717a]">IDLE HEADROOM ELIMINATED</div>
          <div className="text-2xl font-bold text-sky-400 mt-1">32.4%</div>
          <div className="text-[10px] text-sky-400 mt-1">Right-sized via Pareto optimizer</div>
        </div>
        <div className="p-4 rounded-lg bg-[#141418] border border-[#27272a]">
          <div className="text-[11px] text-[#71717a]">SLO COST EFFICIENCY</div>
          <div className="text-2xl font-bold text-emerald-400 mt-1">99.94%</div>
          <div className="text-[10px] text-emerald-400 mt-1">Zero budget breaches</div>
        </div>
      </div>

      {/* Breakdown Table */}
      <div className="rounded-lg border border-[#27272a] bg-[#101014] overflow-hidden">
        <div className="p-4 border-b border-[#27272a] text-xs font-bold font-sans text-[#fafafa]">
          FinOps Cost Allocation by Resource
        </div>
        <table className="w-full text-left text-xs">
          <thead className="bg-[#18181b] text-[#71717a] uppercase border-b border-[#27272a] text-[10px] tracking-wider">
            <tr>
              <th className="px-4 py-3">Resource Component</th>
              <th className="px-4 py-3">Hourly Rate</th>
              <th className="px-4 py-3">Monthly Estimate</th>
              <th className="px-4 py-3">% Total</th>
              <th className="px-4 py-3 text-right">Optimization Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#27272a]">
            {costBreakdown.map(item => (
              <tr key={item.category} className="hover:bg-[#18181b]/50 transition-colors">
                <td className="px-4 py-3.5 font-bold text-[#fafafa]">
                  {item.category}
                </td>
                <td className="px-4 py-3.5 text-[#fafafa]">
                  ${item.hourly.toFixed(2)}/hr
                </td>
                <td className="px-4 py-3.5 text-[#a1a1aa]">
                  ${item.monthly.toLocaleString()}
                </td>
                <td className="px-4 py-3.5">
                  <div className="flex items-center gap-2">
                    <div className="w-16 bg-zinc-800 h-2 rounded-full overflow-hidden">
                      <div className="h-full bg-sky-500" style={{ width: `${item.pct}%` }} />
                    </div>
                    <span>{item.pct}%</span>
                  </div>
                </td>
                <td className="px-4 py-3.5 text-right">
                  <span className="px-2 py-0.5 rounded bg-emerald-950 text-emerald-400 text-[10px] font-bold border border-emerald-800">
                    RIGHT-SIZED
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
