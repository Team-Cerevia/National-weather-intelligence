"""Extractor functions for social media and news data parsing.

Provides deterministic, lightweight helpers for hashtag extraction, media URL parsing,
language normalization, and structured location extraction without external ML or network calls.
"""

import re
from typing import Any

# Regular expressions for hashtags and URLs
HASHTAG_REGEX = re.compile(r"#\w+", re.UNICODE)
URL_REGEX = re.compile(r"https?://[^\s]+", re.IGNORECASE)
MEDIA_FILE_EXT_REGEX = re.compile(r"\.(?:jpg|jpeg|png|gif|mp4|mov|webm)(?:\?.*)?$", re.IGNORECASE)

# Common Hinglish/Hindi romanized indicators
HINGLISH_KEYWORDS = re.compile(
    r"\b(mein|hai|baarish|barish|paani|pani|tez|ho|rhi|rahi|bhai|doob|rha|gaya|gayi|se|ko|par|bohot|bahut)\b",
    re.IGNORECASE,
)


def extract_hashtags(text: str | None) -> list[str]:
    """Extracts unique hashtags from raw text content preserving leading '#' and deterministic ordering."""
    if not text or not isinstance(text, str):
        return []
    matches = HASHTAG_REGEX.findall(text)
    seen: set[str] = set()
    result: list[str] = []
    for tag in matches:
        if tag not in seen:
            seen.add(tag)
            result.append(tag)
    return result


def extract_urls(text: str | None) -> list[str]:
    """Extracts all http/https URLs from raw text."""
    if not text or not isinstance(text, str):
        return []
    matches = URL_REGEX.findall(text)
    seen: set[str] = set()
    result: list[str] = []
    for url in matches:
        cleaned_url = url.rstrip(".,;!?)")
        if cleaned_url and cleaned_url not in seen:
            seen.add(cleaned_url)
            result.append(cleaned_url)
    return result


def extract_media_urls(
    text: str | None = None,
    payload: dict[str, Any] | list[Any] | str | None = None,
) -> list[str]:
    """Extracts image/video media URLs from structured payload objects and text content.

    Supports payload fields: media, media_urls, image, images, video, videos, url.
    Avoids duplicates and preserves deterministic ordering.
    """
    media_list: list[str] = []
    seen: set[str] = set()

    def _add_url(u: Any) -> None:
        if isinstance(u, str) and u.strip():
            url_str = u.strip()
            if url_str not in seen:
                seen.add(url_str)
                media_list.append(url_str)

    if isinstance(payload, str):
        _add_url(payload)
    elif isinstance(payload, list):
        for item in payload:
            if isinstance(item, str):
                _add_url(item)
            elif isinstance(item, dict):
                _add_url(item.get("url") or item.get("src") or item.get("link"))
    elif isinstance(payload, dict):
        for key in ("media_urls", "media", "images", "image", "videos", "video", "url"):
            val = payload.get(key)
            if isinstance(val, str):
                if key == "url" and not MEDIA_FILE_EXT_REGEX.search(val):
                    continue
                _add_url(val)
            elif isinstance(val, list):
                for item in val:
                    if isinstance(item, str):
                        _add_url(item)
                    elif isinstance(item, dict):
                        _add_url(item.get("url") or item.get("src") or item.get("link"))

    if text:
        text_urls = extract_urls(text)
        for url in text_urls:
            if MEDIA_FILE_EXT_REGEX.search(url):
                _add_url(url)

    return media_list


def detect_language(text: str | None = None, declared_lang: str | None = None) -> str | None:
    """Normalizes declared language string or performs lightweight heuristic detection.

    Supports 'en', 'hi', 'hinglish'.
    """
    if declared_lang and isinstance(declared_lang, str) and declared_lang.strip():
        lang_clean = declared_lang.strip().lower()
        if lang_clean in ("en", "english"):
            return "en"
        if lang_clean in ("hi", "hindi"):
            return "hi"
        if lang_clean in ("hinglish", "hi-en", "hin-eng"):
            return "hinglish"
        return lang_clean

    if not text or not isinstance(text, str) or not text.strip():
        return None

    if re.search(r"[\u0900-\u097F]", text):
        return "hi"

    if HINGLISH_KEYWORDS.search(text):
        return "hinglish"

    return "en"


def extract_location_info(
    payload: dict[str, Any] | None = None,
    city: str | None = None,
    state: str | None = None,
    district: str | None = None,
    country: str | None = None,
) -> dict[str, Any]:
    """Extracts and normalizes structured location fields from payload dicts or explicit arguments.

    Returns a normalized location dictionary containing city, district, state, country, latitude, longitude.
    """
    res: dict[str, Any] = {
        "city": city.strip() if isinstance(city, str) and city.strip() else None,
        "district": district.strip() if isinstance(district, str) and district.strip() else None,
        "state": state.strip() if isinstance(state, str) and state.strip() else None,
        "country": country.strip() if isinstance(country, str) and country.strip() else None,
        "latitude": None,
        "longitude": None,
    }

    if payload and isinstance(payload, dict):
        for field_name in ("city", "district", "state", "country"):
            val = payload.get(field_name)
            if not res[field_name] and isinstance(val, str) and val.strip():
                res[field_name] = val.strip()

        for place_key in ("location", "place", "geo"):
            place_val = payload.get(place_key)
            if isinstance(place_val, dict):
                if not res["city"]:
                    c_val = place_val.get("city") or place_val.get("name")
                    if isinstance(c_val, str) and c_val.strip():
                        res["city"] = c_val.strip()
                if not res["state"]:
                    s_val = place_val.get("state") or place_val.get("region")
                    if isinstance(s_val, str) and s_val.strip():
                        res["state"] = s_val.strip()
                if not res["country"]:
                    co_val = place_val.get("country")
                    if isinstance(co_val, str) and co_val.strip():
                        res["country"] = co_val.strip()
                lat_val = place_val.get("latitude") or place_val.get("lat")
                lon_val = place_val.get("longitude") or place_val.get("lon") or place_val.get("lng")
                if res["latitude"] is None and isinstance(lat_val, (int, float)):
                    res["latitude"] = float(lat_val)
                if res["longitude"] is None and isinstance(lon_val, (int, float)):
                    res["longitude"] = float(lon_val)
            elif isinstance(place_val, str) and place_val.strip() and not res["city"]:
                parts = [p.strip() for p in place_val.split(",") if p.strip()]
                if len(parts) >= 2:
                    res["city"] = parts[0]
                    if not res["state"]:
                        res["state"] = parts[1]
                elif len(parts) == 1:
                    res["city"] = parts[0]

        lat_top = payload.get("latitude") or payload.get("lat")
        lon_top = payload.get("longitude") or payload.get("lon") or payload.get("lng")
        if res["latitude"] is None and isinstance(lat_top, (int, float)):
            res["latitude"] = float(lat_top)
        if res["longitude"] is None and isinstance(lon_top, (int, float)):
            res["longitude"] = float(lon_top)

    if (res["city"] or res["state"]) and not res["country"]:
        res["country"] = "India"

    return res
