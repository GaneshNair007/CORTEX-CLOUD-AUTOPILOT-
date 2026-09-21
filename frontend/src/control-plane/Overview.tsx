import { useState } from "react";
import { ArrowRight, ShieldCheck } from "lucide-react";
import { client } from "./client";
import { useResource } from "./hooks";
import type { Health, Service } from "./contracts";
import { Graph, ServiceDialog } from "./Topology";
import { AiStatus } from "./AiStatus";
import {
  Badge,
  Empty,
  Metric,
  Notice,
  Panel,
  ResourceState,
  RouteLink,
  date,
  num,
  statusTone,
} from "./ui";

export default function Overview({ health }: { health?: Health }) {
  const topology = useResource(client.topology);
  const incidents = useResource(client.incidents);
  const operations = useResource(client.operations);
  const events = useResource(client.events);
  const approvals = useResource(client.approvals);
  const [service, setService] = useState<Service | null>(null);
  const open = incidents.data?.incidents.filter((i) => i.status === "OPEN");
  const pending = approvals.data?.pending_approvals.filter(
    (a) =>
      a.status === "pending" &&
      a.created_at * 1000 + a.ttl_seconds * 1000 > Date.now(),
  );
  const recent = operations.data?.operations[0];
  return (
    <>
      <div className="overview-intro">
        <div>
          <span className="eyebrow">YOUR INFRASTRUCTURE, IN PERSPECTIVE</span>
          <h1>
            Command center<span className="heading-dot">.</span>
          </h1>
          <p>Observe the system. Understand the change. Stay in control.</p>
        </div>
        <a className="primary-link" href="#/demo">
          Run control loop <ArrowRight size={16} />
        </a>
      </div>
      <div className="metrics-grid">
        <Metric
          label="Services in topology"
          value={num(topology.data?.nodes.length)}
          detail="Modeled infrastructure inventory"
        />
        <Metric
          label="Open incidents"
          value={num(open?.length)}
          detail={
            incidents.error
              ? "Last snapshot · refresh unavailable"
              : "Persisted incident records"
          }
          tone={open?.length ? "warning" : ""}
        />
        <Metric
          label="Pending approvals"
          value={num(pending?.length)}
          detail={
            approvals.error
              ? "Last snapshot · refresh unavailable"
              : "Awaiting an operator decision"
          }
        />
        <Metric
          label="Autonomy"
          value={health ? `L${health.autonomy_level}` : "—"}
          detail={
            health
              ? ["Observe", "Recommend", "Guarded", "Autonomous"][
                  health.autonomy_level
                ]
              : "Waiting for backend"
          }
        />
      </div>
      <AiStatus />
      <div className="overview-main">
        <Panel
          title="Infrastructure map"
          detail="Service relationships and modeled state"
          action={<RouteLink route="topology">Explore</RouteLink>}
        >
          <ResourceState resource={topology} />
          {topology.data ? (
            <Graph data={topology.data} onSelect={setService} />
          ) : (
            <Empty
              title="Waiting for your topology"
              detail="Connect the backend to view its infrastructure graph."
            />
          )}
          <div className="panel-foot">
            <Badge tone="info">Modeled data</Badge>
            <span>Select a service to inspect</span>
          </div>
        </Panel>
        <Panel
          title="Decision desk"
          detail="Latest recorded operation"
          className="decision-panel"
        >
          <div className="decision-icon">
            <ShieldCheck size={24} />
          </div>
          {recent ? (
            <>
              <Badge tone={statusTone(recent.status)}>{recent.status}</Badge>
              <h3>{recent.action_type.replaceAll("_", " ")}</h3>
              <p>{recent.target}</p>
              <dl className="detail-list">
                <dt>Risk score</dt>
                <dd>{recent.risk_score}/100</dd>
                <dt>Guard</dt>
                <dd>{recent.guard_decision || "Not recorded"}</dd>
                <dt>Verification</dt>
                <dd>{recent.verification_outcome || "Not recorded"}</dd>
              </dl>
              <RouteLink route="operations">Inspect operation</RouteLink>
            </>
          ) : (
            <>
              <h3>No recorded decision</h3>
              <p>
                Proposals, authorization, and verification appear here after a
                control loop runs.
              </p>
              <RouteLink route="demo">Open control loop</RouteLink>
            </>
          )}
          <ResourceState resource={operations} />
        </Panel>
      </div>
      <div className="two-columns">
        <Panel
          title="Incident queue"
          detail="Most recent persisted incidents"
          action={<RouteLink route="incidents">View all</RouteLink>}
        >
          <ResourceState resource={incidents} />
          {incidents.data?.incidents.length ? (
            <div className="record-list">
              {incidents.data.incidents.slice(0, 4).map((i) => (
                <a
                  href={`#/incidents?id=${encodeURIComponent(i.id)}`}
                  key={i.id}
                >
                  <span className="record-icon">!</span>
                  <div>
                    <strong>{i.title}</strong>
                    <small>
                      {i.service} · {i.id}
                    </small>
                  </div>
                  <Badge tone={statusTone(i.status)}>{i.status}</Badge>
                </a>
              ))}
            </div>
          ) : (
            <Empty
              title="No incidents returned"
              detail="New incidents will appear once recorded by the backend."
            />
          )}
        </Panel>
        <Panel
          title="Activity stream"
          detail="Events returned by the control plane"
          action={<RouteLink route="events">View all</RouteLink>}
        >
          <ResourceState resource={events} />
          {events.data?.events.length ? (
            <div className="event-list">
              {events.data.events
                .slice(-5)
                .reverse()
                .map((e) => (
                  <div key={e.event_id}>
                    <span className="event-point" />
                    <div>
                      <strong>{e.type.replaceAll("_", " ")}</strong>
                      <small>{date(e.timestamp)}</small>
                    </div>
                  </div>
                ))}
            </div>
          ) : (
            <Empty
              title="The event stream is quiet"
              detail="Control-loop events appear here as the backend emits them."
            />
          )}
        </Panel>
      </div>
      {approvals.error && (
        <Notice danger>Approval count: {approvals.error}</Notice>
      )}
      <div className="loop-strip">
        {[
          "Observe",
          "Understand",
          "Predict",
          "Simulate",
          "Optimize",
          "Authorize",
          "Act",
          "Verify",
          "Learn",
        ].map((stage, i) => (
          <span key={stage}>
            <small>{String(i + 1).padStart(2, "0")}</small>
            {stage}
            {i < 8 && <ArrowRight size={12} />}
          </span>
        ))}
      </div>
      <ServiceDialog service={service} onClose={() => setService(null)} />
    </>
  );
}
