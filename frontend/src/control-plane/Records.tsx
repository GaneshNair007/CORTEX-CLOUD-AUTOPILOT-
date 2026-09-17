import { useState } from "react";
import { client } from "./client";
import { useResource } from "./hooks";
import type { Incident } from "./contracts";
import {
  Badge,
  Empty,
  JsonDetails,
  Modal,
  Panel,
  ResourceState,
  date,
  statusTone,
} from "./ui";

export function Incidents() {
  const resource = useResource(client.incidents);
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("ALL");
  const [selectedId, setSelectedId] = useState(
    new URLSearchParams(location.hash.split("?")[1]).get("id"),
  );
  const rows =
    resource.data?.incidents.filter(
      (i) =>
        (status === "ALL" || i.status === status) &&
        `${i.id} ${i.service} ${i.title}`
          .toLowerCase()
          .includes(query.toLowerCase()),
    ) || [];
  const selected: Incident | undefined = resource.data?.incidents.find(
    (i) => i.id === selectedId,
  );
  return (
    <>
      <ResourceState resource={resource} />
      <Panel
        title="Incident command"
        detail="Persisted incidents, their root causes, and recorded outcomes."
      >
        <div className="toolbar">
          <input
            aria-label="Search incidents"
            placeholder="Search incidents or services…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <select
            aria-label="Incident status"
            value={status}
            onChange={(e) => setStatus(e.target.value)}
          >
            <option value="ALL">All statuses</option>
            <option>OPEN</option>
            <option>RESOLVED</option>
          </select>
          <Badge>{rows.length} records</Badge>
        </div>
        {rows.length ? (
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Incident / service</th>
                  <th>Summary</th>
                  <th>Severity</th>
                  <th>Status</th>
                  <th>Detected</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((i) => (
                  <tr key={i.id}>
                    <td>
                      <button
                        className="text-link"
                        onClick={() => setSelectedId(i.id)}
                      >
                        {i.id}
                      </button>
                      <small>{i.service}</small>
                    </td>
                    <td>{i.title}</td>
                    <td>
                      <Badge tone={i.severity === "P1" ? "danger" : "warning"}>
                        {i.severity}
                      </Badge>
                    </td>
                    <td>
                      <Badge tone={statusTone(i.status)}>{i.status}</Badge>
                    </td>
                    <td className="mono">{date(i.detected_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <Empty
            title={
              query || status !== "ALL"
                ? "No matching incidents"
                : "No incidents returned"
            }
          />
        )}
      </Panel>
      <Modal
        open={!!selected}
        onClose={() => setSelectedId(null)}
        title={selected?.id || "Incident"}
        description={selected?.title || ""}
      >
        {selected && (
          <>
            <Badge tone={statusTone(selected.status)}>{selected.status}</Badge>
            <dl className="detail-list">
              <dt>Service</dt>
              <dd>{selected.service}</dd>
              <dt>Root cause</dt>
              <dd>{selected.root_cause || "Not yet recorded"}</dd>
              <dt>Detected</dt>
              <dd>{date(selected.detected_at)}</dd>
              <dt>Resolved</dt>
              <dd>{date(selected.resolved_at)}</dd>
            </dl>
            <JsonDetails data={selected} />
          </>
        )}
      </Modal>
    </>
  );
}
export function Operations() {
  const resource = useResource(client.operations);
  return (
    <>
      <ResourceState resource={resource} />
      <Panel
        title="Operations & verification"
        detail="Execution status and verification outcomes from the persisted operation store."
      >
        {resource.data?.operations.length ? (
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Operation</th>
                  <th>Target</th>
                  <th>Status</th>
                  <th>Guard</th>
                  <th>Verification</th>
                  <th>Time</th>
                </tr>
              </thead>
              <tbody>
                {resource.data.operations.map((o) => (
                  <tr key={o.proposal_id}>
                    <td>
                      {o.action_type}
                      <small>{o.proposal_id}</small>
                    </td>
                    <td>{o.target}</td>
                    <td>
                      <Badge tone={statusTone(o.status)}>{o.status}</Badge>
                    </td>
                    <td>{o.guard_decision || "Not recorded"}</td>
                    <td>{o.verification_outcome || "Not recorded"}</td>
                    <td>{date(o.executed_at || o.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <Empty title="No operations recorded" />
        )}
      </Panel>
    </>
  );
}
export function Events() {
  const resource = useResource(client.events);
  const [query, setQuery] = useState("");
  const rows =
    resource.data?.events
      .filter((e) =>
        JSON.stringify(e).toLowerCase().includes(query.toLowerCase()),
      )
      .slice()
      .reverse() || [];
  return (
    <>
      <ResourceState resource={resource} />
      <Panel
        title="Control-plane events"
        detail="Search lifecycle events and inspect their original payloads."
      >
        <div className="toolbar">
          <input
            aria-label="Search events"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search event type, service, or correlation…"
          />
        </div>
        {rows.length ? (
          rows.map((e) => (
            <div className="event-record" key={e.event_id}>
              <div className="row-between">
                <strong>{e.type.replaceAll("_", " ")}</strong>
                <small>{date(e.timestamp)}</small>
              </div>
              <JsonDetails data={e.payload} />
            </div>
          ))
        ) : (
          <Empty />
        )}
      </Panel>
    </>
  );
}
