"""
NLP Extractor & Transformer Model Embedder for Weather Reports.
Combines rule-based taxonomy classification with ONNX Runtime neural text embedding generation.
"""

import logging
import os
import re
from pathlib import Path
from typing import Any, List, Optional

import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Optional runtime dependencies — graceful degradation if missing
# ---------------------------------------------------------------------------
try:
    import onnxruntime as ort

    HAS_ONNX = True
except ImportError:
    HAS_ONNX = False

try:
    from tokenizers import Tokenizer

    HAS_TOKENIZERS = True
except ImportError:
    HAS_TOKENIZERS = False

# Auto-detect model files from models/ directory (adjacent to project root)
_DEFAULT_MODELS_DIR = Path(__file__).parent.parent / "models"
_DEFAULT_ONNX_PATH = _DEFAULT_MODELS_DIR / "model.onnx"
_DEFAULT_TOKENIZER_PATH = _DEFAULT_MODELS_DIR / "tokenizer.json"

# Official Event Ontology Taxonomy with Vernacular Terms (Hindi, Tamil, Bengali, Marathi)
EVENT_CATEGORIES = {
    "RAIN": ["rain", "rainfall", "downpour", "drizzle", "shower", "baarish", "varsha", "precipitation", "mazhai"],
    "FLOOD": ["flood", "flooding", "inundation", "overflow", "deluge", "baadh", "vellam", "bonyo"],
    "WATERLOGGING": [
        "waterlogging",
        "waterlogged",
        "water-logged",
        "submerged",
        "paani bhara",
        "standing water",
        "jal-bhorao",
        "jalbhrav",
        "water logging",
    ],
    "THUNDERSTORM": ["thunderstorm", "thunder", "storm", "tempest", "toofan", "tufan", "idimazhai"],
    "LIGHTNING": ["lightning", "thunderbolt", "bijli", "tadik", "minnal"],
    "HEATWAVE": ["heatwave", "heat wave", "extreme heat", "scorching", "loo", "garmi", "heat wave alert"],
    "FOG": ["fog", "dense fog", "smog", "mist", "low visibility", "kohra", "manju"],
    "DUST_STORM": ["dust storm", "duststorm", "sandstorm", "andhi", "dhool bhari aandhi"],
    "STRONG_WIND": ["strong wind", "gale", "high winds", "gusty wind", "squall", "tez hawa", "kaatru"],
    "HAILSTORM": ["hailstorm", "hail", "ice pellets", "olay", "hairstorm"],
    "CYCLONE": ["cyclone", "typhoon", "hurricane", "tropical storm", "chakrawat", "chuyal"],
}

# Negation triggers — matched only when appearing within 8 words of a weather keyword
# This prevents false positives like "not just rain but ALSO flooding" being classified as negation
NEGATION_PATTERNS = [
    r"\bno\s+(?:reports?\s+of\s+|signs?\s+of\s+|evidence\s+of\s+)?\b",
    r"\bdid\s+not\b",
    r"\bnot\s+(?:confirmed|reported|observed|detected|seen)\b",
    r"\bfalse\s+alarm\b",
    r"\brumou?r\b",
    r"\bdenied\b",
    r"\bclear\s+sky\b",
    r"\bsun\s+is\s+out\b",
    r"\bnormal\s+traffic\b",
    r"\bno\s+flood\b",
    r"\bno\s+rain\b",
    r"\bno\s+damage\b",
]

# Weather keywords used for proximity check in negation detection
_WEATHER_PROXIMITY_KEYWORDS = [
    "rain",
    "flood",
    "storm",
    "wind",
    "fog",
    "hail",
    "cyclone",
    "lightning",
    "heat",
    "waterlogging",
    "inundation",
    "baarish",
    "baadh",
    "toofan",
]

# Indian Location Gazetteer & NER Patterns for Location Entity Extraction
LOCATION_NER_PATTERNS = [
    r"\b(?:in|at|near|around|from)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b",
    r"\b(Delhi|New Delhi|Noida|Gurgaon|Gurugram|Faridabad|Ghaziabad|Mumbai|Thane|Kolkata|Chennai|Bengaluru|Bangalore|Hyderabad|Ahmedabad|Pune|Jaipur|Lucknow|Kanpur|Patna|Bhopal|Guwahati|Shimla|Srinagar|Bhubaneswar|Cuttack|Visakhapatnam|Vizag|Kochi|Trivandrum|Thiruvananthapuram|Wayanad|Siliguri|Darjeeling|Dehradun|Agartala|Imphal|Ranchi|Raipur)\b",
]


