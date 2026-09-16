import React, { useState, useEffect } from 'react';
import {
  Activity,
  AlertTriangle,
  ShieldCheck,
  ShieldAlert,
  ArrowRight,
  TrendingUp,
  Cpu,
  Database,
  Server,
  Zap,
  CheckCircle2,
  XCircle,
  Play,
  RotateCcw,
  Layers,
  Sparkles,
  ChevronRight,
  Clock,
  Radio
} from 'lucide-react';
import { api } from '../../services/api';
import { ServiceHealthItem } from '../../types';

interface CommandCenterViewProps {
  onSelectService: (service: ServiceHealthItem) => void;
  onSelectIncident: (incidentId: string) => void;
  onNavigateRoute: (route: string) => void;
  autonomyLevel: number;
  killSwitchEngaged: boolean;
}

export const CommandCenterView: React.FC<CommandCenterViewProps> = ({
  onSelectService,
  onSelectIncident,
  onNavigateRoute,
  autonomyLevel,
  killSwitchEngaged
}) => {
  const [topologyNodes, setTopologyNodes] = useState<any[]>([]);
  const [topologyEdges, setTopologyEdges] = useState<any[]>([]);
  const [forecastData, setForecastData] = useState<any>(null);
  const [recentEvents, setRecentEvents] = useState<any[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [runningDemo, setRunningDemo] = useState<boolean>(false);
  const [selectedNodeId, setSelectedNodeId] = useState<string>('payment-api');
  const [pipelineResult, setPipelineResult] = useState<any>(null);

  // Fallback initial nodes for instant responsiveness
  const defaultServices = [
    { id: 'ingress', name: 'Ingress Controller', tier: 'edge', status: 'Healthy', rps: 1840, errorRate: 0.01, p95: 12, x: 80, y: 160 },
    { id: 'api-gateway', name: 'API Gateway', tier: 'gateway', status: 'Healthy', rps: 1840, errorRate: 0.02, p95: 28, x: 280, y: 160 },
    { id: 'auth-service', name: 'Auth Service', tier: 'service', status: 'Healthy', rps: 420, errorRate: 0.05, p95: 45, x: 490, y: 60 },
    { id: 'order-service', name: 'Order Service', tier: 'service', status: 'Healthy', rps: 640, errorRate: 0.12, p95: 72, x: 490, y: 160 },
    { id: 'payment-api', name: 'Payment API', tier: 'service', status: 'Degraded', rps: 780, errorRate: 4.82, p95: 420, x: 490, y: 260 },
    { id: 'redis-cache', name: 'Redis Cluster', tier: 'cache', status: 'Healthy', rps: 1450, errorRate: 0.0, p95: 4, x: 720, y: 60 },
    { id: 'postgres-primary', name: 'PostgreSQL Primary', tier: 'database', status: 'Warning', rps: 820, errorRate: 1.15, p95: 140, x: 720, y: 210 },
    { id: 'coredns', name: 'CoreDNS DaemonSet', tier: 'infra', status: 'Healthy', rps: 2900, errorRate: 0.0, p95: 2, x: 280, y: 320 },
  ];

  // Fetch topology and forecast
  useEffect(() => {
    let isMounted = true;
    const loadData = async () => {
      try {
        const [topo, fc, evs] = await Promise.allSettled([
          api.getTopology(),
          api.getForecast(30),
          api.listEvents()
        ]);

        if (!isMounted) return;

        if (topo.status === 'fulfilled' && topo.value?.nodes) {
          setTopologyNodes(topo.value.nodes);
          setTopologyEdges(topo.value.edges || []);
        } else {
          setTopologyNodes(defaultServices);
        }

        if (fc.status === 'fulfilled' && fc.value) {
          setForecastData(fc.value);
        }

        if (evs.status === 'fulfilled' && evs.value?.events) {
          setRecentEvents(evs.value.events.slice(-5).reverse());
        }
      } catch (err) {
        console.error('Command center data fetch error', err);
        setTopologyNodes(defaultServices);
      } finally {
        if (isMounted) setLoading(false);
      }
    };

    loadData();
    const interval = setInterval(loadData, 8000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  const handleRunIncidentDiagnosis = async () => {
    setRunningDemo(true);
    try {
      const result = await api.runPipeline(
        'payment-api',
        'HIGH',
        'p95 Latency 840ms with 4.8% HTTP 504 Gateway Timeouts after v4.6 rollout',
        false
      );
      setPipelineResult(result);
      // Reload events
      const evs = await api.listEvents();
      if (evs.events) setRecentEvents(evs.events.slice(-5).reverse());
    } catch (e: any) {
      console.error('Incident pipeline error', e);
    } finally {
      setRunningDemo(false);
    }
  };

  const handleNodeClick = (node: any) => {
    setSelectedNodeId(node.id);
    onSelectService({
      id: node.id,
      name: node.name || node.label || node.id,
      tier: node.tier || 'service',
      status: node.status || (node.errorRate > 2 ? 'Degraded' : 'Healthy'),
      rps: node.rps || 500,
      errorRate: node.errorRate || 0.1,
      p95LatencyMs: node.p95 || node.p95LatencyMs || 50,
      cpuPercent: 48,
      memoryPercent: 62,
      replicas: 6,
      dependencies: ['redis-cache', 'postgres-primary'],
      recentEvents: ['Config map applied 12m ago', 'HPA target evaluated']
    });
  };

  const selectedNode = topologyNodes.find(n => n.id === selectedNodeId) || defaultServices[4];

  return (
    <div className="flex-1 flex flex-col h-full bg-[#09090b] text-[#fafafa] overflow-hidden">
      {/* Top Operations Status Rail */}
      <div className="h-12 border-b border-[#27272a] bg-[#0c0c0e] px-6 flex items-center justify-between text-xs font-mono shrink-0">
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            <span className="text-[#a1a1aa]">HEALTH:</span>
            <span className="font-semibold text-[#fafafa]">99.96%</span>
          </div>
          <div className="hidden sm:flex items-center gap-2">
            <span className="text-[#71717a]">P95 LATENCY:</span>
            <span className="text-[#fafafa]">142ms</span>
            <span className="text-[10px] text-emerald-400 font-normal">(-18ms vs SLO)</span>
          </div>
          <div className="hidden md:flex items-center gap-2">
            <span className="text-[#71717a]">HOURLY BURN:</span>
            <span className="text-[#fafafa]">$18.42/hr</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-[#71717a]">INCIDENTS:</span>
            <span className="px-1.5 py-0.5 rounded bg-amber-950/80 text-amber-400 border border-amber-800/60 font-semibold">
              1 ACTIVE
            </span>
          </div>
        </div>

        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <span className="text-[#71717a]">AUTONOMY:</span>
            <span className={`px-2 py-0.5 rounded border text-[10px] font-semibold ${
              autonomyLevel === 3 ? 'bg-emerald-950 text-emerald-400 border-emerald-800' :
              autonomyLevel === 2 ? 'bg-sky-950 text-sky-400 border-sky-800' :
              autonomyLevel === 1 ? 'bg-amber-950 text-amber-400 border-amber-800' :
              'bg-zinc-800 text-zinc-400 border-zinc-700'
            }`}>
              {autonomyLevel === 3 ? 'L3 AUTONOMOUS' : autonomyLevel === 2 ? 'L2 GUARDED' : autonomyLevel === 1 ? 'L1 RECOMMEND' : 'L0 OBSERVE'}
            </span>
          </div>
          {killSwitchEngaged && (
            <span className="px-2 py-0.5 rounded bg-rose-950 text-rose-300 border border-rose-700 text-[10px] animate-pulse">
              KILL SWITCH ENGAGED
            </span>
          )}
        </div>
      </div>

      {/* Main Grid: Topology (Left/Center) + CORTEX Decision Card (Right) */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 overflow-hidden">
        {/* Interactive Topology Graph Canvas (Cols 1-8) */}
        <div className="lg:col-span-8 flex flex-col border-r border-[#27272a] bg-[#09090b] relative">
          {/* Canvas Sub-Header */}
          <div className="h-10 px-5 border-b border-[#27272a] flex items-center justify-between bg-[#101014]/60 text-xs">
            <div className="flex items-center gap-2 text-[#a1a1aa] font-mono">
              <Layers className="w-3.5 h-3.5 text-sky-400" />
              <span>LIVE INFRASTRUCTURE GRAPH</span>
              <span className="text-[#52525b]">•</span>
              <span className="text-[11px] text-[#71717a]">{topologyNodes.length} NODES MONITORED</span>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => onNavigateRoute('topology')}
                className="text-[11px] font-mono text-[#a1a1aa] hover:text-[#fafafa] flex items-center gap-1 transition-colors cursor-pointer"
              >
                Fullscreen Topology <ArrowRight className="w-3 h-3" />
              </button>
            </div>
          </div>

          {/* SVG Topology Viewport */}
          <div className="flex-1 relative overflow-auto p-4 flex items-center justify-center min-h-[380px]">
            {/* Grid dot background */}
            <div className="absolute inset-0 bg-[radial-gradient(#27272a_1px,transparent_1px)] [background-size:24px_24px] opacity-40 pointer-events-none" />

            <div className="relative w-full max-w-[840px] h-[360px]">
              {/* Edges */}
              <svg className="absolute inset-0 w-full h-full pointer-events-none">
                <defs>
                  <linearGradient id="edgeGrad" x1="0%" y1="0%" x2="100%" y2="0%">
                    <stop offset="0%" stopColor="#3f3f46" />
                    <stop offset="100%" stopColor="#71717a" />
                  </linearGradient>
                </defs>
                {/* Connect Ingress to API Gateway */}
                <line x1="160" y1="180" x2="280" y2="180" stroke="#3f3f46" strokeWidth="2" strokeDasharray="4 4" className="animate-pulse" />
                {/* Gateway to Auth, Orders, Payments */}
                <line x1="360" y1="170" x2="490" y2="80" stroke="#3f3f46" strokeWidth="1.5" />
                <line x1="360" y1="180" x2="490" y2="180" stroke="#3f3f46" strokeWidth="1.5" />
                <line x1="360" y1="190" x2="490" y2="280" stroke="#f43f5e" strokeWidth="2" strokeDasharray="3 3" />
                {/* Services to Databases / Redis */}
                <line x1="570" y1="80" x2="720" y2="80" stroke="#10b981" strokeWidth="1.5" />
                <line x1="570" y1="180" x2="720" y2="230" stroke="#3f3f46" strokeWidth="1.5" />
                <line x1="570" y1="280" x2="720" y2="230" stroke="#f43f5e" strokeWidth="2" strokeDasharray="4 4" />
                {/* Ingress to CoreDNS */}
                <line x1="320" y1="200" x2="320" y2="320" stroke="#3f3f46" strokeWidth="1" strokeDasharray="2 2" />
              </svg>

              {/* Service Nodes */}
              {(topologyNodes.length > 0 ? topologyNodes : defaultServices).map((node: any) => {
                const isSelected = node.id === selectedNodeId;
                const isDegraded = node.status === 'Degraded' || node.errorRate > 2.0;
                const isWarning = node.status === 'Warning' || (node.errorRate > 0.5 && !isDegraded);

                const left = node.x !== undefined ? `${node.x}px` : '100px';
                const top = node.y !== undefined ? `${node.y}px` : '100px';

                return (
                  <div
                    key={node.id}
                    onClick={() => handleNodeClick(node)}
                    style={{ left, top }}
                    className={`absolute w-36 -translate-x-1/2 -translate-y-1/2 p-2.5 rounded-lg border transition-all cursor-pointer backdrop-blur-md select-none group ${
                      isSelected
                        ? 'ring-2 ring-sky-400 shadow-[0_0_15px_rgba(14,165,233,0.3)]'
                        : ''
                    } ${
                      isDegraded
                        ? 'bg-[#181113] border-rose-800/80 hover:border-rose-600'
                        : isWarning
                        ? 'bg-[#181611] border-amber-800/80 hover:border-amber-600'
                        : 'bg-[#121215] border-[#27272a] hover:border-[#3f3f46]'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-[10px] font-mono uppercase text-[#71717a] truncate max-w-[80px]">
                        {node.tier || 'POD'}
                      </span>
                      <span className={`w-1.5 h-1.5 rounded-full ${
                        isDegraded ? 'bg-rose-500 animate-ping' : isWarning ? 'bg-amber-400' : 'bg-emerald-400'
                      }`} />
                    </div>
                    <div className="text-xs font-semibold text-[#fafafa] truncate group-hover:text-white">
                      {node.name || node.id}
                    </div>
                    <div className="flex items-center justify-between mt-1 text-[10px] font-mono text-[#a1a1aa]">
                      <span>{node.rps || 450} rps</span>
                      <span className={isDegraded ? 'text-rose-400 font-bold' : ''}>
                        {node.p95 ? `${node.p95}ms` : '42ms'}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Lower Quick Controls Toolbar */}
          <div className="h-12 border-t border-[#27272a] bg-[#0c0c0e] px-4 flex items-center justify-between text-xs">
            <div className="flex items-center gap-3">
              <span className="text-[11px] font-mono text-[#71717a]">LIVE CONTROLS:</span>
              <button
                disabled={runningDemo}
                onClick={handleRunIncidentDiagnosis}
                className="px-2.5 py-1 bg-sky-600 hover:bg-sky-500 disabled:bg-zinc-800 text-white text-xs font-medium rounded flex items-center gap-1.5 transition-colors cursor-pointer"
              >
                <Play className="w-3 h-3" />
                <span>{runningDemo ? 'Diagnosing...' : 'Trigger Incident Self-Healing'}</span>
              </button>
              <button
                onClick={() => onNavigateRoute('simulator')}
                className="px-2.5 py-1 bg-[#18181b] hover:bg-[#27272a] text-[#fafafa] border border-[#27272a] text-xs font-mono rounded flex items-center gap-1.5 transition-colors cursor-pointer"
              >
                <Cpu className="w-3 h-3 text-sky-400" />
                <span>Simulate Shadow Mutation</span>
              </button>
            </div>
            <div className="hidden sm:flex items-center gap-2 text-[11px] font-mono text-[#71717a]">
              <span>CLICK ANY NODE TO INSPECT METRICS</span>
            </div>
          </div>
        </div>

        {/* CORTEX Active Decision & Governance Inspector (Cols 9-12) */}
        <div className="lg:col-span-4 flex flex-col bg-[#0c0c0e] overflow-y-auto">
          {/* Decision Header */}
          <div className="h-10 px-5 border-b border-[#27272a] flex items-center justify-between bg-[#141418] text-xs">
            <div className="flex items-center gap-2 font-mono text-[#fafafa]">
              <Sparkles className="w-3.5 h-3.5 text-sky-400" />
              <span className="font-semibold">CORTEX CONTROL LOOP</span>
            </div>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-800">
              GUARD ACTIVE
            </span>
          </div>

          {/* Active Incident / Autonomous Candidate Card */}
          <div className="p-4 space-y-4 text-xs font-sans">
            <div className="p-3 rounded-lg border border-[#27272a] bg-[#141418] space-y-3">
              <div className="flex items-center justify-between">
                <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-rose-950 text-rose-300 border border-rose-800">
                  INC-1042 • HIGH
                </span>
                <span className="text-[11px] font-mono text-[#71717a] flex items-center gap-1">
                  <Clock className="w-3 h-3" /> 2m ago
                </span>
              </div>
              <div>
                <h4 className="font-semibold text-sm text-[#fafafa]">
                  Payment API Connection Spike & Gateway Timeouts
                </h4>
                <p className="text-[11px] text-[#a1a1aa] mt-1 leading-relaxed">
                  p95 latency breached 800ms threshold. RAG matched postmortem <code className="text-[#fafafa] bg-zinc-800 px-1 py-0.5 rounded">INC-005</code> and Runbook <code className="text-[#fafafa] bg-zinc-800 px-1 py-0.5 rounded">RB-001</code>.
                </p>
              </div>

              {/* Self-Critique & Recommendation */}
              <div className="p-2.5 rounded bg-[#09090b] border border-[#27272a] space-y-1.5 text-[11px] font-mono">
                <div className="text-amber-400 font-semibold flex items-center gap-1.5">
                  <ShieldAlert className="w-3.5 h-3.5" />
                  <span>CORTEX INTERCEPTION:</span>
                </div>
                <div className="text-[#fafafa]">
                  Action Proposal: <span className="text-sky-300">scale_replicas (6 → 9)</span>
                </div>
                <div className="text-[#a1a1aa]">
                  Risk Score: <span className="text-emerald-400 font-bold">24/100 (LOW)</span> • Blast Radius: 1 service
                </div>
                <div className="text-emerald-400 flex items-center gap-1">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  <span>Passed all 5 policy guardrails. Safe to auto-apply.</span>
                </div>
              </div>

              <div className="flex items-center gap-2 pt-1">
                <button
                  onClick={() => onNavigateRoute('approvals')}
                  className="flex-1 py-1.5 bg-[#27272a] hover:bg-[#3f3f46] text-[#fafafa] text-xs font-medium rounded transition-colors cursor-pointer text-center"
                >
                  View Approvals Queue
                </button>
                <button
                  onClick={() => onSelectIncident('INC-1042')}
                  className="px-3 py-1.5 bg-sky-600 hover:bg-sky-500 text-white text-xs font-medium rounded transition-colors cursor-pointer flex items-center gap-1"
                >
                  Forensics <ChevronRight className="w-3 h-3" />
                </button>
              </div>
            </div>

            {/* Selected Service Diagnostic */}
            <div className="p-3 rounded-lg border border-[#27272a] bg-[#141418] space-y-2.5">
              <div className="text-[10px] font-mono text-[#71717a] uppercase tracking-wider">
                NODE TELEMETRY: {selectedNode.name || selectedNode.id}
              </div>
              <div className="grid grid-cols-2 gap-2 text-xs font-mono">
                <div className="p-2 rounded bg-[#09090b] border border-[#27272a]">
                  <div className="text-[#71717a] text-[10px]">CURRENT RPS</div>
                  <div className="text-[#fafafa] font-semibold text-sm">{selectedNode.rps || 780}</div>
                </div>
                <div className="p-2 rounded bg-[#09090b] border border-[#27272a]">
                  <div className="text-[#71717a] text-[10px]">P95 LATENCY</div>
                  <div className="text-amber-400 font-semibold text-sm">{selectedNode.p95 || 420}ms</div>
                </div>
                <div className="p-2 rounded bg-[#09090b] border border-[#27272a]">
                  <div className="text-[#71717a] text-[10px]">ERROR RATE</div>
                  <div className="text-rose-400 font-semibold text-sm">{selectedNode.errorRate || 4.8}%</div>
                </div>
                <div className="p-2 rounded bg-[#09090b] border border-[#27272a]">
                  <div className="text-[#71717a] text-[10px]">ACTIVE REPLICAS</div>
                  <div className="text-sky-400 font-semibold text-sm">6 (Max 15)</div>
                </div>
              </div>
              <button
                onClick={() => handleNodeClick(selectedNode)}
                className="w-full py-1.5 border border-[#27272a] hover:border-[#3f3f46] text-[#a1a1aa] hover:text-[#fafafa] rounded text-xs font-mono transition-colors cursor-pointer"
              >
                Open Full Node Inspector
              </button>
            </div>

            {/* Live Operational Event Stream */}
            <div className="space-y-2">
              <div className="flex items-center justify-between text-[10px] font-mono text-[#71717a] uppercase">
                <span>RECENT AUDIT LEDGER EVENTS</span>
                <button
                  onClick={() => onNavigateRoute('audit')}
                  className="hover:text-[#fafafa] transition-colors"
                >
                  VIEW ALL
                </button>
              </div>
              <div className="space-y-1.5 font-mono text-[11px]">
                {recentEvents.length > 0 ? (
                  recentEvents.map((ev, i) => (
                    <div key={i} className="p-2 rounded bg-[#101014] border border-[#222226] flex items-start gap-2">
                      <span className="text-[#71717a] text-[10px] mt-0.5">{ev.time || '14:28'}</span>
                      <div className="flex-1 truncate">
                        <span className="text-sky-300 font-semibold">{ev.event_type || 'SCALE_ACTION'}</span>
                        <span className="text-[#71717a] block truncate text-[10px]">{ev.details || 'Replicas adjusted from 6 to 9'}</span>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="p-2 rounded bg-[#101014] border border-[#222226] text-[#71717a] text-[11px]">
                    No unhandled audit ledger events.
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Lower Ribbon: 30-Min Forecast & Verification Strip */}
      <div className="h-16 border-t border-[#27272a] bg-[#0c0c0e] px-6 flex items-center justify-between shrink-0 font-mono text-xs">
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2 text-sky-400">
            <TrendingUp className="w-4 h-4" />
            <span className="font-semibold text-xs">30-MIN FORECAST:</span>
          </div>
          <div className="flex items-center gap-4 text-xs text-[#a1a1aa]">
            <div>
              <span className="text-[#71717a]">TRAFFIC SURGE:</span>{' '}
              <span className="text-[#fafafa] font-semibold">+42% at T+15m (680 rps)</span>
            </div>
            <div className="hidden md:block">
              <span className="text-[#71717a]">OPTIMAL REPLICAS:</span>{' '}
              <span className="text-emerald-400 font-semibold">9 Pods (+3 pro-active)</span>
            </div>
            <div className="hidden lg:block">
              <span className="text-[#71717a]">EST. SAVINGS VS REACTIVE:</span>{' '}
              <span className="text-[#fafafa] font-semibold">$34.10/day</span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => onNavigateRoute('predictions')}
            className="px-3 py-1 rounded bg-[#18181b] hover:bg-[#27272a] text-[#fafafa] border border-[#27272a] text-xs font-mono transition-colors cursor-pointer"
          >
            Detailed Predictions
          </button>
          <button
            onClick={() => onNavigateRoute('optimizer')}
            className="px-3 py-1 rounded bg-sky-600/20 hover:bg-sky-600/30 text-sky-300 border border-sky-700/50 text-xs font-mono transition-colors cursor-pointer"
          >
            Optimizer Pareto
          </button>
        </div>
      </div>
    </div>
  );
};
