# Track D2: Interactive GIS Dashboard & Provenance UI

> **Owner:** Frontend Developer / Teammate D  
> **Branch:** `feat/frontend-dashboard`  
> **Goal:** Build the interactive Leaflet GIS India map dashboard with incident filtering controls and the "Why is this real?" Evidence Provenance Drawer.

---

## Responsibility Boundary

### What You Own
- **Next.js Web Application (`frontend/`):** Dashboard shell, navbar, live status indicator.
- **GIS Map Component (`frontend/src/components/Map.tsx`):** Leaflet / MapLibre map centered on India (`lat: 20.5937, lng: 78.9629`) with color-coded severity markers.
- **Evidence Provenance Drawer (`frontend/src/components/EvidenceDrawer.tsx`):** Slide-over panel displaying verification confidence, supporting news/tweets/IMD evidence, and contradicting reports.
- **API Client Layer (`frontend/src/lib/api.ts`):** Decoupled API client that fetches from `/api/v1/incidents` (or local `mock_incidents.json` during standalone dev).

### What You Do NOT Own
- Database schema or FastAPI backend routes (Track D1).
- Redis event streaming (Track B).
- ML intelligence pipeline (Track C).

---

## Data Contract Integration

Uses `Incident` and `EvidenceItem` JSON structures matching `contracts/`:

```typescript
export interface Incident {
  incident_id: string;
  event_type: 'FLOOD' | 'RAIN' | 'THUNDERSTORM' | 'HEATWAVE' | 'FOG';
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  verification_status: 'SUPPORTED' | 'UNVERIFIED' | 'CONTRADICTED';
  confidence_score: number;
  location: { latitude: number; longitude: number; name: string };
}
```

---

## File Checklist

- `frontend/src/components/Map.tsx`
- `frontend/src/components/EvidenceDrawer.tsx`
- `frontend/src/components/FilterSidebar.tsx`
- `frontend/src/lib/api.ts`
- `frontend/src/data/mock_incidents.json`

---

## Definition of Done

1. Next.js app builds and runs smoothly (`npm run dev`).
2. Leaflet map renders incidents on India map with interactive popups/markers.
3. Clicking a marker slides open the Evidence Provenance Drawer.
4. Filter sidebar updates displayed map markers dynamically.
