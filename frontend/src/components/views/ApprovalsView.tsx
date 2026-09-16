import React, { useState } from 'react';
import {
  CheckCircle2,
  XCircle,
  AlertTriangle,
  ShieldAlert,
  Clock,
  Cpu,
  UserCheck,
  ArrowRight,
  Sparkles
} from 'lucide-react';
import { api } from '../../services/api';

export const ApprovalsView: React.FC = () => {
  const [approvals, setApprovals] = useState([
    {
      id: 'APP-108',
      timestamp: '14:20:15 UTC',
      service: 'postgres-primary',
      action: 'failover_to_replica',
      parameters: { target_replica: 'pg-replica-02', force_drain: true },
      risk_score: 74,
      blast_radius: 4,
      reason: 'Rule POL-004: Primary database failover carries moderate risk of 15s in-flight query drop.',
      safer_alternative: 'Promote replica without force-drain during read-only traffic window.',
      status: 'PENDING'
    },
    {
      id: 'APP-107',
      timestamp: '13:45:00 UTC',
      service: 'auth-service',
      action: 'rotate_signing_keys',
      parameters: { key_id: 'rsa-2026-v2', grace_period_sec: 300 },
      risk_score: 62,
      blast_radius: 3,
      reason: 'Rule POL-008: Auth token key rotation requires cryptographic SRE authorization to prevent logout cascade.',
      safer_alternative: 'Dual-sign tokens for 24 hours prior to key deprecation.',
      status: 'PENDING'
    }
  ]);
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  const handleResolve = async (id: string, approved: boolean) => {
    try {
      await api.resolveApproval(id, approved, 'sre-lead');
      setApprovals(approvals.map(a => a.id === id ? { ...a, status: approved ? 'APPROVED' : 'REJECTED' } : a));
      setActionMessage(`Action ${id} ${approved ? 'APPROVED' : 'REJECTED'} successfully.`);
    } catch (e) {
      setApprovals(approvals.map(a => a.id === id ? { ...a, status: approved ? 'APPROVED' : 'REJECTED' } : a));
      setActionMessage(`Action ${id} ${approved ? 'APPROVED' : 'REJECTED'} (Simulated locally).`);
    }
  };

  return (
    <div className="flex-1 p-6 space-y-6 overflow-y-auto bg-[#09090b] text-[#fafafa] font-mono">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-[#27272a] pb-5">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-[#fafafa] flex items-center gap-2.5">
            <UserCheck className="w-5 h-5 text-amber-400" />
            Human-in-the-Loop Governance Queue
          </h2>
          <p className="text-xs text-[#a1a1aa] mt-1 font-sans">
            Gated high blast-radius operational actions intercepted by CORTEX Guard awaiting human SRE authorization.
          </p>
        </div>

        <div className="flex items-center gap-2 text-xs">
          <span className="px-2.5 py-1 rounded bg-amber-950 text-amber-400 border border-amber-800">
            {approvals.filter(a => a.status === 'PENDING').length} PENDING AUTHORIZATIONS
          </span>
        </div>
      </div>

      {actionMessage && (
        <div className="p-3 rounded bg-emerald-950/60 border border-emerald-800 text-emerald-300 text-xs flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4" />
          <span>{actionMessage}</span>
        </div>
      )}

      {/* Approvals Cards */}
      <div className="space-y-4">
        {approvals.map(app => {
          const isPending = app.status === 'PENDING';
          return (
            <div
              key={app.id}
              className={`p-5 rounded-lg border transition-all ${
                isPending
                  ? 'bg-[#141418] border-[#27272a]'
                  : 'bg-[#0f0f12] border-[#222225] opacity-60'
              }`}
            >
              <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 border-b border-[#27272a] pb-3">
                <div className="flex items-center gap-3">
                  <span className="px-2 py-0.5 rounded bg-amber-950 text-amber-300 border border-amber-800 text-xs font-bold">
                    {app.id}
                  </span>
                  <span className="text-xs text-[#a1a1aa]">{app.timestamp}</span>
                  <span className="text-xs font-bold text-[#fafafa]">{app.service}</span>
                </div>

                <div className="flex items-center gap-3 text-xs">
                  <span className="text-[#71717a]">Risk Score:</span>
                  <span className="text-amber-400 font-bold">{app.risk_score} / 100</span>
                  <span className="text-[#71717a]">Blast Radius:</span>
                  <span className="text-rose-400 font-bold">{app.blast_radius} Services</span>
                </div>
              </div>

              <div className="py-4 space-y-3 font-sans text-xs">
                <div>
                  <span className="font-mono text-[10px] text-[#71717a] uppercase block">
                    Proposed Mutation
                  </span>
                  <span className="font-mono font-bold text-sm text-sky-300">
                    {app.action}({JSON.stringify(app.parameters)})
                  </span>
                </div>

                <div>
                  <span className="font-mono text-[10px] text-[#71717a] uppercase block">
                    Interception Reason
                  </span>
                  <p className="text-[#a1a1aa] mt-0.5 leading-relaxed">
                    {app.reason}
                  </p>
                </div>

                <div className="p-3 rounded bg-[#09090b] border border-[#27272a] text-[11px] text-[#d4d4d8]">
                  <span className="text-emerald-400 font-bold font-mono">SAFER COUNTER-PROPOSAL: </span>
                  {app.safer_alternative}
                </div>
              </div>

              {isPending ? (
                <div className="flex items-center gap-3 pt-2 border-t border-[#27272a]">
                  <button
                    onClick={() => handleResolve(app.id, true)}
                    className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded font-sans text-xs font-semibold flex items-center gap-1.5 transition-colors cursor-pointer"
                  >
                    <CheckCircle2 className="w-4 h-4" />
                    <span>Authorize & Execute</span>
                  </button>

                  <button
                    onClick={() => handleResolve(app.id, false)}
                    className="px-4 py-2 bg-[#27272a] hover:bg-rose-950/80 hover:text-rose-300 text-[#a1a1aa] rounded font-sans text-xs font-semibold flex items-center gap-1.5 transition-colors cursor-pointer"
                  >
                    <XCircle className="w-4 h-4" />
                    <span>Reject Action</span>
                  </button>
                </div>
              ) : (
                <div className="pt-2 text-xs font-mono font-bold text-[#a1a1aa]">
                  STATUS: {app.status}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
