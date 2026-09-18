import { useEffect, useRef, useState, type CSSProperties } from "react";
import {
  ArrowDown,
  ArrowRight,
  ArrowUpRight,
  Menu,
  X,
  Pause,
  Play,
} from "lucide-react";
import { destinations } from "./navigation";
import { useLandingMotion } from "./useLandingMotion";
import { MetalStar } from "./MetalStar";

const descriptions: Record<string, string> = {
  console:
    "Bring incidents, service dependencies, and recent decisions into one view.",
  incidents:
    "Find recorded incidents and inspect the evidence behind each one.",
  topology:
    "Explore the modeled service graph and calculate a change’s blast radius.",
  events: "Follow operational events and add context with operator notes.",
  predictions:
    "Inspect generated demand forecasts, uncertainty bounds, and model evidence.",
  simulator:
    "Test a proposed change in the digital twin before reviewing execution.",
  optimizer: "Compare modeled capacity, cost, and carbon tradeoffs.",
  memory:
    "Retrieve relevant incident history and runbooks with their source evidence.",
  cortex: "Review autonomy settings and the backend’s reported freeze state.",
  approvals: "Inspect pending requests and record an operator’s decision.",
  policies: "Read the policy rules returned by the connected control plane.",
  audit:
    "Inspect the evidence ledger, verify its hash chain, and export records.",
  demo: "Review an incident, run the control loop, and inspect each returned stage.",
  operations:
    "Trace execution attempts and the verification evidence they produced.",
  chaos:
    "Review a fault experiment, inspect its status, and clear injected faults.",
  reliability:
    "Compare modeled service latency against its configured objective.",
  cost: "Explore the cost implications of candidate capacity configurations.",
  sustainability:
    "Compare estimated energy and carbon across planning options.",
  evaluation:
    "Inspect retrieval measurements and the benchmark’s stated limits.",
  providers:
    "Check provider capabilities and distinguish placeholders from available adapters.",
  settings: "Choose the backend connection used by this browser session.",
};

const phases = [
  {
    title: "Observe & predict",
    headline: "Start with a clearer picture.",
    text: "Follow the incident record, explore service dependencies, and inspect workload forecasts. The console keeps modeled inputs and backend evidence visible, so you can understand what informs a decision.",
    route: "topology",
    link: "Explore infrastructure",
    steps: ["Observe", "Understand", "Predict"],
  },
  {
    title: "Simulate & optimize",
    headline: "Explore the consequences first.",
    text: "Compare a proposed change in the digital twin, then examine capacity, cost, and carbon estimates. Planning stays separate from execution, with a review step before a change is submitted.",
    route: "simulator",
    link: "Open the digital twin",
    steps: ["Simulate", "Optimize"],
  },
  {
    title: "Authorize & act",
    headline: "Make authority explicit.",
    text: "Read policies, inspect the reported autonomy level, and review pending approvals. Action controls surface the response returned by CORTEX, including blocked and failed outcomes.",
    route: "cortex",
    link: "Review CORTEX Guard",
    steps: ["Authorize", "Act"],
  },
  {
    title: "Verify & learn",
    headline: "Keep the evidence close.",
    text: "Inspect execution history and verification results, check the evidence ledger, and retrieve relevant operational memory. A completed request is only the beginning of understanding its outcome.",
    route: "audit",
    link: "Inspect the evidence ledger",
    steps: ["Verify", "Learn"],
  },
];

const workflows = [
  {
    number: "01",
    category: "Infrastructure",
    title: "See how everything connects.",
    text: "Service dependencies, incident context, and modeled blast radius — in one place.",
    route: "topology",
    visual: "map",
    labels: ["Services", "Dependencies", "Impact"],
  },
  {
    number: "02",
    category: "Intelligence",
    title: "Give the next move some thought.",
    text: "Forecast demand, compare candidates, and simulate a proposed change before acting.",
    route: "simulator",
    visual: "twin",
    labels: ["Propose", "Simulate", "Review"],
  },
  {
    number: "03",
    category: "Governance",
    title: "Keep control in the loop.",
    text: "Inspect policies, review approvals, and follow the evidence behind an execution.",
    route: "cortex",
    visual: "guard",
    labels: ["Policy", "Approval", "Evidence"],
  },
];

