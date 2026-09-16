import React, { useState } from 'react';
import {
  ShieldCheck,
  ShieldAlert,
  ShieldX,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Lock,
  Radio,
  Sliders,
  Play,
  RotateCcw,
  Sparkles
} from 'lucide-react';
import { api } from '../../services/api';

interface CortexGuardViewProps {
  autonomyLevel: number;
  onAutonomyChange: (level: number) => void;
  killSwitchEngaged: boolean;
  onKillSwitchToggle: (engaged: boolean) => void;
}

export const CortexGuardView: React.FC<CortexGuardViewProps> = ({
  autonomyLevel,
  onAutonomyChange,
  killSwitchEngaged,
  onKillSwitchToggle
}) => {
  const [testAction, setTestAction] = useState('restart_database');
  const [testResult, setTestResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const autonomyLevels = [
    { level: 0, name: 'L0: OBSERVE', desc: 'Read-only telemetry monitoring. No automated actions permitted.' },
    { level: 1, name: 'L1: RECOMMEND', desc: 'AI generates actions, but every action requires human operator execution.' },
    { level: 2, name: 'L2: GUARDED (DEFAULT)', desc: 'Auto-executes safe, verified actions; gates high blast-radius mutations for human approval.' },
    { level: 3, name: 'L3: FULL AUTONOMOUS', desc: 'Closed-loop self-healing with post-action verification and automatic rollback.' },
  ];

  const interceptedActions = [
    {
      id: 'ACT-9021',
      time: '14:28:10',
      action: 'scale_replicas',
      target: 'payment-api',
      params: '6 → 9 pods',
      risk: 24,
      guardDecision: 'ALLOW',
      reason: 'Low blast radius (1 service). Passed SLO reserve and capacity contract.'
    },
    {
      id: 'ACT-9020',
      time: '14:25:04',
      action: 'restart_database',
      target: 'postgres-primary',
      params: 'kill -9 postgres master',
      risk: 94,
      guardDecision: 'BLOCK',
      reason: 'Rule POL-001 Violation: Dangerous mutation on critical cluster with 4 downstream dependencies.'
    },
    {
      id: 'ACT-9019',
      time: '13:58:32',
      action: 'failover_to_replica',
      target: 'postgres-primary',
      params: 'promote replica-02',
      risk: 68,
      guardDecision: 'REQUIRE_APPROVAL',
      reason: 'Rule POL-004: Production database failover requires SRE Lead cryptographic authorization.'
    },
    {
      id: 'ACT-9018',
      time: '13:12:44',
      action: 'flush_redis_cache',
      target: 'redis-cache',
      params: 'FLUSHALL async',
      risk: 58,
      guardDecision: 'CONSTRAIN',
      reason: 'Constrained: Refactored to selective key invalidation to prevent thundering herd.'
    }
  ];

  const handleTestEvaluation = async () => {
    setLoading(true);
    try {
      if (testAction === 'restart_database') {
        setTestResult({
          action: 'restart_database',
          decision: 'BLOCK',
          risk_score: 92,
          blast_radius: 4,
          rule_triggered: 'POL-001 (Zero Production Outage Invariant)',
          explanation: 'Restarts on primary database nodes are strictly prohibited by CORTEX Guard. Safe alternative: trigger failover to standby replica.'
        });
      } else if (testAction === 'scale_replicas') {
        setTestResult({
          action: 'scale_replicas',
          decision: 'ALLOW',
          risk_score: 18,
          blast_radius: 1,
          rule_triggered: 'POL-002 (Adaptive Scaling Contract)',
          explanation: 'Safe progressive scale within registered quota limits (max 15 pods).'
        });
      } else {
        setTestResult({
          action: testAction,
          decision: 'REQUIRE_APPROVAL',
          risk_score: 65,
          blast_radius: 3,
          rule_triggered: 'POL-004 (Human Authorization Mandate)',
          explanation: 'Moderate blast radius mutation requires signed operator approval.'
        });
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex-1 p-6 space-y-6 overflow-y-auto bg-[#09090b] text-[#fafafa] font-mono">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-[#27272a] pb-5">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-[#fafafa] flex items-center gap-2.5">
            <ShieldCheck className="w-5 h-5 text-emerald-400" />
            CORTEX Guard & Autonomy Engine
          </h2>
          <p className="text-xs text-[#a1a1aa] mt-1 font-sans">
            Cryptographic policy enforcement gate. Intercepts AI action proposals, validates capability contracts, and enforces blast radius boundaries.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => onKillSwitchToggle(!killSwitchEngaged)}
            className={`px-3 py-1.5 rounded text-xs font-bold transition-all cursor-pointer border ${
              killSwitchEngaged
                ? 'bg-rose-950 text-rose-300 border-rose-700 animate-pulse'
                : 'bg-[#18181b] text-rose-400 border-rose-900/60 hover:bg-rose-950/40'
            }`}
          >
            {killSwitchEngaged ? 'DISENGAGE KILL SWITCH' : 'EMERGENCY KILL SWITCH'}
          </button>
        </div>
      </div>

      {/* Autonomy Level Slider / Cards */}
      <div className="space-y-3">
        <div className="text-xs text-[#71717a] uppercase tracking-wider">
          ACTIVE AUTONOMY GOVERNANCE LEVEL
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {autonomyLevels.map(lvl => {
            const isSelected = autonomyLevel === lvl.level;
            return (
              <div
                key={lvl.level}
                onClick={() => onAutonomyChange(lvl.level)}
                className={`p-4 rounded-lg border transition-all cursor-pointer ${
                  isSelected
                    ? 'bg-[#161822] border-sky-500 shadow-[0_0_15px_rgba(14,165,233,0.2)]'
                    : 'bg-[#121216] border-[#27272a] hover:border-[#3f3f46]'
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <span className={`text-xs font-bold ${isSelected ? 'text-sky-400' : 'text-[#fafafa]'}`}>
                    {lvl.name}
                  </span>
                  {isSelected && <CheckCircle2 className="w-4 h-4 text-sky-400" />}
                </div>
                <p className="text-[11px] text-[#a1a1aa] font-sans leading-relaxed">
                  {lvl.desc}
                </p>
              </div>
            );
          })}
        </div>
      </div>

      {/* Interception Sandbox & Live Interception Stream */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Live Interception Stream (Cols 1-7) */}
        <div className="lg:col-span-7 rounded-lg border border-[#27272a] bg-[#101014] overflow-hidden">
          <div className="p-4 border-b border-[#27272a] flex items-center justify-between text-xs">
            <span className="font-bold text-[#fafafa] font-sans">Live Interception Stream</span>
            <span className="text-[11px] text-emerald-400 flex items-center gap-1">
              <Radio className="w-3 h-3 animate-pulse" /> POLICY GATE ACTIVE
            </span>
          </div>

          <div className="divide-y divide-[#27272a]">
            {interceptedActions.map(act => (
              <div key={act.id} className="p-4 space-y-2 hover:bg-[#16161c] transition-colors">
                <div className="flex items-center justify-between text-xs">
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-[#fafafa]">{act.action}</span>
                    <span className="text-[#71717a]">({act.target})</span>
                    <span className="text-[10px] bg-zinc-800 px-1.5 py-0.2 rounded text-zinc-300">
                      {act.params}
                    </span>
                  </div>
                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                    act.guardDecision === 'ALLOW' ? 'bg-emerald-950 text-emerald-400 border border-emerald-800' :
                    act.guardDecision === 'BLOCK' ? 'bg-rose-950 text-rose-400 border border-rose-800' :
                    act.guardDecision === 'REQUIRE_APPROVAL' ? 'bg-amber-950 text-amber-400 border border-amber-800' :
                    'bg-sky-950 text-sky-400 border border-sky-800'
                  }`}>
                    {act.guardDecision}
                  </span>
                </div>

                <p className="text-[11px] text-[#a1a1aa] font-sans leading-relaxed">
                  {act.reason}
                </p>

                <div className="flex items-center justify-between text-[10px] text-[#71717a] pt-1">
                  <span>ID: {act.id} • TIME: {act.time}</span>
                  <span>Risk Score: {act.risk}/100</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Interactive Policy Tester (Cols 8-12) */}
        <div className="lg:col-span-5 p-5 rounded-lg border border-[#27272a] bg-[#121216] space-y-4 text-xs">
          <div>
            <span className="text-[10px] text-[#71717a] uppercase tracking-wider block">
              GUARD SECURITY PLAYGROUND
            </span>
            <h3 className="text-sm font-bold text-[#fafafa] font-sans mt-1">
              Simulate Action Interception
            </h3>
            <p className="text-[11px] text-[#a1a1aa] font-sans mt-1">
              Submit synthetic proposals to evaluate CORTEX Guard defense against dangerous hallucinations.
            </p>
          </div>

          <div className="space-y-2">
            <label className="text-[11px] text-[#71717a] uppercase">Select Action Proposal:</label>
            <select
              value={testAction}
              onChange={e => setTestAction(e.target.value)}
              className="w-full bg-[#18181b] border border-[#27272a] rounded px-3 py-2 text-xs text-[#fafafa] focus:outline-none focus:border-sky-500"
            >
              <option value="restart_database">restart_database (High Risk Mutation)</option>
              <option value="scale_replicas">scale_replicas (Safe Operational Action)</option>
              <option value="failover_to_replica">failover_to_replica (Approval Mandate)</option>
              <option value="drain_node">drain_node (Capacity Constraint)</option>
            </select>
          </div>

          <button
            onClick={handleTestEvaluation}
            disabled={loading}
            className="w-full py-2 bg-sky-600 hover:bg-sky-500 disabled:bg-zinc-800 text-white rounded font-sans text-xs font-semibold transition-colors cursor-pointer"
          >
            {loading ? 'Evaluating Policy...' : 'Evaluate Against Guardrails'}
          </button>

          {testResult && (
            <div className={`p-4 rounded-lg border space-y-2 ${
              testResult.decision === 'BLOCK' ? 'bg-rose-950/40 border-rose-800 text-rose-200' :
              testResult.decision === 'ALLOW' ? 'bg-emerald-950/40 border-emerald-800 text-emerald-200' :
              'bg-amber-950/40 border-amber-800 text-amber-200'
            }`}>
              <div className="flex items-center justify-between font-bold text-xs">
                <span>INTERCEPTION RESULT:</span>
                <span className="px-2 py-0.5 rounded bg-black/40 border border-current">
                  {testResult.decision}
                </span>
              </div>
              <div className="text-[11px]">
                Triggered Rule: <span className="font-semibold">{testResult.rule_triggered}</span>
              </div>
              <p className="text-[11px] font-sans leading-relaxed text-[#fafafa]">
                {testResult.explanation}
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
