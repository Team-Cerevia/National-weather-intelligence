"use client";
import { useState } from "react";
import { format } from "date-fns";
import type { Incident } from "@/lib/types";
import { useIncidentDetail } from "@/hooks/useIncidentDetail";
import { SeverityBadge } from "@/components/shared/SeverityBadge";
import { VerificationBadge } from "@/components/shared/VerificationBadge";
import { EventIcon } from "@/components/shared/EventIcon";
import { EvidencePanel } from "./EvidencePanel";
import { TimelineView } from "./TimelineView";

type Tab = "overview" | "evidence" | "timeline";

interface IncidentDetailProps {
  incidentId: string | null;
  onClose: () => void;
}

export function IncidentDetail({ incidentId, onClose }: IncidentDetailProps) {
  const { incident, isLoading } = useIncidentDetail(incidentId);
  const [tab, setTab] = useState<Tab>("overview");

  if (!incidentId) return null;

  return (
    <>
      {/* Backdrop */}
      <div className="detail-backdrop" onClick={onClose} />

      {/* Panel */}
      <aside className={`detail-panel ${incidentId ? "detail-panel--open" : ""}`}>
        <div className="detail-panel-inner">
          {/* Header */}
          <div className="detail-header">
            <button className="detail-close" onClick={onClose} aria-label="Close">
              ✕
            </button>
            {isLoading && !incident ? (
              <div className="detail-loading">
                <div className="spinner" />
              </div>
            ) : incident ? (
              <>
                <div className="detail-title-row">
                  <EventIcon category={incident.event_category} size="lg" />
                  <h2 className="detail-title">{incident.title}</h2>
                </div>
                <div className="detail-badges">
                  <SeverityBadge severity={incident.severity} />
                  <VerificationBadge
                    status={
                      incident.verification_summary?.verification_status ??
                      "UNVERIFIED"
                    }
                  />
                  <span className="detail-state-badge">{incident.state.replace("_", " ")}</span>
                </div>

                <div className="detail-meta-grid">
                  <MetaItem label="Location" value={formatLocation(incident)} />
                  <MetaItem
                    label="First Reported"
                    value={format(
                      new Date(incident.first_reported_at),
                      "dd MMM yyyy, HH:mm"
                    )}
                  />
                  <MetaItem
                    label="Last Updated"
                    value={format(
                      new Date(incident.last_updated_at),
                      "dd MMM yyyy, HH:mm"
                    )}
                  />
                  <MetaItem
                    label="Reports"
                    value={String(incident.report_ids.length)}
                  />
                  {incident.priority_score !== null &&
                    incident.priority_score !== undefined && (
                      <MetaItem
                        label="Priority Score"
                        value={`${incident.priority_score.toFixed(1)} / 100`}
                      />
                    )}
                  {incident.verification_summary?.overall_confidence !==
                    null &&
                    incident.verification_summary?.overall_confidence !==
                      undefined && (
                      <MetaItem
                        label="Confidence"
                        value={`${Math.round(
                          incident.verification_summary.overall_confidence * 100
                        )}%`}
                      />
                    )}
                </div>
              </>
            ) : null}
          </div>

          {/* Tabs */}
          {incident && (
            <>
              <div className="detail-tabs">
                {(["overview", "evidence", "timeline"] as Tab[]).map((t) => (
                  <button
                    key={t}
                    className={`detail-tab ${tab === t ? "detail-tab--active" : ""}`}
                    onClick={() => setTab(t)}
                  >
                    {t === "overview"
                      ? "Overview"
                      : t === "evidence"
                      ? `Evidence (${incident.verification_summary?.evidence_items.length ?? 0})`
                      : `Timeline (${incident.timeline.length})`}
                  </button>
                ))}
              </div>

              <div className="detail-body">
                {tab === "overview" && (
                  <OverviewTab incident={incident} />
                )}
                {tab === "evidence" && (
                  <>
                    {incident.verification_summary ? (
                      <EvidencePanel summary={incident.verification_summary} />
                    ) : (
                      <p className="detail-empty-sub">
                        No evidence evaluated yet.
                      </p>
                    )}
                  </>
                )}
                {tab === "timeline" && (
                  <TimelineView timeline={incident.timeline} />
                )}
              </div>
            </>
          )}
        </div>
      </aside>
    </>
  );
}

function OverviewTab({ incident }: { incident: Incident }) {
  const vs = incident.verification_summary;
  return (
    <div className="overview-tab">
      {vs && (
        <div className="overview-explanation-box">
          <p className="overview-explanation-label">Evidence Summary</p>
          <p className="overview-explanation">{vs.explanation}</p>
        </div>
      )}
      {incident.latitude && incident.longitude && (
        <div className="overview-coord-box">
          <p className="overview-coord-label">Coordinates</p>
          <p className="overview-coord">
            {incident.latitude.toFixed(4)}, {incident.longitude.toFixed(4)}
          </p>
        </div>
      )}
      {vs?.supporting_sources && vs.supporting_sources.length > 0 && (
        <div className="overview-sources">
          <p className="overview-sources-label">Supporting Sources</p>
          <div className="source-tags">
            {vs.supporting_sources.map((s) => (
              <span key={s} className="source-tag source-tag--supporting">
                {s}
              </span>
            ))}
          </div>
        </div>
      )}
      {vs?.contradicting_sources && vs.contradicting_sources.length > 0 && (
        <div className="overview-sources">
          <p className="overview-sources-label">Contradicting Sources</p>
          <div className="source-tags">
            {vs.contradicting_sources.map((s) => (
              <span key={s} className="source-tag source-tag--contradicting">
                {s}
              </span>
            ))}
          </div>
        </div>
      )}
      <div className="overview-report-ids">
        <p className="overview-sources-label">Report IDs</p>
        {incident.report_ids.map((id) => (
          <code key={id} className="report-id-chip">
            {id}
          </code>
        ))}
      </div>
    </div>
  );
}

function MetaItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="meta-item">
      <span className="meta-label">{label}</span>
      <span className="meta-value">{value}</span>
    </div>
  );
}

function formatLocation(incident: Incident): string {
  return (
    [incident.city, incident.district, incident.state_name, incident.country]
      .filter(Boolean)
      .join(", ") || "Unknown"
  );
}
