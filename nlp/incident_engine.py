"""Spatio-Temporal & Semantic Incident Correlation Engine."""

import hashlib
from datetime import timedelta

import h3

from contracts.incident import Incident, IncidentSeverity, IncidentState, IncidentTimeline
from contracts.weather_report import DEFAULT_H3_RESOLUTION, WeatherReport
from nlp.nlp_extractor import NLPExtractor

# Event type compatibility mapping (events that belong to the same weather phenomenon)
COMPATIBLE_EVENTS = {
    "RAIN": {"RAIN", "FLOOD", "WATERLOGGING", "THUNDERSTORM"},
    "FLOOD": {"RAIN", "FLOOD", "WATERLOGGING"},
    "WATERLOGGING": {"RAIN", "FLOOD", "WATERLOGGING"},
    "THUNDERSTORM": {"RAIN", "THUNDERSTORM", "LIGHTNING", "STRONG_WIND", "HAILSTORM"},
    "LIGHTNING": {"THUNDERSTORM", "LIGHTNING"},
    "HEATWAVE": {"HEATWAVE"},
    "FOG": {"FOG"},
    "DUST_STORM": {"DUST_STORM", "STRONG_WIND"},
    "STRONG_WIND": {"THUNDERSTORM", "STRONG_WIND", "DUST_STORM", "CYCLONE"},
    "HAILSTORM": {"THUNDERSTORM", "HAILSTORM"},
    "CYCLONE": {"CYCLONE", "STRONG_WIND", "RAIN", "FLOOD"},
    "OTHER": {"OTHER"},
}


class IncidentEngine:
    """Correlates WeatherReport inputs into Incident objects using spatial, temporal, and semantic criteria."""

    def __init__(self, time_window_hours: float = 6.0, spatial_k_ring: int = 1) -> None:
        self.time_window = timedelta(hours=time_window_hours)
        self.spatial_k_ring = spatial_k_ring
        self.nlp_extractor = NLPExtractor()

    def correlate_reports(self, reports: list[WeatherReport]) -> list[Incident]:
        """Processes a list of raw weather reports and returns clustered Incident objects."""
        if not reports:
            return []

        incidents: list[Incident] = []

        for report in sorted(reports, key=lambda r: r.timestamp):
            category = self.nlp_extractor.extract_event_category(report.text)
            is_negated = self.nlp_extractor.is_negated(report.text)

            # Skip negated false alarm reports from creating new incidents alone
            if is_negated and not incidents:
                continue

            matched_incident = self._find_matching_incident(incidents, report, category)

            if matched_incident:
                self._add_report_to_incident(matched_incident, report, category)
            else:
                new_incident = self._create_incident(report, category)
                incidents.append(new_incident)

        return incidents

    def _find_matching_incident(
        self, incidents: list[Incident], report: WeatherReport, category: str
    ) -> Incident | None:
        """Finds an existing incident matching the report spatially, temporally, and semantically."""
        report_cell = report.h3_cell

        # Calculate neighboring H3 cells if cell is present
        neighbor_cells = set()
        if report_cell and h3.is_valid_cell(report_cell):
            neighbor_cells = set(h3.grid_disk(report_cell, self.spatial_k_ring))

        for incident in incidents:
            # 1. Event compatibility check
            compatible_set = COMPATIBLE_EVENTS.get(incident.event_category, {incident.event_category})
            if category not in compatible_set:
                continue

            # 2. Temporal window check
            time_diff = abs(report.timestamp - incident.last_updated_at)
            if time_diff > self.time_window:
                continue

            # 3. Spatial proximity check
            spatial_match = False
            if report_cell and incident.h3_cells:
                if any(cell in neighbor_cells for cell in incident.h3_cells):
                    spatial_match = True
            elif report.latitude is not None and incident.latitude is not None:
                # Coordinate distance check (~20km)
                lat_diff = abs(report.latitude - incident.latitude)
                lon_diff = abs(report.longitude - incident.longitude)
                if lat_diff <= 0.2 and lon_diff <= 0.2:
                    spatial_match = True

            if spatial_match:
                return incident

        return None

    def _create_incident(self, report: WeatherReport, category: str) -> Incident:
        """Constructs a new Incident from a triggering WeatherReport."""
        location_str = (
            report.city or report.state or f"({report.latitude:.2f}, {report.longitude:.2f})"
            if report.latitude
            else "Unknown Location"
        )
        title = f"{category.replace('_', ' ').title()} Alert in {location_str}"

        # Generate deterministic incident ID
        raw_key = f"{category}_{report.h3_cell or report.latitude}_{report.timestamp.isoformat()}"
        inc_hash = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()[:12]
        incident_id = f"inc_{category.lower()}_{inc_hash}"

        h3_cells = []
        if report.h3_cell and h3.is_valid_cell(report.h3_cell):
            res = h3.get_resolution(report.h3_cell)
            if res == DEFAULT_H3_RESOLUTION:
                h3_cells.append(report.h3_cell)

        # Initial severity heuristic based on metrics/source
        severity = IncidentSeverity.MODERATE
        if "flood" in category.lower() or "cyclone" in category.lower():
            severity = IncidentSeverity.HIGH

        timeline_entry = IncidentTimeline(
            timestamp=report.timestamp,
            event_type="incident_created",
            description=f"Incident created from initial {report.source} report.",
            new_state=IncidentState.REPORTED,
            new_severity=severity,
            report_id=report.report_id,
        )

        return Incident(
            incident_id=incident_id,
            title=title,
            event_category=category,
            state=IncidentState.REPORTED,
            severity=severity,
            priority_score=50.0,
            latitude=report.latitude,
            longitude=report.longitude,
            h3_cells=h3_cells,
            city=report.city,
            district=report.district,
            state_name=report.state,
            country=report.country or "India",
            first_reported_at=report.timestamp,
            last_updated_at=report.timestamp,
            report_ids=[report.report_id],
            timeline=[timeline_entry],
        )

    def _add_report_to_incident(self, incident: Incident, report: WeatherReport, category: str) -> None:
        """Adds a matching report to an existing incident, updating spatial bounds and timeline."""
        if report.report_id not in incident.report_ids:
            incident.report_ids.append(report.report_id)

        # Update last updated timestamp
        if report.timestamp > incident.last_updated_at:
            incident.last_updated_at = report.timestamp

        # Spatial expansion (add H3 cell if valid)
        if report.h3_cell and h3.is_valid_cell(report.h3_cell):
            res = h3.get_resolution(report.h3_cell)
            if res == DEFAULT_H3_RESOLUTION and report.h3_cell not in incident.h3_cells:
                incident.h3_cells.append(report.h3_cell)

        # Add timeline entry
        timeline_entry = IncidentTimeline(
            timestamp=report.timestamp,
            event_type="report_correlated",
            description=f"Correlated supporting report from {report.source}.",
            report_id=report.report_id,
        )
        incident.timeline.append(timeline_entry)
