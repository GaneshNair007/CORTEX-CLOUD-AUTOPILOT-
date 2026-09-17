import type { ReactNode } from "react";
import { Button } from "@flowstack-ui/brick/button";
import { AlertCircle, ArrowUpRight, Inbox, RefreshCw } from "lucide-react";
import { Card } from "./template/card";
import {
  Dialog,
  DialogContent,
  DialogTitle,
  DialogDescription,
} from "./template/dialog";
export { Button };

export function Panel({
  title,
  detail,
  action,
  children,
  className = "",
}: {
  title: string;
  detail?: string;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <Card className={`cp-panel ${className}`}>
      <div className="panel-heading">
        <div>
          <h2>{title}</h2>
          {detail && <p>{detail}</p>}
        </div>
        {action}
      </div>
      {children}
    </Card>
  );
}
export function Badge({
  children,
  tone = "neutral",
}: {
  children: ReactNode;
  tone?: string;
}) {
  return (
    <span className={`cp-badge ${tone}`}>
      <span className="status-dot" />
      {children}
    </span>
  );
}
export function statusTone(value: string) {
  return /fail|block|critical|outage|error/i.test(value)
    ? "danger"
    : /pend|warn|degrad|risk|open|expired/i.test(value)
      ? "warning"
      : /success|healthy|allow|resolv|pass|verified|approved/i.test(value)
        ? "success"
        : "neutral";
}
export function Notice({
  children,
  danger = false,
}: {
  children: ReactNode;
  danger?: boolean;
}) {
  return (
    <div
      className={`cp-notice ${danger ? "danger" : ""}`}
      role={danger ? "alert" : "note"}
    >
      <AlertCircle size={16} />
      <span>{children}</span>
    </div>
  );
}
export function Empty({
  title = "No records yet",
  detail = "Records will appear here when the backend returns them.",
}: {
  title?: string;
  detail?: string;
}) {
  return (
    <div className="cp-empty">
      <Inbox size={28} />
      <h3>{title}</h3>
      <p>{detail}</p>
    </div>
  );
}
export function ResourceState({
  resource,
}: {
  resource: {
    loading: boolean;
    error: string;
    updatedAt?: number;
    refresh: () => void;
    stale: boolean;
  };
}) {
  if (!resource.error && resource.updatedAt)
    return (
      <div className="data-age">
        {resource.stale ? "Snapshot is stale · " : ""}Fetched{" "}
        {new Date(resource.updatedAt).toLocaleTimeString()}{" "}
        <button onClick={resource.refresh} aria-label="Refresh data">
          <RefreshCw size={13} />
        </button>
      </div>
    );
  if (resource.error)
    return (
      <Notice danger>
        {resource.updatedAt ? "Showing the last snapshot. " : ""}
        {resource.error}{" "}
        <button className="text-link" onClick={resource.refresh}>
          Retry
        </button>
      </Notice>
    );
  return (
    <div className="cp-loading" role="status">
      <RefreshCw size={16} className="spin" /> Loading backend data…
    </div>
  );
}
export function Metric({
  label,
  value,
  detail,
  tone = "",
}: {
  label: string;
  value: ReactNode;
  detail: string;
  tone?: string;
}) {
  return (
    <Card className="cp-metric">
      <span>{label}</span>
      <strong className={tone}>{value}</strong>
      <small>{detail}</small>
    </Card>
  );
}
export function Modal({
  open,
  onClose,
  title,
  description,
  children,
  wide = false,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  description: string;
  children: ReactNode;
  wide?: boolean;
}) {
  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className={`cp-dialog ${wide ? "wide" : ""}`}>
        <DialogTitle>{title}</DialogTitle>
        <DialogDescription>{description}</DialogDescription>
        {children}
      </DialogContent>
    </Dialog>
  );
}
export function JsonDetails({
  data,
  title = "Inspect response",
}: {
  data: unknown;
  title?: string;
}) {
  return (
    <details className="json-details">
      <summary>{title}</summary>
      <pre>{JSON.stringify(data, null, 2)}</pre>
    </details>
  );
}
export function RouteLink({
  route,
  children,
}: {
  route: string;
  children: ReactNode;
}) {
  return (
    <a className="text-link" href={`#/${route}`}>
      {children}
      <ArrowUpRight size={14} />
    </a>
  );
}
export function date(value?: string | null) {
  return value ? new Date(value).toLocaleString() : "Not recorded";
}
export function num(value?: number | null, digits = 0) {
  return typeof value === "number" && Number.isFinite(value)
    ? value.toLocaleString(undefined, { maximumFractionDigits: digits })
    : "—";
}
