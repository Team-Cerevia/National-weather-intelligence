import { format } from "date-fns";
import type { IncidentTimeline } from "@/lib/types";

const EVENT_CONFIG: Record<string, { label: string; badgeClass: string }> = {
  incident_created: { label: "Incident Initialized", badgeClass: "timeline-badge--created" },
  report_correlated: { label: "Multi-Source Correlated", badgeClass: "timeline-badge--correlated" },
  state_change: { label: "State Transition", badgeClass: "timeline-badge--state" },
  severity_escalated: { label: "Severity Escalation", badgeClass: "timeline-badge--severity" },
  report_added: { label: "Evidence Report Ingested", badgeClass: "timeline-badge--report" },
};

export function TimelineView({ timeline }: { timeline: IncidentTimeline[] }) {
  const sorted = [...timeline].sort(
    (a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
  );

  if (sorted.length === 0) {
    return (
      <div className="timeline-empty">
        <p className="detail-empty-sub">No timeline progression events recorded yet.</p>
      </div>
    );
  }

  return (
    <div className="timeline-container">
      <div className="timeline-header-summary">
        <span className="timeline-count-badge">{timeline.length} Progression Events</span>
        <span className="timeline-status-text">Chronological Audit Trail</span>
      </div>

      <ol className="timeline">
        {sorted.map((entry, i) => {
          const cfg = EVENT_CONFIG[entry.event_type] ?? {
            label: entry.event_type.replace(/_/g, " ").toUpperCase(),
            badgeClass: "timeline-badge--default",
          };
          const isLatest = i === 0;

          return (
            <li key={i} className={`timeline-item ${isLatest ? "timeline-item--latest" : ""}`}>
              <div className="timeline-marker-wrapper">
                <div className={`timeline-dot ${isLatest ? "timeline-dot--active" : ""}`} />
                {i < sorted.length - 1 && <div className="timeline-connector" />}
              </div>

              <div className="timeline-content-card">
                <div className="timeline-card-header">
                  <span className={`timeline-event-type ${cfg.badgeClass}`}>
                    {cfg.label}
                  </span>
                  <time className="timeline-time">
                    {format(new Date(entry.timestamp), "dd MMM yyyy, HH:mm:ss")}
                  </time>
                </div>

                <p className="timeline-desc">{entry.description}</p>

                <div className="timeline-meta-row">
                  {entry.previous_state && entry.new_state && (
                    <div className="timeline-state-change">
                      <span className="state-pill state-pill--old">{entry.previous_state}</span>
                      <span className="state-arrow">→</span>
                      <span className="state-pill state-pill--new">{entry.new_state}</span>
                    </div>
                  )}

                  {!entry.previous_state && entry.new_state && (
                    <span className="state-pill state-pill--new">STATE: {entry.new_state}</span>
                  )}

                  {entry.new_severity && (
                    <span className={`severity-tag severity-tag--${entry.new_severity.toLowerCase()}`}>
                      {entry.previous_severity ? `${entry.previous_severity} → ` : ""}
                      {entry.new_severity}
                    </span>
                  )}

                  {entry.report_id && (
                    <code className="timeline-report-id">
                      REF: {entry.report_id}
                    </code>
                  )}
                </div>
              </div>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
