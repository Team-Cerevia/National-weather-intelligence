"""Intelligence Pipeline Orchestrator linking raw WeatherReport inputs to Incident outputs."""

from contracts.incident import Incident
from contracts.weather_report import WeatherReport
from intelligence.evidence_engine import EvidenceEngine
from intelligence.incident_engine import IncidentEngine
from intelligence.nlp_extractor import NLPExtractor


class IntelligenceOrchestrator:
    """Master pipeline orchestrator that processes raw weather reports into verified incidents."""

    def __init__(self, time_window_hours: float = 6.0, spatial_k_ring: int = 1) -> None:
        self.nlp_extractor = NLPExtractor()
        self.incident_engine = IncidentEngine(time_window_hours=time_window_hours, spatial_k_ring=spatial_k_ring)
        self.evidence_engine = EvidenceEngine()

    def process_reports(self, reports: list[WeatherReport]) -> list[Incident]:
        """Runs end-to-end intelligence pipeline on input reports:
        1. Correlate raw reports into spatial-temporal Incident clusters.
        2. Evaluate evidence provenance and calculate confidence scores.
        """
        if not reports:
            return []

        # 1. Spatio-temporal & NLP correlation
        incidents = self.incident_engine.correlate_reports(reports)

        # 2. Evidence provenance evaluation
        verified_incidents: list[Incident] = []
        for incident in incidents:
            evaluated = self.evidence_engine.evaluate_incident(incident, reports)
            verified_incidents.append(evaluated)

        return verified_incidents
