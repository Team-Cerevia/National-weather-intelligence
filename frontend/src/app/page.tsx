"use client";
import { useCallback, useRef, useState } from "react";
import { useIncidents } from "@/hooks/useIncidents";
import { useRealtimeStream } from "@/hooks/useRealtimeStream";
import { StatsBar } from "@/components/stats/StatsBar";
import { FilterBar } from "@/components/sidebar/FilterBar";
import { IncidentList } from "@/components/sidebar/IncidentList";
import { IncidentDetail } from "@/components/detail/IncidentDetail";
import type { Incident, IncidentFilters } from "@/lib/types";
import dynamic from "next/dynamic";

// Map must be client-only (uses browser APIs)
const IncidentMap = dynamic(
  () => import("@/components/map/IncidentMap").then((m) => m.IncidentMap),
  { ssr: false, loading: () => <div className="map-placeholder" /> }
);

export default function DashboardPage() {
  const [filters, setFilters] = useState<IncidentFilters>({});
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [newIds, setNewIds] = useState<Set<string>>(new Set());
  const { incidents, isLoading, refresh } = useIncidents(filters);

  const handleNewIncident = useCallback(
    (incident: Incident) => {
      setNewIds((prev) => {
        const next = new Set(prev);
        next.add(incident.incident_id);
        // Remove "new" highlight after 8 seconds
        setTimeout(() => {
          setNewIds((s) => {
            const n = new Set(s);
            n.delete(incident.incident_id);
            return n;
          });
        }, 8000);
        return next;
      });
      refresh();
    },
    [refresh]
  );

  const { connected, lastEventAt } = useRealtimeStream(handleNewIncident);

  return (
    <div className="dashboard">
      <StatsBar
        incidents={incidents}
        connected={connected}
        lastEventAt={lastEventAt}
      />

      <div className="dashboard-body">
        {/* Sidebar */}
        <aside className="sidebar">
          <FilterBar filters={filters} onChange={setFilters} />
          <IncidentList
            incidents={incidents}
            isLoading={isLoading}
            selectedId={selectedId}
            newIds={newIds}
            onSelect={setSelectedId}
          />
        </aside>

        {/* Map */}
        <main className="map-area">
          <IncidentMap
            incidents={incidents}
            selectedId={selectedId}
            onSelect={setSelectedId}
          />
        </main>
      </div>

      {/* Detail Slide-Over */}
      <IncidentDetail
        incidentId={selectedId}
        onClose={() => setSelectedId(null)}
      />
    </div>
  );
}
