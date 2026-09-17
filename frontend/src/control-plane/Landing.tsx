import {
  ArrowRight,
  ArrowUpRight,
  Activity,
  Layers,
  ShieldCheck,
  Fingerprint,
  Network,
  BrainCircuit,
} from "lucide-react";
import { Badge, Button } from "./ui";
import corridor from "../assets/images/1_corridor.jpg";
export default function Landing() {
  return (
    <div className="landing-page">
      <header className="landing-nav">
        <a className="brand" href="#/">
          <span className="brand-mark">
            <Layers size={23} />
          </span>
          CORTEX<span className="brand-sub">CLOUD AUTOPILOT</span>
        </a>
        <nav aria-label="Product">
          <a href="#/topology">Infrastructure</a>
          <a href="#/cortex">Governance</a>
          <a href="#/memory">Intelligence</a>
        </nav>
        <Button href="#/console" size="sm" variant="outline">
          Open console <ArrowUpRight size={15} />
        </Button>
      </header>
      <main>
        <section className="landing-hero">
          <div className="hero-copy">
            <Badge tone="info">PREDICTIVE · POLICY-GOVERNED · AUTONOMOUS</Badge>
            <h1>
              Cloud complexity.
              <br />
              <span>Under control.</span>
            </h1>
            <p>
              One control plane to understand incidents, test the consequences,
              and govern every infrastructure change.
            </p>
            <div className="button-row">
              <Button href="#/console" size="lg" tone="accent">
                Launch command center <ArrowRight size={17} />
              </Button>
              <Button href="#/simulator" size="lg" variant="outline">
                Explore digital twin
              </Button>
            </div>
            <div className="hero-caption">
              <span className="status-dot" />
              An inspectable control loop. Evidence at every step.
            </div>
          </div>
          <div className="hero-visual">
            <img src={corridor} alt="Server racks in a data-center corridor" />
            <div className="hero-visual-overlay" />
            <div className="visual-caption">
              <span className="mono">CORTEX / SYSTEM ARCHITECTURE</span>
              <span>01 — 09</span>
            </div>
            <div className="hero-diagram">
              <div>
                <Activity size={20} />
                <span>OBSERVE</span>
              </div>
              <i />
              <div className="hero-core">
                <Layers size={34} />
                <strong>CORTEX</strong>
                <small>Decision & governance</small>
              </div>
              <i />
              <div>
                <ShieldCheck size={20} />
                <span>VERIFY</span>
              </div>
            </div>
            <div className="visual-bottom">
              <Fingerprint size={20} />
              <p>
                Every action accountable.
                <br />
                <span>Every outcome inspectable.</span>
              </p>
            </div>
          </div>
        </section>
        <section className="landing-loop" aria-label="Control loop stages">
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
          ].map((s, i) => (
            <div key={s}>
              <small>{String(i + 1).padStart(2, "0")}</small>
              <span>{s}</span>
            </div>
          ))}
        </section>
        <section className="landing-features">
          <div className="section-intro">
            <span className="eyebrow">INTELLIGENCE WITH BOUNDARIES</span>
            <h2>
              From signal to decision.
              <br />
              From decision to evidence.
            </h2>
            <p>
              Explore the connected workflows behind CORTEX Cloud Autopilot.
            </p>
          </div>
          <div className="feature-grid">
            {[
              {
                icon: Network,
                title: "See the dependencies",
                text: "Inspect service relationships and explore the blast radius of a proposed change.",
                route: "topology",
                link: "Explore infrastructure",
              },
              {
                icon: BrainCircuit,
                title: "Reason before acting",
                text: "Retrieve relevant runbooks, forecast demand, and compare modeled outcomes in the digital twin.",
                route: "simulator",
                link: "Test a proposed change",
              },
              {
                icon: ShieldCheck,
                title: "Keep authority explicit",
                text: "Review policies, resolve approval requests, and inspect execution and verification evidence.",
                route: "cortex",
                link: "Meet CORTEX Guard",
              },
            ].map((f) => (
              <article key={f.title}>
                <f.icon size={26} />
                <h3>{f.title}</h3>
                <p>{f.text}</p>
                <a href={`#/${f.route}`}>
                  {f.link}
                  <ArrowUpRight size={16} />
                </a>
              </article>
            ))}
          </div>
        </section>
        <section className="landing-close">
          <span className="eyebrow">BUILT FOR THE OPERATOR</span>
          <h2>
            Your next decision starts
            <br />
            with a clearer picture.
          </h2>
          <Button href="#/console" tone="accent" size="lg">
            Enter the command center <ArrowRight size={17} />
          </Button>
          <p>
            Modeled data is labeled in the console. Provider support depends on
            the connected backend.
          </p>
        </section>
      </main>
      <footer>
        <a className="brand" href="#/">
          CORTEX
        </a>
        <span>Cloud Autopilot · Predict. Govern. Verify.</span>
        <a
          href="https://github.com/GaneshNair007/CORTEX-CLOUD-AUTOPILOT-"
          target="_blank"
          rel="noreferrer"
        >
          View project <ArrowUpRight size={14} />
        </a>
      </footer>
    </div>
  );
}
