"use client";
import { useEffect, useRef } from "react";
import Map, {
  Marker,
  NavigationControl,
} from "react-map-gl/maplibre";
import type { MapRef } from "react-map-gl/maplibre";
import type { Incident } from "@/lib/types";
import { EventIcon } from "@/components/shared/EventIcon";
import "maplibre-gl/dist/maplibre-gl.css";

// Free OpenFreeMap tiles — no API key
const MAP_STYLE =
  "https://tiles.openfreemap.org/styles/liberty";

const SEVERITY_COLOR: Record<string, string> = {
  LOW: "#7aaa8a",
  MODERATE: "#d4a04a",
  HIGH: "#e8a87c",
  CRITICAL: "#d45a5a",
};

interface IncidentMapProps {
  incidents: Incident[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}

export function IncidentMap({
  incidents,
  selectedId,
  onSelect,
}: IncidentMapProps) {
  const mapRef = useRef<MapRef | null>(null);


  // When selection changes, fly to that incident
  useEffect(() => {
    if (!selectedId) return;
    const incident = incidents.find((i) => i.incident_id === selectedId);
    if (!incident?.latitude || !incident?.longitude) return;
    const map = mapRef.current?.getMap();
    if (!map) return;
    map.flyTo({
      center: [incident.longitude, incident.latitude],
      zoom: 9,
      duration: 900,
    });
  }, [selectedId, incidents]);

  const mappable = incidents.filter(
    (i) => i.latitude !== null && i.longitude !== null
  );

  return (
    <div className="map-container">
      <Map
        ref={mapRef as any}
        initialViewState={{
          longitude: 78.9629,
          latitude: 22.5937,
          zoom: 4.5,
        }}
        style={{ width: "100%", height: "100%" }}
        mapStyle={MAP_STYLE}
        attributionControl={false}
      >
        <NavigationControl position="top-right" />

        {mappable.map((incident) => {
          const isSelected = incident.incident_id === selectedId;
          const color = SEVERITY_COLOR[incident.severity] ?? "#89bcd4";
          const locationLabel = [incident.city, incident.state_name].filter(Boolean).join(", ") || incident.country || "Location";

          return (
            <Marker
              key={incident.incident_id}
              longitude={incident.longitude!}
              latitude={incident.latitude!}
              anchor="bottom"
              onClick={(e) => {
                e.originalEvent.stopPropagation();
                onSelect(incident.incident_id);
              }}
            >
              <div className="flex flex-col items-center group cursor-pointer">
                {/* Always-visible or Hover Location Label Callout */}
                <div
                  className={`px-2 py-0.5 mb-1 rounded-md text-[11px] font-semibold whitespace-nowrap shadow-md transition-all border ${
                    isSelected
                      ? "bg-slate-900 text-white border-slate-700 scale-105 z-30"
                      : "bg-white/95 text-slate-800 border-slate-200 group-hover:scale-105 group-hover:bg-slate-900 group-hover:text-white"
                  }`}
                >
                  <svg className="w-3 h-3 inline mr-1 opacity-75 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z" />
                    <circle cx="12" cy="10" r="3" />
                  </svg>
                  {locationLabel}
                </div>

                {/* Pin Circle Marker */}
                <div
                  className={`map-marker ${isSelected ? "map-marker--selected" : ""}`}
                  style={{ "--marker-color": color } as React.CSSProperties}
                  title={incident.title}
                >
                  <span className="map-marker-icon">
                    <EventIcon category={incident.event_category} size="sm" />
                  </span>
                  {isSelected && (
                    <div className="map-marker-pulse" style={{ "--marker-color": color } as React.CSSProperties} />
                  )}
                </div>
              </div>
            </Marker>
          );
        })}
      </Map>

      {/* GIS Command Map Overlay Legend & Controls */}
      <div className="absolute bottom-4 left-4 z-10 bg-slate-900/90 backdrop-blur-md text-white px-3 py-2 rounded-lg border border-slate-700/60 shadow-lg text-xs flex flex-col gap-1.5 min-w-[200px]">
        <div className="flex items-center justify-between font-semibold border-b border-slate-700/80 pb-1 text-[11px] text-slate-300 uppercase tracking-wider">
          <span>GIS Incident Legend</span>
          <span className="text-[10px] text-emerald-400 font-mono">LIVE H3-GRID</span>
        </div>
        <div className="grid grid-cols-2 gap-x-3 gap-y-1">
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-[#d45a5a]" />
            <span>Critical</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-[#e8a87c]" />
            <span>High</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-[#d4a04a]" />
            <span>Moderate</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-[#7aaa8a]" />
            <span>Low</span>
          </div>
        </div>
      </div>

      {mappable.length === 0 && (
        <div className="map-empty-overlay">
          <svg className="w-10 h-10 text-slate-400 opacity-60" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="4" />
            <path d="M12 2v2" /><path d="M12 20v2" />
            <path d="m4.93 4.93 1.41 1.41" /><path d="m17.66 17.66 1.41 1.41" />
            <path d="M2 12h2" /><path d="M20 12h2" />
            <path d="m6.34 17.66-1.41 1.41" /><path d="m19.07 4.93-1.41 1.41" />
          </svg>
          <p>Waiting for geolocated incidents…</p>
          <p className="map-empty-sub">Ingestion runs every 3–5 minutes</p>
        </div>
      )}
    </div>
  );
}
