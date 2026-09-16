import React from 'react';
import {
  Cloud,
  CheckCircle2,
  Server,
  Network,
  Cpu,
  ShieldCheck,
  Radio
} from 'lucide-react';

export const CloudProvidersView: React.FC = () => {
  const providers = [
    {
      id: 'k8s-local',
      name: 'Local Kubernetes Control Plane',
      type: 'Kubernetes v1.31',
      region: 'localhost / on-premise',
      status: 'CONNECTED',
      nodes: 3,
      pods: 24,
      deployments: 8,
      isPrimary: true
    },
    {
      id: 'aws-east',
      name: 'Amazon Web Services (AWS)',
      type: 'EKS + RDS Aurora + ElastiCache',
      region: 'us-east-1 (N. Virginia)',
      status: 'SIMULATED',
      nodes: 12,
      pods: 86,
      deployments: 14,
      isPrimary: false
    },
    {
      id: 'azure-east',
      name: 'Microsoft Azure',
      type: 'AKS + Azure Postgres Flexible',
      region: 'eastus (Virginia)',
      status: 'SIMULATED',
      nodes: 8,
      pods: 48,
      deployments: 10,
      isPrimary: false
    },
    {
      id: 'gcp-central',
      name: 'Google Cloud Platform (GCP)',
      type: 'GKE Autopilot + Cloud SQL',
      region: 'us-central1 (Iowa)',
      status: 'SIMULATED',
      nodes: 10,
      pods: 64,
      deployments: 12,
      isPrimary: false
    }
  ];

  return (
    <div className="flex-1 p-6 space-y-6 overflow-y-auto bg-[#09090b] text-[#fafafa] font-mono">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-[#27272a] pb-5">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-[#fafafa] flex items-center gap-2.5">
            <Cloud className="w-5 h-5 text-sky-400" />
            Cloud Provider Neutrality Hub
          </h2>
          <p className="text-xs text-[#a1a1aa] mt-1 font-sans">
            CORTEX operates as an abstracted cloud-agnostic control plane, interfacing seamlessly with Kubernetes, AWS, Azure, and GCP.
          </p>
        </div>

        <div className="flex items-center gap-2 text-xs">
          <span className="px-2.5 py-1 rounded bg-emerald-950 text-emerald-400 border border-emerald-800 flex items-center gap-1.5">
            <Radio className="w-3.5 h-3.5 animate-pulse" />
            4 PROVIDERS REGISTERED
          </span>
        </div>
      </div>

      {/* Provider Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {providers.map(p => (
          <div
            key={p.id}
            className={`p-5 rounded-lg border transition-all ${
              p.isPrimary
                ? 'bg-[#121620] border-sky-600 shadow-[0_0_15px_rgba(14,165,233,0.15)]'
                : 'bg-[#101014] border-[#27272a]'
            }`}
          >
            <div className="flex items-center justify-between mb-2">
              <span className="font-bold text-sm text-[#fafafa] font-sans">
                {p.name}
              </span>
              <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                p.status === 'CONNECTED'
                  ? 'bg-emerald-950 text-emerald-400 border border-emerald-800'
                  : 'bg-zinc-800 text-zinc-300 border border-zinc-700'
              }`}>
                {p.status}
              </span>
            </div>

            <div className="text-xs text-[#a1a1aa] font-sans">
              {p.type} • <span className="font-mono text-[11px] text-[#71717a]">{p.region}</span>
            </div>

            <div className="grid grid-cols-3 gap-2 mt-4 text-center">
              <div className="p-2 rounded bg-[#09090b] border border-[#27272a]">
                <div className="text-[10px] text-[#71717a]">NODES</div>
                <div className="text-base font-bold text-[#fafafa] mt-0.5">{p.nodes}</div>
              </div>
              <div className="p-2 rounded bg-[#09090b] border border-[#27272a]">
                <div className="text-[10px] text-[#71717a]">PODS</div>
                <div className="text-base font-bold text-sky-400 mt-0.5">{p.pods}</div>
              </div>
              <div className="p-2 rounded bg-[#09090b] border border-[#27272a]">
                <div className="text-[10px] text-[#71717a]">SERVICES</div>
                <div className="text-base font-bold text-[#fafafa] mt-0.5">{p.deployments}</div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
