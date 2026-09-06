"use client";
import type { IncidentFilters, IncidentSeverity, VerificationStatus } from "@/lib/types";

const EVENT_CATEGORIES = [
  "RAIN", "FLOOD", "WATERLOGGING", "THUNDERSTORM",
  "LIGHTNING", "HEATWAVE", "FOG", "DUST_STORM",
  "STRONG_WIND", "HAILSTORM", "CYCLONE", "OTHER",
];

const SEVERITIES: IncidentSeverity[] = ["LOW", "MODERATE", "HIGH", "CRITICAL"];

const VERIFICATION_STATUSES: VerificationStatus[] = [
  "SUPPORTED", "VERIFIED", "UNVERIFIED", "CONTRADICTED", "PENDING_REVIEW",
];

interface FilterBarProps {
  filters: IncidentFilters;
  onChange: (filters: IncidentFilters) => void;
}

export function FilterBar({ filters, onChange }: FilterBarProps) {
  function set(patch: Partial<IncidentFilters>) {
    onChange({ ...filters, ...patch });
  }

  function clear() {
    onChange({});
  }

  const hasActive =
    filters.event_category ||
    filters.severity ||
    filters.verification_status ||
    filters.state;

  return (
    <div className="filter-bar">
      <div className="filter-row">
        <label className="filter-label">Event Type</label>
        <select
          className="filter-select"
          value={filters.event_category ?? ""}
          onChange={(e) =>
            set({ event_category: e.target.value || undefined })
          }
        >
          <option value="">All types</option>
          {EVENT_CATEGORIES.map((c) => (
            <option key={c} value={c}>
              {c.replace("_", " ")}
            </option>
          ))}
        </select>
      </div>

      <div className="filter-row">
        <label className="filter-label">Severity</label>
        <select
          className="filter-select"
          value={filters.severity ?? ""}
          onChange={(e) =>
            set({ severity: (e.target.value as IncidentSeverity) || undefined })
          }
        >
          <option value="">All severities</option>
          {SEVERITIES.map((s) => (
            <option key={s} value={s}>
              {s.charAt(0) + s.slice(1).toLowerCase()}
            </option>
          ))}
        </select>
      </div>

      <div className="filter-row">
        <label className="filter-label">Verification</label>
        <select
          className="filter-select"
          value={filters.verification_status ?? ""}
          onChange={(e) =>
            set({
              verification_status:
                (e.target.value as VerificationStatus) || undefined,
            })
          }
        >
          <option value="">All statuses</option>
          {VERIFICATION_STATUSES.map((v) => (
            <option key={v} value={v}>
              {v.replace("_", " ")}
            </option>
          ))}
        </select>
      </div>

      <div className="filter-row">
        <label className="filter-label">City / State</label>
        <input
          className="filter-input"
          placeholder="e.g. Mumbai"
          value={filters.city ?? ""}
          onChange={(e) => set({ city: e.target.value || undefined })}
        />
      </div>

      {hasActive && (
        <button className="filter-clear-btn" onClick={clear}>
          ✕ Clear filters
        </button>
      )}
    </div>
  );
}