function Arrow({ diagonal = false }: { diagonal?: boolean }) {
  const Icon = diagonal ? ArrowUpRight : ArrowRight;
  return (
    <span className="br-round-arrow" aria-hidden="true">
      <Icon size={21} />
    </span>
  );
}

const services = [
  {
    title: "Infrastructure & incidents",
    text: "Explore dependencies, inspect incident evidence, and trace the impact of a proposed change.",
    route: "topology",
  },
  {
    title: "Prediction & intelligence",
    text: "Inspect workload forecasts and retrieve relevant history with source evidence.",
    route: "predictions",
  },
  {
    title: "Simulation & optimization",
    text: "Compare capacity, cost, and carbon before submitting an action for review.",
    route: "simulator",
  },
  {
    title: "Policy & governance",
    text: "Keep autonomy, approvals, and the reported freeze state visible at every decision.",
    route: "cortex",
  },
  {
    title: "Execution & evidence",
    text: "Follow the control loop, inspect execution results, and verify the evidence ledger.",
    route: "demo",
  },
  {
    title: "One connected workspace",
    text: "Twenty-one views. One considered path from signal to action.",
    route: "console",
  },
];
const story =
  "We bring your infrastructure, intelligence, and decisions together — so you can understand what is happening, explore what comes next, and keep control of every action.";

