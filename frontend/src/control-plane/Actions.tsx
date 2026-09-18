import { useState } from "react";
import { client } from "./client";
import { useAction, useResource } from "./hooks";
import type {
  ActionResult,
  Pipeline,
  RecordData,
  Twin as TwinData,
} from "./contracts";
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

export function Twin({
  available,
  frozen,
}: {
  available: boolean;
  frozen: boolean;
}) {
  const topology = useResource(client.topology, 30000);
  const [target, setTarget] = useState(
    new URLSearchParams(location.hash.split("?")[1]).get("service") || "",
  );
  const [kind, setKind] = useState("scale_service");
  const [replicas, setReplicas] = useState(8);
  const [result, setResult] = useState<TwinData>();
  const [execution, setExecution] = useState<ActionResult>();
  const [confirm, setConfirm] = useState(false);
  const action = useAction();
  const params: RecordData =
    kind === "scale_service"
      ? { service: target, replicas }
      : { service: target };
  const invalidate = () => {
    setResult(undefined);
    setExecution(undefined);
  };
  return (
    <>
      <Notice>
        The twin calculates consequences using a modeled graph and heuristic
        impact assumptions. Simulation is not proof that a real action is safe.
      </Notice>
      <Panel
        title="Counterfactual digital twin"
        detail="Build a proposed change and inspect its modeled consequences."
      >
        <form
          className="form-grid"
          onSubmit={(e) => {
            e.preventDefault();
            invalidate();
            void action.run(async () =>
              setResult(await client.twin(kind, params)),
            );
          }}
        >
          <label>
            Target service
            <select
              aria-label="Target service"
              disabled={action.pending}
              required
              value={target}
              onChange={(e) => {
                setTarget(e.target.value);
                invalidate();
              }}
            >
              <option value="">Choose service</option>
              {topology.data?.nodes.map((n) => (
                <option key={n.id}>{n.id}</option>
              ))}
            </select>
          </label>
          <label>
            Proposed action
            <select
              disabled={action.pending}
              value={kind}
              onChange={(e) => {
                setKind(e.target.value);
                invalidate();
              }}
            >
              {[
                "scale_service",
                "restart_service",
                "rollback_deployment",
                "restart_database",
              ].map((k) => (
                <option key={k}>{k}</option>
              ))}
            </select>
          </label>
          {kind === "scale_service" && (
            <label>
              Target replicas
              <input
                disabled={action.pending}
                type="number"
                min="1"
                max="1000"
                step="1"
                required
                value={replicas}
                onChange={(e) => {
                  setReplicas(Number(e.target.value));
                  invalidate();
                }}
              />
            </label>
          )}
          <Button
            type="submit"
            disabled={!target || action.pending || !available}
          >
            {action.pending ? "Working…" : "Simulate change"}
          </Button>
        </form>
        <ResourceState resource={topology} />
        {action.error && <Notice danger>{action.error}</Notice>}
      </Panel>
      {result ? (
        <>
          <div className="metrics-grid">
            <Metric
              label="Blast radius"
              value={`${result.blast_radius.score}/100`}
              detail={result.blast_radius.risk_level}
            />
            <Metric
              label="Affected services"
              value={result.blast_radius.affected_services.length}
              detail="Transitive dependencies"
            />
            <Metric
              label="Projected downtime"
              value={`${num(result.projected_downtime_sec)}s`}
              detail="Heuristic estimate"
            />
            <Metric
              label="Predicted p95"
              value={`${num(result.predicted_p95_ms)} ms`}
              detail="Modeled target latency"
            />
          </div>
          <Panel title="Simulation result" detail={result.summary}>
            <Badge tone="info">{result.reversibility}</Badge>
            {result.slo_breaches.map((b) => (
              <Notice key={b}>{b}</Notice>
            ))}
            <JsonDetails
              data={result}
              title="Inspect shadow state and critical paths"
            />
            <div className="panel-foot">
              <span>Every action is submitted to the backend gateway.</span>
              <Button
                disabled={frozen || !available || action.pending}
                onClick={() => setConfirm(true)}
              >
                Review execution
              </Button>
            </div>
          </Panel>
        </>
      ) : (
        <Empty
          title="Test a change before you act"
          detail="Select a target and simulate a proposed action."
        />
      )}
      {execution && (
        <Panel title="Gateway outcome" detail={execution.message}>
          <Badge
            tone={statusTone(
              execution.action_result?.status ||
                execution.execution_result?.status ||
                execution.status,
            )}
          >
            {execution.action_result?.status ||
              execution.execution_result?.status ||
              execution.status}
          </Badge>
          <JsonDetails data={execution} />
        </Panel>
      )}
      <Modal
        open={confirm}
        onClose={() => {
          if (!action.pending) setConfirm(false);
        }}
        title="Submit an infrastructure change?"
        description="This may mutate infrastructure. The gateway evaluates the action again and may block it or require approval."
      >
        <JsonDetails
          data={{ action_type: kind, params }}
          title="Exact proposal"
        />
        <Notice>
          Simulation uses modeled targets. Confirm this service name matches the
          environment connected to your backend.
        </Notice>
        {action.error && <Notice danger>{action.error}</Notice>}
        <div className="dialog-actions">
          <Button
            variant="outline"
            disabled={action.pending}
            onClick={() => setConfirm(false)}
          >
            Cancel
          </Button>
          <Button
            disabled={!available || frozen || action.pending}
            onClick={() =>
              void action.run(async () => {
                const r = await client.action(kind, params);
                setExecution(r);
                setConfirm(false);
              })
            }
          >
            {action.pending ? "Submitting…" : "Submit through CORTEX"}
          </Button>
        </div>
      </Modal>
    </>
  );
}
const stages = [
  "observe",
  "understand",
  "predict",
  "simulate",
  "optimize",
  "authorize",
  "act",
  "verify",
  "learn",
];
export function PipelinePage({
  available,
  frozen,
}: {
  available: boolean;
  frozen: boolean;
}) {
  const [service, setService] = useState("payment-service");
  const [severity, setSeverity] = useState("P1");
  const [symptom, setSymptom] = useState("");
  const [result, setResult] = useState<Pipeline>();
  const [confirm, setConfirm] = useState(false);
  const action = useAction();
  return (
    <>
      <Notice>
        The control loop can execute real infrastructure changes. It returns all
        stages after completion; this API does not stream stage progress.
      </Notice>
      <Panel
        title="Closed-loop operations"
        detail="Observe → understand → predict → simulate → optimize → authorize → act → verify → learn."
      >
        <form
          className="form-grid"
          onSubmit={(e) => {
            e.preventDefault();
            setConfirm(true);
          }}
        >
          <label>
            Backend service identifier
            <input
              disabled={action.pending}
              required
              value={service}
              onChange={(e) => setService(e.target.value)}
              maxLength={100}
            />
          </label>
          <label>
            Severity
            <select
              disabled={action.pending}
              value={severity}
              onChange={(e) => setSeverity(e.target.value)}
            >
              {["P1", "P2", "P3"].map((s) => (
                <option key={s}>{s}</option>
              ))}
            </select>
          </label>
          <label className="full">
            Observed symptom
            <textarea
              disabled={action.pending}
              required
              minLength={10}
              maxLength={4000}
              value={symptom}
              onChange={(e) => setSymptom(e.target.value)}
              placeholder="Describe what you observed and the service affected…"
            />
          </label>
          <Button
            type="submit"
            disabled={!available || frozen || action.pending}
          >
            Review control-loop run
          </Button>
        </form>
        {action.pending && (
          <Notice>
            Control loop is running. Waiting for the backend response;
            operations may continue if the connection times out.
          </Notice>
        )}
        {action.error && <Notice danger>{action.error}</Notice>}
      </Panel>
      {result ? (
        <>
          <div className="metrics-grid two">
            <Metric
              label="Execution outcome"
              value={result.action_result.status}
              detail={result.incident_id}
            />
            <Metric
              label="Backend duration"
              value={`${num(result.total_duration_sec, 2)}s`}
              detail="Duration of this run"
            />
          </div>
          <div className="stage-grid">
            {stages.map((stage, i) => (
              <Panel
                title={`${String(i + 1).padStart(2, "0")} · ${stage}`}
                key={stage}
              >
                <Badge tone={result.stages[stage] ? "info" : "warning"}>
                  {result.stages[stage] ? "Response received" : "Not returned"}
                </Badge>
                <JsonDetails
                  data={result.stages[stage] || { status: "Not returned" }}
                  title="Stage evidence"
                />
              </Panel>
            ))}
          </div>
          <Panel title="Complete execution response">
            <JsonDetails data={result.action_result} />
          </Panel>
        </>
      ) : (
        <Empty
          title="Every decision leaves evidence"
          detail="Run a reviewed incident to inspect each stage and the final verification outcome."
        />
      )}
      <Modal
        open={confirm}
        onClose={() => {
          if (!action.pending) setConfirm(false);
        }}
        title="Run the infrastructure control loop?"
        description={`Target: ${service} · Severity: ${severity}. The backend may execute a remediation action.`}
      >
        <p className="body-copy preserve">{symptom}</p>
        {action.error && <Notice danger>{action.error}</Notice>}
        <div className="dialog-actions">
          <Button
            variant="outline"
            disabled={action.pending}
            onClick={() => setConfirm(false)}
          >
            Cancel
          </Button>
          <Button
            disabled={!available || frozen || action.pending}
            onClick={() => {
              setConfirm(false);
              setResult(undefined);
              void action.run(async () =>
                setResult(
                  await client.pipeline(
                    service.trim(),
                    severity,
                    symptom.trim(),
                  ),
                ),
              );
            }}
          >
            Run reviewed incident
          </Button>
        </div>
      </Modal>
    </>
  );
}
export function Chaos({
  available,
  frozen,
}: {
  available: boolean;
  frozen: boolean;
}) {
  const resource = useResource(client.experiments, 5000);
  const [service, setService] = useState("payment-service");
  const [fault, setFault] = useState("latency");
  const [confirm, setConfirm] = useState(false);
  const [result, setResult] = useState<RecordData>();
  const action = useAction();
  return (
    <>
      <Notice>
        Fault injection affects the backend’s sandbox. The endpoint fixes
        duration at 30 seconds; expiry labels do not prove recovery. Clear the
        fault and check the resulting response.
      </Notice>
      <Panel
        title="Chaos laboratory"
        detail="Controlled experiments against the connected sandbox."
      >
        <form
          className="form-grid"
          onSubmit={(e) => {
            e.preventDefault();
            setConfirm(true);
          }}
        >
          <label>
            Sandbox service
            <input
              disabled={action.pending}
              required
              value={service}
              onChange={(e) => setService(e.target.value)}
            />
          </label>
          <label>
            Fault type
            <select
              disabled={action.pending}
              value={fault}
              onChange={(e) => setFault(e.target.value)}
            >
              {[
                "pod_kill",
                "cpu_saturation",
                "db_outage",
                "latency",
                "traffic_spike",
              ].map((f) => (
                <option key={f}>{f}</option>
              ))}
            </select>
          </label>
          <Button
            type="submit"
            tone="danger"
            disabled={!available || frozen || action.pending}
          >
            Review experiment
          </Button>
        </form>
        {action.error && <Notice danger>{action.error}</Notice>}
        {result && <JsonDetails data={result} title="Last chaos response" />}
      </Panel>
      <ResourceState resource={resource} />
      <Panel title="Experiments" detail="Backend-reported experiment state.">
        {resource.data?.experiments.length ? (
          resource.data.experiments.map((e) => (
            <article className="event-record" key={e.experiment_id}>
              <div className="row-between">
                <div>
                  <h3>
                    {e.fault_type} · {e.target_service}
                  </h3>
                  <small>{e.experiment_id}</small>
                </div>
                <Badge tone={statusTone(e.status)}>{e.status}</Badge>
              </div>
              <div className="panel-foot">
                <span>
                  {e.duration_sec
                    ? `${e.duration_sec}s configured duration`
                    : ""}
                </span>
                <Button
                  variant="outline"
                  disabled={!available || action.pending}
                  onClick={() =>
                    void action.run(async () => {
                      setResult(await client.clearChaos(e.target_service));
                      resource.refresh();
                    })
                  }
                >
                  Clear faults on {e.target_service}
                </Button>
              </div>
            </article>
          ))
        ) : (
          <Empty title="No experiments returned" />
        )}
      </Panel>
      <Modal
        open={confirm}
        onClose={() => {
          if (!action.pending) setConfirm(false);
        }}
        title="Inject this sandbox fault?"
        description={`${fault} on ${service}. This deliberately disrupts the selected sandbox service.`}
      >
        {action.error && <Notice danger>{action.error}</Notice>}
        <div className="dialog-actions">
          <Button
            variant="outline"
            disabled={action.pending}
            onClick={() => setConfirm(false)}
          >
            Cancel
          </Button>
          <Button
            tone="danger"
            disabled={!available || frozen || action.pending}
            onClick={() =>
              void action.run(async () => {
                setResult(await client.chaos(fault, service.trim()));
                setConfirm(false);
                resource.refresh();
              })
            }
          >
            {action.pending ? "Injecting…" : "Inject sandbox fault"}
          </Button>
        </div>
      </Modal>
    </>
  );
}
