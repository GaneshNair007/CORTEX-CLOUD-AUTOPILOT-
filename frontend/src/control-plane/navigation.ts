import {
  Activity,
  AlertTriangle,
  Network,
  TrendingUp,
  SlidersHorizontal,
  Database,
  ShieldCheck,
  Layers,
  CheckCheck,
  FileCode,
  FlaskConical,
  Gauge,
  DollarSign,
  Leaf,
  Fingerprint,
  ChartNoAxesCombined,
  Cloud,
  Workflow,
  Settings,
  ScrollText,
  Radio,
} from "lucide-react";
export const navigation = [
  {
    group: "WORKSPACE",
    items: [
      { id: "console", label: "Command center", icon: Activity },
      { id: "incidents", label: "Incidents", icon: AlertTriangle },
      { id: "topology", label: "Infrastructure", icon: Network },
      { id: "events", label: "Activity stream", icon: Radio },
    ],
  },
  {
    group: "INTELLIGENCE",
    items: [
      { id: "predictions", label: "Predictions", icon: TrendingUp },
      { id: "simulator", label: "Digital twin", icon: Layers },
      { id: "optimizer", label: "Optimizer", icon: SlidersHorizontal },
      { id: "memory", label: "Incident memory", icon: Database },
    ],
  },
  {
    group: "GOVERNANCE",
    items: [
      { id: "cortex", label: "CORTEX Guard", icon: ShieldCheck },
      { id: "approvals", label: "Approvals", icon: CheckCheck },
      { id: "policies", label: "Policies", icon: FileCode },
      { id: "audit", label: "Evidence ledger", icon: Fingerprint },
    ],
  },
  {
    group: "OPERATIONS",
    items: [
      { id: "demo", label: "Control loop", icon: Workflow },
      { id: "operations", label: "Execution history", icon: ScrollText },
      { id: "chaos", label: "Chaos lab", icon: FlaskConical },
      { id: "reliability", label: "Reliability", icon: Gauge },
      { id: "cost", label: "Cost planner", icon: DollarSign },
      { id: "sustainability", label: "Sustainability", icon: Leaf },
      { id: "evaluation", label: "Evaluation", icon: ChartNoAxesCombined },
      { id: "providers", label: "Cloud providers", icon: Cloud },
    ],
  },
];
export const destinations = [
  ...navigation.flatMap((g) => g.items),
  { id: "settings", label: "Connection settings", icon: Settings },
];
export function readRoute() {
  return location.hash.replace(/^#\/?/, "").split("?")[0] || "landing";
}
