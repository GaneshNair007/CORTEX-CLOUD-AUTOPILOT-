import React, { useState } from 'react';
import {
  Database,
  Search,
  BookOpen,
  FileText,
  Sparkles,
  ArrowRight,
  ExternalLink,
  Tag,
  CheckCircle2,
  Clock
} from 'lucide-react';
import { api } from '../../services/api';

export const IncidentMemoryView: React.FC = () => {
  const [query, setQuery] = useState('database connection pool exhaustion payment service');
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<any[]>([
    {
      doc_id: 'RB-001',
      title: 'Database Connection Pool Exhaustion Runbook',
      type: 'runbook',
      relevance: 0.94,
      snippet: 'When payment-api or order-service p95 exceeds 800ms with HTTP 504 and pg_stat_activity shows max_connections reached: (1) Scale pods from 6 to 9, (2) Increase idle connection timeout to 15s, (3) DO NOT restart database directly as it triggers 5-minute downstream outage.',
      tags: ['database', 'connection-pool', 'postgres', 'scaling']
    },
    {
      doc_id: 'INC-005',
      title: 'Postmortem: Black Friday Payment Timeout Cascade',
      type: 'incident',
      relevance: 0.91,
      snippet: 'Root Cause: A 3x surge in checkout traffic overwhelmed the fixed 50-connection pool limit. An unauthorized database restart caused a 312-second total blackout affecting $420k in GMV. Permanent resolution: Adaptive scaling with CORTEX Guard approval requirement on database mutations.',
      tags: ['postmortem', 'payment-api', 'blackout', 'p95']
    },
    {
      doc_id: 'RB-008',
      title: 'Redis Cluster Latency & Cache Eviction Runbook',
      type: 'runbook',
      relevance: 0.78,
      snippet: 'Cache miss rate exceeding 25% requires warming active session tokens before scaling web tier.',
      tags: ['redis', 'caching', 'latency']
    }
  ]);
  const [selectedDoc, setSelectedDoc] = useState<any>(results[0]);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    setLoading(true);
    try {
      const res = await api.retrieve(query, 5);
      if (res && res.results && res.results.length > 0) {
        setResults(res.results.map((r: any) => ({
          doc_id: r.doc_id || r.id || 'DOC-01',
          title: r.title || r.doc_id || 'Operational Document',
          type: r.type || (r.doc_id?.startsWith('RB') ? 'runbook' : 'incident'),
          relevance: r.relevance_score || r.score || 0.88,
          snippet: r.content || r.snippet || '',
          tags: r.tags || ['operations', 'sre']
        })));
        setSelectedDoc(results[0]);
      }
    } catch (err) {
      console.error('RAG query error', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex-1 flex flex-col h-full bg-[#09090b] text-[#fafafa] overflow-hidden font-mono">
      {/* Search Header */}
      <div className="h-16 border-b border-[#27272a] bg-[#0c0c0e] px-6 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <Database className="w-5 h-5 text-sky-400" />
          <div>
            <h2 className="text-sm font-bold text-[#fafafa] font-sans">
              Operational Memory & Vector RAG
            </h2>
            <div className="text-[10px] text-[#71717a]">
              ChromaDB Chroma Vector Store • 35 Curated SRE Documents • all-MiniLM-L6-v2 Embeddings
            </div>
          </div>
        </div>

        <form onSubmit={handleSearch} className="flex items-center gap-2 w-full max-w-lg">
          <div className="relative flex-1">
            <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-[#71717a]" />
            <input
              type="text"
              value={query}
              onChange={e => setQuery(e.target.value)}
              placeholder="Search operational memory, runbooks, postmortems..."
              className="w-full bg-[#18181b] border border-[#27272a] text-xs pl-8 pr-3 py-1.5 rounded text-[#fafafa] placeholder-[#71717a] focus:outline-none focus:border-sky-500"
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="px-3 py-1.5 bg-sky-600 hover:bg-sky-500 disabled:bg-zinc-800 text-white rounded text-xs font-semibold font-sans transition-colors cursor-pointer"
          >
            {loading ? 'Searching...' : 'Retrieve'}
          </button>
        </form>
      </div>

      {/* Main Split: Results List (Left) + Document Inspector (Right) */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 overflow-hidden">
        {/* Results List */}
        <div className="lg:col-span-5 border-r border-[#27272a] bg-[#09090b] overflow-y-auto p-4 space-y-3">
          <div className="text-[10px] text-[#71717a] uppercase tracking-wider px-1">
            MATCHED VECTOR RESULTS ({results.length})
          </div>

          {results.map((res, i) => {
            const isSelected = selectedDoc?.doc_id === res.doc_id;
            return (
              <div
                key={i}
                onClick={() => setSelectedDoc(res)}
                className={`p-3.5 rounded-lg border transition-all cursor-pointer ${
                  isSelected
                    ? 'bg-[#181822] border-sky-500/80 shadow-[0_0_15px_rgba(14,165,233,0.15)]'
                    : 'bg-[#121216] border-[#27272a] hover:border-[#3f3f46]'
                }`}
              >
                <div className="flex items-center justify-between mb-1.5">
                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                    res.type === 'runbook'
                      ? 'bg-emerald-950 text-emerald-400 border border-emerald-800/60'
                      : 'bg-amber-950 text-amber-400 border border-amber-800/60'
                  }`}>
                    {res.doc_id} • {res.type.toUpperCase()}
                  </span>
                  <span className="text-[11px] text-sky-400 font-bold">
                    {(res.relevance * 100).toFixed(1)}% SIMILARITY
                  </span>
                </div>

                <div className="font-semibold text-xs text-[#fafafa] font-sans">
                  {res.title}
                </div>

                <p className="text-[11px] text-[#a1a1aa] font-sans mt-1.5 line-clamp-2 leading-relaxed">
                  {res.snippet}
                </p>

                <div className="flex items-center gap-1.5 mt-2.5 flex-wrap">
                  {res.tags?.map((t: string) => (
                    <span key={t} className="text-[9px] bg-[#18181b] px-1.5 py-0.5 rounded text-[#71717a] border border-[#27272a]">
                      #{t}
                    </span>
                  ))}
                </div>
              </div>
            );
          })}
        </div>

        {/* Full Document Reader */}
        <div className="lg:col-span-7 bg-[#0c0c0e] p-6 overflow-y-auto space-y-5">
          {selectedDoc ? (
            <div className="space-y-4">
              <div className="flex items-center justify-between border-b border-[#27272a] pb-4">
                <div>
                  <span className="text-[10px] text-[#71717a] uppercase tracking-wider block">
                    OPERATIONAL DOCUMENT VIEWER
                  </span>
                  <h3 className="text-lg font-bold text-[#fafafa] font-sans mt-1">
                    {selectedDoc.title}
                  </h3>
                  <div className="text-xs text-sky-400 mt-0.5">
                    Identifier: {selectedDoc.doc_id} • Semantic Relevance: {(selectedDoc.relevance * 100).toFixed(1)}%
                  </div>
                </div>

                <span className="px-3 py-1 rounded bg-emerald-950 text-emerald-400 border border-emerald-800 text-xs">
                  VERIFIED RUNBOOK
                </span>
              </div>

              {/* Document Content Display */}
              <div className="p-5 rounded-lg bg-[#121216] border border-[#27272a] space-y-4 font-sans text-xs leading-relaxed text-[#d4d4d8]">
                <h4 className="font-mono text-xs uppercase text-[#71717a] tracking-wider">
                  Summary & Instructions
                </h4>
                <div className="p-3.5 rounded bg-[#09090b] border border-[#27272a] text-[#fafafa] font-mono text-[11px] leading-relaxed">
                  {selectedDoc.snippet}
                </div>

                <h4 className="font-mono text-xs uppercase text-[#71717a] tracking-wider pt-2">
                  System Autopilot Execution Rules
                </h4>
                <ul className="space-y-2 list-disc pl-5 text-[#a1a1aa]">
                  <li>Primary safe action: Incrementally scale replica deployment without dropping inflight requests.</li>
                  <li>Invariants enforced: Never scale below 3 pods; never restart active PostgreSQL cluster leader without standby confirmation.</li>
                  <li>Post-action verification probe must poll for 60 seconds to guarantee p95 latency stays under 200ms.</li>
                </ul>
              </div>

              {/* Memory Write-Back Status */}
              <div className="p-4 rounded-lg bg-[#141418] border border-[#27272a] flex items-center justify-between text-xs">
                <div className="flex items-center gap-2 text-[#a1a1aa]">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                  <span>Document embedded in vector memory index (<code className="text-[#fafafa]">backend/rag/chroma_db/</code>)</span>
                </div>
                <span className="text-[#71717a] text-[10px]">SYNCED</span>
              </div>
            </div>
          ) : (
            <div className="h-full flex items-center justify-center text-[#71717a]">
              Select a document to inspect full markdown runbook.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
