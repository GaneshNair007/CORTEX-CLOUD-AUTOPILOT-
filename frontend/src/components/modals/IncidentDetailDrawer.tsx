import React from 'react';
import { X, AlertTriangle, ShieldCheck, CheckCircle2, ShieldAlert, BookOpen, Clock, Zap } from 'lucide-react';

interface IncidentDetailDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  incident: any | null;
}

export const IncidentDetailDrawer: React.FC<IncidentDetailDrawerProps> = ({
  isOpen,
  onClose,
  incident,
}) => {
  if (!isOpen || !incident) return null;

  return (
    <div className="fixed inset-y-0 right-0 w-[450px] bg-[#18181b] border-l border-[#27272a] shadow-2xl z-50 flex flex-col font-sans select-none animate-in slide-in-from-right duration-200">
      {/* Header */}
      <div className="p-4 border-b border-[#27272a] flex items-center justify-between bg-[#09090b]">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded bg-rose-950/60 border border-rose-800/50 text-rose-400">
            <AlertTriangle className="w-4 h-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-sm font-semibold text-[#fafafa]">{incident.id || 'INC-1042'}</h2>
              <span className="px-1.5 py-0.2 rounded text-[10px] font-mono bg-rose-950 text-rose-300 border border-rose-800/60">
                {incident.severity || 'P1'}
              </span>
            </div>
            <div className="text-[10px] font-mono text-[#71717a] uppercase tracking-wider">
              {incident.service || 'payment-api'} • Detected 8m ago
            </div>
          </div>
        </div>
        <button onClick={onClose} className="text-[#71717a] hover:text-[#fafafa] p-1.5 rounded hover:bg-[#27272a]">
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* Summary Description */}
        <div className="p-3 rounded bg-[#09090b] border border-[#27272a] space-y-1">
          <div className="text-[10px] font-mono font-semibold uppercase text-[#71717a]">Incident Symptom</div>
          <div className="text-xs text-[#fafafa] leading-relaxed">
            {incident.symptom || incident.description || 'HTTP 504 Gateway Timeout spike on /v1/checkout. Latency p99 increased to 4.2s. Postgres connection pool utilization at 100%.'}
          </div>
        </div>

        {/* AI Forensic Diagnosis & Self-Critique */}
        <div className="p-3.5 rounded bg-[#09090b] border border-[#27272a] space-y-2.5">
          <div className="flex items-center justify-between border-b border-[#27272a] pb-2">
            <span className="text-[10px] font-mono font-semibold uppercase text-sky-400">AI Root-Cause Diagnosis</span>
            <span className="text-xs font-mono font-bold text-emerald-400">
              Confidence: {Math.round((incident.confidence || 0.88) * 100)}%
            </span>
          </div>
          <div className="text-xs text-[#fafafa] leading-relaxed">
            {incident.hypothesis || 'Primary root cause: Postgres connection pool exhausted following deployment v4.6 holding connections open in idle-in-transaction state.'}
          </div>

          <div className="pt-2 border-t border-[#27272a]/60 space-y-1">
            <div className="text-[10px] font-mono font-semibold uppercase text-[#71717a]">Self-Critique & Counter-Evidence</div>
            <div className="text-[11px] text-[#a1a1aa] italic leading-relaxed">
              {incident.critique || 'Pool-exhaustion is consistent with 504 timeout patterns. Network partition ruled out via healthy out-of-band synthetic probes.'}
            </div>
          </div>
        </div>

        {/* Retrieved Evidence Stack */}
        <div className="p-3.5 rounded bg-[#09090b] border border-[#27272a] space-y-2">
          <div className="flex items-center justify-between border-b border-[#27272a] pb-1.5">
            <span className="text-[10px] font-mono font-semibold uppercase text-[#71717a]">Retrieved Evidence (RAG)</span>
            <BookOpen className="w-3.5 h-3.5 text-[#71717a]" />
          </div>
          <div className="space-y-1.5">
            <div className="flex items-center justify-between p-2 rounded bg-zinc-900 border border-zinc-800 text-xs">
              <span className="font-mono text-[#fafafa]">RB-001_k8s_pod_crashloop.md</span>
              <span className="text-[10px] font-mono text-emerald-400">Score 0.89</span>
            </div>
            <div className="flex items-center justify-between p-2 rounded bg-zinc-900 border border-zinc-800 text-xs">
              <span className="font-mono text-[#fafafa]">INC-2026-005_api_gateway_504.json</span>
              <span className="text-[10px] font-mono text-emerald-400">Score 0.86</span>
            </div>
          </div>
        </div>

        {/* CORTEX Guard Decision & Verification */}
        <div className="p-3.5 rounded bg-[#09090b] border border-[#27272a] space-y-2 text-xs">
          <div className="flex items-center justify-between border-b border-[#27272a] pb-1.5">
            <span className="text-[10px] font-mono font-semibold uppercase text-[#71717a]">CORTEX Governance</span>
            <span className="px-2 py-0.5 rounded font-mono font-bold text-[10px] bg-emerald-950 text-emerald-300 border border-emerald-800">
              {incident.guard_decision || 'ALLOW'}
            </span>
          </div>
          <div className="flex items-center justify-between py-1 border-b border-[#27272a]/60">
            <span className="text-[#a1a1aa]">Proposed Action</span>
            <span className="font-mono text-[#fafafa]">{incident.proposed_action || 'restart_service'}</span>
          </div>
          <div className="flex items-center justify-between py-1 border-b border-[#27272a]/60">
            <span className="text-[#a1a1aa]">Blast Radius</span>
            <span className="font-mono text-emerald-400">Score 13 / 100 (Low)</span>
          </div>
          <div className="flex items-center justify-between py-1">
            <span className="text-[#a1a1aa]">Post-Verification</span>
            <span className="font-mono text-emerald-400 flex items-center gap-1">
              <CheckCircle2 className="w-3.5 h-3.5" /> RECOVERED
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};
