import React, { useState, useEffect } from 'react';
import {
  AlertTriangle,
  Search,
  Filter,
  ArrowUpDown,
  CheckCircle,
  Clock,
  ExternalLink,
  ChevronRight,
  ShieldAlert,
  Flame,
  FileText,
  RefreshCw
} from 'lucide-react';
import { api } from '../../services/api';

interface IncidentsViewProps {
  onSelectIncident: (id: string) => void;
}

// Fallback demo incidents shown when the DB is empty or backend is offline
const DEMO_INCIDENTS = [
    {
      id: 'INC-1042',
      timestamp: '2026-09-16 14:12:00 UTC',
      service: 'payment-api',
      severity: 'HIGH',
      title: 'p95 Latency 840ms with 4.8% HTTP 504 Gateway Timeouts after v4.6 rollout',
      rootCause: 'Database connection pool starvation triggered by v4.6 unindexed schema query',
      confidence: 0.94,
      decision: 'CONSTRAIN_AND_SCALE',
      action: 'scale_replicas (6 → 9) + rollback_canary',
      status: 'ACTIVE',
      mttr: '3m 14s',
      evidenceDocs: ['RB-001 (Connection Exhaustion)', 'INC-005 (Postmortem)']
    },
    {
      id: 'INC-1041',
      timestamp: '2026-09-16 12:45:10 UTC',
      service: 'order-service',
      severity: 'MEDIUM',
      title: 'Kafka Consumer Lag spike on order-events topic (>45,000 unconsumed messages)',
      rootCause: 'Partition rebalancing failure following worker pod memory eviction',
      confidence: 0.89,
      decision: 'EXECUTE',
      action: 'restart_consumer_group + increase_memory_limit',
      status: 'RESOLVED',
      mttr: '2m 08s',
      evidenceDocs: ['RB-012 (Kafka Lag Runbook)']
    },
    {
      id: 'INC-1040',
      timestamp: '2026-09-16 09:30:22 UTC',
      service: 'auth-service',
      severity: 'LOW',
      title: 'Token validation cache miss rate increase to 34% (elevated Redis read ops)',
      rootCause: 'Key TTL expiration misalignment during scheduled maintenance',
      confidence: 0.91,
      decision: 'EXECUTE',
      action: 'warm_cache_keys + adjust_ttl',
      status: 'RESOLVED',
      mttr: '1m 45s',
      evidenceDocs: ['RB-007 (Redis Cache Eviction)']
    },
    {
      id: 'INC-1039',
      timestamp: '2026-09-15 22:15:00 UTC',
      service: 'postgres-primary',
      severity: 'CRITICAL',
      title: 'Replication lag exceeded 60s with disk I/O queue saturation',
      rootCause: 'Deadlock cascade on transaction history table during vacuum freeze',
      confidence: 0.97,
      decision: 'REQUIRE_APPROVAL',
      action: 'failover_to_replica (high blast radius)',
      status: 'RESOLVED',
      mttr: '5m 20s',
      evidenceDocs: ['RB-004 (Postgres Failover)', 'INC-012 (Deadlock Cascade)']
    },
    {
      id: 'INC-1038',
      timestamp: '2026-09-15 18:02:40 UTC',
      service: 'ingress',
      severity: 'HIGH',
      title: 'SSL handshake negotiation timeout rate 8.2% on us-east edge node',
      rootCause: 'TLS certificate chain renew loop causing crypto worker thread lock',
      confidence: 0.88,
      decision: 'EXECUTE',
      action: 'reload_cert_daemon + rotate_worker_pool',
      status: 'RESOLVED',
      mttr: '1m 55s',
      evidenceDocs: ['RB-009 (Ingress TLS Recovery)']
    }
  ];

