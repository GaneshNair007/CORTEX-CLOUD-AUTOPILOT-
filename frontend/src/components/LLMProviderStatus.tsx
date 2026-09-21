/**
 * CORTEX — LLM Provider Status Badge
 *
 * Displays the real AI provider, model, health, and fallback state.
 * The display is ALWAYS truthful:
 *   - Heuristic fallback → "HEURISTIC FALLBACK ACTIVE" (never "Gemini Active")
 *   - Paid route        → "PAID ROUTE" label shown
 *   - Free tier         → "FREE-TIER" label
 *   - Circuit open      → "DEGRADED" + error code
 *
 * No credentials, wallet balance, or key fragments are ever rendered.
 */

import { useEffect, useState, useCallback } from 'react';
import { getLLMStatus } from '../services/api';
import type { LLMStatusResponse } from '../types';

// ─── Status colour mapping ────────────────────────────────────────────────────
const STATUS_STYLES: Record<string, { dot: string; label: string; badge: string }> = {
  HEALTHY:    { dot: 'bg-emerald-400', label: 'text-emerald-300', badge: 'border-emerald-500/40 bg-emerald-950/40' },
  CONFIGURED: { dot: 'bg-sky-400',     label: 'text-sky-300',     badge: 'border-sky-500/40 bg-sky-950/40' },
  DEGRADED:   { dot: 'bg-amber-400 animate-pulse', label: 'text-amber-300', badge: 'border-amber-500/40 bg-amber-950/40' },
  UNAVAILABLE:{ dot: 'bg-red-400 animate-pulse',   label: 'text-red-300',   badge: 'border-red-500/40 bg-red-950/40' },
  UNKNOWN:    { dot: 'bg-zinc-400',    label: 'text-zinc-300',    badge: 'border-zinc-600/40 bg-zinc-900/40' },
};

function getStatusStyle(status: string) {
  return STATUS_STYLES[status?.toUpperCase()] ?? STATUS_STYLES.UNKNOWN;
}

function costLabel(costType?: string, isPaid?: boolean): string {
  if (!costType) return isPaid ? 'PAID ROUTE' : 'FREE';
  if (costType.includes('wallet')) return 'WALLET-BACKED';
  if (costType.includes('free-tier')) return 'FREE-TIER';
  if (costType.includes('usage')) return 'USAGE-BASED';
  if (costType.includes('local')) return 'LOCAL';
  if (costType.includes('no network')) return 'OFFLINE';
  return costType.toUpperCase();
}

function providerDisplayName(provider: string): string {
  const names: Record<string, string> = {
    gemini:           'Google Gemini',
    cheaperinference: 'CheaperInference',
    openai:           'OpenAI',
    anthropic:        'Anthropic',
    ollama:           'Ollama (Local)',
    heuristic:        'Heuristic Fallback',
  };
  return names[provider?.toLowerCase()] ?? provider;
}

// ─── Main component ───────────────────────────────────────────────────────────
interface Props {
  /** Polling interval in ms (0 = no polling). Default 30 000 */
  refreshIntervalMs?: number;
  compact?: boolean;
}

