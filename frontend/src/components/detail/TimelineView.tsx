import { format } from "date-fns";
import type { IncidentTimeline } from "@/lib/types";

const EVENT_TYPE_LABEL: Record<string, string> = {
  incident_created: "Incident Created",
  report_correlated: "Report Correlated",
  state_change: "State Changed",
  severity_escalated: "Severity Escalated",
  report_added: "Report Added",
};

export function TimelineView({ timeline }: { timeline: IncidentTimeline[] }) {
  const sorted = [...timeline].sort(
    (a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
  );

  if (sorted.length === 0) {
    return (
      <p className="detail-empty-sub">No timeline events recorded yet.</p>
    );
  }

  return (
    <ol className="timeline">
      {sorted.map((entry, i) => {
        const label =
          EVENT_TYPE_LABEL[entry.event_type] ??
          entry.event_type.replace(/_/g, " ");
        const isFirst = i === 0;

        return (
          <li key={i} className={`timeline-item ${isFirst ? "timeline-item--latest" : ""}`}>
            <div className="timeline-dot" />
            <div className="timeline-content">
              <div className="timeline-header">
                <span className="timeline-event">{label}</span>
                <time className="timeline-time">
                  {format(new Date(entry.timestamp), "dd MMM, HH:mm")}
                </time>
              </div>
              <p className="timeline-desc">{entry.description}</p>
              {entry.new_state && (
                <span className="timeline-tag">→ {entry.new_state}</span>
              )}
              {entry.new_severity && (
                <span className="timeline-tag timeline-tag--sev">
                  SEVERITY: {entry.new_severity}
                </span>
              )}
            </div>
          </li>
        );
      })}
    </ol>
  );
}
