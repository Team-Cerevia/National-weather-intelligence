"""Social Media adapter for converting social posts and weather hashtags into canonical WeatherReport objects."""

from typing import Any

from contracts.weather_report import WeatherReport
from ingestion.adapters.base import BaseWeatherAdapter
from ingestion.adapters.social.extractors import (
    detect_language,
    extract_hashtags,
    extract_location_info,
    extract_media_urls,
)
from ingestion.exceptions import IngestionError


class SocialAdapter(BaseWeatherAdapter):
    """Adapter for ingesting social media posts (e.g. X/Twitter, Hashtags #IMD).

    Converts raw social post dictionaries into canonical WeatherReport contract objects
    using deterministic ID generation and extractor helpers.
    """

    def fetch_and_parse(
        self, posts: list[dict[str, Any]] | dict[str, Any] | None = None, **kwargs: Any
    ) -> list[WeatherReport]:
        """Fetches raw social media posts from input parameters or mock payloads and parses them.

        Args:
            posts: Single post dictionary or list of post dictionaries.
            **kwargs: Additional parameters (e.g. raw_posts).

        Returns:
            List of validated canonical WeatherReport instances.
        """
        raw_data = posts if posts is not None else kwargs.get("raw_posts")
        if raw_data is None:
            return []

        return self.parse_payload(raw_data)

    def parse_payload(self, raw_posts: list[dict[str, Any]] | dict[str, Any] | None) -> list[WeatherReport]:
        """Parses raw social post payloads (list or single dict) into canonical WeatherReport objects.

        Raises IngestionError if input is malformed or unparseable.
        """
        if raw_posts is None:
            return []

        if isinstance(raw_posts, dict):
            if "social_posts" in raw_posts and isinstance(raw_posts["social_posts"], list):
                posts_list = raw_posts["social_posts"]
            else:
                posts_list = [raw_posts]
        elif isinstance(raw_posts, list):
            posts_list = raw_posts
        else:
            raise IngestionError(f"Raw posts payload must be a list or dict, got {type(raw_posts).__name__}")

        reports: list[WeatherReport] = []
        for post in posts_list:
            if not isinstance(post, dict):
                raise IngestionError(f"Each social post payload item must be a dict, got {type(post).__name__}")
            report = self.parse_post(post)
            reports.append(report)

        return reports

    def parse_post(self, raw_post: dict[str, Any]) -> WeatherReport:
        """Parses a single social post dictionary into a canonical WeatherReport instance.

        Validates required fields, extracts hashtags/media/location/language, and normalizes
        timestamps and deterministic report IDs.
        """
        if not isinstance(raw_post, dict):
            raise IngestionError("Social post item must be a dictionary.")

        # Extract text content
        text = raw_post.get("text") or raw_post.get("content") or raw_post.get("caption")
        if not text or not isinstance(text, str) or not text.strip():
            raise IngestionError("Social post missing required non-empty 'text' or 'content' field.")

        # Extract source_id
        source_id_raw = (
            raw_post.get("source_id") or raw_post.get("post_id") or raw_post.get("id") or raw_post.get("tweet_id")
        )
        if source_id_raw is None or str(source_id_raw).strip() == "":
            raise IngestionError("Social post missing required 'source_id' or 'post_id'.")
        source_id = str(source_id_raw).strip()

        # Extract timestamp
        ts_val = (
            raw_post.get("timestamp") or raw_post.get("created_at") or raw_post.get("pubDate") or raw_post.get("date")
        )
        if ts_val is None:
            raise IngestionError("Social post missing required timestamp or created_at field.")

        try:
            dt_utc = self.ensure_utc_datetime(ts_val, assume_utc_if_naive=True)
        except Exception as e:
            raise IngestionError(f"Social post timestamp parsing failed for '{ts_val}': {e}") from e

        # Source metadata
        source = str(raw_post.get("source") or "x_social").strip().lower()
        source_type = "social_media"

        # URL reference
        url = raw_post.get("url") or raw_post.get("link")
        url_str = str(url).strip() if isinstance(url, str) and url.strip() else None

        # Extractor integrations
        extracted_tags = extract_hashtags(text)
        payload_tags = raw_post.get("hashtags")
        hashtags: list[str] = list(extracted_tags)
        if isinstance(payload_tags, list):
            for tag in payload_tags:
                if isinstance(tag, str) and tag.strip() and tag.strip() not in hashtags:
                    hashtags.append(tag.strip())

        media_urls = extract_media_urls(text=text, payload=raw_post)
        lang = detect_language(text=text, declared_lang=raw_post.get("language") or raw_post.get("lang"))
        location_info = extract_location_info(payload=raw_post)

        # Coordinate extraction & validation
        lat = location_info.get("latitude")
        lon = location_info.get("longitude")
        if lat is not None or lon is not None:
            try:
                self.validate_coordinates(lat, lon)
            except ValueError as e:
                raise IngestionError(f"Invalid social post coordinates: {e}") from e

        # Deterministic Report ID
        report_id = self.generate_deterministic_report_id(source, source_id, dt_utc)

        try:
            return WeatherReport(
                report_id=report_id,
                source=source,
                source_type=source_type,
                source_id=source_id,
                timestamp=dt_utc,
                text=text.strip(),
                latitude=lat,
                longitude=lon,
                city=location_info.get("city"),
                district=location_info.get("district"),
                state=location_info.get("state"),
                country=location_info.get("country"),
                url=url_str,
                media_urls=media_urls,
                hashtags=hashtags,
                language=lang,
                raw_payload=raw_post,
            )
        except Exception as e:
            raise IngestionError(f"WeatherReport validation failed for social post {source_id}: {e}") from e


# Alias for backward compatibility / clear naming
SocialMediaAdapter = SocialAdapter
