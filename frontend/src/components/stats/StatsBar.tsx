"use client";
import { useEffect, useState } from "react";
import type { Incident } from "@/lib/types";

interface StatsBarProps {
  incidents: Incident[];
  connected: boolean;
  lastEventAt: Date | null;
  activeView?: "map" | "records" | "copilot";
  onViewChange?: (view: "map" | "records" | "copilot") => void;
  onOpenReportModal?: () => void;
}

export function StatsBar({
  incidents,
  connected,
  lastEventAt,
  activeView = "map",
  onViewChange,
  onOpenReportModal,
}: StatsBarProps) {
  const [pulse, setPulse] = useState(false);

  const total = incidents.length;
  const critical = incidents.filter((i) => i.severity === "CRITICAL").length;
  const high = incidents.filter((i) => i.severity === "HIGH").length;
  const active = incidents.filter(
    (i) => i.state !== "RESOLVED"
  ).length;

  // Flash the live badge when a new event arrives
  useEffect(() => {
    if (!lastEventAt) return;
    setPulse(true);
    const t = setTimeout(() => setPulse(false), 1200);
    return () => clearTimeout(t);
  }, [lastEventAt]);

  return (
    <header className="stats-bar">
      <div className="stats-bar-brand">
        <img
          src="/logo.png"
          alt="METEORA Logo"
          className="brand-logo-img"
        />
        <div>
          <h1 className="brand-title">METEORA</h1>
          <p className="brand-sub">National Weather Big Data Analytics Platform</p>
        </div>
      </div>

      <div className="stats-bar-metrics">
        <StatPill label="Total Incidents" value={total} variant="neutral" />
        <StatPill label="Active" value={active} variant="neutral" />
        <StatPill label="High Severity" value={high} variant="warn" />
        <StatPill label="Critical" value={critical} variant="danger" />
      </div>

      <div className="stats-bar-views">
        <button
          className={`view-nav-btn ${activeView === "map" ? "view-nav-btn--active" : ""}`}
          onClick={() => onViewChange?.("map")}
        >
          GIS Command Map
        </button>
        <button
          className={`view-nav-btn ${activeView === "records" ? "view-nav-btn--active" : ""}`}
          onClick={() => onViewChange?.("records")}
        >
          Records & SITREP
        </button>
        <button
          className={`view-nav-btn ${activeView === "copilot" ? "view-nav-btn--active" : ""}`}
          onClick={() => onViewChange?.("copilot")}
        >
          Operator Copilot
        </button>
      </div>

      <div className="stats-bar-actions">
        <button className="submit-report-btn" onClick={onOpenReportModal}>
          + Report Ground Incident
        </button>
        <div className="stats-bar-live">
          <span className={`live-dot ${connected ? "live-dot--on" : "live-dot--off"} ${pulse ? "live-dot--pulse" : ""}`} />
          <span className={`live-label ${connected ? "live-label--on" : "live-label--off"}`}>
            {connected ? "Live Stream" : "Reconnecting…"}
          </span>
          {lastEventAt && (
            <span className="live-last">
              Last update {lastEventAt.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
            </span>
          )}
        </div>
      </div>
    </header>
  );
}

function StatPill({
  label,
  value,
  variant,
}: {
  label: string;
  value: number;
  variant: "neutral" | "warn" | "danger";
}) {
  return (
    <div className={`stat-pill stat-pill--${variant}`}>
      <span className="stat-pill-value">{value}</span>
      <span className="stat-pill-label">{label}</span>
    </div>
  );
}
