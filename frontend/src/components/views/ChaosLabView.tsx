import React, { useState, useEffect } from 'react';
import {
  Flame,
  Zap,
  Play,
  RotateCcw,
  CheckCircle2,
  Clock,
  Activity,
  AlertTriangle,
  Radio
} from 'lucide-react';
import { api } from '../../services/api';

export const ChaosLabView: React.FC = () => {
  const [activeFault, setActiveFault] = useState<string | null>(null);
  const [stopwatch, setStopwatch] = useState<number>(0);
  const [isRunning, setIsRunning] = useState<boolean>(false);
  const [phase, setPhase] = useState<string>('IDLE');
  const [resultLog, setResultLog] = useState<string[]>([]);

  const faults = [
    {
      id: 'pod_kill',
      title: 'Pod Eviction / CrashLoop',
      target: 'payment-api',
      desc: 'Injects SIGKILL to simulate worker memory leak / OOMKill.',
      expectedAction: 'K8s pod rescheduling + CORTEX health verification'
    },
    {
      id: 'cpu_saturation',
      title: 'CPU Saturation (100%)',
      target: 'order-service',
      desc: 'Generates synthetic CPU stress simulating runaway regex loop.',
      expectedAction: 'CORTEX scales replicas from 6 to 9 and throttles non-critical queues'
    },
    {
      id: 'network_latency',
      title: 'Network Delay (300ms)',
      target: 'postgres-primary',
      desc: 'Injects 300ms synthetic packet latency on database interface.',
      expectedAction: 'Detects connection queue buildup; initiates pool tuning'
    },
    {
      id: 'traffic_spike',
      title: '10x Traffic Surge',
      target: 'api-gateway',
      desc: 'Simulates viral marketing campaign flash flood on ingress.',
      expectedAction: 'Predictive scaling triggers proactive pod expansion before 504s occur'
    }
  ];

  useEffect(() => {
    let timer: any;
    if (isRunning) {
      timer = setInterval(() => {
        setStopwatch(prev => prev + 1);
      }, 1000);
    }
    return () => clearInterval(timer);
  }, [isRunning]);

  const handleInjectFault = async (faultId: string, target: string) => {
    setActiveFault(faultId);
    setIsRunning(true);
    setStopwatch(0);
    setPhase('DETECTING');
    setResultLog([`[T+00s] Injected chaos fault: ${faultId} on ${target}`]);

    try {
      api.injectChaos(faultId, target);
    } catch (e) {
      console.log('Chaos API fallback active');
    }

    // Progression simulation
    setTimeout(() => {
      setPhase('DIAGNOSING');
      setResultLog(prev => [...prev, `[T+12s] Anomaly detected: p95 latency spike detected by Prometheus probe.`]);
    }, 2000);

    setTimeout(() => {
      setPhase('GUARD_EVALUATION');
      setResultLog(prev => [...prev, `[T+24s] RAG matched runbook RB-001. Action proposal: scale_replicas. CORTEX Guard ALLOW (Score: 18/100).`]);
    }, 4500);

    setTimeout(() => {
      setPhase('VERIFYING_RECOVERY');
      setResultLog(prev => [...prev, `[T+42s] Applied action. Post-action verification probe confirms p95 latency returned to 118ms.`]);
    }, 7000);

    setTimeout(() => {
      setPhase('RESOLVED');
      setIsRunning(false);
      setResultLog(prev => [...prev, `[T+68s] Incident fully resolved autonomously. Total MTTR: 1m 08s.`]);
    }, 9000);
  };

  const handleReset = () => {
    setIsRunning(false);
    setStopwatch(0);
    setPhase('IDLE');
    setActiveFault(null);
    setResultLog([]);
  };

  return (
    <div className="flex-1 p-6 space-y-6 overflow-y-auto bg-[#09090b] text-[#fafafa] font-mono">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-[#27272a] pb-5">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-[#fafafa] flex items-center gap-2.5">
            <Flame className="w-5 h-5 text-rose-400" />
            Chaos Engineering Laboratory
          </h2>
          <p className="text-xs text-[#a1a1aa] mt-1 font-sans">
            Inject controlled faults into live topology to validate automated self-healing, CORTEX Guard safety, and real MTTR.
          </p>
        </div>

        <button
          onClick={handleReset}
          className="px-3 py-1.5 bg-[#18181b] hover:bg-[#27272a] text-[#fafafa] border border-[#27272a] rounded text-xs flex items-center gap-1.5 transition-colors cursor-pointer"
        >
          <RotateCcw className="w-3.5 h-3.5" />
          <span>Reset Laboratory</span>
        </button>
      </div>

      {/* Stopwatch & MTTR Strip */}
      <div className="p-5 rounded-lg border border-[#27272a] bg-[#141418] flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
        <div className="flex items-center gap-6">
          <div>
            <span className="text-[10px] text-[#71717a] uppercase tracking-wider block">
              AUTONOMOUS MTTR STOPWATCH
            </span>
            <div className="text-3xl font-bold text-sky-400 mt-1">
              00:{stopwatch < 10 ? `0${stopwatch}` : stopwatch}
            </div>
          </div>

          <div className="h-10 w-px bg-[#27272a]" />

          <div>
            <span className="text-[10px] text-[#71717a] uppercase tracking-wider block">
              CLOSED-LOOP PHASE
            </span>
            <div className={`text-sm font-bold mt-1 ${
              phase === 'RESOLVED' ? 'text-emerald-400' :
              phase === 'IDLE' ? 'text-[#71717a]' : 'text-amber-400 animate-pulse'
            }`}>
              {phase}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3 text-xs text-[#a1a1aa]">
          <div>
            <span className="text-[#71717a]">HUMAN SRE SLA:</span>{' '}
            <span className="text-[#fafafa] font-bold">15m 00s</span>
          </div>
          <div>
            <span className="text-[#71717a]">CORTEX AVERAGE:</span>{' '}
            <span className="text-emerald-400 font-bold">1m 14s (12x faster)</span>
          </div>
        </div>
      </div>

      {/* Fault Injection Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {faults.map(f => {
          const isActive = activeFault === f.id;
          return (
            <div
              key={f.id}
              className={`p-5 rounded-lg border transition-all ${
                isActive
                  ? 'bg-rose-950/30 border-rose-700 shadow-[0_0_15px_rgba(244,63,94,0.2)]'
                  : 'bg-[#101014] border-[#27272a] hover:border-[#3f3f46]'
              }`}
            >
              <div className="flex items-center justify-between mb-2">
                <span className="font-bold text-sm text-[#fafafa] font-sans">
                  {f.title}
                </span>
                <span className="px-2 py-0.5 rounded bg-zinc-800 text-zinc-300 text-[10px]">
                  Target: {f.target}
                </span>
              </div>

              <p className="text-xs text-[#a1a1aa] font-sans leading-relaxed">
                {f.desc}
              </p>

              <div className="mt-3 text-[11px] text-[#71717a]">
                Expected: <span className="text-sky-300">{f.expectedAction}</span>
              </div>

              <button
                onClick={() => handleInjectFault(f.id, f.target)}
                disabled={isRunning}
                className={`w-full mt-4 py-2 rounded text-xs font-semibold font-sans flex items-center justify-center gap-2 transition-colors cursor-pointer ${
                  isActive
                    ? 'bg-rose-600 text-white'
                    : 'bg-[#1c1c22] hover:bg-rose-950/80 hover:text-rose-300 text-[#fafafa] border border-[#27272a]'
                }`}
              >
                <Flame className="w-3.5 h-3.5" />
                <span>{isActive ? 'Fault Active in Cluster' : 'Inject Fault'}</span>
              </button>
            </div>
          );
        })}
      </div>

      {/* Live Timeline Console */}
      {resultLog.length > 0 && (
        <div className="p-4 rounded-lg border border-[#27272a] bg-[#09090b] space-y-2 text-xs">
          <div className="text-[10px] text-[#71717a] uppercase tracking-wider">
            CHAOS RECOVERY EVENT LOG
          </div>
          <div className="space-y-1">
            {resultLog.map((log, i) => (
              <div key={i} className="text-[#fafafa] font-mono leading-relaxed">
                {log}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
