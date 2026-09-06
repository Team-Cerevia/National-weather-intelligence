"use client";
import { useEffect, useState } from "react";
import type { Incident } from "@/lib/types";

interface StatsBarProps {
  incidents: Incident[];
  connected: boolean;
  lastEventAt: Date | null;
}

export function StatsBar({ incidents, connected, lastEventAt }: StatsBarProps) {
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
        <span className="brand-icon">🌦️</span>
        <div>
          <h1 className="brand-title">Weather Intelligence</h1>
          <p className="brand-sub">National Big Data Analytics Platform</p>
        </div>
      </div>

      <div className="stats-bar-metrics">
        <StatPill label="Total Incidents" value={total} variant="neutral" />
        <StatPill label="Active" value={active} variant="neutral" />
        <StatPill label="High Severity" value={high} variant="warn" />
        <StatPill label="Critical" value={critical} variant="danger" />
      </div>

      <div className="stats-bar-live">
        <span className={`live-dot ${connected ? "live-dot--on" : "live-dot--off"} ${pulse ? "live-dot--pulse" : ""}`} />
        <span className={`live-label ${connected ? "live-label--on" : "live-label--off"}`}>
          {connected ? "Live" : "Reconnecting…"}
        </span>
        {lastEventAt && (
          <span className="live-last">
            Last update {lastEventAt.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
          </span>
        )}
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