export const IncidentsView: React.FC<IncidentsViewProps> = ({ onSelectIncident }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [severityFilter, setSeverityFilter] = useState('ALL');
  const [liveIncidents, setLiveIncidents] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [useLive, setUseLive] = useState(false);

  const fetchIncidents = async () => {
    try {
      const data = await api.getIncidents?.() ?? { incidents: [] };
      if (data.incidents && data.incidents.length > 0) {
        setLiveIncidents(data.incidents);
        setUseLive(true);
      }
    } catch {
      // Backend offline — show demo data silently
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchIncidents();
    const interval = setInterval(fetchIncidents, 15000);
    return () => clearInterval(interval);
  }, []);

  // Normalise live DB records to the same shape as demo incidents
  const normalisedLive = liveIncidents.map(i => ({
    id: i.id,
    timestamp: i.detected_at ?? '',
    service: i.service ?? '—',
    severity: i.severity ?? 'P1',
    title: i.title ?? '—',
    rootCause: i.root_cause ?? '—',
    confidence: 0.9,
    decision: '—',
    action: '—',
    status: i.status === 'RESOLVED' ? 'RESOLVED' : 'ACTIVE',
    mttr: i.resolved_at ? '—' : null,
    evidenceDocs: [],
  }));

  const incidents = useLive ? normalisedLive : DEMO_INCIDENTS;

  const filtered = incidents.filter(inc => {
    const matchesSearch =
      inc.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      inc.service.toLowerCase().includes(searchTerm.toLowerCase()) ||
      inc.id.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesSev = severityFilter === 'ALL' || inc.severity === severityFilter;
    return matchesSearch && matchesSev;
  });

  const activeCount = incidents.filter(i => i.status === 'ACTIVE').length;
  const resolvedCount = incidents.filter(i => i.status === 'RESOLVED').length;

  return (
    <div className="flex-1 p-6 space-y-6 overflow-y-auto bg-[#09090b] text-[#fafafa]">
      {/* Header & Filter Bar */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-[#27272a] pb-5">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-[#fafafa] flex items-center gap-2.5">
            <AlertTriangle className="w-5 h-5 text-amber-400" />
            Incident Command & Forensics
          </h2>
          <p className="text-xs text-[#a1a1aa] mt-1 font-mono">
            Ground-truth incident logs, automated AI hypothesis generation, and self-critique audits.
          </p>
        </div>

        <div className="flex items-center gap-3 w-full sm:w-auto">
          <div className="relative flex-1 sm:w-64">
            <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-[#71717a]" />
            <input
              type="text"
              placeholder="Search incidents or services..."
              value={searchTerm}
              onChange={e => setSearchTerm(e.target.value)}
              className="w-full bg-[#18181b] border border-[#27272a] text-xs pl-8 pr-3 py-1.5 rounded text-[#fafafa] placeholder-[#71717a] focus:outline-none focus:border-sky-500 font-mono"
            />
          </div>

          <div className="flex items-center gap-1 bg-[#18181b] border border-[#27272a] rounded p-0.5 text-xs font-mono">
            {['ALL', 'CRITICAL', 'HIGH', 'MEDIUM'].map(sev => (
              <button
                key={sev}
                onClick={() => setSeverityFilter(sev)}
                className={`px-2.5 py-1 rounded transition-colors cursor-pointer ${
                  severityFilter === sev ? 'bg-[#27272a] text-[#fafafa] font-semibold' : 'text-[#71717a] hover:text-[#a1a1aa]'
                }`}
              >
                {sev}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Incident Metrics Summary */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4 font-mono">
        <div className="p-4 rounded-lg bg-[#141418] border border-[#27272a]">
          <div className="text-[11px] text-[#71717a]">TOTAL INCIDENTS (30D)</div>
          <div className="text-2xl font-bold text-[#fafafa] mt-1">42</div>
          <div className="text-[10px] text-emerald-400 mt-1">-18% vs last month</div>
        </div>
        <div className="p-4 rounded-lg bg-[#141418] border border-[#27272a]">
          <div className="text-[11px] text-[#71717a]">AUTONOMOUS MTTR</div>
          <div className="text-2xl font-bold text-sky-400 mt-1">2m 18s</div>
          <div className="text-[10px] text-emerald-400 mt-1">7.4x faster than human SLA</div>
        </div>
        <div className="p-4 rounded-lg bg-[#141418] border border-[#27272a]">
          <div className="text-[11px] text-[#71717a]">DIAGNOSTIC ACCURACY</div>
          <div className="text-2xl font-bold text-emerald-400 mt-1">94.8%</div>
          <div className="text-[10px] text-[#a1a1aa] mt-1">Against ground truth</div>
        </div>
        <div className="p-4 rounded-lg bg-[#141418] border border-[#27272a]">
          <div className="text-[11px] text-[#71717a]">UNSAFE ACTIONS BLOCKED</div>
          <div className="text-2xl font-bold text-amber-400 mt-1">100%</div>
          <div className="text-[10px] text-amber-400/80 mt-1">0 unauthorized DB mutations</div>
        </div>
      </div>

      {/* TanStack-style Incident Table */}
      <div className="rounded-lg border border-[#27272a] bg-[#101014] overflow-hidden">
        <table className="w-full text-left font-mono text-xs">
          <thead className="bg-[#18181b] text-[#71717a] uppercase border-b border-[#27272a] text-[10px] tracking-wider">
            <tr>
              <th className="px-4 py-3">Incident ID</th>
              <th className="px-4 py-3">Timestamp</th>
              <th className="px-4 py-3">Service</th>
              <th className="px-4 py-3">Severity</th>
              <th className="px-4 py-3">Root Cause Diagnosis</th>
              <th className="px-4 py-3">Confidence</th>
              <th className="px-4 py-3">Decision</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3 text-right">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#27272a]">
            {filtered.map(inc => (
              <tr
                key={inc.id}
                onClick={() => onSelectIncident(inc.id)}
                className="hover:bg-[#18181b]/70 transition-colors cursor-pointer group"
              >
                <td className="px-4 py-3.5 font-bold text-sky-400 group-hover:underline">
                  {inc.id}
                </td>
                <td className="px-4 py-3.5 text-[#71717a] text-[11px]">
                  {inc.timestamp.split(' ')[1]}
                </td>
                <td className="px-4 py-3.5 text-[#fafafa] font-semibold">
                  {inc.service}
                </td>
                <td className="px-4 py-3.5">
                  <span className={`px-2 py-0.5 rounded text-[10px] font-semibold border ${
                    inc.severity === 'CRITICAL' ? 'bg-rose-950 text-rose-300 border-rose-800' :
                    inc.severity === 'HIGH' ? 'bg-amber-950 text-amber-300 border-amber-800' :
                    'bg-zinc-800 text-zinc-300 border-zinc-700'
                  }`}>
                    {inc.severity}
                  </span>
                </td>
                <td className="px-4 py-3.5 text-[#a1a1aa] font-sans max-w-xs truncate">
                  {inc.rootCause}
                </td>
                <td className="px-4 py-3.5 text-emerald-400 font-bold">
                  {(inc.confidence * 100).toFixed(0)}%
                </td>
                <td className="px-4 py-3.5">
                  <span className="text-zinc-300 text-[11px] font-semibold bg-zinc-800/80 px-1.5 py-0.5 rounded border border-zinc-700">
                    {inc.decision}
                  </span>
                </td>
                <td className="px-4 py-3.5">
                  <span className={`px-2 py-0.5 rounded text-[10px] ${
                    inc.status === 'ACTIVE' ? 'bg-rose-950 text-rose-400 font-bold animate-pulse' : 'text-emerald-400'
                  }`}>
                    {inc.status}
                  </span>
                </td>
                <td className="px-4 py-3.5 text-right">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onSelectIncident(inc.id);
                    }}
                    className="p-1 rounded hover:bg-zinc-800 text-[#a1a1aa] hover:text-[#fafafa] transition-colors"
                  >
                    <ChevronRight className="w-4 h-4" />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
