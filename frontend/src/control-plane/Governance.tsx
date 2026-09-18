import { useState } from "react";
import { client } from "./client";
import { useAction, useResource } from "./hooks";
import type { Approval, Health, RecordData } from "./contracts";
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
  date,
  num,
  statusTone,
} from "./ui";

export function Guard({
  health,
  refresh,
  available,
}: {
  health?: Health;
  refresh: () => void;
  available: boolean;
}) {
  const [level, setLevel] = useState<number>();
  const [resume, setResume] = useState(false);
  const [result, setResult] = useState("");
  const action = useAction();
  const labels = ["Observe", "Recommend", "Guarded", "Autonomous"];
  async function freeze(engaged: boolean) {
    await action.run(async () => {
      const result = await client.freeze(engaged);
      if (result.kill_switch_engaged !== engaged)
        throw new Error(
          "The backend did not confirm the requested freeze state.",
        );
      setResult(
        engaged
          ? "Backend accepted the freeze flag."
          : "Backend accepted the resume request.",
      );
      setResume(false);
      refresh();
    });
  }
  return (
    <>
      <div className="metrics-grid two">
        <Metric
          label="Reported autonomy"
          value={health ? `L${health.autonomy_level}` : "—"}
          detail={
            health ? labels[health.autonomy_level] : "Waiting for backend"
          }
        />
        <Metric
          label="Reported mutation gate"
          value={
            health
              ? health.kill_switch_engaged
                ? "Frozen"
                : "Enabled"
              : "Unknown"
          }
          detail="Last confirmed backend state"
          tone={health?.kill_switch_engaged ? "danger" : ""}
        />
      </div>
      {action.error && <Notice danger>{action.error}</Notice>}
      {result && <Notice>{result}</Notice>}
      <Notice>
        This backend revision does not apply these controls consistently to
        pipeline execution. A reported level or freeze flag is not proof of
        enforcement. Verify the backend controls before running automation.
      </Notice>
      <Panel
        title="Autonomy envelope"
        detail="Request an operating level from the backend."
      >
        <div className="autonomy-grid">
          {labels.map((label, i) => (
            <button
              className={`autonomy-option ${health?.autonomy_level === i ? "chosen" : ""}`}
              key={label}
              onClick={() => setLevel(i)}
              disabled={!available || action.pending}
            >
              <span className="mono">LEVEL {i}</span>
              <h3>{label}</h3>
              <p>
                {
                  [
                    "Read-only observation.",
                    "Require human confirmation.",
                    "Policy-governed safe actions.",
                    "Expanded autonomous authority.",
                  ][i]
                }
              </p>
              {health?.autonomy_level === i && (
                <Badge tone="success">Current</Badge>
              )}
            </button>
          ))}
        </div>
      </Panel>
      <Panel
        title="Emergency mutation freeze"
        detail="Ask the backend to freeze new mutations through its execution gateway."
      >
        <Notice>
          Freeze does not cancel an operation already in progress or stop a
          chaos experiment. Inspect operations and clear sandbox faults
          separately.
        </Notice>
        <div className="panel-foot">
          <p>
            {health?.kill_switch_engaged
              ? "The backend reports mutations are frozen."
              : "Request a freeze of new gateway actions."}
          </p>
          <Button
            tone="danger"
            variant="outline"
            disabled={!available || action.pending}
            onClick={() =>
              health?.kill_switch_engaged ? setResume(true) : void freeze(true)
            }
          >
            {health?.kill_switch_engaged ? "Review resume" : "Freeze mutations"}
          </Button>
        </div>
      </Panel>
      <Modal
        open={level !== undefined || resume}
        onClose={() => {
          if (!action.pending) {
            setLevel(undefined);
            setResume(false);
          }
        }}
        title={
          resume
            ? "Resume infrastructure mutations?"
            : `Set autonomy to L${level}?`
        }
        description="This requests a backend control change. Review the scope before applying."
      >
        <p className="body-copy">
          {resume
            ? "The backend will be asked to clear its freeze flag."
            : `Request ${labels[level ?? 0]} mode. This revision needs an enforcement fix before the setting governs all control-loop decisions.`}
        </p>
        {action.error && <Notice danger>{action.error}</Notice>}
        <div className="dialog-actions">
          <Button
            variant="outline"
            disabled={action.pending}
            onClick={() => {
              setLevel(undefined);
              setResume(false);
            }}
          >
            Cancel
          </Button>
          <Button
            disabled={action.pending}
            onClick={() =>
              resume
                ? void freeze(false)
                : void action.run(async () => {
                    const r = await client.autonomy(level!);
                    if (r.autonomy_level !== level)
                      throw new Error(
                        "Backend did not confirm the requested autonomy level.",
                      );
                    setResult(
                      `Backend confirmed autonomy L${r.autonomy_level}.`,
                    );
                    setLevel(undefined);
                    refresh();
                  })
            }
          >
            {action.pending ? "Applying…" : "Apply change"}
          </Button>
        </div>
      </Modal>
    </>
  );
}
export function Policies() {
  const resource = useResource(client.policies);
  return (
    <>
      <ResourceState resource={resource} />
      <Notice>
        Rules are read-only here. The backend exposes a policy list but no
        policy editing or standalone policy-test endpoint.
      </Notice>
      <Panel
        title="Policy registry"
        detail="The active policies returned by CORTEX Guard."
      >
        {resource.data?.policies.length ? (
          <div className="policy-list">
            {resource.data.policies.map((p) => (
              <article key={p.code}>
                <span className="policy-code">{p.code}</span>
                <div>
                  <h3>{p.name}</h3>
                  <p>{p.description}</p>
                </div>
                <Badge tone="info">Listed by backend</Badge>
              </article>
            ))}
          </div>
        ) : (
          <Empty />
        )}
      </Panel>
    </>
  );
}
export function Approvals({
  available,
  frozen,
}: {
  available: boolean;
  frozen: boolean;
}) {
  const resource = useResource(client.approvals, 5000);
  const [selected, setSelected] = useState<{
    record: Approval;
    approved: boolean;
  }>();
  const [approver, setApprover] = useState("");
  const [result, setResult] = useState<RecordData>();
  const action = useAction();
  const pending =
    resource.data?.pending_approvals.filter((a) => a.status === "pending") ||
    [];
  const expired = (a: Approval) =>
    a.created_at * 1000 + a.ttl_seconds * 1000 <= Date.now();
  return (
    <>
      <ResourceState resource={resource} />
      <Notice>
        Approving may immediately execute the proposed action. The backend
        remains responsible for validating policy and approval expiry.
      </Notice>
      <Panel
        title="Human approval queue"
        detail="Review the exact action and parameters before resolving."
      >
        {pending.length ? (
          pending.map((a) => (
            <article className="approval-card" key={a.approval_id}>
              <div className="row-between">
                <div>
                  <span className="mono muted">{a.approval_id}</span>
                  <h3>{a.action_type.replaceAll("_", " ")}</h3>
                </div>
                <Badge tone="warning">
                  {expired(a) ? "Expired" : `Risk ${a.risk_score}/100`}
                </Badge>
              </div>
              <JsonDetails data={a.params} title="Proposed parameters" />
              <div className="panel-foot">
                <span>
                  {expired(a)
                    ? "Re-evaluation required"
                    : `Expires ${new Date((a.created_at + a.ttl_seconds) * 1000).toLocaleTimeString()}`}
                </span>
                <div className="button-row">
                  <Button
                    variant="outline"
                    disabled={
                      !available ||
                      action.pending ||
                      expired(a) ||
                      resource.stale
                    }
                    onClick={() => setSelected({ record: a, approved: false })}
                  >
                    Reject
                  </Button>
                  <Button
                    disabled={
                      !available ||
                      frozen ||
                      action.pending ||
                      expired(a) ||
                      resource.stale
                    }
                    onClick={() => setSelected({ record: a, approved: true })}
                  >
                    Review approval
                  </Button>
                </div>
              </div>
            </article>
          ))
        ) : (
          <Empty
            title="No pending approvals"
            detail="Actions requiring operator authorization will appear here."
          />
        )}
      </Panel>
      {result && (
        <Panel title="Resolution response">
          <JsonDetails data={result} />
        </Panel>
      )}
      <Modal
        open={!!selected}
        onClose={() => {
          if (!action.pending) setSelected(undefined);
        }}
        title={
          selected?.approved ? "Approve this action?" : "Reject this action?"
        }
        description={
          selected
            ? `${selected.record.action_type} · ${selected.record.approval_id}`
            : ""
        }
      >
        <JsonDetails
          data={selected?.record.params}
          title="Exact action parameters"
        />
        <label>
          Operator name
          <input
            value={approver}
            onChange={(e) => setApprover(e.target.value)}
            placeholder="Name for the audit record"
          />
        </label>
        <p className="muted">This is audit attribution, not authentication.</p>
        {action.error && <Notice danger>{action.error}</Notice>}
        <div className="dialog-actions">
          <Button
            variant="outline"
            disabled={action.pending}
            onClick={() => setSelected(undefined)}
          >
            Cancel
          </Button>
          <Button
            disabled={
              !approver.trim() ||
              !available ||
              action.pending ||
              !selected ||
              expired(selected.record) ||
              (selected.approved && frozen)
            }
            onClick={() =>
              void action.run(async () => {
                if (!selected) return;
                const r = await client.resolve(
                  selected.record.approval_id,
                  selected.approved,
                  approver.trim(),
                );
                if (r.status !== "success")
                  throw new Error(r.message || `Approval was ${r.status}.`);
                setResult(r as RecordData);
                setSelected(undefined);
                resource.refresh();
              })
            }
          >
            {action.pending
              ? "Resolving…"
              : selected?.approved
                ? "Approve and submit"
                : "Confirm rejection"}
          </Button>
        </div>
      </Modal>
    </>
  );
}
export function Audit() {
  const resource = useResource(client.ledger);
  const logs = useResource(client.logs, 30000);
  const [query, setQuery] = useState("");
  const rows =
    resource.data?.records
      .filter((r) =>
        JSON.stringify(r).toLowerCase().includes(query.toLowerCase()),
      )
      .slice()
      .reverse() || [];
  function download() {
    const url = URL.createObjectURL(
      new Blob([JSON.stringify(resource.data, null, 2)], {
        type: "application/json",
      }),
    );
    const a = document.createElement("a");
    a.href = url;
    a.download = `cortex-ledger-${Date.now()}.json`;
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  return (
    <>
      <ResourceState resource={resource} />
      <div className="metrics-grid two">
        <Metric
          label="Chain integrity"
          value={
            resource.data
              ? resource.data.integrity.valid
                ? "Verified"
                : "Failed"
              : "Unknown"
          }
          detail="Integrity reported by backend SHA-256 verifier"
          tone={resource.data?.integrity.valid ? "success" : ""}
        />
        <Metric
          label="Returned records"
          value={num(resource.data?.count)}
          detail="API returns up to 100 recent ledger records"
        />
      </div>
      {resource.data?.integrity.reason && (
        <Notice danger>{resource.data.integrity.reason}</Notice>
      )}
      <Panel
        title="Evidence ledger"
        detail="Inspect attribution, correlation, payload, and hash lineage."
        action={
          <Button
            variant="outline"
            onClick={download}
            disabled={!resource.data}
          >
            Export JSON
          </Button>
        }
      >
        <div className="toolbar">
          <input
            aria-label="Search ledger"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search actor, incident, hash, or event…"
          />
        </div>
        {rows.length ? (
          rows.map((r, i) => (
            <article className="event-record" key={`${r.hash}-${i}`}>
              <div className="row-between">
                <div>
                  <Badge tone={statusTone(r.event_type)}>{r.event_type}</Badge>
                  <p>
                    {r.actor} · {r.correlation_id}
                  </p>
                </div>
                <small>{date(r.timestamp)}</small>
              </div>
              <JsonDetails data={r} title="Inspect event and hash chain" />
            </article>
          ))
        ) : (
          <Empty />
        )}
      </Panel>
      <Panel
        title="Action audit log"
        detail="Separate action log exposed by the backend."
      >
        <ResourceState resource={logs} />
        <JsonDetails data={logs.data?.logs || []} />
      </Panel>
    </>
  );
}
