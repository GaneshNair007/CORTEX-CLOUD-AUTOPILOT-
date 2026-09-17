import { useState } from "react";
import { Database, Network, Server } from "lucide-react";
import { client } from "./client";
import { useAction, useResource } from "./hooks";
import type { Blast, Service, Topology as TopologyData } from "./contracts";
import {
  Badge,
  Button,
  Empty,
  JsonDetails,
  Metric,
  Modal,
  Notice,
  Panel,
  ResourceState,
  num,
  statusTone,
} from "./ui";

export function Graph({
  data,
  onSelect,
  affected = [],
}: {
  data: TopologyData;
  onSelect: (service: Service) => void;
  affected?: string[];
}) {
  if (!data.nodes.length) return <Empty title="No topology available" />;
  // Layout derives from graph relationships. Cycles remain in a bounded last column.
  const levels = new Map(data.nodes.map((n) => [n.id, 0]));
  for (let i = 0; i < Math.min(data.nodes.length, 5); i++)
    for (const edge of data.edges)
      levels.set(
        edge.target,
        Math.min(
          4,
          Math.max(
            levels.get(edge.target) ?? 0,
            (levels.get(edge.source) ?? 0) + 1,
          ),
        ),
      );
  const columns = [...new Set(levels.values())].sort((a, b) => a - b);
  const positions = new Map<string, { x: number; y: number }>();
  columns.forEach((level, col) => {
    const nodes = data.nodes.filter((n) => levels.get(n.id) === level);
    nodes.forEach((n, i) =>
      positions.set(n.id, { x: 25 + col * 200, y: 32 + i * 104 }),
    );
  });
  const width = Math.max(660, columns.length * 200);
  const height = Math.max(
    270,
    Math.max(
      ...columns.map(
        (l) => data.nodes.filter((n) => levels.get(n.id) === l).length,
      ),
    ) *
      104 +
      40,
  );
  return (
    <div className="graph-scroll">
      <div className="service-graph" style={{ width, height }}>
        <svg width={width} height={height} aria-hidden="true">
          <defs>
            <marker
              id="edge-arrow"
              markerWidth="6"
              markerHeight="6"
              refX="5"
              refY="3"
              orient="auto"
            >
              <path d="M0,0 L6,3 L0,6" fill="currentColor" />
            </marker>
          </defs>
          {data.edges.map((edge) => {
            const a = positions.get(edge.source),
              b = positions.get(edge.target);
            if (!a || !b) return null;
            return (
              <path
                key={edge.id}
                d={`M ${a.x + 163} ${a.y + 32} C ${a.x + 185} ${a.y + 32}, ${b.x - 20} ${b.y + 32}, ${b.x} ${b.y + 32}`}
                className={affected.includes(edge.source) ? "affected" : ""}
                markerEnd="url(#edge-arrow)"
              />
            );
          })}
        </svg>
        {data.nodes.map((n) => {
          const p = positions.get(n.id)!;
          const Icon = n.is_stateful
            ? Database
            : n.tier === "edge"
              ? Network
              : Server;
          return (
            <button
              key={n.id}
              className={`service-node ${affected.includes(n.id) ? "affected" : ""}`}
              style={{ left: p.x, top: p.y }}
              onClick={() => onSelect(n)}
              aria-label={`Inspect ${n.id}`}
            >
              <span className="node-top">
                <Icon size={15} />
                <span className={`status-dot ${statusTone(n.health)}`} />
                {n.tier}
              </span>
              <strong>{n.id}</strong>
              <small>
                {num(n.p95_ms)} ms <span>·</span> {n.replicas} replicas
              </small>
            </button>
          );
        })}
      </div>
    </div>
  );
}
export function ServiceDialog({
  service,
  onClose,
}: {
  service: Service | null;
  onClose: () => void;
}) {
  return (
    <Modal
      open={!!service}
      onClose={onClose}
      title={service?.name || "Service inspector"}
      description="Backend topology snapshot · modeled infrastructure, not a live provider inventory."
    >
      {service && (
        <>
          <Badge tone={statusTone(service.health)}>{service.health}</Badge>
          <div className="metrics-grid two">
            <Metric
              label="p95 latency"
              value={`${num(service.p95_ms)} ms`}
              detail={`Modeled SLO ${service.slo_ms} ms`}
            />
            <Metric
              label="Replicas"
              value={num(service.replicas)}
              detail={service.region}
            />
          </div>
          <dl className="detail-list">
            <dt>Service</dt>
            <dd>{service.id}</dd>
            <dt>Request rate</dt>
            <dd>{num(service.rps)} RPS</dd>
            <dt>Error rate</dt>
            <dd>{num(service.error_rate * 100, 2)}%</dd>
            <dt>Criticality</dt>
            <dd>{service.criticality}/5</dd>
            <dt>Stateful</dt>
            <dd>{service.is_stateful ? "Yes" : "No"}</dd>
          </dl>
          <Button
            href={`#/simulator?service=${encodeURIComponent(service.id)}`}
            variant="outline"
          >
            Simulate a change
          </Button>
        </>
      )}
    </Modal>
  );
}