class ONNXEmbeddingEngine:
    """
    ONNX Runtime Multilingual Transformer Embedding Engine.

    Model: paraphrase-multilingual-MiniLM-L12-v2 (50+ languages, 384-d)
    Supports English, Hindi, Tamil, Bengali, Marathi, Telugu, and 44 other languages.

    Inference pipeline (when model files are present):
        text → HuggingFace Tokenizer (WordPiece) → input_ids + attention_mask
             → ONNX Runtime session → token embeddings (batch × seq × 384)
             → mean pooling over non-padding tokens → L2 normalisation → 384-d vector

    Prototype fallback (when models/ files are absent):
        Deterministic hash-space pseudo-embedding — stable but not semantically meaningful.
        Run `uv run python scripts/download_model.py` to enable real inference.
    """

    EMBEDDING_DIM = 384
    MAX_SEQ_LEN = 128

    def __init__(self, model_path: Optional[str] = None, tokenizer_path: Optional[str] = None) -> None:
        self.session: Optional[Any] = None
        self._tokenizer: Optional[Any] = None
        self.model_name = "paraphrase-multilingual-MiniLM-L12-v2"
        self._using_real_model = False

        # Resolve paths: explicit argument > env var > auto-detected models/ directory
        resolved_model = (
            model_path
            or os.getenv("NLP_ONNX_MODEL_PATH")
            or (str(_DEFAULT_ONNX_PATH) if _DEFAULT_ONNX_PATH.exists() else None)
        )
        resolved_tokenizer = (
            tokenizer_path
            or os.getenv("NLP_TOKENIZER_PATH")
            or (str(_DEFAULT_TOKENIZER_PATH) if _DEFAULT_TOKENIZER_PATH.exists() else None)
        )

        if HAS_ONNX and HAS_TOKENIZERS and resolved_model and resolved_tokenizer:
            try:
                self.session = ort.InferenceSession(
                    resolved_model,
                    providers=["CPUExecutionProvider"],
                )
                self._tokenizer = Tokenizer.from_file(resolved_tokenizer)
                self._tokenizer.enable_padding(pad_id=0, pad_token="[PAD]", length=self.MAX_SEQ_LEN)
                self._tokenizer.enable_truncation(max_length=self.MAX_SEQ_LEN)
                self._using_real_model = True
                logger.info(
                    "ONNX Embedding Engine ready: %s (real inference, %d-d)",
                    self.model_name,
                    self.EMBEDDING_DIM,
                )
            except Exception as e:
                logger.warning("Could not load ONNX model or tokenizer: %s — falling back to hash-space embedding", e)
        else:
            missing = []
            if not HAS_ONNX:
                missing.append("onnxruntime")
            if not HAS_TOKENIZERS:
                missing.append("tokenizers")
            if not resolved_model:
                missing.append("models/model.onnx (run scripts/download_model.py)")
            if not resolved_tokenizer:
                missing.append("models/tokenizer.json (run scripts/download_model.py)")
            logger.info(
                "ONNX Embedding Engine: using hash-space fallback. Missing: %s",
                ", ".join(missing),
            )

    @property
    def is_real_model(self) -> bool:
        """True when real ONNX inference is active; False when using hash-space fallback."""
        return self._using_real_model

    def generate_embedding(self, text: str) -> List[float]:
        """
        Generates a normalised 384-d embedding for the input text.

        When real model is loaded:
            Uses proper WordPiece tokenisation → ONNX inference → mean-pooled L2-normalised vector.
            Semantically similar texts (even across languages) will have high cosine similarity.

        Prototype fallback:
            Deterministic hash-space vector seeded by character composition.
            Stable across runs, but does NOT capture semantic similarity.
        """
        if not text:
            return [0.0] * self.EMBEDDING_DIM

        # --- Real ONNX inference path ---
        if self._using_real_model and self._tokenizer is not None and self.session is not None:
            try:
                encoding = self._tokenizer.encode(text)
                input_ids = np.array([encoding.ids], dtype=np.int64)  # (1, 128)
                attention_mask = np.array([encoding.attention_mask], dtype=np.int64)  # (1, 128)
                token_type_ids = np.zeros_like(input_ids)  # (1, 128) — all 0 for single sentence

                outputs = self.session.run(
                    None,
                    {
                        "input_ids": input_ids,
                        "attention_mask": attention_mask,
                        "token_type_ids": token_type_ids,
                    },
                )
                # outputs[0]: (batch=1, seq_len, hidden=384) — token-level embeddings
                token_embeddings = outputs[0][0]  # (seq_len, 384)

                # Mean pooling: average only over non-padding tokens
                mask = attention_mask[0].astype(bool)  # (seq_len,)
                pooled = token_embeddings[mask].mean(axis=0)  # (384,)

                # L2 normalisation so cosine similarity == dot product
                norm = np.linalg.norm(pooled)
                normalised = (pooled / norm if norm > 0 else pooled).tolist()
                return normalised
            except Exception as e:
                logger.error("ONNX inference error: %s — falling back to hash-space embedding", e)

        # --- Hash-space fallback ---
        # Deterministic and stable across runs, but not semantically meaningful.
        seed = sum(ord(c) for c in text)
        np.random.seed(seed % 2**32)
        vec = np.random.randn(self.EMBEDDING_DIM)
        norm = np.linalg.norm(vec)
        return (vec / norm if norm > 0 else vec).tolist()


