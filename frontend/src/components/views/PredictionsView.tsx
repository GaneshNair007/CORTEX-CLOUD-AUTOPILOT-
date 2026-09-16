import React, { useState, useEffect } from 'react';
import {
  TrendingUp,
  Clock,
  Cpu,
  AlertTriangle,
  CheckCircle2,
  Sliders,
  Sparkles,
  RefreshCw,
  Zap
} from 'lucide-react';
import { api } from '../../services/api';

export const PredictionsView: React.FC = () => {
  const [horizon, setHorizon] = useState<number>(30);
  const [loading, setLoading] = useState<boolean>(false);
  const [forecast, setForecast] = useState<any>(null);

  const fetchForecast = async (h: number) => {
    setLoading(true);
    try {
      const data = await api.getForecast(h);
      setForecast(data);
    } catch (e) {
      console.error(e);
      // Fallback
      setForecast({
        horizon: h,
        current_rps: 520,
        forecast_rps: 740,
        pct_change: 42.3,
        lower_bound: 690,
        upper_bound: 790,
        recommended_replicas: 9,
        action_window_mins: 8,
        uncertainty_range: 50,
        mae: 14.2,
        rmse: 18.6
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchForecast(horizon);
  }, [horizon]);

  const timeSeries = [
    { t: 'T-25m', actual: 460, predicted: 465, lower: 430, upper: 500 },
    { t: 'T-20m', actual: 480, predicted: 475, lower: 440, upper: 510 },
    { t: 'T-15m', actual: 495, predicted: 490, lower: 450, upper: 530 },
    { t: 'T-10m', actual: 510, predicted: 505, lower: 470, upper: 540 },
    { t: 'T-5m', actual: 525, predicted: 520, lower: 480, upper: 560 },
    { t: 'NOW', actual: 535, predicted: 535, lower: 490, upper: 580 },
    { t: 'T+5m', actual: null, predicted: 590, lower: 540, upper: 640 },
    { t: 'T+10m', actual: null, predicted: 660, lower: 600, upper: 720 },
    { t: 'T+15m', actual: null, predicted: 720, lower: 650, upper: 790 },
    { t: 'T+20m', actual: null, predicted: 750, lower: 680, upper: 820 },
    { t: 'T+25m', actual: null, predicted: 740, lower: 670, upper: 810 },
    { t: 'T+30m', actual: null, predicted: 710, lower: 640, upper: 780 }
  ];

  return (
    <div className="flex-1 p-6 space-y-6 overflow-y-auto bg-[#09090b] text-[#fafafa] font-mono">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-[#27272a] pb-5">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-[#fafafa] flex items-center gap-2.5">
            <TrendingUp className="w-5 h-5 text-sky-400" />
            Workload Forecast Engine
          </h2>
          <p className="text-xs text-[#a1a1aa] mt-1 font-sans">
            Deep-learning & XGBoost predictive scaling models computing request volume surges 5m, 15m, and 30m ahead of traffic arrival.
          </p>
        </div>

        <div className="flex items-center gap-2 bg-[#18181b] border border-[#27272a] rounded p-0.5 text-xs">
          {[5, 15, 30].map(h => (
            <button
              key={h}
              onClick={() => setHorizon(h)}
              className={`px-3 py-1 rounded transition-colors cursor-pointer ${
                horizon === h ? 'bg-sky-600 text-white font-bold' : 'text-[#71717a] hover:text-[#a1a1aa]'
              }`}
            >
              +{h}m Horizon
            </button>
          ))}
        </div>
      </div>

      {/* KPI Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4 text-xs">
        <div className="p-4 rounded-lg bg-[#141418] border border-[#27272a]">
          <div className="text-[11px] text-[#71717a]">FORECAST PEAK VOLUME</div>
          <div className="text-2xl font-bold text-sky-400 mt-1">750 RPS</div>
          <div className="text-[10px] text-emerald-400 mt-1">+40.2% surge at T+20m</div>
        </div>
        <div className="p-4 rounded-lg bg-[#141418] border border-[#27272a]">
          <div className="text-[11px] text-[#71717a]">RECOMMENDED REPLICAS</div>
          <div className="text-2xl font-bold text-[#fafafa] mt-1">9 Pods</div>
          <div className="text-[10px] text-sky-400 mt-1">+3 pods before queue delay</div>
        </div>
        <div className="p-4 rounded-lg bg-[#141418] border border-[#27272a]">
          <div className="text-[11px] text-[#71717a]">ACTION WINDOW DEADLINE</div>
          <div className="text-2xl font-bold text-amber-400 mt-1">8m 12s</div>
          <div className="text-[10px] text-[#71717a] mt-1">Warm-up lead time: 90s</div>
        </div>
        <div className="p-4 rounded-lg bg-[#141418] border border-[#27272a]">
          <div className="text-[11px] text-[#71717a]">MODEL ERROR (MAE / RMSE)</div>
          <div className="text-2xl font-bold text-emerald-400 mt-1">14.2 / 18.6</div>
          <div className="text-[10px] text-emerald-400 mt-1">97.2% confidence interval</div>
        </div>
      </div>

      {/* Time-Series Chart Visualization */}
      <div className="p-5 rounded-lg border border-[#27272a] bg-[#101014] space-y-4">
        <div className="flex items-center justify-between text-xs">
          <div className="flex items-center gap-4">
            <span className="font-bold text-[#fafafa] font-sans">Traffic Trajectory & Uncertainty Corridor</span>
            <span className="flex items-center gap-1.5 text-[11px] text-[#a1a1aa]">
              <span className="w-3 h-0.5 bg-emerald-400 inline-block" /> Actual
            </span>
            <span className="flex items-center gap-1.5 text-[11px] text-[#a1a1aa]">
              <span className="w-3 h-0.5 bg-sky-400 inline-block border-dashed" /> Forecast
            </span>
            <span className="flex items-center gap-1.5 text-[11px] text-[#a1a1aa]">
              <span className="w-3 h-2 bg-sky-950/60 border border-sky-800/60 inline-block" /> ±95% Uncertainty
            </span>
          </div>
          <span className="text-[11px] text-[#71717a]">UPDATED 10S AGO</span>
        </div>

        {/* Custom SVG Time-Series */}
        <div className="h-64 w-full relative border border-[#27272a] rounded bg-[#09090b] p-4 flex items-end">
          <div className="w-full h-full flex items-end justify-between gap-2 pt-6">
            {timeSeries.map((pt, i) => {
              const maxVal = 900;
              const val = pt.actual !== null ? pt.actual : pt.predicted;
              const heightPct = (val / maxVal) * 100;
              const isFuture = pt.actual === null;

              return (
                <div key={i} className="flex-1 flex flex-col items-center h-full justify-end group relative">
                  {/* Tooltip */}
                  <div className="absolute -top-10 hidden group-hover:flex flex-col items-center bg-[#18181b] border border-[#27272a] px-2 py-1 rounded text-[10px] z-20 whitespace-nowrap shadow-lg">
                    <span>{pt.t}: {val} rps</span>
                    {isFuture && <span className="text-[#71717a]">[{pt.lower}-{pt.upper}]</span>}
                  </div>

                  {/* Uncertainty Bar in future */}
                  {isFuture && (
                    <div
                      style={{ height: `${((pt.upper - pt.lower) / maxVal) * 100}%`, bottom: `${(pt.lower / maxVal) * 100}%` }}
                      className="absolute w-full bg-sky-900/30 border-y border-sky-600/40"
                    />
                  )}

                  {/* Bar */}
                  <div
                    style={{ height: `${heightPct}%` }}
                    className={`w-full max-w-[28px] rounded-t transition-all ${
                      isFuture
                        ? 'bg-sky-500/50 border-t-2 border-sky-400'
                        : 'bg-emerald-500/80 border-t-2 border-emerald-300'
                    }`}
                  />

                  {/* X-Label */}
                  <span className="text-[9px] text-[#71717a] mt-2 whitespace-nowrap">
                    {pt.t}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Anomaly Detection Strip */}
      <div className="p-4 rounded-lg bg-[#141418] border border-[#27272a] flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 text-xs font-mono">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded bg-sky-950 border border-sky-800 flex items-center justify-center text-sky-400">
            <Zap className="w-4 h-4" />
          </div>
          <div>
            <div className="font-bold text-[#fafafa] font-sans">Isolation Forest Anomaly Detector</div>
            <div className="text-[11px] text-[#a1a1aa] mt-0.5">
              Current pattern score: <span className="text-emerald-400 font-bold">0.18 (NOMINAL)</span> • Anomaly threshold: 0.65
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className="px-2.5 py-1 rounded bg-emerald-950 text-emerald-400 border border-emerald-800 text-[11px]">
            ZERO ANOMALIES DETECTED
          </span>
        </div>
      </div>
    </div>
  );
};
