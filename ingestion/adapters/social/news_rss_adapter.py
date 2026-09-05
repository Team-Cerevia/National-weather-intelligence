"""News RSS Feed adapter for fetching and parsing weather news alerts into canonical WeatherReport objects."""

import email.utils
import html
import re
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
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

# Regex to strip HTML tags from RSS item descriptions
HTML_TAG_REGEX = re.compile(r"<[^>]+>")

# Weather relevance keywords for deterministic filtering
WEATHER_KEYWORDS = (
    "weather",
    "rain",
    "rainfall",
    "flood",
    "flooding",
    "monsoon",
    "heatwave",
    "heat wave",
    "cyclone",
    "storm",
    "thunderstorm",
    "fog",
    "dust storm",
    "strong winds",
    "weather alert",
    "imd",
    "temperature",
    "precipitation",
    "hailstorm",
    "waterlogging",
    "downpour",
    "landslide",
    "cloudburst",
)


def strip_html_tags(text: str) -> str:
    """Strips HTML tags and unescapes HTML entities from text content."""
    if not text:
        return ""
    clean_text = HTML_TAG_REGEX.sub(" ", text)
    clean_text = html.unescape(clean_text)
    return re.sub(r"\s+", " ", clean_text).strip()


class NewsRssAdapter(BaseWeatherAdapter):
    """Adapter for fetching and parsing RSS 2.0 and Atom weather news feeds."""

    def fetch_feed(self, url: str, timeout: int = 10) -> str:
        """Fetches raw RSS/Atom feed content over HTTP.

        Raises IngestionError on network, HTTP status, or timeout errors.
        """
        if not url or not isinstance(url, str) or not url.strip():
            raise IngestionError("Feed URL must be a non-empty string.")

        req = urllib.request.Request(
            url.strip(),
            headers={"User-Agent": "NationalWeatherIntelligencePlatform/1.0"},
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                content_bytes = response.read()
                return content_bytes.decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            raise IngestionError(f"News RSS HTTP error {e.code} for '{url}': {e.reason}") from e
        except urllib.error.URLError as e:
            raise IngestionError(f"News RSS connection error for '{url}': {e.reason}") from e
        except Exception as e:
            raise IngestionError(f"Failed to fetch RSS feed from '{url}': {e}") from e

    def fetch_and_parse(
        self,
        url: str | None = None,
        xml_content: str | bytes | None = None,
        filter_weather_relevance: bool = True,
        **kwargs: Any,
    ) -> list[WeatherReport]:
        """Fetches live RSS feeds or accepts raw XML content/fixtures and parses them into WeatherReport instances.

        Args:
            url: RSS/Atom feed URL.
            xml_content: Raw XML string/bytes or mock fixture data for offline testing.
            filter_weather_relevance: Whether to filter out non-weather articles.
            **kwargs: Additional parameters (e.g. raw_xml, feed_data).

        Returns:
            List of canonical WeatherReport instances.
        """
        raw_xml = xml_content if xml_content is not None else kwargs.get("raw_xml")
        raw_fixture = kwargs.get("feed_data") or kwargs.get("news_items")

        if raw_fixture is not None:
            return self.parse_fixture_dict(raw_fixture, filter_weather_relevance=filter_weather_relevance)

        if raw_xml is not None:
            return self.parse_feed_xml(raw_xml, filter_weather_relevance=filter_weather_relevance)

        if url:
            fetched_xml = self.fetch_feed(url)
            return self.parse_feed_xml(fetched_xml, filter_weather_relevance=filter_weather_relevance)

        return []

    def parse_feed_xml(
        self, xml_content: str | bytes | dict[str, Any], filter_weather_relevance: bool = True
    ) -> list[WeatherReport]:
        """Parses raw RSS 2.0 or Atom XML feed content into canonical WeatherReport instances."""
        if isinstance(xml_content, (dict, list)):
            return self.parse_fixture_dict(xml_content, filter_weather_relevance=filter_weather_relevance)

        if not xml_content:
            return []

        xml_bytes = xml_content.encode("utf-8") if isinstance(xml_content, str) else xml_content
        try:
            root = ET.fromstring(xml_bytes)
        except ET.ParseError as e:
            raise IngestionError(f"Malformed RSS XML feed: {e}") from e

        # Extract feed-level language if declared
        feed_lang = None
        lang_elem = root.find(".//language")
        if lang_elem is not None and lang_elem.text:
            feed_lang = lang_elem.text.strip()

        # Find items (<item> in RSS 2.0 or <entry> in Atom)
        items = root.findall(".//item")
        if not items:
            items = root.findall(".//{http://www.w3.org/2005/Atom}entry")
            if not items:
                items = root.findall(".//entry")

        reports: list[WeatherReport] = []
        seen_report_ids: set[str] = set()

        for item in items:
            try:
                report = self._parse_xml_item(
                    item, feed_lang=feed_lang, filter_weather_relevance=filter_weather_relevance
                )
                if report and report.report_id not in seen_report_ids:
                    seen_report_ids.add(report.report_id)
                    reports.append(report)
            except Exception:
                continue

        return reports

    def _parse_xml_item(
        self, item_elem: ET.Element, feed_lang: str | None = None, filter_weather_relevance: bool = True
    ) -> WeatherReport | None:
        """Parses a single XML element (<item> or <entry>) into a WeatherReport."""

        def get_child_text(tag_name: str) -> str | None:
            for child in item_elem:
                clean_tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
                if clean_tag.lower() == tag_name.lower() and child.text:
                    return child.text.strip()
            return None

        title = get_child_text("title") or ""
        description_raw = get_child_text("description") or get_child_text("summary") or get_child_text("content") or ""
        clean_desc = strip_html_tags(description_raw)
        clean_title = strip_html_tags(title)

        if not clean_title and not clean_desc:
            raise IngestionError("RSS item missing both title and description.")

        full_text = f"{clean_title}. {clean_desc}".strip(" .") if clean_desc else clean_title

        if filter_weather_relevance:
            text_lower = full_text.lower()
            tags_in_text = extract_hashtags(full_text)
            is_relevant = any(kw in text_lower for kw in WEATHER_KEYWORDS) or len(tags_in_text) > 0
            if not is_relevant:
                return None

        link = get_child_text("link")
        if not link:
            for child in item_elem:
                clean_tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
                if clean_tag.lower() == "link":
                    link = child.attrib.get("href")
                    if link:
                        break
        link_str = link.strip() if isinstance(link, str) and link.strip() else None

        guid = get_child_text("guid") or get_child_text("id") or link_str
        if not guid:
            identity = f"{clean_title}:{link_str or ''}"
            guid = f"news_{hash(identity)}"
        source_id = str(guid).strip()

        pub_date_str = (
            get_child_text("pubDate")
            or get_child_text("published")
            or get_child_text("updated")
            or get_child_text("date")
        )
        if not pub_date_str:
            raise IngestionError("RSS item missing publication date.")

        dt_utc = self.parse_rss_date(pub_date_str)
        source = "news_rss"
        source_type = "news"

        hashtags = extract_hashtags(full_text)
        media_list = extract_media_urls(text=full_text)
        for child in item_elem:
            clean_tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
            if clean_tag.lower() in ("enclosure", "content", "thumbnail"):
                m_url = child.attrib.get("url")
                if m_url and isinstance(m_url, str) and m_url.strip() not in media_list:
                    media_list.append(m_url.strip())

        lang = detect_language(text=full_text, declared_lang=feed_lang)
        location_info = extract_location_info(payload={})
        report_id = self.generate_deterministic_report_id(source, source_id, dt_utc)

        return WeatherReport(
            report_id=report_id,
            source=source,
            source_type=source_type,
            source_id=source_id,
            timestamp=dt_utc,
            text=full_text,
            latitude=location_info.get("latitude"),
            longitude=location_info.get("longitude"),
            city=location_info.get("city"),
            district=location_info.get("district"),
            state=location_info.get("state"),
            country=location_info.get("country"),
            url=link_str,
            media_urls=media_list,
            hashtags=hashtags,
            language=lang,
            raw_payload={
                "title": clean_title,
                "description": clean_desc,
                "link": link_str,
                "guid": source_id,
                "pubDate": pub_date_str,
            },
        )

    def parse_rss_date(self, date_str: str) -> datetime:
        """Parses RFC 822, RFC 1123, or ISO 8601 RSS date strings into timezone-aware UTC datetime."""
        if not date_str or not isinstance(date_str, str) or not date_str.strip():
            raise IngestionError("Date string is empty or invalid.")

        raw_str = date_str.strip()

        try:
            parsed_tuple = email.utils.parsedate_to_datetime(raw_str)
            if parsed_tuple is not None:
                return self.ensure_utc_datetime(parsed_tuple, assume_utc_if_naive=True)
        except Exception:
            pass

        try:
            return self.ensure_utc_datetime(raw_str, assume_utc_if_naive=True)
        except Exception as e:
            raise IngestionError(f"Failed to parse RSS publication date '{date_str}': {e}") from e

    def parse_fixture_dict(
        self, fixture_data: dict[str, Any] | list[Any], filter_weather_relevance: bool = True
    ) -> list[WeatherReport]:
        """Parses mock fixture dictionaries or lists for offline testing."""
        if isinstance(fixture_data, dict):
            items_list = fixture_data.get("news_items") or fixture_data.get("items") or [fixture_data]
        elif isinstance(fixture_data, list):
            items_list = fixture_data
        else:
            return []

        reports: list[WeatherReport] = []
        for item in items_list:
            if not isinstance(item, dict):
                continue
            title = strip_html_tags(str(item.get("title") or ""))
            desc = strip_html_tags(str(item.get("description") or item.get("summary") or ""))
            full_text = f"{title}. {desc}".strip(" .") if desc else title

            if not full_text:
                continue

            if filter_weather_relevance:
                text_lower = full_text.lower()
                tags_in_text = extract_hashtags(full_text)
                is_relevant = any(kw in text_lower for kw in WEATHER_KEYWORDS) or len(tags_in_text) > 0
                if not is_relevant:
                    continue

            guid = str(item.get("guid") or item.get("id") or item.get("link") or hash(full_text)).strip()
            pub_date_str = str(item.get("pubDate") or item.get("published") or item.get("updated") or "").strip()
            if not pub_date_str:
                continue

            dt_utc = self.parse_rss_date(pub_date_str)
            source = str(item.get("source") or "news_rss").strip().lower()
            source_type = "news"

            link = str(item.get("link") or "").strip() or None
            hashtags = extract_hashtags(full_text)
            media_list = extract_media_urls(text=full_text, payload=item)
            lang = detect_language(text=full_text, declared_lang=item.get("language"))
            location_info = extract_location_info(payload=item)

            report_id = self.generate_deterministic_report_id(source, guid, dt_utc)

            reports.append(
                WeatherReport(
                    report_id=report_id,
                    source=source,
                    source_type=source_type,
                    source_id=guid,
                    timestamp=dt_utc,
                    text=full_text,
                    latitude=location_info.get("latitude"),
                    longitude=location_info.get("longitude"),
                    city=location_info.get("city"),
                    district=location_info.get("district"),
                    state=location_info.get("state"),
                    country=location_info.get("country"),
                    url=link,
                    media_urls=media_list,
                    hashtags=hashtags,
                    language=lang,
                    raw_payload=item,
                )
            )

        return reports