export default function Landing({
  motion,
}: {
  motion: { enabled: boolean; reduced: boolean; toggle: () => void };
}) {
  const root = useRef<HTMLDivElement>(null);
  const manualPhase = useRef(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const [phase, setPhase] = useState(0);
  const current = phases[phase];
  useLandingMotion(root, motion.enabled, setPhase, manualPhase);
  useEffect(() => {
    const close = (event: KeyboardEvent) => {
      if (event.key === "Escape") setMenuOpen(false);
    };
    window.addEventListener("keydown", close);
    return () => window.removeEventListener("keydown", close);
  }, []);
  useEffect(() => {
    const process = root.current?.querySelector<HTMLElement>(".br-process");
    const tabs = process?.querySelector<HTMLElement>(".br-process-tabs");
    const label = process?.querySelector<HTMLElement>(".br-process-label");
    const active = process?.querySelector<HTMLElement>(
      ".br-process-tab.is-active",
    );
    if (!process || !tabs || !label || !active) return;
    const alignTimeline = () => {
      const dot = active.querySelector<HTMLElement>(".br-process-dot")!;
      const center = dot.getBoundingClientRect().top + dot.offsetHeight / 2;
      process.style.setProperty(
        "--phase-offset",
        `${center - label.getBoundingClientRect().top - 40}px`,
      );
      process.style.setProperty(
        "--phase-fill",
        `${center - tabs.getBoundingClientRect().top}px`,
      );
    };
    alignTimeline();
    const observer = new ResizeObserver(alignTimeline);
    observer.observe(tabs);
    return () => observer.disconnect();
  }, [phase]);
  function choosePhase(index: number) {
    manualPhase.current = true;
    setPhase(index);
  }
  return (
    <div className="br-page" ref={root} data-motion-enabled={motion.enabled}>
      <a
        className="skip-link"
        href="#br-main"
        onClick={(event) => {
          event.preventDefault();
          document.getElementById("br-main")?.focus();
        }}
      >
        Skip to content
      </a>
      <header className="br-nav" data-condensed="false">
        <a className="br-logo" href="#/" aria-label="CORTEX home">
          Cortex
          <span className="br-logo-star" aria-hidden="true">
            ✦
          </span>
        </a>
        <button
          className="br-menu-toggle"
          aria-label={
            menuOpen ? "Close product navigation" : "Open product navigation"
          }
          aria-expanded={menuOpen}
          aria-controls="br-product-navigation"
          onClick={() => setMenuOpen(!menuOpen)}
        >
          {menuOpen ? <X size={22} /> : <Menu size={22} />}
        </button>
        <nav
          id="br-product-navigation"
          className={`br-nav-links ${menuOpen ? "is-open" : ""}`}
          aria-label="Product"
        >
          <a className="br-nav-emblem" href="#/" aria-label="CORTEX home">
            ✦
          </a>
          <a href="#/topology">Infrastructure</a>
          <a href="#/memory">Intelligence</a>
          <a href="#/cortex">Governance</a>
        </nav>
        <a className="br-nav-cta" href="#/console">
          Open console <Arrow diagonal />
        </a>
      </header>

      <main id="br-main" tabIndex={-1}>
        <section className="br-hero" aria-labelledby="br-hero-title">
          <h1 id="br-hero-title" className="br-hero-heading">
            <span className="br-hero-line">
              <span>Your cloud,</span>
            </span>
            <span className="br-hero-line">
              <span>under control.</span>
            </span>
          </h1>
          <div className="br-hero-bottom">
            <a className="br-cta" href="#/console">
              Launch command center <Arrow />
            </a>
            <p className="br-hero-copy">
              A clearer view of your infrastructure.
              <br />A considered path from signal to action.
              <br />
              This is CORTEX Cloud Autopilot.
            </p>
          </div>
        </section>

        <section
          className="br-stage"
          aria-label="CORTEX control plane illustration"
          data-motion-progress="0"
        >
          <div className="br-stage-background" />
          <div className="br-stage-sticky">
            <div className="br-stage-top">
              <span>CORTEX / CLOUD AUTOPILOT</span>
              <span>From signal to evidence</span>
            </div>
            <div className="br-stage-art">
              <MetalStar className="br-metal-left" />
              <MetalStar className="br-metal-right" />
              <div className="br-stage-wordmark" aria-hidden="true">
                Cortex
              </div>
              <h2 className="br-story" aria-label={story}>
                {story.split(" ").map((word, index) => (
                  <span
                    className="br-story-word"
                    aria-hidden="true"
                    key={index}
                  >
                    {word}{" "}
                  </span>
                ))}
              </h2>
            </div>
            <div className="br-stage-bottom">
              <span>Clarity in complexity.</span>
              <span>
                Scroll to explore <ArrowDown size={18} aria-hidden="true" />
              </span>
            </div>
          </div>
        </section>

        <section className="br-about" aria-labelledby="br-about-title">
          <span className="br-pill" data-reveal>
            Meet your control plane
          </span>
          <div>
            <h2 id="br-about-title" data-reveal>
              Complex infrastructure.
              <br />
              <span>A clearer perspective.</span>
            </h2>
            <div className="br-about-copy" data-reveal>
              <p>
                CORTEX brings the signals, models, and evidence behind your
                cloud operations into one connected workspace.
              </p>
              <p>
                Explore a change before acting. Review the authority behind a
                decision. Keep the outcome and its evidence in view.
              </p>
            </div>
            <a className="br-cta" href="#/console" data-reveal>
              Meet the workspace <Arrow />
            </a>
          </div>
        </section>

        <section className="br-services" aria-labelledby="br-services-title">
          <div className="br-services-label" data-reveal>
            <span className="br-pill">What you can do</span>
            <h2 id="br-services-title">
              Every signal.
              <br />
              <span>A next step.</span>
            </h2>
          </div>
          <div className="br-services-stack">
            {services.map((service, index) => (
              <a
                className="br-service-card"
                href={`#/${service.route}`}
                style={{ "--stack-index": index } as CSSProperties}
                key={service.route}
              >
                <span className="br-service-index">0{index + 1}</span>
                <div>
                  <h3>{service.title}</h3>
                  <p>{service.text}</p>
                </div>
                <Arrow diagonal />
              </a>
            ))}
            <p className="br-services-note" data-reveal>
              From the first signal to the final evidence.
              <br />
              <span>Connected by design.</span>
            </p>
          </div>
        </section>

        <section className="br-process" aria-labelledby="br-process-title">
          <div className="br-process-sticky">
            <div className="br-process-label">
              <span className="br-pill">How it works</span>
              <h2 id="br-process-title" className="sr-only">
                The control loop
              </h2>
              <div className="br-process-track" aria-hidden="true">
                <span>✦</span>
              </div>
            </div>
            <div className="br-process-grid">
              <div
                className="br-process-tabs"
                aria-label="Explore control-loop phases"
              >
                {phases.map((item, index) => (
                  <div
                    className={`br-process-step ${phase === index ? "is-active" : ""}`}
                    key={item.title}
                  >
                    <button
                      className={`br-process-tab ${phase === index ? "is-active" : ""}`}
                      aria-label={item.title}
                      aria-pressed={phase === index}
                      aria-controls="br-process-detail"
                      onClick={() => choosePhase(index)}
                    >
                      <span className="br-process-number">0{index + 1}</span>
                      <span className="br-process-dot" aria-hidden="true" />
                      <span>{item.title.split(" & ")[0]}</span>
                    </button>
                    {phase === index && (
                      <div
                        className="br-process-detail"
                        id="br-process-detail"
                        aria-live="polite"
                        aria-atomic="true"
                      >
                        <h3>{current.headline}</h3>
                        <p>{current.text}</p>
                        <div
                          className={`br-process-illustration br-phase-${phase}`}
                          aria-hidden="true"
                        >
                          <span />
                          <i />
                          <span />
                        </div>
                        <a className="br-cta" href={`#/${current.route}`}>
                          {current.link}
                          <Arrow />
                        </a>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        <section className="br-intro" aria-labelledby="br-workflows-title">
          <div className="br-section-heading" data-reveal>
            <span className="br-pill">What you can do</span>
            <h2 id="br-workflows-title">
              One connected view.
              <br />
              <span>Every next step.</span>
            </h2>
            <p>
              Move between the workflows that turn infrastructure questions into
              inspectable decisions.
            </p>
          </div>
          <div className="br-workflows">
            {workflows.map((workflow) => (
              <a
                className="br-workflow"
                data-reveal
                href={`#/${workflow.route}`}
                key={workflow.number}
              >
                <div
                  className={`br-workflow-visual br-visual-${workflow.visual}`}
                  aria-hidden="true"
                >
                  <span className="br-workflow-number">{workflow.number}</span>
                  <div className="br-workflow-diagram">
                    {workflow.labels.map((label) => (
                      <span key={label}>{label}</span>
                    ))}
                  </div>
                  <Arrow diagonal />
                </div>
                <div className="br-workflow-copy">
                  <span>{workflow.category}</span>
                  <h3>{workflow.title}</h3>
                  <p>{workflow.text}</p>
                </div>
              </a>
            ))}
          </div>
        </section>

        <section className="br-directory" aria-labelledby="br-directory-title">
          <div className="br-section-heading" data-reveal>
            <span className="br-pill">Inside the workspace</span>
            <h2 id="br-directory-title">
              The whole picture.
              <br />
              <span>Within reach.</span>
            </h2>
            <p>
              Every console workspace connects to a backend capability or its
              configuration. Modeled data, unavailable connections, and provider
              limitations stay visible where they matter.
            </p>
          </div>
          <div className="br-directory-grid">
            {destinations.map((destination, index) => (
              <a
                className="br-directory-link"
                href={`#/${destination.id}`}
                key={destination.id}
              >
                <span className="br-directory-number">
                  {String(index + 1).padStart(2, "0")}
                </span>
                <div>
                  <h3>{destination.label}</h3>
                  <p>{descriptions[destination.id]}</p>
                </div>
                <Arrow diagonal />
              </a>
            ))}
          </div>
        </section>
      </main>

      <footer className="br-footer">
        <div className="br-footer-top" data-reveal>
          <div>
            <span className="br-pill">
              Make the next move a considered one.
            </span>
            <h2>
              Let’s see what’s
              <br />
              happening.
            </h2>
          </div>
          <a className="br-cta" href="#/console">
            Enter the command center
            <Arrow diagonal />
          </a>
        </div>
        <div className="br-footer-wordmark" aria-hidden="true">
          Cortex<span>✳</span>
        </div>
        <div className="br-footer-bottom">
          <span>CORTEX Cloud Autopilot</span>
          <span>Observe. Reason. Govern. Verify.</span>
          <a
            href="https://github.com/GaneshNair007/CORTEX-CLOUD-AUTOPILOT-"
            target="_blank"
            rel="noreferrer"
          >
            View project <ArrowUpRight size={16} aria-hidden="true" />
          </a>
        </div>
      </footer>
      <button
        className="br-motion-toggle"
        onClick={motion.toggle}
        disabled={motion.reduced}
        aria-label={
          motion.reduced
            ? "Motion reduced by system preference"
            : motion.enabled
              ? "Pause motion"
              : "Enable motion"
        }
      >
        {motion.enabled ? <Pause size={13} /> : <Play size={13} />}
        <span>
          {motion.reduced
            ? "Reduced motion"
            : motion.enabled
              ? "Motion on"
              : "Motion off"}
        </span>
      </button>
    </div>
  );
}