export default function LLMProviderStatus({ refreshIntervalMs = 30_000, compact = false }: Props) {
  const [status, setStatus] = useState<LLMStatusResponse | null>(null);
  const [error, setError]   = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchStatus = useCallback(async () => {
    try {
      const data = await getLLMStatus();
      setStatus(data);
      setError(null);
    } catch (e: any) {
      setError(e.message ?? 'Failed to fetch LLM status');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStatus();
    if (refreshIntervalMs > 0) {
      const id = setInterval(fetchStatus, refreshIntervalMs);
      return () => clearInterval(id);
    }
  }, [fetchStatus, refreshIntervalMs]);

  // ── Loading state ─────────────────────────────────────────────────────────
  if (loading) {
    return (
      <div className="flex items-center gap-2 text-xs text-zinc-500 animate-pulse">
        <span className="h-2 w-2 rounded-full bg-zinc-500 inline-block" />
        Probing AI provider…
      </div>
    );
  }

  // ── Error / backend disconnected ──────────────────────────────────────────
  if (error || !status) {
    return (
      <div className="flex items-center gap-2 text-xs text-zinc-400 border border-zinc-700 rounded px-2 py-1">
        <span className="h-2 w-2 rounded-full bg-zinc-500 inline-block" />
        AI STATUS UNKNOWN
        {error && <span className="text-zinc-600 ml-1">({error})</span>}
      </div>
    );
  }

  const activeProvider = status.active_provider;
  const primaryInfo    = status.primary;
  const providerStatus = primaryInfo?.status ?? 'UNKNOWN';
  const isFallback     = status.fallback_used;
  const isHeuristic    = activeProvider === 'heuristic';
  const style          = getStatusStyle(isHeuristic ? 'DEGRADED' : isFallback ? 'DEGRADED' : providerStatus);

  // ── Compact badge (for nav bar / header) ─────────────────────────────────
  if (compact) {
    return (
      <div className={`flex items-center gap-1.5 border rounded px-2 py-0.5 text-xs font-mono ${style.badge}`}>
        <span className={`h-1.5 w-1.5 rounded-full inline-block ${style.dot}`} />
        <span className={style.label}>
          {isHeuristic ? 'HEURISTIC' : providerDisplayName(activeProvider).toUpperCase()}
        </span>
        {isFallback && <span className="text-amber-400 ml-0.5">↩</span>}
      </div>
    );
  }

  // ── Full panel ────────────────────────────────────────────────────────────
  return (
    <div className={`border rounded-md px-3 py-2 text-xs font-mono space-y-1 ${style.badge}`}>
      {/* Header row */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className={`h-2 w-2 rounded-full inline-block flex-shrink-0 ${style.dot}`} />
          <span className={`font-semibold tracking-wide ${style.label}`}>
            AI — {providerDisplayName(activeProvider).toUpperCase()}
          </span>
        </div>
        <span className={`uppercase text-[10px] tracking-widest font-bold ${style.label}`}>
          {isHeuristic ? 'DEGRADED' : isFallback ? 'FALLBACK' : providerStatus}
        </span>
      </div>

      {/* Model row */}
      {status.active_model && (
        <div className="text-zinc-400">
          Model: <span className="text-zinc-200">{status.active_model}</span>
        </div>
      )}

      {/* Heuristic warning */}
      {isHeuristic && (
        <div className="text-amber-300 font-bold uppercase tracking-wide border-t border-amber-700/40 pt-1 mt-1">
          ⚠ HEURISTIC FALLBACK ACTIVE — responses are not from a real LLM
        </div>
      )}

      {/* Fallback (non-heuristic) notice */}
      {isFallback && !isHeuristic && (
        <div className="text-amber-300 border-t border-amber-700/40 pt-1">
          Fallback active — primary provider {providerDisplayName(status.primary?.provider ?? '')} unavailable
        </div>
      )}

      {/* Cost type / paid route label */}
      <div className="text-zinc-500 flex items-center gap-2">
        <span>{costLabel(primaryInfo?.cost_type, primaryInfo?.is_paid)}</span>
        {!status.allow_paid_fallback && (
          <span className="text-zinc-600">· paid fallback disabled</span>
        )}
      </div>

      {/* Fallback chain */}
      {status.fallbacks.length > 0 && (
        <div className="text-zinc-600 border-t border-zinc-700/40 pt-1">
          Fallbacks: {status.fallbacks.map(f => providerDisplayName(f.provider)).join(' → ')}
        </div>
      )}

      {/* Circuit breaker warning */}
      {primaryInfo?.circuit_state === 'OPEN' && (
        <div className="text-red-400 font-semibold">
          ⚡ Circuit OPEN — {primaryInfo?.last_error_code ?? 'provider failing'}
        </div>
      )}

      {/* Refresh button */}
      <button
        onClick={fetchStatus}
        className="text-zinc-600 hover:text-zinc-300 text-[10px] mt-0.5 cursor-pointer transition-colors"
        aria-label="Refresh LLM status"
      >
        ↻ refresh
      </button>
    </div>
  );
}
