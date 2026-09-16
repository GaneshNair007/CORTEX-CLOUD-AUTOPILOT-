import React from 'react';
import { X, Server, Activity, ShieldCheck, Database, ArrowRight, Zap } from 'lucide-react';

interface ServiceInspectorProps {
  isOpen: boolean;
  onClose: () => void;
  service: any | null;
  onSimulateAction?: (actionType: string, params: any) => void;
}

export const ServiceInspectorDrawer: React.FC<ServiceInspectorProps> = ({
  isOpen,
  onClose,
  service,
  onSimulateAction,
}) => {
  if (!isOpen || !service) return null;

  return (
    <div className="fixed inset-y-0 right-0 w-96 bg-[#18181b] border-l border-[#27272a] shadow-2xl z-50 flex flex-col font-sans select-none animate-in slide-in-from-right duration-200">
      {/* Header */}
      <div className="p-4 border-b border-[#27272a] flex items-center justify-between bg-[#09090b]">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded bg-[#27272a] text-[#fafafa]">
            <Server className="w-4 h-4" />
          </div>
          <div>
            <h2 className="text-sm font-semibold text-[#fafafa]">{service.name || service.id}</h2>
            <div className="text-[10px] font-mono text-[#71717a] uppercase tracking-wider">
              {service.tier || 'Microservice'} • {service.region || 'us-east-1'}
            </div>
          </div>
        </div>
        <button onClick={onClose} className="text-[#71717a] hover:text-[#fafafa] p-1.5 rounded hover:bg-[#27272a]">
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* Health & Status Strip */}
        <div className="grid grid-cols-2 gap-2">
          <div className="p-3 rounded bg-[#09090b] border border-[#27272a]">
            <div className="text-[10px] font-mono text-[#71717a] uppercase">State</div>
            <div className="text-xs font-semibold text-emerald-400 mt-1 flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              {service.health || 'Healthy'}
            </div>
          </div>
          <div className="p-3 rounded bg-[#09090b] border border-[#27272a]">
            <div className="text-[10px] font-mono text-[#71717a] uppercase">Replicas</div>
            <div className="text-xs font-semibold text-[#fafafa] mt-1 font-mono">
              {service.replicas || 4} Pods
            </div>
          </div>
        </div>

        {/* Live Telemetry Card */}
        <div className="p-3.5 rounded bg-[#09090b] border border-[#27272a] space-y-3">
          <div className="flex items-center justify-between border-b border-[#27272a] pb-2">
            <span className="text-[10px] font-mono font-semibold uppercase text-[#71717a]">Live Telemetry</span>
            <Activity className="w-3.5 h-3.5 text-[#71717a]" />
          </div>
          <div className="grid grid-cols-2 gap-3 text-xs font-mono">
            <div>
              <div className="text-[#71717a] text-[10px]">p95 Latency</div>
              <div className="text-[#fafafa] font-semibold text-sm">{service.p95_ms || 142} ms</div>
              <div className="text-[9px] text-[#71717a]">SLO: {service.slo_ms || 200} ms</div>
            </div>
            <div>
              <div className="text-[#71717a] text-[10px]">Throughput</div>
              <div className="text-[#fafafa] font-semibold text-sm">{service.rps || 380} req/s</div>
              <div className="text-[9px] text-[#71717a]">Capacity: {(service.replicas || 4) * 60} rps</div>
            </div>
            <div>
              <div className="text-[#71717a] text-[10px]">Error Rate</div>
              <div className="text-emerald-400 font-semibold">{((service.error_rate || 0.002) * 100).toFixed(2)}%</div>
            </div>
            <div>
              <div className="text-[#71717a] text-[10px]">Criticality Tier</div>
              <div className="text-sky-400 font-semibold">Tier {service.criticality || 5} / 5</div>
            </div>
          </div>
        </div>

        {/* Statefulness & Failover */}
        <div className="p-3.5 rounded bg-[#09090b] border border-[#27272a] space-y-2 text-xs">
          <div className="text-[10px] font-mono font-semibold uppercase text-[#71717a]">Architecture Profile</div>
          <div className="flex items-center justify-between py-1 border-b border-[#27272a]/60">
            <span className="text-[#a1a1aa]">Statefulness</span>
            <span className="font-mono text-[#fafafa]">{service.is_stateful ? 'Stateful Storage' : 'Stateless Service'}</span>
          </div>
          <div className="flex items-center justify-between py-1">
            <span className="text-[#a1a1aa]">Failover Replica</span>
            <span className={`font-mono ${service.failover_available === false ? 'text-rose-400' : 'text-emerald-400'}`}>
              {service.failover_available === false ? 'Unavailable (Single Point)' : 'Ready (Multi-AZ)'}
            </span>
          </div>
        </div>

        {/* Quick Simulation Trigger */}
        <div className="p-3.5 rounded bg-[#09090b] border border-[#27272a] space-y-2">
          <div className="text-[10px] font-mono font-semibold uppercase text-[#71717a]">CORTEX Shadow Actions</div>
          <button
            onClick={() => onSimulateAction && onSimulateAction('restart_service', { service: service.id })}
            className="w-full py-2 px-3 rounded bg-zinc-800 hover:bg-zinc-700 text-[#fafafa] text-xs font-mono flex items-center justify-between transition-colors cursor-pointer"
          >
            <span>Simulate Service Restart</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={() => onSimulateAction && onSimulateAction('scale_deployment', { deployment: service.id, replicas: (service.replicas || 4) + 3 })}
            className="w-full py-2 px-3 rounded bg-zinc-800 hover:bg-zinc-700 text-[#fafafa] text-xs font-mono flex items-center justify-between transition-colors cursor-pointer"
          >
            <span>Simulate Scale +3 Replicas</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </div>
  );
};
