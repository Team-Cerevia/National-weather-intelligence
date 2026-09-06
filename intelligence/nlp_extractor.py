"""NLP Extractor & Event Classifier for Weather Reports."""

import re
from typing import Any

# Official Event Ontology Taxonomy
EVENT_CATEGORIES = {
    "RAIN": ["rain", "rainfall", "downpour", "drizzle", "shower", "baarish", "precipitation"],
    "FLOOD": ["flood", "flooding", "inundation", "overflow", "deluge", "baadh"],
    "WATERLOGGING": ["waterlogging", "waterlogged", "water-logged", "submerged", "paani bhara", "standing water"],
    "THUNDERSTORM": ["thunderstorm", "thunder", "storm", "tempest", "toofan"],
    "LIGHTNING": ["lightning", "thunderbolt", "bijli"],
    "HEATWAVE": ["heatwave", "heat wave", "extreme heat", "scorching", "loo", "high temp"],
    "FOG": ["fog", "dense fog", "smog", "mist", "low visibility", "kohra"],
    "DUST_STORM": ["dust storm", "duststorm", "sandstorm", "andhi"],
    "STRONG_WIND": ["strong wind", "gale", "high winds", "gusty wind", "squall", "tez hawa"],
    "HAILSTORM": ["hailstorm", "hail", "ice pellets", "olay"],
    "CYCLONE": ["cyclone", "typhoon", "hurricane", "tropical storm"],
}

# Negation Triggers indicating false alarm or clear conditions
NEGATION_PATTERNS = [
    r"\bno\b",
    r"\bnot\b",
    r"\bfalse\b",
    r"\brumor\b",
    r"\brumour\b",
    r"\bfake\b",
    r"\bdenied\b",
    r"\bclear\s+sky\b",
    r"\bsun\s+is\s+out\b",
    r"\bno\s+reports?\s+of\b",
    r"\bwithout\s+any\b",
]

# Indian Location Gazetteer & NER Patterns for Location Entity Extraction
LOCATION_NER_PATTERNS = [
    r"\b(?:in|at|near|around|from)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b",
    r"\b(Delhi|New Delhi|Noida|Gurgaon|Gurugram|Faridabad|Ghaziabad|Mumbai|Kolkata|Chennai|Bengaluru|Bangalore|Hyderabad|Ahmedabad|Pune|Jaipur|Lucknow|Kanpur|Patna|Bhopal|Guwahati|Shimla|Srinagar)\b",
]


class NLPExtractor:
    """Parses text to extract event category, negation status, location NER entities, and numerical metrics."""

    def __init__(self) -> None:
        self._compiled_negations = [re.compile(pattern, re.IGNORECASE) for pattern in NEGATION_PATTERNS]
        self._compiled_locations = [re.compile(pattern, re.IGNORECASE) for pattern in LOCATION_NER_PATTERNS]

    def extract_event_category(self, text: str) -> str:
        """Classifies text into one of the 12 canonical EventType categories."""
        if not text:
            return "OTHER"

        text_lower = text.lower()
        scores: dict[str, int] = {}

        for category, keywords in EVENT_CATEGORIES.items():
            count = sum(1 for kw in keywords if kw in text_lower)
            if count > 0:
                scores[category] = count

        if not scores:
            return "OTHER"

        # Prioritize specific severe events over generic RAIN if both match
        if "FLOOD" in scores:
            return "FLOOD"
        if "WATERLOGGING" in scores:
            return "WATERLOGGING"
        if "CYCLONE" in scores:
            return "CYCLONE"

        return max(scores, key=scores.get)  # type: ignore

    def is_negated(self, text: str) -> bool:
        """Detects if the weather report contains negation or false alarm context."""
        if not text:
            return False

        for pattern in self._compiled_negations:
            if pattern.search(text):
                return True
        return False

    def extract_locations_ner(self, text: str) -> list[str]:
        """Extracts location Named Entities (NER) from text using spatial entity patterns."""
        if not text:
            return []

        locations: set[str] = set()
        for pattern in self._compiled_locations:
            matches = pattern.findall(text)
            for m in matches:
                loc = m.strip() if isinstance(m, str) else m[0].strip()
                if len(loc) > 2 and loc.lower() not in [
                    "the",
                    "this",
                    "heavy",
                    "severe",
                    "north",
                    "south",
                    "east",
                    "west",
                ]:
                    locations.add(loc.title())

        return list(locations)

    def extract_metrics(self, text: str) -> dict[str, Any]:
        """Extracts quantitative weather metrics (rainfall mm, wind speed km/h, temperature deg C)."""
        metrics: dict[str, Any] = {}
        if not text:
            return metrics

        # Rainfall mm
        rain_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:mm|millimeters?)", text, re.IGNORECASE)
        if rain_match:
            metrics["rainfall_mm"] = float(rain_match.group(1))

        # Wind speed km/h
        wind_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:km/h|kmh|kmph|knots)", text, re.IGNORECASE)
        if wind_match:
            metrics["wind_speed_kmh"] = float(wind_match.group(1))

        # Temperature deg C
        temp_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:°C|deg C|degrees C|C\b)", text, re.IGNORECASE)
        if temp_match:
            metrics["temperature_c"] = float(temp_match.group(1))

        return metrics

    def extract_entities(self, text: str) -> dict[str, Any]:
        """Extracts extracted structured metadata from text."""
        return {
            "event_category": self.extract_event_category(text),
            "is_negated": self.is_negated(text),
            "locations": self.extract_locations_ner(text),
            "metrics": self.extract_metrics(text),
        }
