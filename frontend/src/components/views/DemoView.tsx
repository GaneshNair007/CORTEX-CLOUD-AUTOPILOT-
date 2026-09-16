import React, { useState } from 'react';
import {
  PlayCircle,
  ShieldAlert,
  ShieldCheck,
  CheckCircle2,
  XCircle,
  RotateCcw,
  Sparkles,
  ArrowRight,
  Clock,
  Cpu,
  Database,
  Flame,
  Activity
} from 'lucide-react';
import { api } from '../../services/api';

export const DemoView: React.FC = () => {
  const [runningDemo, setRunningDemo] = useState<string | null>(null);
  const [demoStep, setDemoStep] = useState<number>(0);
  const [demoLogs, setDemoLogs] = useState<string[]>([]);

  const runSafeDemo = async () => {
    setRunningDemo('SAFE_SELF_HEALING');
    setDemoStep(1);
    setDemoLogs(['[T+00s] STAGE 1: OBSERVE — Ingestion probe flags Payment API p95 latency: 840ms with 4.8% 504 errors.']);

    setTimeout(() => {
      setDemoStep(2);
      setDemoLogs(prev => [...prev, '[T+10s] STAGE 2: UNDERSTAND — ChromaDB vector retrieval matches Runbook RB-001 and Postmortem INC-005. LLM self-critique isolates connection starvation.']);
    }, 1800);

    setTimeout(() => {
      setDemoStep(3);
      setDemoLogs(prev => [...prev, '[T+22s] STAGE 3: PREDICT — Workload forecast estimates +42% traffic growth over the next 15 minutes.']);
    }, 3600);

    setTimeout(() => {
      setDemoStep(4);
      setDemoLogs(prev => [...prev, '[T+34s] STAGE 4: SIMULATE — Counterfactual Digital Twin simulates scaling from 6 to 9 pods. Shadow state shows latency drops from 420ms to 128ms with zero downstream degradation.']);
    }, 5400);

    setTimeout(() => {
      setDemoStep(5);
      setDemoLogs(prev => [...prev, '[T+46s] STAGE 5: AUTHORIZE — CORTEX Guard evaluates proposed action: Risk score 18/100, blast radius 1 service. Result: ALLOWED under L2 Guard.']);
    }, 7200);

    setTimeout(() => {
      setDemoStep(6);
      setDemoLogs(prev => [...prev, '[T+58s] STAGE 6: ACT & VERIFY — Kubernetes actuator applies deployment patch. Telemetry verifier confirms p95 latency restored to 118ms and error rate drops to 0.08%.']);
    }, 9000);

    setTimeout(() => {
      setDemoStep(7);
      setDemoLogs(prev => [...prev, '[T+70s] STAGE 7: LEARN — Resolution details cryptographically hashed and appended to tamper-evident audit ledger block #04.']);
      setRunningDemo(null);
    }, 10800);

    try {
      await api.runPipeline('payment-api', 'HIGH', 'p95 latency spike 840ms', false);
    } catch (e) {
      console.log('Pipeline run recorded');
    }
  };

  const runUnsafeDemo = async () => {
    setRunningDemo('UNSAFE_BLOCK');
    setDemoStep(1);
    setDemoLogs(['[T+00s] Simulating an unconstrained AI model attempting a mutating database restart on postgres-primary...']);

    setTimeout(() => {
      setDemoStep(2);
      setDemoLogs(prev => [...prev, '[T+08s] CORTEX GUARD INTERCEPTION: Invariant evaluation kernel intercepts command: restart_database.']);
    }, 1500);

    setTimeout(() => {
      setDemoStep(3);
      setDemoLogs(prev => [...prev, '[T+18s] BLAST RADIUS ASSESSMENT: 4 critical downstream services affected (Payment API, Order Service, API Gateway, Checkout). Calculated Risk Score: 94 / 100.']);
    }, 3000);

    setTimeout(() => {
      setDemoStep(4);
      setDemoLogs(prev => [...prev, '[T+28s] POLICY VIOLATION: Rule POL-001 (Zero Production Outage Invariant) triggered. Unconditionally BLOCKED before shell dispatch.']);
    }, 4500);

    setTimeout(() => {
      setDemoStep(5);
      setDemoLogs(prev => [...prev, '[T+38s] CORTEX proposes safe counter-action: promote_standby_replica with zero downtime. Outage prevented!']);
      setRunningDemo(null);
    }, 6000);

    try {
      await api.runPipeline('postgres-primary', 'CRITICAL', 'Direct database restart attempt', true);
    } catch (e) {
      console.log('Unsafe simulation intercepted');
    }
  };

  const handleReset = () => {
    setRunningDemo(null);
    setDemoStep(0);
    setDemoLogs([]);
  };

  return (
    <div className="flex-1 p-6 space-y-6 overflow-y-auto bg-[#09090b] text-[#fafafa] font-mono">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-[#27272a] pb-5">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-[#fafafa] flex items-center gap-2.5">
            <PlayCircle className="w-5 h-5 text-sky-400" />
            Interactive Control Plane Walkthrough
          </h2>
          <p className="text-xs text-[#a1a1aa] mt-1 font-sans">
            1-click guided interactive demonstration showcasing end-to-end autonomous healing and defensive safety gating.
          </p>
        </div>

        <button
          onClick={handleReset}
          className="px-3 py-1.5 bg-[#18181b] hover:bg-[#27272a] text-[#fafafa] border border-[#27272a] rounded text-xs flex items-center gap-1.5 transition-colors cursor-pointer"
        >
          <RotateCcw className="w-3.5 h-3.5" />
          <span>Reset Demo Console</span>
        </button>
      </div>

      {/* Two Demo Launcher Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Demo 1: Autonomous Healing */}
        <div className="p-5 rounded-lg border border-sky-800/60 bg-[#101420] space-y-4 shadow-[0_0_20px_rgba(14,165,233,0.1)]">
          <div className="flex items-center justify-between">
            <span className="px-2 py-0.5 rounded bg-sky-950 text-sky-300 border border-sky-800 text-[10px] font-bold">
              SCENARIO A • CLOSED LOOP
            </span>
            <Sparkles className="w-4 h-4 text-sky-400" />
          </div>

          <div>
            <h3 className="text-base font-bold text-[#fafafa] font-sans">
              Autonomous Incident Self-Healing
            </h3>
            <p className="text-xs text-[#a1a1aa] font-sans mt-1 leading-relaxed">
              Triggers a live Payment API latency breach. Watch CORTEX traverse all stages: Observe $\rightarrow$ Understand $\rightarrow$ Predict $\rightarrow$ Simulate $\rightarrow$ Authorize $\rightarrow$ Act $\rightarrow$ Verify $\rightarrow$ Learn.
            </p>
          </div>

          <button
            onClick={runSafeDemo}
            disabled={runningDemo !== null}
            className="w-full py-2.5 bg-sky-600 hover:bg-sky-500 disabled:bg-zinc-800 text-white rounded font-sans text-xs font-semibold flex items-center justify-center gap-2 transition-colors cursor-pointer"
          >
            <PlayCircle className="w-4 h-4" />
            <span>{runningDemo === 'SAFE_SELF_HEALING' ? 'Running Self-Healing...' : 'Start Autonomous Incident Demo'}</span>
          </button>
        </div>

        {/* Demo 2: Safety Interception */}
        <div className="p-5 rounded-lg border border-rose-800/60 bg-[#161012] space-y-4 shadow-[0_0_20px_rgba(244,63,94,0.1)]">
          <div className="flex items-center justify-between">
            <span className="px-2 py-0.5 rounded bg-rose-950 text-rose-300 border border-rose-800 text-[10px] font-bold">
              SCENARIO B • DEFENSIVE GATE
            </span>
            <ShieldAlert className="w-4 h-4 text-rose-400" />
          </div>

          <div>
            <h3 className="text-base font-bold text-[#fafafa] font-sans">
              CORTEX Guard Blocks Dangerous Mutation
            </h3>
            <p className="text-xs text-[#a1a1aa] font-sans mt-1 leading-relaxed">
              Simulates an AI model hallucinating an unsafe <code className="text-rose-300">restart_database</code> command. Watch CORTEX Guard intercept, assess blast radius, and unconditionally block the destructive action.
            </p>
          </div>

          <button
            onClick={runUnsafeDemo}
            disabled={runningDemo !== null}
            className="w-full py-2.5 bg-rose-700 hover:bg-rose-600 disabled:bg-zinc-800 text-white rounded font-sans text-xs font-semibold flex items-center justify-center gap-2 transition-colors cursor-pointer"
          >
            <ShieldAlert className="w-4 h-4" />
            <span>{runningDemo === 'UNSAFE_BLOCK' ? 'Intercepting Action...' : 'Run Unsafe-Action Defense Demo'}</span>
          </button>
        </div>
      </div>

      {/* Live Stage Progress Indicator */}
      {runningDemo && (
        <div className="p-5 rounded-lg border border-[#27272a] bg-[#141418] space-y-3">
          <div className="text-[10px] text-[#71717a] uppercase tracking-wider">
            ACTIVE STAGE PROGRESSION
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-7 gap-2 text-center text-xs">
            {['1. Observe', '2. Understand', '3. Predict', '4. Simulate', '5. Authorize', '6. Act/Verify', '7. Learn'].map((st, i) => {
              const isPast = demoStep > i + 1;
              const isCurrent = demoStep === i + 1;
              return (
                <div
                  key={st}
                  className={`p-2 rounded border transition-all ${
                    isPast
                      ? 'bg-emerald-950/60 text-emerald-400 border-emerald-800'
                      : isCurrent
                      ? 'bg-sky-950 text-sky-300 border-sky-600 animate-pulse font-bold'
                      : 'bg-[#101014] text-[#71717a] border-[#27272a]'
                  }`}
                >
                  {st}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Real-Time Live Execution Log Terminal */}
      {demoLogs.length > 0 && (
        <div className="p-5 rounded-lg border border-[#27272a] bg-[#0c0c0e] space-y-3">
          <div className="flex items-center justify-between text-xs border-b border-[#27272a] pb-2">
            <span className="text-[#71717a] uppercase">REAL-TIME EXECUTION AUDIT STREAM</span>
            <span className="text-emerald-400 flex items-center gap-1 text-[11px]">
              <CheckCircle2 className="w-3.5 h-3.5" /> LIVE RECEPTOR
            </span>
          </div>
          <div className="space-y-2 text-xs">
            {demoLogs.map((log, i) => (
              <div key={i} className="text-[#fafafa] leading-relaxed font-mono">
                {log}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