class NLPExtractor:
    """Parses text to extract event category, negation status, location NER entities, numerical metrics, and ONNX embeddings."""

    def __init__(self, onnx_model_path: Optional[str] = None) -> None:
        self._compiled_negations = [re.compile(pattern, re.IGNORECASE) for pattern in NEGATION_PATTERNS]
        self._compiled_locations = [re.compile(pattern, re.IGNORECASE) for pattern in LOCATION_NER_PATTERNS]
        self.embedding_engine = ONNXEmbeddingEngine(model_path=onnx_model_path)

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
        """Detects if the weather report contains negation of the weather event.

        Uses proximity-based matching: a negation pattern only applies when
        it appears within 8 words of a weather keyword. This prevents false positives
        like 'not just rain but also flooding' from being classified as negated.
        """
        if not text:
            return False

        text_lower = text.lower()
        words = text_lower.split()

        # Find positions of weather proximity keywords
        weather_positions: list[int] = []
        for i, word in enumerate(words):
            if any(kw in word for kw in _WEATHER_PROXIMITY_KEYWORDS):
                weather_positions.append(i)

        for pattern in self._compiled_negations:
            for m in pattern.finditer(text_lower):
                # Find word position of the match
                char_pos = m.start()
                word_pos = len(text_lower[:char_pos].split())
                # Check if within 8 words of any weather keyword
                for wp in weather_positions:
                    if abs(word_pos - wp) <= 8:
                        return True
                # Standalone absolute negation patterns (no proximity needed)
                if pattern.pattern in (
                    r"\bfalse\s+alarm\b",
                    r"\brumou?r\b",
                    r"\bclear\s+sky\b",
                    r"\bsun\s+is\s+out\b",
                    r"\bnormal\s+traffic\b",
                ):
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

        # Rainfall mm or cm
        rain_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:mm|millimeters?|cm|centimeters?)", text, re.IGNORECASE)
        if rain_match:
            val = float(rain_match.group(1))
            if "cm" in rain_match.group(0).lower():
                val = val * 10.0
            metrics["rainfall_mm"] = val

        # Wind speed km/h
        wind_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:km/h|kmh|kmph|knots)", text, re.IGNORECASE)
        if wind_match:
            metrics["wind_speed_kmh"] = float(wind_match.group(1))

        # Temperature deg C
        temp_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:°C|deg C|degrees C|C\b)", text, re.IGNORECASE)
        if temp_match:
            metrics["temperature_c"] = float(temp_match.group(1))

        return metrics

    def compute_embedding(self, text: str) -> List[float]:
        """Computes 384-dimensional ONNX/Neural embedding vector."""
        return self.embedding_engine.generate_embedding(text)

    def extract_entities(self, text: str) -> dict[str, Any]:
        """Extracts structured metadata and neural embedding from text."""
        return {
            "event_category": self.extract_event_category(text),
            "is_negated": self.is_negated(text),
            "locations": self.extract_locations_ner(text),
            "metrics": self.extract_metrics(text),
            "embedding": self.compute_embedding(text),
        }
