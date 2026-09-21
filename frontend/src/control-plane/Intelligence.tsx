import { useCallback, useState } from "react";
import { client } from "./client";
import { useAction, useResource } from "./hooks";
import type {
  EvidenceResponse,
  EvaluationReport,
  Forecast,
  Optimization,
} from "./contracts";
import {
  Badge,
  Button,
  Empty,
  JsonDetails,
  Metric,
  Notice,
  Panel,
  ResourceState,
  num,
} from "./ui";

function ForecastChart({ data }: { data: Forecast }) {
  const history = data.history,
    forecast = data.prediction.forecast_series;
  if (!history.length || !forecast.length)
    return <Empty title="No forecast series returned" />;
  const values = [
    ...history.map((p) => p.actual_rps),
    ...forecast.map((p) => p.high_bound),
    ...forecast.map((p) => p.slo_threshold_rps),
  ];
  const max = Math.max(1, ...values) * 1.1,
    count = history.length + forecast.length;
  const x = (i: number) => 55 + (i / Math.max(1, count - 1)) * 830;
  const y = (v: number) => 240 - (v / max) * 200;
  const line = (points: { x: number; y: number }[]) =>
    points.map((p, i) => `${i ? "L" : "M"}${p.x},${p.y}`).join(" ");
  const lower = forecast.map((p, i) => ({
    x: x(history.length + i),
    y: y(p.low_bound),
  }));
  const upper = forecast
    .map((p, i) => ({ x: x(history.length + i), y: y(p.high_bound) }))
    .reverse();
  return (
    <div className="chart-wrap">
      <svg
        viewBox="0 0 920 290"
        role="img"
        aria-label="Modeled historical requests and forecast with uncertainty bounds"
      >
        <title>Request rate, requests per second</title>
        {[0, 1, 2, 3, 4].map((i) => (
          <g key={i}>
            <line
              x1="55"
              x2="885"
              y1={y((max * i) / 4)}
              y2={y((max * i) / 4)}
              className="chart-grid"
            />
            <text x="45" y={y((max * i) / 4) + 4} textAnchor="end">
              {num((max * i) / 4)}
            </text>
          </g>
        ))}
        <path d={`${line([...lower, ...upper])} Z`} className="chart-band" />
        <line
          x1={x(history.length - 1)}
          x2={x(history.length - 1)}
          y1="25"
          y2="240"
          className="chart-boundary"
        />
        <path
          d={line(history.map((p, i) => ({ x: x(i), y: y(p.actual_rps) })))}
          className="chart-history"
        />
        <path
          d={line([
            { x: x(history.length - 1), y: y(history.at(-1)!.actual_rps) },
            ...forecast.map((p, i) => ({
              x: x(history.length + i),
              y: y(p.predicted_rps),
            })),
          ])}
          className="chart-forecast"
        />
        <text x="55" y="273">
          {history[0].timestamp}
        </text>
        <text x={x(history.length - 1)} y="273" textAnchor="middle">
          Now
        </text>
        <text x="885" y="273" textAnchor="end">
          +{forecast.length} minutes
        </text>
      </svg>
      <div className="chart-legend">
        <span>
          <i className="actual" />
          Generated history
        </span>
        <span>
          <i className="forecast" />
          Predicted demand
        </span>
        <span>
          <i className="band" />
          Model bounds
        </span>
      </div>
    </div>
  );
}
export function Predictions() {
  const [horizon, setHorizon] = useState(30);
  const load = useCallback(
    (s: AbortSignal) => client.forecast(horizon, s),
    [horizon],
  );
  const resource = useResource(load, 60000);
  const prediction = resource.data?.prediction;
  return (
    <>
      <Notice>
        The backend generates the input history for this forecast. These
        predictions and model scores do not establish live production accuracy.
      </Notice>
      <ResourceState resource={resource} />
      <Panel
        title="Workload forecast"
        detail={prediction?.model || "Demand and capacity planning"}
        action={
          <select
            aria-label="Forecast horizon"
            value={horizon}
            onChange={(e) => setHorizon(Number(e.target.value))}
          >
            {[5, 15, 30, 60].map((h) => (
              <option key={h} value={h}>
                {h} minutes
              </option>
            ))}
          </select>
        }
      >
        {resource.data ? (
          <ForecastChart data={resource.data} />
        ) : (
          <Empty title="Waiting for forecast" />
        )}
      </Panel>
      <div className="metrics-grid">
        <Metric
          label="Current modeled demand"
          value={num(prediction?.current_rps)}
          detail="Requests per second"
        />
        <Metric
          label="Recommended capacity"
          value={num(prediction?.recommended_replicas)}
          detail="Replicas from model"
        />
        <Metric
          label="Capacity reserve"
          value={
            prediction ? `${num(prediction.adaptive_reserve_pct, 1)}%` : "—"
          }
          detail="Modeled reserve allowance"
        />
        <Metric
          label="Forecast horizon"
          value={`${horizon}m`}
          detail="User-selected interval"
        />
      </div>
      {prediction && (
        <Panel
          title="Model evidence"
          detail="Metadata and scores returned by the forecast endpoint."
        >
          <JsonDetails
            data={prediction.eval_metrics}
            title="Evaluation metrics"
          />
          <JsonDetails
            data={prediction.model_metadata}
            title="Training metadata"
          />
          <details className="json-details">
            <summary>Accessible forecast data table</summary>
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>Minute</th>
                    <th>RPS</th>
                    <th>Lower bound</th>
                    <th>Upper bound</th>
                  </tr>
                </thead>
                <tbody>
                  {prediction.forecast_series.map((p) => (
                    <tr key={p.minute_offset}>
                      <td>+{p.minute_offset}</td>
                      <td>{p.predicted_rps}</td>
                      <td>{p.low_bound}</td>
                      <td>{p.high_bound}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </details>
        </Panel>
      )}
    </>
  );
}
export function Optimizer({
  mode: initialMode = "BALANCED",
}: {
  mode?: string;
}) {
  const [mode, setMode] = useState(initialMode);
  const [replicas, setReplicas] = useState(6);
  const [rps, setRps] = useState(480);
  const [result, setResult] = useState<Optimization>();
  const action = useAction();
  return (
    <>
      <Notice>
        Planning estimates use the backend’s fixed price, energy, carbon, and
        latency assumptions. They are not billing data or measured emissions.
      </Notice>
      <Panel
        title={
          initialMode === "GREEN"
            ? "Sustainability planner"
            : initialMode === "COST"
              ? "Cost planner"
              : "Multi-objective optimizer"
        }
        detail="Compare capacity choices before proposing a change."
      >
        <form
          className="form-grid"
          onSubmit={(e) => {
            e.preventDefault();
            setResult(undefined);
            void action.run(async () =>
              setResult(await client.optimize(mode, replicas, rps)),
            );
          }}
        >
          <label>
            Optimization mode
            <select
              disabled={action.pending}
              value={mode}
              onChange={(e) => {
                setMode(e.target.value);
                setResult(undefined);
              }}
            >
              {[
                "BALANCED",
                "COST",
                "PERFORMANCE",
                "RELIABILITY",
                "GREEN",
                "EMERGENCY",
              ].map((m) => (
                <option key={m}>{m}</option>
              ))}
            </select>
          </label>
          <label>
            Current replicas
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
                setResult(undefined);
              }}
            />
          </label>
          <label>
            Forecast demand (RPS)
            <input
              disabled={action.pending}
              type="number"
              min="1"
              max="1000000"
              required
              value={rps}
              onChange={(e) => {
                setRps(Number(e.target.value));
                setResult(undefined);
              }}
            />
          </label>
          <Button type="submit" disabled={action.pending}>
            {action.pending ? "Comparing…" : "Compare configurations"}
          </Button>
        </form>
        {action.error && <Notice danger>{action.error}</Notice>}
      </Panel>
      {result ? (
        <>
          <div className="metrics-grid">
            <Metric
              label="Selected configuration"
              value={result.selected_candidate.replicas}
              detail="Replicas · recommendation only"
            />
            <Metric
              label="Estimated hourly cost"
              value={`$${num(result.selected_candidate.estimated_cost_per_hr, 2)}`}
              detail="Model assumption · USD/hour"
            />
            <Metric
              label="Expected latency"
              value={`${num(result.selected_candidate.expected_p95_ms)} ms`}
              detail="Modeled p95"
            />
            <Metric
              label="Estimated carbon"
              value={num(result.selected_candidate.carbon_gco2_per_hr, 1)}
              detail="gCO₂/hour · model assumption"
            />
          </div>
          <Panel
            title="Candidate comparison"
            detail={result.selection_rationale}
          >
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>Configuration</th>
                    <th>Cost / hour</th>
                    <th>p95</th>
                    <th>SLO risk</th>
                    <th>Energy / hour</th>
                    <th>Carbon / hour</th>
                    <th>Frontier</th>
                  </tr>
                </thead>
                <tbody>
                  {result.candidates.map((c) => (
                    <tr
                      key={c.replicas}
                      className={
                        c.replicas === result.selected_candidate.replicas
                          ? "selected-row"
                          : ""
                      }
                    >
                      <td>
                        {c.name}
                        {c.replicas === result.selected_candidate.replicas && (
                          <small>Recommended</small>
                        )}
                      </td>
                      <td>${num(c.estimated_cost_per_hr, 2)}</td>
                      <td>{num(c.expected_p95_ms, 1)} ms</td>
                      <td>{num(c.slo_violation_probability * 100, 1)}%</td>
                      <td>{num(c.energy_kwh_per_hr, 3)} kWh</td>
                      <td>{num(c.carbon_gco2_per_hr, 1)} gCO₂</td>
                      <td>
                        {c.is_pareto ? (
                          <Badge tone="info">Pareto</Badge>
                        ) : (
                          "Dominated"
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="panel-foot">
              <span>Comparing configurations does not execute a change.</span>
              <Button href="#/simulator" variant="outline">
                Open digital twin
              </Button>
            </div>
          </Panel>
        </>
      ) : (
        <Empty
          title="Explore the trade-offs"
          detail="Choose your planning inputs and compare backend-generated candidates."
        />
      )}
    </>
  );
}
export function Memory() {
  const [query, setQuery] = useState("");
  const [k, setK] = useState(5);
  const [response, setResponse] = useState<EvidenceResponse>();
  const [service, setService] = useState("");
  const [environment, setEnvironment] = useState("");
  const [technology, setTechnology] = useState("");
  const results = response?.results;
  const [searched, setSearched] = useState("");
  const action = useAction();
  return (
    <>
      <Panel
        title="Operational memory"
        detail="Search incident evidence by failure signals, operational context, and verified outcomes."
      >
        <form
          className="toolbar"
          onSubmit={(e) => {
            e.preventDefault();
            if (!query.trim()) return;
            void action.run(async () => {
              setResponse(
                await client.retrieve(query.trim(), k, {
                  ...(service.trim() ? { service: service.trim() } : {}),
                  ...(environment.trim()
                    ? { environment: environment.trim() }
                    : {}),
                  ...(technology.trim()
                    ? {
                        technologies: technology
                          .split(",")
                          .map((item) => item.trim())
                          .filter(Boolean),
                      }
                    : {}),
                }),
              );
              setSearched(query.trim());
            });
          }}
        >
          <input
            aria-label="Search operational memory"
            required
            minLength={3}
            maxLength={12000}
            placeholder="Describe an incident, symptom, or failure…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <select
            aria-label="Result count"
            value={k}
            onChange={(e) => setK(Number(e.target.value))}
          >
            {[3, 5, 10].map((n) => (
              <option key={n} value={n}>
                Top {n}
              </option>
            ))}
          </select>
          <Button type="submit" disabled={action.pending}>
            {action.pending ? "Searching…" : "Search memory"}
          </Button>
        </form>
        <details className="json-details">
          <summary>Optional incident context</summary>
          <div className="form-grid">
            <label>
              Service
              <input
                maxLength={200}
                value={service}
                onChange={(e) => setService(e.target.value)}
                placeholder="payment-api"
              />
            </label>
            <label>
              Environment
              <input
                maxLength={200}
                value={environment}
                onChange={(e) => setEnvironment(e.target.value)}
                placeholder="production"
              />
            </label>
            <label>
              Technologies
              <input
                maxLength={1000}
                value={technology}
                onChange={(e) => setTechnology(e.target.value)}
                placeholder="postgresql, pgbouncer"
              />
            </label>
          </div>
          <p className="body-copy">
            Enter known details. Related incidents from other services can still
            be relevant.
          </p>
        </details>
        {action.error && <Notice danger>{action.error}</Notice>}
        {response?.warnings?.map((warning, index) => (
          <Notice key={`${index}-${warning}`}>{warning}</Notice>
        ))}
        {response && (
          <div className="row-between">
            <Badge
              tone={
                response.status === "DEGRADED_RETRIEVAL" ? "warning" : "info"
              }
            >
              {response.status === "DEGRADED_RETRIEVAL"
                ? "Degraded retrieval"
                : "Evidence retrieved"}
            </Badge>
            <span className="mono">
              {response.retrieval_stage?.replaceAll("_", " ")} ·{" "}
              {num(response.retrieval_time_ms)} ms
            </span>
          </div>
        )}
        {results && (
          <p className="body-copy">
            {results.length} results for “{searched}”
          </p>
        )}
        {results?.length ? (
          <div className="evidence-grid">
            {results.map((r, i) => (
              <article className="evidence-card" key={`${r.id}-${i}`}>
                <div className="row-between">
                  <Badge tone="info">{r.document_type}</Badge>
                  <span className="mono">
                    Score {num(r.final_score ?? r.score, 3)}
                  </span>
                </div>
                <h3>{r.title}</h3>
                <p className="mono muted">{r.id}</p>
                {r.simulated && <Badge tone="warning">Modeled sandbox evidence</Badge>}
                {r.environment && <p className="muted">Environment: {r.environment}</p>}
                {r.verification_outcome && (
                  <Badge
                    tone={
                      /WORSE|ROLLED_BACK|NO_CHANGE|FAILED/.test(
                        r.verification_outcome,
                      )
                        ? "warning"
                        : /^(VERIFIED_)?RECOVERED$/.test(r.verification_outcome)
                          ? "success"
                          : "neutral"
                    }
                  >
                    {r.verification_outcome.replaceAll("_", " ")}
                  </Badge>
                )}
                {/WORSE|ROLLED_BACK|NO_CHANGE|FAILED/.test(
                  r.verification_outcome || "",
                ) && (
                  <Notice>
                    Negative evidence:{" "}
                    {r.historical_action?.replaceAll("_", " ") ||
                      "the historical action"}{" "}
                    did not establish recovery. This record is not a
                    recommendation to repeat it.
                  </Notice>
                )}
                {!!r.why_retrieved?.length && (
                  <div>
                    <h4>Why this matched</h4>
                    <ul className="body-copy">
                      {r.why_retrieved.map((reason, index) => (
                        <li key={`${index}-${reason}`}>{reason}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {(r.content || r.text) && (
                  <p className="body-copy preserve">{r.content || r.text}</p>
                )}
                <div className="tag-list">
                  {r.tags?.map((t) => (
                    <span key={t}>{t}</span>
                  ))}
                </div>
                <JsonDetails data={r} title="Source details" />
              </article>
            ))}
          </div>
        ) : (
          <Empty
            title={results ? "No matching evidence" : "Start with a symptom"}
            detail="Try a specific service and failure pattern, such as auth-service CrashLoopBackOff."
          />
        )}
      </Panel>
      {response?.stages_attempted && (
        <Panel
          title="Search scope"
          detail="Search stages and filters actually reported by the retrieval engine."
        >
          <p className="body-copy">
            {response.stages_attempted
              .map((stage) => stage.replaceAll("_", " "))
              .join(" → ")}
          </p>
          <p className="body-copy">
            Candidates considered: {num(response.candidate_count)} · Semantic
            index: {response.semantic_available ? "available" : "unavailable"}
          </p>
          {!!response.relaxed_filters?.length && (
            <p className="body-copy">
              Scope expanded: {response.relaxed_filters.join(", ")}
            </p>
          )}
          <JsonDetails
            data={response.filters_applied}
            title="Applied filters"
          />
        </Panel>
      )}
    </>
  );
}
export function Evaluation() {
  const action = useAction();
  const [result, setResult] = useState<EvaluationReport>();
  return (
    <>
      <Notice>
        This benchmark measures retrieval against labeled scenarios. Safety
        authorization is tested separately. A small corpus does not establish
        performance at production scale.
      </Notice>
      <Panel
        title="Evaluation workbench"
        detail="Run the backend’s retrieval benchmark against its scenario dataset."
        action={
          <Button
            disabled={action.pending}
            onClick={() =>
              void action.run(async () => setResult(await client.benchmark()))
            }
          >
            {action.pending ? "Evaluating…" : "Run retrieval benchmark"}
          </Button>
        }
      >
        {action.error && <Notice danger>{action.error}</Notice>}
        {result ? (
          <>
            <Badge tone="info">{result.status}</Badge>
            <p className="body-copy">
              {result.corpus_size} indexed documents · {result.embedding_model}{" "}
              · Model/index warmup {num(result.model_index_warmup_ms)} ms
            </p>
            <div className="table-scroll">
              <table>
                <caption>Measured retrieval baselines</caption>
                <thead>
                  <tr>
                    <th>Strategy</th>
                    <th>Scenarios</th>
                    <th>Hit@1</th>
                    <th>Hit@3</th>
                    <th>Recall@5</th>
                    <th>MRR</th>
                    <th>NDCG@5</th>
                    <th>p95 latency</th>
                  </tr>
                </thead>
                <tbody>
                  {result.baselines.map((row) => (
                    <tr key={row.strategy}>
                      <td>{row.strategy.replaceAll("_", " ")}</td>
                      <td>{row.scenarios}</td>
                      <td>{num(row.hit_at_1, 3)}</td>
                      <td>{num(row.hit_at_3, 3)}</td>
                      <td>{num(row.recall_at_5, 3)}</td>
                      <td>{num(row.mrr, 3)}</td>
                      <td>{num(row.ndcg_at_5, 3)}</td>
                      <td>{num(row.p95_latency_ms, 1)} ms</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <Notice>
              Safety evaluation: {result.safety.status.replaceAll("_", " ")}.{" "}
              {result.safety.reason}
            </Notice>
            {result.limitations.map((limitation) => (
              <p className="body-copy" key={limitation}>
                {limitation}
              </p>
            ))}
            <JsonDetails data={result} title="Full measured report" />
          </>
        ) : (
          <Empty
            title="No benchmark run in this session"
            detail="Run the benchmark to retrieve measured scores. This may take a few minutes."
          />
        )}
      </Panel>
    </>
  );
}
