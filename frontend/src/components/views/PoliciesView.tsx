import React, { useState } from 'react';
import {
  FileCode,
  ShieldCheck,
  CheckCircle2,
  Lock,
  Search,
  Code2,
  Sparkles,
  Layers
} from 'lucide-react';

export const PoliciesView: React.FC = () => {
  const policies = [
    {
      id: 'POL-001',
      name: 'Zero Production Database Restarts',
      severity: 'HARD_BLOCK',
      category: 'Data Integrity',
      target: 'postgres-primary, redis-cluster',
      description: 'Mutations attempting to directly execute restart, stop, or kill signals against primary database or persistent storage nodes are unconditionally blocked.',
      code: `rule "no_prod_db_restart" {
  when: action.type in ["restart_database", "stop_service"] && service.tier == "database"
  then: block("Direct database restarts forbidden in production. Use managed failover.")
}`,
      enabled: true
    },
    {
      id: 'POL-002',
      name: 'Minimum SLO Capacity Reserve',
      severity: 'CONSTRAINT',
      category: 'Availability',
      target: 'all stateless services',
      description: 'Under no operational condition or cost optimization directive can replica counts be reduced below 3 pods for tier-1 user-facing services.',
      code: `rule "min_capacity_reserve" {
  when: action.type == "scale_replicas" && action.params.replicas < 3
  then: constrain(action.params.replicas, min=3)
}`,
      enabled: true
    },
    {
      id: 'POL-003',
      name: 'Maximum Scale Burst Limit',
      severity: 'CONSTRAINT',
      category: 'Cost & Quota',
      target: 'all services',
      description: 'Prevents runaway AI scaling by capping single-step horizontal scaling to at most 2.5x current capacity or maximum 15 replicas.',
      code: `rule "max_scale_burst" {
  when: action.type == "scale_replicas" && action.params.replicas > current.replicas * 2.5
  then: constrain(action.params.replicas, max=current.replicas * 2.5)
}`,
      enabled: true
    },
    {
      id: 'POL-004',
      name: 'Production Primary Failover Requires SRE Lead Authorization',
      severity: 'GATE_APPROVAL',
      category: 'Security & Risk',
      target: 'postgres-primary',
      description: 'Database failover carries moderate risk of in-flight transaction aborts. CORTEX requires explicit cryptographic approval from an SRE Lead.',
      code: `rule "require_failover_approval" {
  when: action.type == "failover_to_replica"
  then: require_approval(role="sre-lead", timeout="15m")
}`,
      enabled: true
    },
    {
      id: 'POL-005',
      name: 'Throttled Action Cadence',
      severity: 'RATE_LIMIT',
      category: 'Stability',
      target: 'all services',
      description: 'Enforces a 60-second cooldown window after any mutating action on a service before subsequent mutations can be dispatched to avoid oscillation.',
      code: `rule "action_cooldown" {
  when: time_since_last_action(service) < 60s
  then: reject("Service cooldown active; telemetry must stabilize for 60s.")
}`,
      enabled: true
    }
  ];

  const [selectedPolicy, setSelectedPolicy] = useState(policies[0]);

  return (
    <div className="flex-1 p-6 space-y-6 overflow-y-auto bg-[#09090b] text-[#fafafa] font-mono">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-[#27272a] pb-5">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-[#fafafa] flex items-center gap-2.5">
            <FileCode className="w-5 h-5 text-sky-400" />
            Policy-as-Code Engine
          </h2>
          <p className="text-xs text-[#a1a1aa] mt-1 font-sans">
            Declarative invariant rules compiled into the CORTEX Guard enforcement kernel.
          </p>
        </div>

        <div className="flex items-center gap-2 text-xs">
          <span className="px-2.5 py-1 rounded bg-emerald-950 text-emerald-400 border border-emerald-800">
            5/5 POLICIES COMPILED & ACTIVE
          </span>
        </div>
      </div>

      {/* Main Grid: Policy List (Left) + Code Inspector (Right) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        <div className="lg:col-span-6 space-y-3">
          <div className="text-[10px] text-[#71717a] uppercase tracking-wider">
            REGISTERED INVARIANT RULES
          </div>

          {policies.map(pol => {
            const isSelected = selectedPolicy.id === pol.id;
            return (
              <div
                key={pol.id}
                onClick={() => setSelectedPolicy(pol)}
                className={`p-4 rounded-lg border transition-all cursor-pointer ${
                  isSelected
                    ? 'bg-[#181822] border-sky-500 shadow-[0_0_15px_rgba(14,165,233,0.15)]'
                    : 'bg-[#121216] border-[#27272a] hover:border-[#3f3f46]'
                }`}
              >
                <div className="flex items-center justify-between mb-1.5 text-xs">
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-sky-400">{pol.id}</span>
                    <span className="text-[#fafafa] font-sans font-semibold">{pol.name}</span>
                  </div>
                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                    pol.severity === 'HARD_BLOCK' ? 'bg-rose-950 text-rose-400 border border-rose-800' :
                    pol.severity === 'GATE_APPROVAL' ? 'bg-amber-950 text-amber-400 border border-amber-800' :
                    'bg-sky-950 text-sky-400 border border-sky-800'
                  }`}>
                    {pol.severity}
                  </span>
                </div>

                <p className="text-[11px] text-[#a1a1aa] font-sans line-clamp-2 leading-relaxed">
                  {pol.description}
                </p>

                <div className="mt-2 text-[10px] text-[#71717a] flex items-center justify-between">
                  <span>Category: {pol.category}</span>
                  <span>Scope: {pol.target}</span>
                </div>
              </div>
            );
          })}
        </div>

        {/* Code Inspector */}
        <div className="lg:col-span-6 p-5 rounded-lg border border-[#27272a] bg-[#101014] space-y-4">
          <div className="flex items-center justify-between border-b border-[#27272a] pb-3 text-xs">
            <span className="font-bold text-[#fafafa] font-sans">
              Rule Definition: {selectedPolicy.id}
            </span>
            <span className="text-[10px] text-emerald-400 flex items-center gap-1">
              <CheckCircle2 className="w-3.5 h-3.5" /> ENFORCED
            </span>
          </div>

          <div className="p-4 rounded bg-[#09090b] border border-[#27272a] text-xs text-[#fafafa] overflow-x-auto">
            <pre className="font-mono leading-relaxed text-sky-300">
              {selectedPolicy.code}
            </pre>
          </div>

          <div className="space-y-2 text-xs font-sans text-[#a1a1aa]">
            <h4 className="font-mono text-[10px] uppercase text-[#71717a] tracking-wider">
              Enforcement Guarantees
            </h4>
            <p className="leading-relaxed">
              This policy runs deterministically before any Python or Kubernetes tool execution.
              If an LLM hallucinates an unsafe argument, CORTEX Guard intercepts and blocks the call with zero delay.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
