"""Evidence Verification Engine for Evidence Aggregation and Confidence Scoring."""

import hashlib
from datetime import datetime, timezone

from contracts.evidence import EvidenceItem, EvidenceRelationship, VerificationStatus, VerificationSummary
from contracts.incident import Incident, IncidentSeverity, IncidentState
from contracts.weather_report import WeatherReport
from intelligence.nlp_extractor import NLPExtractor

# Source Reliability Weights (0.0 to 1.0)
SOURCE_RELIABILITY_WEIGHTS = {
    "imd": 0.95,
    "open_meteo": 0.90,
    "news_rss": 0.80,
    "twitter": 0.60,
    "social_media": 0.60,
    "citizen_app": 0.55,
}


class EvidenceEngine:
    """Evaluates multi-source report evidence to construct an explainable VerificationSummary for Incidents."""

    def __init__(self) -> None:
        self.nlp_extractor = NLPExtractor()

    def evaluate_incident(self, incident: Incident, reports: list[WeatherReport]) -> Incident:
        """Evaluates supporting/contradicting evidence for an incident and updates its verification summary and state."""
        if not reports:
            return incident

        # Filter reports belonging to this incident
        incident_reports = [r for r in reports if r.report_id in incident.report_ids]
        if not incident_reports:
            return incident

        evidence_items: list[EvidenceItem] = []
        supporting_sources: set[str] = set()
        contradicting_sources: set[str] = set()

        supporting_weighted_sum = 0.0
        total_weight = 0.0

        for report in incident_reports:
            is_negated = self.nlp_extractor.is_negated(report.text)
            rel_type = EvidenceRelationship.CONTRADICTING if is_negated else EvidenceRelationship.SUPPORTING

            weight = SOURCE_RELIABILITY_WEIGHTS.get(report.source.lower(), 0.50)
            if report.source_type == "official":
                weight = max(weight, 0.90)

            reasoning = (
                f"Report from {report.source} explicitly contradicts event presence (negation detected)."
                if is_negated
                else f"Report from {report.source} provides corroborating text and spatial proximity."
            )

            ev_hash = hashlib.sha256(f"{report.report_id}_{incident.incident_id}".encode("utf-8")).hexdigest()[:10]
            evidence_id = f"ev_{ev_hash}"

            evidence = EvidenceItem(
                evidence_id=evidence_id,
                report_id=report.report_id,
                source=report.source,
                source_type=report.source_type,
                relationship=rel_type,
                confidence_score=weight,
                source_reliability_weight=weight,
                reasoning=reasoning,
                extracted_event=incident.event_category,
                extracted_location=report.city or report.state,
                media_proof_urls=report.media_urls,
                timestamp=report.timestamp,
            )
            evidence_items.append(evidence)

            if rel_type == EvidenceRelationship.SUPPORTING:
                supporting_sources.add(report.source)
                supporting_weighted_sum += weight
            else:
                contradicting_sources.add(report.source)

            total_weight += weight

        supporting_count = len([e for e in evidence_items if e.relationship == EvidenceRelationship.SUPPORTING])
        contradicting_count = len([e for e in evidence_items if e.relationship == EvidenceRelationship.CONTRADICTING])

        # Overall confidence score calculation (combines average source trust weight with supporting ratio)
        if total_weight > 0:
            avg_source_weight = supporting_weighted_sum / supporting_count if supporting_count > 0 else 0.0
            supporting_ratio = supporting_weighted_sum / total_weight
            overall_confidence = round(avg_source_weight * supporting_ratio, 2)
        else:
            overall_confidence = 0.0

        # Verification Status Logic
        if contradicting_count > supporting_count and contradicting_count > 1:
            status = VerificationStatus.CONTRADICTED
            state = IncidentState.DE_ESCALATING
            explanation = (
                f"Incident contradicts ground reality. {contradicting_count} contradicting report(s) "
                f"outweigh {supporting_count} supporting report(s)."
            )
        elif supporting_count >= 2 or any(r.source_type == "official" for r in incident_reports):
            status = VerificationStatus.SUPPORTED
            state = IncidentState.VERIFIED
            explanation = (
                f"Verified by {supporting_count} multi-source report(s) including "
                f"{', '.join(supporting_sources)} with {overall_confidence * 100:.0f}% confidence."
            )
        else:
            status = VerificationStatus.UNVERIFIED
            state = IncidentState.REPORTED
            explanation = f"Single unverified report from {list(supporting_sources)[0] if supporting_sources else 'unknown source'}. Awaiting further multi-source reports."

        # Calculate Priority Score (0-100)
        priority = round(min(100.0, (overall_confidence * 60) + (supporting_count * 10)), 1)
        if incident.severity == IncidentSeverity.HIGH:
            priority = min(100.0, priority + 15.0)
        elif incident.severity == IncidentSeverity.CRITICAL:
            priority = min(100.0, priority + 30.0)

        verification_summary = VerificationSummary(
            verification_status=status,
            overall_confidence=overall_confidence,
            supporting_count=supporting_count,
            contradicting_count=contradicting_count,
            supporting_sources=list(supporting_sources),
            contradicting_sources=list(contradicting_sources),
            evidence_items=evidence_items,
            explanation=explanation,
            updated_at=datetime.now(timezone.utc),
        )

        incident.verification_summary = verification_summary
        incident.state = state
        incident.priority_score = priority

        return incident
