import { useState } from "react";
import { client } from "./client";
import { useAction, useResource } from "./hooks";
import type { Incident } from "./contracts";
import {
  Badge,
  Button,
  Empty,
  JsonDetails,
  Modal,
  Notice,
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
  const action = useAction();
  const [note, setNote] = useState("");
  const [confirmation, setConfirmation] = useState(false);
  const [message, setMessage] = useState("");
  const available = !!resource.data && !resource.error && !resource.stale;
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
      <Panel
        title="Operator notes"
        detail="Add context to the shared activity stream."
      >
        <form
          className="toolbar"
          onSubmit={(event) => {
            event.preventDefault();
            if (!note.trim() || !available || action.pending) return;
            void action.run(async () => {
              setMessage("");
              const response = await client.emitNote(note.trim());
              if (response.status !== "success")
                throw new Error(
                  response.message || "The note was not accepted.",
                );
              setMessage("Note added to the activity stream.");
              setNote("");
              resource.refresh();
            });
          }}
        >
          <input
            aria-label="Operator note"
            value={note}
            maxLength={2000}
            disabled={action.pending}
            onChange={(event) => setNote(event.target.value)}
            placeholder="What should the next operator know?"
          />
          <Button
            type="submit"
            disabled={!available || !note.trim() || action.pending}
          >
            Add note
          </Button>
        </form>
        {message && <p role="status">{message}</p>}
        {action.error && !confirmation && (
          <Notice danger>{action.error}</Notice>
        )}
        <details>
          <summary>Activity stream maintenance</summary>
          <p className="body-copy">
            Clear the shared event timeline. Export any information you need
            before continuing.
          </p>
          <Button
            tone="danger"
            variant="outline"
            disabled={!available || action.pending}
            onClick={() => setConfirmation(true)}
          >
            Clear activity stream
          </Button>
        </details>
      </Panel>
      <Modal
        open={confirmation}
        onClose={() => {
          if (!action.pending) setConfirmation(false);
        }}
        title="Clear the shared activity stream?"
        description="This removes all timeline events from the backend event store for every operator. This cannot be undone from the console."
      >
        {action.error && <Notice danger>{action.error}</Notice>}
        <div className="dialog-actions">
          <Button
            variant="outline"
            disabled={action.pending}
            onClick={() => setConfirmation(false)}
          >
            Cancel
          </Button>
          <Button
            tone="danger"
            disabled={!available || action.pending}
            onClick={() =>
              void action.run(async () => {
                setMessage("");
                const response = await client.clearEvents();
                if (response.status !== "success")
                  throw new Error(
                    response.message || "The timeline was not cleared.",
                  );
                setConfirmation(false);
                setMessage("Activity stream cleared.");
                resource.refresh();
              })
            }
          >
            {action.pending ? "Clearing…" : "Confirm clear"}
          </Button>
        </div>
      </Modal>
    </>
  );
}
