# Brilean reference analysis and CORTEX implementation

The user's Brilean reference supersedes the previous dark dashboard and corridor-photo landing. This redesign changes frontend presentation across the product landing and all 21 console routes. Existing backend contracts and operational interactions remain in place; backend source is unchanged by this redesign.

## Reference observations

The analysis covered the public [homepage](https://www.brilean.com/), [Who we are](https://www.brilean.com/who-we-are), and [Digital Products](https://www.brilean.com/digital-products) pages. Measurements below describe the inspected desktop rendering at a 1262px viewport, rather than universal values for every breakpoint.

| Reference element | Observed treatment | CORTEX translation |
| --- | --- | --- |
| Palette | Off-white `#f9f9f9`, charcoal `#1a1918`, bright lime emphasis, quiet gray secondary text | Shared light console; charcoal feature sections; lime navigation and primary accents |
| Typography | Ease Semi Display headings and TT Hoves Pro body; large regular-weight letterforms | Inter Tight with Inter/Arial fallbacks; similar tight spacing and hierarchy |
| Homepage composition | Broad typographic opening, services, process narrative, selected work, expansive footer | Cloud-operation proposition, capabilities, control-loop phases, workflow links, complete workspace directory |
| Who we are | 80px/88px stacked hero words; inactive lines gray; 48px and 64px section headings | Contrasting active/inactive process phases and restrained supporting typography |
| Digital Products | Charcoal hero, 112px heading, muted second line, lime circles, project panels and prominent results | Dark story/control-loop sections; large metric values and featured topology presentation |
| Spacing | 64px desktop side gutters; many editorial sections use 120px vertical padding | Approximately 5% landing gutters and 120px desktop editorial spacing; denser console spacing |
| Controls | Small category labels, circular arrow affordances, modest panel rounding, limited decoration | Numbered labels, round arrow links, 4px console panel corners, capsule controls |
| Navigation | Broad initial header becomes a compact floating menu during scroll | Fixed landing header condenses after 50px; full console navigation remains available |
| Motion | Header colors transition around 0.3s; prominent button transitions around 0.4s; scroll-linked storytelling | Scoped GSAP/ScrollTrigger sequences, CSS transitions, reduced-motion and pause support |

The reference is a public studio site, while CORTEX is an operational interface. Its visual hierarchy is applied to actual tools and evidence. Marketing claims, client statistics, customer imagery, and company copy are not reproduced. CORTEX retains its own identity and content.

## Shared presentation

The active entry, `src/main.tsx`, loads `theme.css`, then `brilean.css`, then `brilean-motion.css`, and selects FLOWSTACK's light appearance. The effective design palette is off-white `#f9f9f9`, charcoal `#1a1918`, and lime `#f1ff66`. White cards, gray dividers, and muted text support the data-heavy views. Red, amber, green, and blue retain operational meaning rather than being replaced with brand lime.

`index.html` loads Inter Tight. The commercial reference fonts are not bundled or claimed. Console headings use a responsive 40–72px scale on larger screens, while the landing heading can grow larger. Shared cards, forms, tables, notices, diagrams, dialogs, navigation, and footer receive the new styling, so route changes do not revert to the previous dark design.

`Application.tsx` retains lazy routes, keyboard command search, mobile navigation, connection warnings, error boundaries, and health-based action gating. It adds the CORTEX wordmark treatment, numbered route headings, product-overview navigation, and the shared footer. Navigation remains a complete sidebar in the console because 21 operational destinations need persistent discoverability.

## Landing composition and motion

`Landing.tsx` presents a large two-line introduction, metallic story stage, product explanation, six capability cards, four control-loop phases, three workflow entries, a directory generated from all 21 destinations, and an expansive lime footer. Links lead to functioning CORTEX routes. Descriptive content calls out modeled information and provider limitations rather than implying a connected production system.

`MetalStar.tsx` supplies original faceted SVG geometry with gradients, a hollow center, and CSS perspective transforms. The stars do not use downloaded reference assets, a branded 3D model, or a continuous WebGL rendering loop. The implementation aims for the reference's visual character; it is not a pixel-identical reproduction of its proprietary artwork or fonts.

Motion is owned by `useLandingMotion.ts` and styled in `brilean-motion.css`:

- **Navigation:** condenses at `window.scrollY > 50`; its contrast adjusts when dark story/process sections pass under the header.
- **Scrolling:** Lenis uses `lerp: 0.1`, smooth wheel input, and native touch behavior. It is initialized only while landing motion is enabled.
- **Hero and reveals:** heading lines enter with a stagger; explanatory elements reveal once as they approach the viewport.
- **Story:** a CSS-sticky stage spans `185svh` (1.85 viewport heights) on desktop. A GSAP timeline with `scrub: 0.8` separates and rotates the metallic stars, transitions the wordmark to the product statement, and progressively reveals the statement's words. The background subtly scales near the section exit.
- **Services:** above 900px width and 680px height, capability cards stack with sticky offsets and scroll-linked scale changes. Smaller screens use ordinary flowing cards.
- **Control loop:** the large-screen process section spans `340svh` (3.4 viewport heights) with a sticky inner composition. Scroll progress advances four phases; the lime marker and timeline fill align with the active phase. Each phase is also a real button; explicit selection remains until new wheel, touch, or scrolling-key input releases that selection.
- **Footer and controls:** the large wordmark enters with scrubbed movement; arrow links and phase illustrations use restrained CSS animation. Console pages share brief heading/panel entrances and hover feedback.

## Accessibility, reduced motion, and cleanup

`motionPreference.ts` honors `prefers-reduced-motion`, watches for preference changes, and persists a manual pause choice under `cortex-motion` in local storage when storage is available. System reduced motion takes precedence. The landing motion button exposes the current setting with an accessible label; paused/reduced mode displays the story as static content and removes the long sticky process treatment.

The preference sets `html[data-motion="off"]`, disabling CSS animation and transitions throughout the active interface. The motion hook removes scroll/input listeners, destroys Lenis, reverts its GSAP media context and scoped animations, and prevents a late font-ready callback from refreshing disposed effects. Landing scroll effects therefore do not remain active after entering the console.

The landing and console have skip links. Decorative stars are hidden from assistive technology. The full story is exposed as one readable heading rather than separate animated words. Phase buttons retain `aria-pressed`, and changed detail is announced politely. Mobile layouts replace dense navigation with an explicit menu. Semantic status colors, visible focus styles, backend-unavailable messages, and action confirmation dialogs remain part of the interface.

## All 21 route mappings

Every route below uses the same light shell, typography, status palette, panel treatment, and footer. The table describes the retained functional presentation inside that design system.

| Route | View | Visual and functional representation |
| --- | --- | --- |
| `#/console` | Command center | Editorial title, large metric strip, featured dark topology panel, decisions and activity |
| `#/incidents` | Incidents | Searchable record table, quiet metadata, semantic statuses, inspectable details |
| `#/topology` | Infrastructure | Wide dependency graph, light service nodes, selected impact styling, blast-radius controls |
| `#/events` | Activity stream | Searchable activity records, operator-note form, confirmed maintenance action |
| `#/predictions` | Predictions | Large forecast stage, uncertainty bounds, model details, accessible values table |
| `#/simulator` | Digital twin | Distinct proposal, simulation evidence, and reviewed execution stages |
| `#/optimizer` | Optimizer | Light input panel, large comparison results, candidate table and modeled estimates |
| `#/memory` | Incident memory | Prominent query control and readable source evidence panels |
| `#/cortex` | CORTEX Guard | Authority and freeze controls with clear labels, confirmed state, semantic warnings |
| `#/approvals` | Approvals | Decision records with expiry, operator attribution, and review dialogs |
| `#/policies` | Policies | Readable policy sections and rule details in the shared editorial treatment |
| `#/audit` | Evidence ledger | Integrity summary, ledger records, original evidence, and export action |
| `#/demo` | Control loop | Reviewed incident inputs and returned stage sequence with actual outcome evidence |
| `#/operations` | Execution history | Execution table emphasizing status, guard decisions, and verification details |
| `#/chaos` | Chaos lab | Experiment setup, explicit confirmation, active records, and cleanup controls |
| `#/reliability` | Reliability | Service comparisons with modeled latency/SLO labels and restrained indicators |
| `#/cost` | Cost planner | Cost-specific optimizer mode with editable planning inputs and comparison results |
| `#/sustainability` | Sustainability | Green optimizer mode with explicitly estimated energy/carbon results |
| `#/evaluation` | Evaluation | Large measured results, explanatory limits, and benchmark comparisons |
| `#/providers` | Cloud providers | Provider capability panels distinguishing placeholders and unknown runtime state |
| `#/settings` | Connection settings | Sparse connection form, validation feedback, and browser-session scope |

The backend endpoint mapping remains in [FRONTEND_IMPLEMENTATION_REPORT.md](FRONTEND_IMPLEMENTATION_REPORT.md). Styling does not add missing backend capabilities or convert modeled results into live measurements.

## Verification status and limits

Final verification: **26 browser tests passed in 1.4 minutes**, including all 21 routes at 390px and 1440px, operational interactions, scroll navigation/story progress, desktop process progression, persistent pause/resume, and system reduced motion. Project TypeScript, strict console TypeScript, the Node production build, and the static production build all passed after the motion changes. The landing motion code is lazy-loaded with the landing route.

An initial full run had one connection-form failure that did not reproduce in five focused repeats or the subsequent clean full run. No test assertion was removed to obtain the final pass. Browser tests exercise explicit fixtures, rather than live cloud mutations.

Manually inspected the desktop hero, metallic story, stacked cards, pinned timeline, and mobile layout in Chromium. Confirmed the preview's effective lime token is `#f1ff66`, motion is enabled, and no Vite error overlay is present. Local screenshots are under ignored `artifacts`; test fixture screenshots are not evidence of live backend data.

Tests use explicit browser fixtures to exercise frontend behavior. They do not establish backend production readiness. The redesign leaves API requests, error handling, stale-data notices, review steps, and backend-source files unchanged. Existing AI configuration, dependency, guard/approval, and outcome-verification concerns are documented in [BACKEND_READINESS_REPORT.md](BACKEND_READINESS_REPORT.md). No external deployment or cloud mutation is part of this visual redesign.
