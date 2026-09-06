import { formatDistanceToNow } from "date-fns";
import type { Incident } from "@/lib/types";
import { SeverityBadge } from "@/components/shared/SeverityBadge";
import { VerificationBadge } from "@/components/shared/VerificationBadge";
import { EventIcon } from "@/components/shared/EventIcon";

interface IncidentCardProps {
  incident: Incident;
  selected: boolean;
  isNew: boolean;
  onClick: () => void;
}

export function IncidentCard({
  incident,
  selected,
  isNew,
  onClick,
}: IncidentCardProps) {
  const location =
    [incident.city, incident.state_name].filter(Boolean).join(", ") ||
    incident.country ||
    "Unknown location";

  const ago = formatDistanceToNow(new Date(incident.last_updated_at), {
    addSuffix: true,
  });

  const confidence = incident.verification_summary?.overall_confidence;
  const verStatus =
    incident.verification_summary?.verification_status ?? "UNVERIFIED";

  return (
    <button
      className={`incident-card ${selected ? "incident-card--selected" : ""} ${isNew ? "incident-card--new" : ""}`}
      onClick={onClick}
    >
      <div className="incident-card-header">
        <EventIcon category={incident.event_category} size="md" />
        <div className="incident-card-meta">
          <span className="priority-pill">
            ★ {incident.priority_score.toFixed(1)} Priority
          </span>
          <SeverityBadge severity={incident.severity} />
          <span className="incident-card-ago">{ago}</span>
        </div>
      </div>

      <p className="incident-card-title">{incident.title}</p>
      <p className="incident-card-location">📍 {location}</p>

      <div className="incident-card-footer">
        <VerificationBadge status={verStatus} />
        {confidence !== null && confidence !== undefined && (
          <span className="incident-card-confidence">
            {Math.round(confidence * 100)}% trust
          </span>
        )}
        <span className="incident-card-reports">
          🔗 {incident.report_ids.length} report{incident.report_ids.length !== 1 ? "s" : ""}
        </span>
      </div>
    </button>
  );
}
