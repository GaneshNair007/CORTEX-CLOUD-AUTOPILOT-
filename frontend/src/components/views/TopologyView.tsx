import React, { useState } from 'react';
import {
  Network,
  Layers,
  ShieldAlert,
  Sliders,
  CheckCircle,
  AlertTriangle,
  Flame,
  Info,
  RefreshCw,
  Search
} from 'lucide-react';
import { api } from '../../services/api';
import { ServiceHealthItem } from '../../types';

interface TopologyViewProps {
  onSelectService: (service: ServiceHealthItem) => void;
}

export const TopologyView: React.FC<TopologyViewProps> = ({ onSelectService }) => {
  const [selectedNode, setSelectedNode] = useState<string>('payment-api');
  const [isSimulatingBlast, setIsSimulatingBlast] = useState<boolean>(true);
  const [tierFilter, setTierFilter] = useState<string>('ALL');
  const [blastResult, setBlastResult] = useState<any>({
    blast_radius: 3,
    score: 68,
    affected_services: ['payment-api', 'order-service', 'api-gateway'],
    criticality: 'HIGH',
    recommendation: 'Block autonomous restart in production; require human approval.'
  });

  const nodes = [
    { id: 'ingress', name: 'Ingress Controller', tier: 'edge', status: 'Healthy', rps: 1840, errorRate: 0.01, p95: 12, x: 100, y: 220, deps: [] },
    { id: 'api-gateway', name: 'API Gateway', tier: 'gateway', status: 'Healthy', rps: 1840, errorRate: 0.02, p95: 28, x: 300, y: 220, deps: ['ingress'] },
    { id: 'auth-service', name: 'Auth Service', tier: 'service', status: 'Healthy', rps: 420, errorRate: 0.05, p95: 45, x: 520, y: 100, deps: ['api-gateway'] },
    { id: 'order-service', name: 'Order Service', tier: 'service', status: 'Healthy', rps: 640, errorRate: 0.12, p95: 72, x: 520, y: 220, deps: ['api-gateway'] },
    { id: 'payment-api', name: 'Payment API', tier: 'service', status: 'Degraded', rps: 780, errorRate: 4.82, p95: 420, x: 520, y: 340, deps: ['api-gateway'] },
    { id: 'redis-cache', name: 'Redis Cluster', tier: 'cache', status: 'Healthy', rps: 1450, errorRate: 0.0, p95: 4, x: 760, y: 100, deps: ['auth-service', 'order-service'] },
    { id: 'postgres-primary', name: 'PostgreSQL Primary', tier: 'database', status: 'Warning', rps: 820, errorRate: 1.15, p95: 140, x: 760, y: 280, deps: ['order-service', 'payment-api'] },
    { id: 'coredns', name: 'CoreDNS DaemonSet', tier: 'infra', status: 'Healthy', rps: 2900, errorRate: 0.0, p95: 2, x: 300, y: 380, deps: [] }
  ];

  const handleSimulateMutation = async (nodeId: string) => {
    setSelectedNode(nodeId);
    try {
      const res = await api.getBlastRadius('restart_database', { service: nodeId });
      setBlastResult(res);
    } catch (e) {
      // Fallback calculation
      const affected = nodeId === 'postgres-primary'
        ? ['postgres-primary', 'payment-api', 'order-service', 'api-gateway']
        : nodeId === 'payment-api'
        ? ['payment-api', 'order-service', 'api-gateway']
        : [nodeId];
      setBlastResult({
        blast_radius: affected.length,
        score: affected.length * 24,
        affected_services: affected,
        criticality: affected.length > 2 ? 'HIGH' : 'LOW',
        recommendation: affected.length > 2 ? 'Requires SRE Lead authorization' : 'Safe to proceed under L2 guard'
      });
    }
  };

  const filteredNodes = nodes.filter(n => tierFilter === 'ALL' || n.tier === tierFilter);

  return (
    <div className="flex-1 flex flex-col h-full bg-[#09090b] text-[#fafafa] overflow-hidden">
      {/* Top Filter & Blast Mode Bar */}
      <div className="h-14 border-b border-[#27272a] bg-[#0c0c0e] px-6 flex items-center justify-between shrink-0 text-xs font-mono">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 font-semibold text-[#fafafa]">
            <Network className="w-4 h-4 text-sky-400" />
            <span>TOPOLOGY DEPENDENCY GRAPH</span>
          </div>

          <div className="hidden md:flex items-center gap-1 bg-[#18181b] border border-[#27272a] rounded p-0.5">
            {['ALL', 'edge', 'gateway', 'service', 'database', 'cache'].map(tier => (
              <button
                key={tier}
                onClick={() => setTierFilter(tier)}
                className={`px-2 py-1 rounded uppercase text-[10px] transition-colors cursor-pointer ${
                  tierFilter === tier ? 'bg-[#27272a] text-[#fafafa] font-bold' : 'text-[#71717a] hover:text-[#a1a1aa]'
                }`}
              >
                {tier}
              </button>
            ))}
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => setIsSimulatingBlast(!isSimulatingBlast)}
            className={`px-3 py-1 rounded border text-xs font-mono flex items-center gap-1.5 transition-colors cursor-pointer ${
              isSimulatingBlast
                ? 'bg-amber-950/80 text-amber-300 border-amber-800'
                : 'bg-[#18181b] text-[#a1a1aa] border-[#27272a] hover:text-[#fafafa]'
            }`}
          >
            <ShieldAlert className="w-3.5 h-3.5" />
            <span>BLAST RADIUS OVERLAY: {isSimulatingBlast ? 'ON' : 'OFF'}</span>
          </button>
        </div>
      </div>

      {/* Main Canvas & Blast Radius Side Panel */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 overflow-hidden">
        {/* Visual Graph Viewport */}
        <div className="lg:col-span-8 relative bg-[#09090b] p-6 overflow-auto flex items-center justify-center min-h-[460px]">
          <div className="absolute inset-0 bg-[radial-gradient(#27272a_1px,transparent_1px)] [background-size:24px_24px] opacity-30 pointer-events-none" />

          <div className="relative w-full max-w-[900px] h-[450px]">
            {/* Edges */}
            <svg className="absolute inset-0 w-full h-full pointer-events-none">
              <line x1="180" y1="230" x2="300" y2="230" stroke="#3f3f46" strokeWidth="2" />
              <line x1="380" y1="220" x2="520" y2="110" stroke="#3f3f46" strokeWidth="1.5" />
              <line x1="380" y1="230" x2="520" y2="230" stroke="#3f3f46" strokeWidth="1.5" />
              <line x1="380" y1="240" x2="520" y2="350" stroke={isSimulatingBlast ? '#f43f5e' : '#3f3f46'} strokeWidth="2" strokeDasharray={isSimulatingBlast ? '4 4' : 'none'} />
              <line x1="600" y1="110" x2="760" y2="110" stroke="#10b981" strokeWidth="1.5" />
              <line x1="600" y1="230" x2="760" y2="290" stroke="#3f3f46" strokeWidth="1.5" />
              <line x1="600" y1="350" x2="760" y2="290" stroke={isSimulatingBlast ? '#f43f5e' : '#3f3f46'} strokeWidth="2" strokeDasharray={isSimulatingBlast ? '4 4' : 'none'} />
              <line x1="340" y1="260" x2="340" y2="380" stroke="#3f3f46" strokeWidth="1" strokeDasharray="3 3" />
            </svg>

            {filteredNodes.map(node => {
              const isSelected = selectedNode === node.id;
              const isAffected = isSimulatingBlast && blastResult?.affected_services?.includes(node.id);

              return (
                <div
                  key={node.id}
                  onClick={() => handleSimulateMutation(node.id)}
                  style={{ left: `${node.x}px`, top: `${node.y}px` }}
                  className={`absolute w-44 -translate-x-1/2 -translate-y-1/2 p-3 rounded-lg border transition-all cursor-pointer select-none backdrop-blur-md ${
                    isSelected
                      ? 'ring-2 ring-sky-400 bg-[#16161c] border-sky-500'
                      : isAffected
                      ? 'bg-rose-950/40 border-rose-700 shadow-[0_0_15px_rgba(244,63,94,0.3)]'
                      : 'bg-[#121215] border-[#27272a] hover:border-[#3f3f46]'
                  }`}
                >
                  <div className="flex items-center justify-between text-[10px] font-mono text-[#71717a] uppercase mb-1">
                    <span>{node.tier}</span>
                    <span className={`w-2 h-2 rounded-full ${
                      isAffected ? 'bg-rose-500 animate-ping' : node.status === 'Degraded' ? 'bg-rose-500' : 'bg-emerald-400'
                    }`} />
                  </div>
                  <div className="text-xs font-semibold text-[#fafafa] truncate">
                    {node.name}
                  </div>
                  <div className="mt-1 flex items-center justify-between text-[10px] font-mono text-[#a1a1aa]">
                    <span>{node.rps} rps</span>
                    <span className={node.errorRate > 1 ? 'text-rose-400 font-bold' : ''}>
                      p95: {node.p95}ms
                    </span>
                  </div>
                  {isAffected && (
                    <div className="mt-1.5 px-1.5 py-0.5 rounded bg-rose-900/60 text-rose-300 text-[9px] font-mono font-bold text-center">
                      BLAST RADIUS ZONE
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* Blast Radius & Risk Inspector Panel */}
        <div className="lg:col-span-4 border-l border-[#27272a] bg-[#0c0c0e] p-5 overflow-y-auto space-y-5 font-mono text-xs">
          <div>
            <span className="text-[10px] text-[#71717a] uppercase tracking-wider block">
              COUNTERFACTUAL IMPACT ANALYSIS
            </span>
            <h3 className="text-sm font-bold text-[#fafafa] mt-1">
              Target: <span className="text-sky-300">{selectedNode}</span>
            </h3>
          </div>

          {/* Blast Score Meter */}
          <div className="p-4 rounded-lg bg-[#141418] border border-[#27272a] space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs text-[#a1a1aa]">BLAST RADIUS SCORE</span>
              <span className={`text-lg font-bold ${blastResult.score > 50 ? 'text-rose-400' : 'text-emerald-400'}`}>
                {blastResult.score} / 100
              </span>
            </div>
            <div className="w-full bg-[#27272a] h-2 rounded-full overflow-hidden">
              <div
                className={`h-full transition-all duration-500 ${blastResult.score > 50 ? 'bg-rose-500' : 'bg-emerald-400'}`}
                style={{ width: `${blastResult.score}%` }}
              />
            </div>
            <div className="flex items-center justify-between text-[11px] text-[#71717a]">
              <span>CONTAINED (1-30)</span>
              <span>MODERATE (31-60)</span>
              <span>CRITICAL (61-100)</span>
            </div>
          </div>

          {/* Affected Services List */}
          <div className="p-4 rounded-lg bg-[#141418] border border-[#27272a] space-y-2">
            <span className="text-[10px] text-[#71717a] uppercase tracking-wider block">
              DOWNSTREAM AFFECTED SERVICES ({blastResult.affected_services?.length || 0})
            </span>
            <div className="space-y-1.5">
              {(blastResult.affected_services || []).map((srv: string) => (
                <div key={srv} className="flex items-center justify-between p-2 rounded bg-[#09090b] border border-[#27272a]">
                  <span className="text-[#fafafa] font-semibold">{srv}</span>
                  <span className="text-rose-400 text-[10px]">CASCADING RISK</span>
                </div>
              ))}
            </div>
          </div>

          {/* Policy Recommendation */}
          <div className="p-4 rounded-lg bg-amber-950/30 border border-amber-800/60 space-y-2 text-amber-200">
            <div className="flex items-center gap-2 font-bold text-amber-300">
              <AlertTriangle className="w-4 h-4" />
              <span>CORTEX GUARD ADVISORY</span>
            </div>
            <p className="text-[11px] leading-relaxed font-sans">
              {blastResult.recommendation}
            </p>
          </div>

          <button
            onClick={() => {
              const node = nodes.find(n => n.id === selectedNode);
              if (node) onSelectService({
                id: node.id,
                name: node.name,
                tier: node.tier,
                status: node.status,
                rps: node.rps,
                errorRate: node.errorRate,
                p95LatencyMs: node.p95,
                cpuPercent: 50,
                memoryPercent: 60,
                replicas: 6,
                dependencies: node.deps,
                recentEvents: []
              });
            }}
            className="w-full py-2 bg-[#27272a] hover:bg-[#3f3f46] text-[#fafafa] font-semibold rounded text-xs transition-colors cursor-pointer"
          >
            Inspect Node Telemetry Drawer
          </button>
        </div>
      </div>
    </div>
  );
};