export default function TopologyPage() {
  const resource = useResource(client.topology);
  const [selected, setSelected] = useState<Service | null>(null);
  const [query, setQuery] = useState("");
  const [blast, setBlast] = useState<Blast>();
  const [target, setTarget] = useState("");
  const action = useAction();
  const nodes =
    resource.data?.nodes.filter((n) =>
      `${n.id} ${n.name} ${n.tier}`.toLowerCase().includes(query.toLowerCase()),
    ) || [];
  const filtered = resource.data && {
    nodes,
    edges: resource.data.edges.filter(
      (e) =>
        nodes.some((n) => n.id === e.source) &&
        nodes.some((n) => n.id === e.target),
    ),
  };
  return (
    <>
      <Notice>
        The topology endpoint currently returns a modeled service graph. Its
        health and traffic values are not live provider measurements.
      </Notice>
      <ResourceState resource={resource} />
      <Panel
        title="Dependency topology"
        detail="Follow dependencies before changing infrastructure."
        action={<Badge tone="info">Modeled snapshot</Badge>}
      >
        <div className="toolbar">
          <input
            aria-label="Filter services"
            placeholder="Find a service, tier, or database…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <Badge>{nodes.length} services</Badge>
        </div>
        {filtered ? (
          <Graph
            data={filtered}
            onSelect={setSelected}
            affected={blast?.affected_services}
          />
        ) : (
          !resource.loading && <Empty />
        )}
      </Panel>
      <Panel
        title="Blast radius explorer"
        detail="Calculate dependencies affected by a database restart. This only simulates a change."
      >
        <form
          className="toolbar"
          onSubmit={(e) => {
            e.preventDefault();
            void action.run(async () =>
              setBlast(
                await client.blast("restart_database", { service: target }),
              ),
            );
          }}
        >
          <select
            aria-label="Blast radius target"
            value={target}
            onChange={(e) => {
              setTarget(e.target.value);
              setBlast(undefined);
            }}
            required
          >
            <option value="">Choose target</option>
            {resource.data?.nodes.map((n) => (
              <option key={n.id}>{n.id}</option>
            ))}
          </select>
          <Button type="submit" disabled={!target || action.pending}>
            Calculate blast radius
          </Button>
        </form>
        {action.error && <Notice danger>{action.error}</Notice>}
        {blast && (
          <>
            <div className="metrics-grid two">
              <Metric
                label="Risk score"
                value={`${blast.score}/100`}
                detail={blast.risk_level}
                tone="warning"
              />
              <Metric
                label="Affected services"
                value={blast.affected_services.length}
                detail={blast.directly_affected}
              />
            </div>
            <p className="body-copy">{blast.explanation}</p>
            <JsonDetails data={blast} />
          </>
        )}
      </Panel>
      <ServiceDialog service={selected} onClose={() => setSelected(null)} />
    </>
  );
}
