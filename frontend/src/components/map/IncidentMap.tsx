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

          return (
            <Marker
              key={incident.incident_id}
              longitude={incident.longitude!}
              latitude={incident.latitude!}
              anchor="center"
              onClick={(e) => {
                e.originalEvent.stopPropagation();
                onSelect(incident.incident_id);
              }}
            >
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
            </Marker>
          );
        })}
      </Map>

      {mappable.length === 0 && (
        <div className="map-empty-overlay">
          <span>🌤️</span>
          <p>Waiting for geolocated incidents…</p>
          <p className="map-empty-sub">Ingestion runs every 3–5 minutes</p>
        </div>
      )}
    </div>
  );
}
