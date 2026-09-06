import type { IncidentSeverity } from "@/lib/types";

const config: Record<
  IncidentSeverity,
  { label: string; className: string }
> = {
  LOW: {
    label: "Low",
    className: "badge-severity-low",
  },
  MODERATE: {
    label: "Moderate",
    className: "badge-severity-moderate",
  },
  HIGH: {
    label: "High",
    className: "badge-severity-high",
  },
  CRITICAL: {
    label: "Critical",
    className: "badge-severity-critical",
  },
};

export function SeverityBadge({ severity }: { severity: IncidentSeverity }) {
  const { label, className } = config[severity] ?? config.MODERATE;
  return <span className={`badge ${className}`}>{label}</span>;
}
