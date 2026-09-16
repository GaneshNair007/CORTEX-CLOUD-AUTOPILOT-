import React, { useState, useEffect } from 'react';
import { Search, X, AlertTriangle, Network, Cpu, TrendingUp, Sliders, ShieldCheck, Flame, History, Award, ArrowRight } from 'lucide-react';
import { ActiveRoute } from './CortexSidebar';

interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
  onNavigate: (route: ActiveRoute) => void;
}

export const CommandPalette: React.FC<CommandPaletteProps> = ({
  isOpen,
  onClose,
  onNavigate,
}) => {
  const [query, setQuery] = useState('');

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        isOpen ? onClose() : null;
      } else if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const commands = [
    { label: 'Overview Command Center', route: 'console' as ActiveRoute, icon: Network, group: 'Navigation' },
    { label: 'Active Incidents & Forensic Reports', route: 'incidents' as ActiveRoute, icon: AlertTriangle, group: 'Navigation' },
    { label: 'Full-Screen Topology & Blast Radius', route: 'topology' as ActiveRoute, icon: Network, group: 'Navigation' },
    { label: 'Workload Forecast Engine (5m/15m/30m)', route: 'predictions' as ActiveRoute, icon: TrendingUp, group: 'Navigation' },
    { label: 'Multi-Objective Optimizer & Pareto Frontier', route: 'optimizer' as ActiveRoute, icon: Sliders, group: 'Navigation' },
    { label: 'Counterfactual Digital Twin Simulation', route: 'simulator' as ActiveRoute, icon: Cpu, group: 'CORTEX' },
    { label: 'CORTEX Guard & Governance Engine', route: 'cortex' as ActiveRoute, icon: ShieldCheck, group: 'CORTEX' },
    { label: 'Pending Approvals Queue', route: 'approvals' as ActiveRoute, icon: ShieldCheck, group: 'CORTEX' },
    { label: 'Chaos Engineering Laboratory', route: 'chaos' as ActiveRoute, icon: Flame, group: 'Reliability' },
    { label: 'Tamper-Evident Audit Ledger', route: 'audit' as ActiveRoute, icon: History, group: 'Evidence' },
    { label: 'Research Benchmarks & Baselines', route: 'evaluation' as ActiveRoute, icon: Award, group: 'Research' },
    { label: 'Guided Autonomous Demo Walkthrough', route: 'demo' as ActiveRoute, icon: ArrowRight, group: 'Demo' },
  ];

  const filtered = commands.filter((c) =>
    c.label.toLowerCase().includes(query.toLowerCase()) || c.group.toLowerCase().includes(query.toLowerCase())
  );

  return (
    <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-start justify-center pt-24 px-4">
      <div className="w-full max-w-xl bg-[#18181b] border border-[#27272a] rounded-lg shadow-2xl overflow-hidden font-sans">
        {/* Search Input */}
        <div className="flex items-center px-4 border-b border-[#27272a] bg-[#09090b]">
          <Search className="w-4 h-4 text-[#71717a] shrink-0 mr-3" />
          <input
            type="text"
            placeholder="Type a command or search routes..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="w-full py-3.5 bg-transparent text-sm text-[#fafafa] placeholder-[#71717a] outline-none font-mono"
            autoFocus
          />
          <button onClick={onClose} className="text-[#71717a] hover:text-[#fafafa] p-1">
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Results List */}
        <div className="max-h-80 overflow-y-auto py-2 px-2 divide-y divide-[#27272a]/50">
          {filtered.length === 0 ? (
            <div className="p-6 text-center text-xs text-[#71717a] font-mono">
              No matching commands or routes found.
            </div>
          ) : (
            filtered.map((cmd) => {
              const Icon = cmd.icon;
              return (
                <button
                  key={cmd.label}
                  onClick={() => {
                    onNavigate(cmd.route);
                    onClose();
                  }}
                  className="w-full flex items-center justify-between px-3 py-2.5 rounded hover:bg-[#27272a] text-left transition-colors cursor-pointer group"
                >
                  <div className="flex items-center gap-3">
                    <div className="p-1.5 rounded bg-[#27272a] group-hover:bg-[#3f3f46] text-[#a1a1aa] group-hover:text-[#fafafa]">
                      <Icon className="w-4 h-4" />
                    </div>
                    <div>
                      <div className="text-xs font-medium text-[#fafafa]">{cmd.label}</div>
                      <div className="text-[10px] text-[#71717a] font-mono">{cmd.group}</div>
                    </div>
                  </div>
                  <span className="text-[10px] text-[#71717a] font-mono opacity-0 group-hover:opacity-100 transition-opacity">
                    Jump ↵
                  </span>
                </button>
              );
            })
          )}
        </div>

        {/* Footer */}
        <div className="px-4 py-2 border-t border-[#27272a] bg-[#09090b] flex items-center justify-between text-[10px] font-mono text-[#71717a]">
          <span>Navigation Shortcut: ⌘K or ESC to close</span>
          <span>CORTEX Control Plane</span>
        </div>
      </div>
    </div>
  );
};
