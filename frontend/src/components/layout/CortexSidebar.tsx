import React from 'react';
import {
  Activity,
  AlertTriangle,
  Network,
  TrendingUp,
  Sliders,
  Database,
  ShieldCheck,
  Cpu,
  CheckCircle2,
  FileCode,
  Flame,
  Gauge,
  DollarSign,
  Leaf,
  History,
  Award,
  Cloud,
  Settings,
  PlayCircle,
  Radio,
  ChevronRight
} from 'lucide-react';

export type ActiveRoute =
  | 'landing'
  | 'console'
  | 'incidents'
  | 'topology'
  | 'predictions'
  | 'optimizer'
  | 'memory'
  | 'cortex'
  | 'simulator'
  | 'approvals'
  | 'policies'
  | 'chaos'
  | 'reliability'
  | 'cost'
  | 'sustainability'
  | 'audit'
  | 'evaluation'
  | 'providers'
  | 'demo'
  | 'settings';

interface SidebarProps {
  currentRoute: ActiveRoute;
  onRouteChange: (route: ActiveRoute) => void;
  pendingApprovalsCount?: number;
  activeIncidentsCount?: number;
}

export const CortexSidebar: React.FC<SidebarProps> = ({
  currentRoute,
  onRouteChange,
  pendingApprovalsCount = 0,
  activeIncidentsCount = 2,
}) => {
  const sections = [
    {
      category: 'OPERATIONS',
      items: [
        { id: 'console' as ActiveRoute, label: 'Overview', icon: Activity },
        { id: 'incidents' as ActiveRoute, label: 'Incidents', icon: AlertTriangle, badge: activeIncidentsCount },
        { id: 'topology' as ActiveRoute, label: 'Topology Graph', icon: Network },
      ],
    },
    {
      category: 'INTELLIGENCE',
      items: [
        { id: 'predictions' as ActiveRoute, label: 'Predictions', icon: TrendingUp },
        { id: 'optimizer' as ActiveRoute, label: 'Optimizer', icon: Sliders },
        { id: 'memory' as ActiveRoute, label: 'Incident Memory', icon: Database },
      ],
    },
    {
      category: 'CORTEX GUARD',
      items: [
        { id: 'cortex' as ActiveRoute, label: 'Guard & Autonomy', icon: ShieldCheck },
        { id: 'simulator' as ActiveRoute, label: 'Digital Twin', icon: Cpu },
        { id: 'approvals' as ActiveRoute, label: 'Approvals Queue', icon: CheckCircle2, badge: pendingApprovalsCount },
        { id: 'policies' as ActiveRoute, label: 'Policies-as-Code', icon: FileCode },
      ],
    },
    {
      category: 'RELIABILITY',
      items: [
        { id: 'chaos' as ActiveRoute, label: 'Chaos Lab', icon: Flame },
        { id: 'reliability' as ActiveRoute, label: 'SLOs & Burn Rate', icon: Gauge },
      ],
    },
    {
      category: 'ECONOMICS',
      items: [
        { id: 'cost' as ActiveRoute, label: 'Cost & FinOps', icon: DollarSign },
        { id: 'sustainability' as ActiveRoute, label: 'Green Cloud', icon: Leaf },
      ],
    },
    {
      category: 'EVIDENCE & RESEARCH',
      items: [
        { id: 'audit' as ActiveRoute, label: 'Audit Ledger', icon: History },
        { id: 'evaluation' as ActiveRoute, label: 'Benchmarks', icon: Award },
      ],
    },
    {
      category: 'SYSTEM',
      items: [
        { id: 'providers' as ActiveRoute, label: 'Cloud Providers', icon: Cloud },
        { id: 'demo' as ActiveRoute, label: 'Interactive Demo', icon: PlayCircle, highlight: true },
      ],
    },
  ];

  return (
    <aside className="w-64 bg-[#09090b] border-r border-[#27272a] flex flex-col h-screen select-none shrink-0 font-sans z-30">
      {/* Brand Header */}
      <div className="h-14 px-5 border-b border-[#27272a] flex items-center justify-between">
        <button
          onClick={() => onRouteChange('landing')}
          className="flex items-center gap-2.5 text-left group cursor-pointer"
        >
          <div className="w-6 h-6 rounded bg-[#fafafa] flex items-center justify-center text-[#09090b] font-mono font-black text-xs">
            C
          </div>
          <div>
            <span className="font-semibold text-sm tracking-tight text-[#fafafa] group-hover:text-white">
              CORTEX
            </span>
            <span className="text-[10px] font-mono uppercase tracking-widest text-[#a1a1aa] block -mt-0.5">
              AUTOPILOT
            </span>
          </div>
        </button>
        <span className="flex items-center gap-1.5 px-2 py-0.5 rounded text-[10px] font-mono bg-emerald-950/60 text-emerald-400 border border-emerald-800/50">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
          ACTIVE
        </span>
      </div>

      {/* Navigation Groups */}
      <div className="flex-1 overflow-y-auto py-3 px-2 space-y-5 scrollbar-thin scrollbar-thumb-zinc-800">
        {sections.map((section) => (
          <div key={section.category}>
            <div className="px-3 mb-1 text-[10px] font-mono font-semibold uppercase tracking-wider text-[#71717a]">
              {section.category}
            </div>
            <div className="space-y-0.5">
              {section.items.map((item) => {
                const Icon = item.icon;
                const isActive = currentRoute === item.id;
                return (
                  <button
                    key={item.id}
                    onClick={() => onRouteChange(item.id)}
                    className={`w-full flex items-center justify-between px-3 py-1.5 rounded text-xs font-medium transition-colors cursor-pointer text-left ${
                      isActive
                        ? 'bg-[#27272a] text-[#fafafa] font-semibold'
                        : item.highlight
                        ? 'text-sky-400 hover:bg-[#18181b] hover:text-sky-300'
                        : 'text-[#a1a1aa] hover:bg-[#18181b] hover:text-[#fafafa]'
                    }`}
                  >
                    <div className="flex items-center gap-2.5">
                      <Icon className={`w-4 h-4 ${isActive ? 'text-[#fafafa]' : item.highlight ? 'text-sky-400' : 'text-[#71717a]'}`} />
                      <span>{item.label}</span>
                    </div>
                    {item.badge !== undefined && item.badge > 0 ? (
                      <span className="px-1.5 py-0.2 rounded-full text-[10px] font-mono bg-rose-950 text-rose-300 border border-rose-800/60">
                        {item.badge}
                      </span>
                    ) : isActive ? (
                      <ChevronRight className="w-3.5 h-3.5 text-[#71717a]" />
                    ) : null}
                  </button>
                );
              })}
            </div>
          </div>
        ))}
      </div>

      {/* Footer Profile & Autonomy */}
      <div className="p-3 border-t border-[#27272a] bg-[#0c0c0e]">
        <div className="flex items-center justify-between text-xs">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded bg-[#27272a] border border-[#3f3f46] flex items-center justify-center font-mono text-[11px] text-[#fafafa]">
              OP
            </div>
            <div>
              <div className="text-[#fafafa] font-medium text-[11px] leading-tight">SRE Operator</div>
              <div className="text-[10px] text-[#71717a] font-mono">us-east-1 (Live)</div>
            </div>
          </div>
          <button
            onClick={() => onRouteChange('demo')}
            className="px-2 py-1 bg-zinc-800 hover:bg-zinc-700 text-[#fafafa] text-[10px] font-mono rounded border border-zinc-700 transition-colors"
          >
            DEMO
          </button>
        </div>
      </div>
    </aside>
  );
};
