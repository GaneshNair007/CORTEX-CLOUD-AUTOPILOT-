import {
  Component,
  Suspense,
  lazy,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import {
  Layers,
  Menu,
  Search,
  Settings as SettingsIcon,
  ChevronRight,
  ArrowUpRight,
  ShieldCheck,
  WifiOff,
} from "lucide-react";
import { client } from "./client";
import { useResource } from "./hooks";
import { destinations, navigation, readRoute } from "./navigation";
import { Button, Empty, Modal, Notice } from "./ui";
const Landing = lazy(() => import("./Landing"));
const Overview = lazy(() => import("./Overview"));
const Topology = lazy(() => import("./Topology"));
const Incidents = lazy(() =>
  import("./Records").then((m) => ({ default: m.Incidents })),
);
const Operations = lazy(() =>
  import("./Records").then((m) => ({ default: m.Operations })),
);
const Events = lazy(() =>
  import("./Records").then((m) => ({ default: m.Events })),
);
const Predictions = lazy(() =>
  import("./Intelligence").then((m) => ({ default: m.Predictions })),
);
const Optimizer = lazy(() =>
  import("./Intelligence").then((m) => ({ default: m.Optimizer })),
);
const Memory = lazy(() =>
  import("./Intelligence").then((m) => ({ default: m.Memory })),
);
const Evaluation = lazy(() =>
  import("./Intelligence").then((m) => ({ default: m.Evaluation })),
);
const Guard = lazy(() =>
  import("./Governance").then((m) => ({ default: m.Guard })),
);
const Policies = lazy(() =>
  import("./Governance").then((m) => ({ default: m.Policies })),
);
const Approvals = lazy(() =>
  import("./Governance").then((m) => ({ default: m.Approvals })),
);
const Audit = lazy(() =>
  import("./Governance").then((m) => ({ default: m.Audit })),
);
const Twin = lazy(() => import("./Actions").then((m) => ({ default: m.Twin })));
const Pipeline = lazy(() =>
  import("./Actions").then((m) => ({ default: m.PipelinePage })),
);
const Chaos = lazy(() =>
  import("./Actions").then((m) => ({ default: m.Chaos })),
);
const Reliability = lazy(() =>
  import("./Support").then((m) => ({ default: m.Reliability })),
);
const Providers = lazy(() =>
  import("./Support").then((m) => ({ default: m.Providers })),
);
const Settings = lazy(() =>
  import("./Support").then((m) => ({ default: m.Settings })),
);
class ErrorBoundary extends Component<
  { children: ReactNode },
  { error: boolean }
> {
  state = { error: false };
  static getDerivedStateFromError() {
    return { error: true };
  }
  render() {
    return this.state.error ? (
      <div className="error-boundary">
        <Notice danger>
          This view could not render. The backend may have returned an
          unsupported response.
        </Notice>
        <Button onClick={() => location.reload()}>Reload console</Button>
      </div>
    ) : (
      this.props.children
    );
  }
}
function ConsoleApp({ reconnect }: { reconnect: () => void }) {
  const [route, setRoute] = useState(readRoute);
  const [palette, setPalette] = useState(false);
  const [query, setQuery] = useState("");
  const [mobile, setMobile] = useState(false);
  const health = useResource(client.health, 10000);
  const available =
    !!health.data &&
    health.data.status === "ok" &&
    !health.error &&
    !health.stale;
  const frozen = health.data?.kill_switch_engaged ?? true;
  useEffect(() => {
    const change = () => {
      setRoute(readRoute());
      setMobile(false);
      setPalette(false);
      document.querySelector(".workspace-scroll")?.scrollTo(0, 0);
    };
    addEventListener("hashchange", change);
    return () => removeEventListener("hashchange", change);
  }, []);
  useEffect(() => {
    const keys = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setPalette((v) => !v);
      }
    };
    addEventListener("keydown", keys);
    return () => removeEventListener("keydown", keys);
  }, []);
  useEffect(() => {
    const media = matchMedia("(min-width: 1024px)");
    const close = () => {
      if (media.matches) setMobile(false);
    };
    media.addEventListener("change", close);
    return () => media.removeEventListener("change", close);
  }, []);
  const destination = destinations.find((d) => d.id === route);
  useEffect(() => {
    document.title = `${destination?.label || "Cloud Autopilot"} · CORTEX`;
  }, [destination]);
  function nav() {
    return (
      <>
        <a className="brand" href="#/">
          <span className="brand-mark">
            <Layers size={22} />
          </span>
          <span>
            CORTEX<small>CLOUD AUTOPILOT</small>
          </span>
        </a>
        <div className="workspace-chip">
          <span className="workspace-avatar">C</span>
          <div>
            CORTEX workspace<small>Control plane</small>
          </div>
          <ChevronRight size={14} />
        </div>
        <nav aria-label="Console navigation">
          {navigation.map((g) => (
            <div className="nav-group" key={g.group}>
              <span>{g.group}</span>
              {g.items.map((item) => (
                <a
                  href={`#/${item.id}`}
                  aria-current={route === item.id ? "page" : undefined}
                  key={item.id}
                >
                  <item.icon size={17} />
                  {item.label}
                  {route === item.id && <span className="nav-active-dot" />}
                </a>
              ))}
            </div>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <a href="#/settings">
            <SettingsIcon size={17} />
            Connection settings
          </a>
          <a href="#/">
            <ArrowUpRight size={17} />
            Product overview
          </a>
          <div>
            <span
              className={`status-dot ${available ? "success" : "warning"}`}
            />
            <span>
              {available
                ? "API reachable"
                : health.loading && !health.data
                  ? "Connecting…"
                  : "API unavailable"}
            </span>
            <small>v2.0</small>
          </div>
        </div>
      </>
    );
  }
  let content: ReactNode;
  const props = { available, frozen };
  switch (route) {
    case "landing":
      return (
        <Suspense fallback={<div className="cp-loading">Loading CORTEX…</div>}>
          <Landing />
        </Suspense>
      );
    case "console":
      content = <Overview health={available ? health.data : undefined} />;
      break;
    case "incidents":
      content = <Incidents />;
      break;
    case "operations":
      content = <Operations />;
      break;
    case "events":
      content = <Events />;
      break;
    case "topology":
      content = <Topology />;
      break;
    case "predictions":
      content = <Predictions />;
      break;
    case "optimizer":
      content = <Optimizer />;
      break;
    case "cost":
      content = <Optimizer mode="COST" />;
      break;
    case "sustainability":
      content = <Optimizer mode="GREEN" />;
      break;
    case "memory":
      content = <Memory />;
      break;
    case "evaluation":
      content = <Evaluation />;
      break;
    case "cortex":
      content = (
        <Guard
          health={health.data}
          available={available}
          refresh={health.refresh}
        />
      );
      break;
    case "policies":
      content = <Policies />;
      break;
    case "approvals":
      content = <Approvals {...props} />;
      break;
    case "audit":
      content = <Audit />;
      break;
    case "simulator":
      content = <Twin {...props} />;
      break;
    case "demo":
      content = <Pipeline {...props} />;
      break;
    case "chaos":
      content = <Chaos {...props} />;
      break;
    case "reliability":
      content = <Reliability />;
      break;
    case "providers":
      content = <Providers />;
      break;
    case "settings":
      content = <Settings onSave={reconnect} />;
      break;
    default:
      content = (
        <>
          <Empty
            title="Page not found"
            detail="Choose a workspace from the sidebar."
          />
          <Button href="#/console">Open command center</Button>
        </>
      );
  }
  return (
    <div className="console-shell">
      <a
        className="skip-link"
        href="#main-content"
        onClick={(e) => {
          e.preventDefault();
          document.getElementById("main-content")?.focus();
        }}
      >
        Skip to content
      </a>
      <aside className="desktop-sidebar">{nav()}</aside>
      <div className="workspace">
        <header className="console-header">
          <Button
            variant="ghost"
            size="sm"
            className="mobile-menu"
            aria-label="Open navigation"
            onClick={() => setMobile(true)}
          >
            <Menu size={20} />
          </Button>
          <div className="breadcrumb">
            <span>Workspace</span>
            <ChevronRight size={13} />
            <strong>{destination?.label || "Not found"}</strong>
          </div>
          <button className="search-trigger" onClick={() => setPalette(true)}>
            <Search size={14} />
            <span>Find a workspace…</span>
            <kbd>⌘ K</kbd>
          </button>
          <div className="header-status">
            <ShieldCheck size={15} />
            <span>
              {available
                ? `L${health.data?.autonomy_level} · ${frozen ? "Frozen" : "Guard enabled"}`
                : "State unknown"}
            </span>
          </div>
          <a
            className="operator-avatar"
            href="#/settings"
            aria-label="Connection settings"
          >
            CX
          </a>
        </header>
        <div className="workspace-scroll">
          <main id="main-content" tabIndex={-1} className="workspace-content">
            {!available && (
              <div className="connection-banner" role="status">
                <WifiOff size={16} />
                <span>
                  {health.loading && !health.data
                    ? "Connecting to the control plane…"
                    : "Backend unavailable. Live actions are disabled; existing snapshots may be stale."}
                </span>
                <a href="#/settings">Connection settings</a>
                <button onClick={health.refresh}>Retry</button>
              </div>
            )}
            {available && frozen && (
              <Notice>
                Mutations are frozen by the backend. Review CORTEX Guard before
                resuming.
              </Notice>
            )}
            {route !== "console" && (
              <div className="page-heading">
                <span className="eyebrow">
                  CORTEX /{" "}
                  {navigation.find((g) => g.items.some((i) => i.id === route))
                    ?.group || "WORKSPACE"}
                </span>
                <h1>{destination?.label || "Page not found"}</h1>
              </div>
            )}
            <ErrorBoundary key={route}>
              <Suspense
                fallback={
                  <div className="cp-loading" role="status">
                    Loading workspace…
                  </div>
                }
              >
                {content}
              </Suspense>
            </ErrorBoundary>
            <footer className="console-footer">
              <span>CORTEX Cloud Autopilot</span>
              <span>Observe. Reason. Govern. Verify.</span>
            </footer>
          </main>
        </div>
      </div>
      <Modal
        open={mobile}
        onClose={() => setMobile(false)}
        title="CORTEX navigation"
        description="Choose a workspace."
      >
        <div className="mobile-navigation">{nav()}</div>
      </Modal>
      <Modal
        open={palette}
        onClose={() => setPalette(false)}
        title="Go to workspace"
        description="Search console pages. Use Tab and Enter to select a result."
      >
        <input
          autoFocus
          aria-label="Search workspaces"
          placeholder="Search workspaces…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <div className="palette-results">
          {destinations
            .filter((d) => d.label.toLowerCase().includes(query.toLowerCase()))
            .map((d) => (
              <a
                href={`#/${d.id}`}
                key={d.id}
                onClick={() => setPalette(false)}
              >
                <d.icon size={17} />
                {d.label}
                <ArrowUpRight size={14} />
              </a>
            ))}
          {!destinations.some((d) =>
            d.label.toLowerCase().includes(query.toLowerCase()),
          ) && <Empty title="No matching workspace" />}
        </div>
      </Modal>
    </div>
  );
}
export function App() {
  const [connection, setConnection] = useState(0);
  return (
    <ErrorBoundary>
      <ConsoleApp
        key={connection}
        reconnect={() => setConnection((v) => v + 1)}
      />
    </ErrorBoundary>
  );
}
export default App;
