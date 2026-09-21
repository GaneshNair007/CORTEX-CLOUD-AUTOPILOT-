import { useState } from "react";
import {
  client,
  getBase,
  saveBase,
  hasOperatorToken,
  setOperatorToken,
  clearOperatorToken,
} from "./client";
import { AiStatus } from "./AiStatus";
import { useResource } from "./hooks";
import { Badge, Button, Empty, Notice, Panel, ResourceState, num } from "./ui";
export function Reliability() {
  const resource = useResource(client.topology);
  return (
    <>
      <Notice>
        This is a modeled p95-to-SLO comparison from topology. Live SLO windows,
        availability history, and error-budget burn are not exposed by the
        backend.
      </Notice>
      <ResourceState resource={resource} />
      <Panel
        title="Reliability targets"
        detail="Compare each service’s modeled latency with its configured SLO."
      >
        {resource.data?.nodes.length ? (
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Service</th>
                  <th>Modeled p95</th>
                  <th>Latency SLO</th>
                  <th>Headroom</th>
                  <th>Comparison</th>
                </tr>
              </thead>
              <tbody>
                {resource.data.nodes.map((s) => (
                  <tr key={s.id}>
                    <td>{s.id}</td>
                    <td>{num(s.p95_ms)} ms</td>
                    <td>{num(s.slo_ms)} ms</td>
                    <td>
                      <div className="budget-bar">
                        <span
                          style={{
                            width: `${Math.max(0, Math.min(100, (1 - s.p95_ms / s.slo_ms) * 100))}%`,
                          }}
                        />
                      </div>
                    </td>
                    <td>
                      <Badge tone={s.p95_ms <= s.slo_ms ? "success" : "danger"}>
                        {s.p95_ms <= s.slo_ms
                          ? "Within model target"
                          : "Exceeds model target"}
                      </Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <Empty />
        )}
      </Panel>
    </>
  );
}
export function Providers() {
  return (
    <>
      <Notice>
        No provider discovery or connection-management endpoint exists in the
        current API. Connection state cannot be verified from this console.
      </Notice>
      <div className="provider-grid">
        {[
          {
            name: "Local sandbox",
            monogram: "SB",
            detail:
              "Local process adapter implemented in the backend. Runtime state is not exposed.",
          },
          {
            name: "Docker",
            monogram: "DK",
            detail:
              "Docker adapter is present. The API does not report whether Docker is connected.",
          },
          {
            name: "Kubernetes",
            monogram: "K8",
            detail:
              "Backend placeholder; connection and operations are not implemented.",
          },
          {
            name: "Amazon Web Services",
            monogram: "AWS",
            detail: "Backend placeholder; no verified AWS connection.",
          },
          {
            name: "Microsoft Azure",
            monogram: "AZ",
            detail: "Backend placeholder; no verified Azure connection.",
          },
          {
            name: "Google Cloud",
            monogram: "GC",
            detail: "Backend placeholder; no verified Google Cloud connection.",
          },
        ].map((p) => (
          <Panel title={p.name} key={p.name}>
            <div className="provider-monogram">{p.monogram}</div>
            <Badge>
              {p.name === "Docker" || p.name === "Local sandbox"
                ? "Runtime unknown"
                : "Not implemented"}
            </Badge>
            <p className="body-copy">{p.detail}</p>
          </Panel>
        ))}
      </div>
    </>
  );
}
export function Settings({ onSave }: { onSave: () => void }) {
  const [value, setValue] = useState(() => {
    try {
      return getBase();
    } catch {
      return "";
    }
  });
  const [error, setError] = useState("");
  const [token, setToken] = useState("");
  const [authenticated, setAuthenticated] = useState(hasOperatorToken);
  return (
    <>
      <Panel
        title="Console connection"
        detail="Choose the backend for this browser tab."
      >
        <form
          className="settings-form"
          onSubmit={(e) => {
            e.preventDefault();
            try {
              saveBase(value);
              if (token.trim()) setOperatorToken(token);
              setToken("");
              setAuthenticated(hasOperatorToken());
              setError("");
              onSave();
            } catch (e) {
              setError(e instanceof Error ? e.message : "Invalid address");
            }
          }}
        >
          <label>
            Backend base URL
            <input
              aria-label="Backend base URL"
              value={value}
              onChange={(e) => setValue(e.target.value)}
              placeholder="http://localhost:8000"
            />
          </label>
          <p className="body-copy">
            Leave blank to use the same-origin frontend proxy. A static-hosted
            frontend needs the HTTPS address of your separately hosted Python
            API.
          </p>
          <Notice>
            The selected backend receives console requests. The address is
            stored for this browser tab only.
          </Notice>
          <label>
            Console access token
            <input
              type="password"
              autoComplete="off"
              spellCheck={false}
              aria-label="Console access token"
              value={token}
              onChange={(event) => setToken(event.target.value)}
              placeholder="Server-issued operator or administrator token"
            />
          </label>
          <p className="body-copy">
            Use your console access token, never an AI provider API key. Access
            stays in memory for up to 30 minutes and is cleared on page reload
            or a backend address change. The server decides which operations
            your role permits.
          </p>
          <Badge tone={authenticated ? "info" : "neutral"}>
            {authenticated
              ? "Access token held in memory"
              : "No access token in memory"}
          </Badge>
          {authenticated && (
            <Button
              type="button"
              variant="outline"
              onClick={() => {
                clearOperatorToken();
                setToken("");
                setAuthenticated(false);
                onSave();
              }}
            >
              Clear console access
            </Button>
          )}
          {error && <Notice danger>{error}</Notice>}
          <Button type="submit">Save connection and reconnect</Button>
        </form>
      </Panel>
      <AiStatus />
    </>
  );
}
