"use client";
import { useState } from "react";
import type { Incident } from "@/lib/types";
import { IncidentCard } from "./IncidentCard";

interface IncidentListProps {
  incidents: Incident[];
  isLoading: boolean;
  selectedId: string | null;
  newIds: Set<string>;
  onSelect: (id: string) => void;
}

export function IncidentList({
  incidents,
  isLoading,
  selectedId,
  newIds,
  onSelect,
}: IncidentListProps) {
  const [sortBy, setSortBy] = useState<"time" | "severity" | "confidence">(
    "time"
  );

  const SEVERITY_ORDER = { CRITICAL: 0, HIGH: 1, MODERATE: 2, LOW: 3 };

  const sorted = [...incidents].sort((a, b) => {
    if (sortBy === "severity") {
      return (
        (SEVERITY_ORDER[a.severity] ?? 4) - (SEVERITY_ORDER[b.severity] ?? 4)
      );
    }
    if (sortBy === "confidence") {
      return (
        (b.verification_summary?.overall_confidence ?? 0) -
        (a.verification_summary?.overall_confidence ?? 0)
      );
    }
    // Default: newest first
    return (
      new Date(b.last_updated_at).getTime() -
      new Date(a.last_updated_at).getTime()
    );
  });

  return (
    <div className="incident-list">
      <div className="incident-list-toolbar">
        <span className="incident-count">
          {incidents.length} incident{incidents.length !== 1 ? "s" : ""}
        </span>
        <div className="sort-tabs">
          {(["time", "severity", "confidence"] as const).map((s) => (
            <button
              key={s}
              className={`sort-tab ${sortBy === s ? "sort-tab--active" : ""}`}
              onClick={() => setSortBy(s)}
            >
              {s === "time" ? "Recent" : s === "severity" ? "Severity" : "Confidence"}
            </button>
          ))}
        </div>
      </div>

      <div className="incident-list-scroll">
        {isLoading && incidents.length === 0 && (
          <div className="list-empty">
            <div className="spinner" />
            <p>Loading incidents…</p>
          </div>
        )}

        {!isLoading && incidents.length === 0 && (
          <div className="list-empty">
            <span className="list-empty-icon">🌤️</span>
            <p>No incidents found</p>
            <p className="list-empty-sub">
              Data will appear as the ingestion pipeline processes live feeds.
            </p>
          </div>
        )}

        {sorted.map((incident) => (
          <IncidentCard
            key={incident.incident_id}
            incident={incident}
            selected={selectedId === incident.incident_id}
            isNew={newIds.has(incident.incident_id)}
            onClick={() => onSelect(incident.incident_id)}
          />
        ))}
      </div>
    </div>
  );
}
