import React from 'react';
import {
  Gauge,
  TrendingDown,
  AlertTriangle,
  CheckCircle2,
  Clock,
  ShieldCheck,
  Activity
} from 'lucide-react';

export const ReliabilityView: React.FC = () => {
  const slos = [
    {
      service: 'Payment API',
      sli: 'p95 Latency < 200ms',
      target: 99.9,
      current: 99.78,
      errorBudgetRemaining: 78.0,
      burnRate1h: 1.8,
      burnRate6h: 1.2,
      burnRate24h: 0.9,
      status: 'BURNING'
    },
    {
      service: 'API Gateway',
      sli: 'HTTP Error Rate < 0.1%',
      target: 99.95,
      current: 99.97,
      errorBudgetRemaining: 94.0,
      burnRate1h: 0.4,
      burnRate6h: 0.3,
      burnRate24h: 0.5,
      status: 'HEALTHY'
    },
    {
      service: 'Order Service',
      sli: 'p95 Latency < 150ms',
      target: 99.9,
      current: 99.92,
      errorBudgetRemaining: 88.5,
      burnRate1h: 0.6,
      burnRate6h: 0.5,
      burnRate24h: 0.4,
      status: 'HEALTHY'
    },
    {
      service: 'Auth Service',
      sli: 'Token Auth Latency < 50ms',
      target: 99.99,
      current: 99.99,
      errorBudgetRemaining: 98.2,
      burnRate1h: 0.1,
      burnRate6h: 0.1,
      burnRate24h: 0.1,
      status: 'HEALTHY'
    }
  ];

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
            Multi-window multi-burn-rate alerting compliant with Google SRE Book standards.
          </p>
        </div>

        <div className="flex items-center gap-2 text-xs">
          <span className="px-2.5 py-1 rounded bg-emerald-950 text-emerald-400 border border-emerald-800">
            GLOBAL SLO COMPLIANCE: 99.91%
          </span>
        </div>
      </div>

      {/* Burn Rate Methodology Card */}
      <div className="p-4 rounded-lg bg-[#141418] border border-[#27272a] text-xs font-sans text-[#a1a1aa] flex items-center justify-between">
        <div>
          <span className="font-mono font-bold text-[#fafafa] block">Multi-Window Alerting Standard:</span>
          Burn rate &gt; 14.4x in 1 hour consumes 2% of budget $\rightarrow$ Page on-call. Burn rate &gt; 6x in 6 hours $\rightarrow$ Autonomous mitigation.
        </div>
        <span className="text-[10px] font-mono px-2 py-1 rounded bg-zinc-800 text-zinc-300">
          GOOGLE SRE COMPLIANT
        </span>
      </div>

      {/* SLO Table */}
      <div className="rounded-lg border border-[#27272a] bg-[#101014] overflow-hidden">
        <table className="w-full text-left text-xs">
          <thead className="bg-[#18181b] text-[#71717a] uppercase border-b border-[#27272a] text-[10px] tracking-wider">
            <tr>
              <th className="px-4 py-3">Service</th>
              <th className="px-4 py-3">Service Level Indicator</th>
              <th className="px-4 py-3">Target</th>
              <th className="px-4 py-3">Current</th>
              <th className="px-4 py-3">Budget Remaining</th>
              <th className="px-4 py-3">1h Burn</th>
              <th className="px-4 py-3">6h Burn</th>
              <th className="px-4 py-3 text-right">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#27272a]">
            {slos.map(slo => (
              <tr key={slo.service} className="hover:bg-[#18181b]/50 transition-colors">
                <td className="px-4 py-3.5 font-bold text-[#fafafa]">
                  {slo.service}
                </td>
                <td className="px-4 py-3.5 text-[#a1a1aa] font-sans">
                  {slo.sli}
                </td>
                <td className="px-4 py-3.5 text-[#71717a]">
                  {slo.target}%
                </td>
                <td className={`px-4 py-3.5 font-bold ${
                  slo.current < slo.target ? 'text-amber-400' : 'text-emerald-400'
                }`}>
                  {slo.current}%
                </td>
                <td className="px-4 py-3.5">
                  <div className="flex items-center gap-2">
                    <div className="w-20 bg-zinc-800 h-2 rounded-full overflow-hidden">
                      <div
                        className={`h-full ${slo.errorBudgetRemaining < 80 ? 'bg-amber-400' : 'bg-emerald-400'}`}
                        style={{ width: `${slo.errorBudgetRemaining}%` }}
                      />
                    </div>
                    <span>{slo.errorBudgetRemaining}%</span>
                  </div>
                </td>
                <td className={`px-4 py-3.5 ${slo.burnRate1h > 1.0 ? 'text-amber-400 font-bold' : 'text-[#a1a1aa]'}`}>
                  {slo.burnRate1h}x
                </td>
                <td className="px-4 py-3.5 text-[#a1a1aa]">
                  {slo.burnRate6h}x
                </td>
                <td className="px-4 py-3.5 text-right">
                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                    slo.status === 'BURNING'
                      ? 'bg-amber-950 text-amber-300 border border-amber-800 animate-pulse'
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
    </div>
  );
};
