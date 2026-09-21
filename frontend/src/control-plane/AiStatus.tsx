import { client } from "./client";
import { useResource } from "./hooks";
import { Badge, Empty, Notice, Panel, ResourceState, date, num } from "./ui";

/** Provider identity comes from the server's last actual route, never its label alone. */
export function AiStatus() {
  const resource = useResource(client.llmStatus, 15000);
  const state = resource.data;
  const heuristic = state?.active_provider === "heuristic";
  const healthy =
    state?.status === "HEALTHY" && Boolean(state.last_call) && !heuristic;
  return (
    <Panel
      title="AI connection"
      detail="Configured provider and the last recorded model call."
    >
      <ResourceState resource={resource} />
      {state ? (
        <>
          <div className="row-between">
            <Badge tone={healthy ? "success" : "warning"}>
              {heuristic ? "DEGRADED · HEURISTIC" : state.status}
            </Badge>
            <span className="mono">{state.active_provider}</span>
          </div>
          <dl className="detail-list">
            <dt>Primary provider</dt>
            <dd>{state.primary.provider}</dd>
            <dt>Active model</dt>
            <dd className="preserve">{state.active_model || "Not recorded"}</dd>
            <dt>Fallback used</dt>
            <dd>
              {state.last_call
                ? state.fallback_used
                  ? "Yes"
                  : "No"
                : "No call recorded"}
            </dd>
            <dt>Last call</dt>
            <dd>
              {state.last_call?.completed_at
                ? date(
                    new Date(state.last_call.completed_at * 1000).toISOString(),
                  )
                : "Not recorded"}
            </dd>
            <dt>Call latency</dt>
            <dd>
              {state.latency_ms == null
                ? "Not recorded"
                : `${num(state.latency_ms)} ms`}
            </dd>
            <dt>Deterministic safety</dt>
            <dd>{state.deterministic_safety}</dd>
          </dl>
          {(!state.last_call || heuristic || state.fallback_used) && (
            <Notice>
              {heuristic
                ? "Local heuristic fallback is active. A successful external AI response has not been established by this result."
                : state.fallback_used
                  ? "The last response used a fallback provider. The active model shown above produced that response."
                  : "Configuration alone does not establish a working AI connection. No model call is recorded in this server session."}
            </Notice>
          )}
        </>
      ) : (
        <Empty
          title="AI status unavailable"
          detail="Connect to the backend to inspect its provider status."
        />
      )}
    </Panel>
  );
}
