import React, { useState } from 'react';
import {
  ShieldAlert,
  ShieldCheck,
  Search,
  ExternalLink,
  Power,
  ChevronDown
} from 'lucide-react';
import { ActiveRoute } from './CortexSidebar';
import { api } from '../../services/api';

interface HeaderProps {
  currentRoute: ActiveRoute;
  onRouteChange: (route: ActiveRoute) => void;
  onOpenCommandPalette: () => void;
  autonomyLevel: number;
  onAutonomyChange: (level: number) => void;
  killSwitchEngaged: boolean;
  onKillSwitchToggle: (engaged: boolean) => void;
}

export const CortexHeader: React.FC<HeaderProps> = ({
  currentRoute,
  onRouteChange,
  onOpenCommandPalette,
  autonomyLevel,
  onAutonomyChange,
  killSwitchEngaged,
  onKillSwitchToggle,
}) => {
  const [showAutonomyDropdown, setShowAutonomyDropdown] = useState(false);

  const getRouteLabel = (route: ActiveRoute) => {
    switch (route) {
      case 'console': return 'Operations Command Center';
      case 'incidents': return 'Incident Command & Forensics';
      case 'topology': return 'Multi-Tier Infrastructure Topology';
      case 'predictions': return 'Workload Forecast Engine (5m / 15m / 30m)';
      case 'optimizer': return 'Multi-Objective CloudPilot & Pareto Frontier';
      case 'memory': return 'Operational Memory & Vector RAG';
      case 'cortex': return 'CORTEX Guard & Governance Engine';
      case 'simulator': return 'Counterfactual Digital Twin Simulator';
      case 'approvals': return 'Human-in-the-Loop Governance Queue';
      case 'policies': return 'Policy-as-Code Engine';
      case 'chaos': return 'Chaos Engineering Laboratory';
      case 'reliability': return 'SLO Management & Error Budget Burn';
      case 'cost': return 'Cloud Cost Intelligence & FinOps';
      case 'sustainability': return 'Green Cloud Carbon Modeling';
      case 'audit': return 'Tamper-Evident Evidence Ledger';
      case 'evaluation': return 'Ground-Truth Research Benchmarks';
      case 'providers': return 'Cloud Provider Neutrality';
      case 'demo': return 'Guided Autonomous & Safety Demo';
      default: return 'Control Plane';
    }
  };

  const autonomyLevels = [
    { level: 0, label: 'L0: OBSERVE', desc: 'Read-only telemetry, no actions' },
    { level: 1, label: 'L1: RECOMMEND', desc: 'AI recommends, operator executes' },
    { level: 2, label: 'L2: GUARDED', desc: 'Auto-executes safe, gates high-risk' },
    { level: 3, label: 'L3: AUTONOMOUS', desc: 'Full closed-loop self-healing' },
  ];

  return (
    <header className="h-14 bg-[#09090b] border-b border-[#27272a] px-6 flex items-center justify-between z-20 select-none">
      {/* Breadcrumb / Title */}
      <div className="flex items-center gap-3">
        <span className="text-[11px] font-mono text-[#71717a] uppercase tracking-wider">
          CORTEX
        </span>
        <span className="text-[#3f3f46]">/</span>
        <h1 className="text-xs font-semibold text-[#fafafa] tracking-tight">
          {getRouteLabel(currentRoute)}
        </h1>
      </div>

      {/* Center Command Palette Search Button */}
      <button
        onClick={onOpenCommandPalette}
        className="hidden md:flex items-center gap-3 px-3 py-1.5 rounded bg-[#18181b] border border-[#27272a] text-[#71717a] hover:text-[#a1a1aa] hover:border-[#3f3f46] text-xs font-mono transition-colors cursor-pointer"
      >
        <Search className="w-3.5 h-3.5 text-[#71717a]" />
        <span>Search services, incidents, actions...</span>
        <kbd className="px-1.5 py-0.5 rounded bg-[#27272a] text-[#a1a1aa] text-[10px] font-sans border border-[#3f3f46]">
          ⌘K
        </kbd>
      </button>

      {/* Right Controls & Autonomy */}
      <div className="flex items-center gap-3">
        {/* Autonomy Dropdown */}
        <div className="relative">
          <button
            onClick={() => setShowAutonomyDropdown(!showAutonomyDropdown)}
            className="flex items-center gap-2 px-2.5 py-1 rounded bg-[#18181b] border border-[#27272a] hover:border-[#3f3f46] text-xs font-mono transition-colors cursor-pointer"
          >
            <ShieldCheck className="w-3.5 h-3.5 text-sky-400" />
            <span className="text-[#fafafa]">
              {autonomyLevels[autonomyLevel]?.label || `L${autonomyLevel}`}
            </span>
            <ChevronDown className="w-3 h-3 text-[#71717a]" />
          </button>

          {showAutonomyDropdown && (
            <div className="absolute right-0 mt-1.5 w-60 bg-[#18181b] border border-[#27272a] rounded shadow-xl py-1 z-50">
              <div className="px-3 py-1 text-[10px] font-mono text-[#71717a] uppercase border-b border-[#27272a]">
                Autonomy Level
              </div>
              {autonomyLevels.map((lvl) => (
                <button
                  key={lvl.level}
                  onClick={() => {
                    onAutonomyChange(lvl.level);
                    setShowAutonomyDropdown(false);
                  }}
                  className={`w-full text-left px-3 py-2 text-xs transition-colors cursor-pointer flex flex-col ${
                    autonomyLevel === lvl.level ? 'bg-zinc-800 text-sky-300' : 'text-[#a1a1aa] hover:bg-zinc-800/50 hover:text-white'
                  }`}
                >
                  <span className="font-semibold">{lvl.label}</span>
                  <span className="text-[10px] text-[#71717a]">{lvl.desc}</span>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Emergency Kill Switch */}
        <button
          onClick={() => onKillSwitchToggle(!killSwitchEngaged)}
          className={`flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-mono border transition-colors cursor-pointer ${
            killSwitchEngaged
              ? 'bg-rose-950 text-rose-300 border-rose-700 animate-pulse'
              : 'bg-[#18181b] text-[#a1a1aa] border-[#27272a] hover:border-rose-900 hover:text-rose-400'
          }`}
          title={killSwitchEngaged ? 'Click to Disengage Emergency Stop' : 'Click to Engage Emergency Kill Switch'}
        >
          <Power className="w-3.5 h-3.5" />
          <span>{killSwitchEngaged ? 'KILL SWITCH ACTIVE' : 'KILL SWITCH'}</span>
        </button>

        {/* Public Landing Link */}
        <button
          onClick={() => onRouteChange('landing')}
          className="p-1.5 rounded hover:bg-[#18181b] text-[#71717a] hover:text-[#fafafa] transition-colors cursor-pointer"
          title="Return to Public Story Landing Page"
        >
          <ExternalLink className="w-4 h-4" />
        </button>
      </div>
    </header>
  );
};
