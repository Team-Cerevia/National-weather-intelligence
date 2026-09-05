"""Comprehensive offline unit tests for Track A1 Social Media & News RSS Ingestion Adapters."""

import json
from datetime import datetime, timezone
from pathlib import Path

import h3
import pytest

from contracts.weather_report import WeatherReport
from ingestion.adapters.social import (
    NewsRssAdapter,
    SocialAdapter,
)
from ingestion.adapters.social.extractors import (
    detect_language,
    extract_hashtags,
    extract_location_info,
    extract_media_urls,
    extract_urls,
)
from ingestion.adapters.social.social_adapter import SocialMediaAdapter
from ingestion.exceptions import IngestionError

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"


# =====================================================================
# TEST GROUP 1 — HASHTAG EXTRACTION
# =====================================================================


def test_extract_hashtags_multiple_and_single():
    """Verify extraction of multiple and single hashtags from text."""
    text_multi = "Heavy waterlogging near Noida #NoidaRain #IMD #Monsoon2026"
    assert extract_hashtags(text_multi) == ["#NoidaRain", "#IMD", "#Monsoon2026"]

    text_single = "Weather report #IMD"
    assert extract_hashtags(text_single) == ["#IMD"]


def test_extract_hashtags_deduplication_and_ordering():
    """Verify hashtags are deduplicated while preserving first-seen deterministic order."""
    text = "#IMD Heavy rain in Noida #NoidaRain #IMD #Monsoon #NoidaRain"
    assert extract_hashtags(text) == ["#IMD", "#NoidaRain", "#Monsoon"]


def test_extract_hashtags_empty_and_none():
    """Verify empty strings, None, and text without hashtags return empty list."""
    assert extract_hashtags("") == []
    assert extract_hashtags(None) == []
    assert extract_hashtags("Heavy rain in Delhi without tags") == []


def test_extract_hashtags_unicode_and_casing():
    """Verify Devanagari text containing hashtags and case preservation."""
    text = "दिल्ली में आज मौसम #DelhiRain #Monsoon #IMD"
    assert extract_hashtags(text) == ["#DelhiRain", "#Monsoon", "#IMD"]


# =====================================================================
# TEST GROUP 2 — MEDIA EXTRACTION
# =====================================================================


def test_extract_media_urls_image_and_video():
    """Verify extraction of image and video file extensions from text."""
    text = "Photos at https://example.com/flood.jpg and video at https://example.com/storm.mp4"
    media = extract_media_urls(text)
    assert media == ["https://example.com/flood.jpg", "https://example.com/storm.mp4"]


def test_extract_media_urls_structured_payload():
    """Verify media URL extraction from structured payload dictionaries and lists."""
    payload = {
        "media_urls": [
            "https://example.com/img1.png",
            "https://example.com/img1.png",  # duplicate
        ],
        "video": "https://example.com/clip.mp4",
    }
    media = extract_media_urls(payload=payload)
    assert media == ["https://example.com/img1.png", "https://example.com/clip.mp4"]


def test_extract_media_urls_non_media_filtering():
    """Verify non-media URLs (articles/pages) in text are not extracted as media."""
    text = "Read news at https://example.com/article and image at https://example.com/pic.jpeg"
    urls = extract_urls(text)
    assert len(urls) == 2

    media = extract_media_urls(text)
    assert media == ["https://example.com/pic.jpeg"]


# =====================================================================
# TEST GROUP 3 — LANGUAGE DETECTION
# =====================================================================


def test_detect_language_declared():
    """Verify normalization of explicitly declared language codes."""
    assert detect_language(declared_lang="English") == "en"
    assert detect_language(declared_lang="Hindi") == "hi"
    assert detect_language(declared_lang="hinglish") == "hinglish"
    assert detect_language(declared_lang="EN") == "en"


def test_detect_language_heuristics():
    """Verify lightweight heuristic language detection for Devanagari and Hinglish."""
    assert detect_language(text="दिल्ली में आज भारी बारिश") == "hi"
    assert detect_language(text="Noida mein heavy baarish ho rahi hai") == "hinglish"
    assert detect_language(text="Heavy rainfall warning for coastal region") == "en"
    assert detect_language(text="") is None
    assert detect_language(text=None) is None


# =====================================================================
# TEST GROUP 4 — LOCATION EXTRACTION
# =====================================================================


def test_extract_location_info_structured():
    """Verify structured location field parsing and coordinate extraction."""
    payload = {
        "city": "Noida",
        "district": "Gautam Buddha Nagar",
        "state": "Uttar Pradesh",
        "latitude": 28.627,
        "longitude": 77.372,
    }
    loc = extract_location_info(payload=payload)
    assert loc["city"] == "Noida"
    assert loc["district"] == "Gautam Buddha Nagar"
    assert loc["state"] == "Uttar Pradesh"
    assert loc["country"] == "India"
    assert loc["latitude"] == 28.627
    assert loc["longitude"] == 77.372


def test_extract_location_info_nested_and_string():
    """Verify location extraction from nested place objects or comma-separated strings."""
    nested_payload = {"location": {"name": "Mumbai", "state": "Maharashtra", "lat": 19.076, "lon": 72.877}}
    loc_nested = extract_location_info(payload=nested_payload)
    assert loc_nested["city"] == "Mumbai"
    assert loc_nested["state"] == "Maharashtra"
    assert loc_nested["latitude"] == 19.076

    string_payload = {"location": "Jaipur, Rajasthan"}
    loc_str = extract_location_info(payload=string_payload)
    assert loc_str["city"] == "Jaipur"
    assert loc_str["state"] == "Rajasthan"


# =====================================================================
# TEST GROUP 5 — SOCIAL MEDIA ADAPTER & FIXTURE INTEGRATION
# =====================================================================


def test_social_adapter_with_fixture_file():
    """Load social_posts.json fixture and convert all records using SocialAdapter."""
    fixture_path = FIXTURES_DIR / "social_posts.json"
    with open(fixture_path, encoding="utf-8") as f:
        fixture_data = json.load(f)

    adapter = SocialAdapter()
    reports = adapter.parse_payload(fixture_data)

    assert len(reports) == len(fixture_data["social_posts"])

    for report in reports:
        assert isinstance(report, WeatherReport)
        assert report.report_id.startswith("rep_")
        assert report.source_type == "social_media"
        assert report.timestamp.tzinfo == timezone.utc
        assert isinstance(report.text, str)
        assert len(report.text) > 0


def test_social_adapter_canonical_fields_mapping():
    """Verify specific field mappings for a representative fixture record."""
    sample_post = {
        "post_id": "soc_test_99",
        "author": "delhi_wx",
        "created_at": "2026-09-04T10:30:00Z",
        "text": "Heavy waterlogging in Noida Sector 62 #NoidaRain #IMD https://example.com/flood.jpg",
        "city": "Noida",
        "state": "Uttar Pradesh",
        "country": "India",
        "latitude": 28.627,
        "longitude": 77.372,
        "language": "en",
        "url": "https://example.com/post/99",
    }

    adapter = SocialAdapter()
    reports = adapter.parse_payload([sample_post])
    assert len(reports) == 1
    report = reports[0]

    assert report.source_id == "soc_test_99"
    assert report.source == "x_social"
    assert report.source_type == "social_media"
    assert report.timestamp == datetime(2026, 9, 4, 10, 30, tzinfo=timezone.utc)
    assert report.city == "Noida"
    assert report.state == "Uttar Pradesh"
    assert report.country == "India"
    assert report.latitude == 28.627
    assert report.longitude == 77.372
    assert report.url == "https://example.com/post/99"
    assert report.language == "en"
    assert "#NoidaRain" in report.hashtags
    assert "#IMD" in report.hashtags
    assert "https://example.com/flood.jpg" in report.media_urls
    assert report.raw_payload == sample_post


# =====================================================================
# TEST GROUP 6 — H3 DERIVATION & DETERMINISM
# =====================================================================


def test_social_adapter_h3_derivation():
    """Verify auto-derivation of valid H3 cell when latitude and longitude are supplied."""
    post_with_coords = {
        "post_id": "soc_h3_01",
        "created_at": "2026-09-04T10:00:00Z",
        "text": "Flood in Noida Sector 62 #IMD",
        "latitude": 28.627,
        "longitude": 77.372,
    }

    adapter = SocialAdapter()
    reports = adapter.parse_payload([post_with_coords])
    report = reports[0]

    assert report.latitude == 28.627
    assert report.longitude == 77.372
    assert report.h3_cell is not None
    assert h3.is_valid_cell(report.h3_cell)
    assert h3.get_resolution(report.h3_cell) == 7


def test_social_adapter_report_id_determinism():
    """Verify processing the exact same post twice produces identical report_ids."""
    post = {
        "post_id": "soc_det_01",
        "created_at": "2026-09-04T10:00:00Z",
        "text": "Heavy rain in Delhi #IMD",
    }
    adapter = SocialAdapter()
    run1 = adapter.parse_payload([post])[0]
    run2 = adapter.parse_payload([post])[0]

    assert run1.report_id == run2.report_id


def test_social_adapter_timestamp_normalization():
    """Verify non-UTC offset timestamps (e.g. +05:30) are converted to timezone-aware UTC."""
    post_ist = {
        "post_id": "soc_tz_01",
        "created_at": "2026-09-04T15:30:00+05:30",
        "text": "Rain update IST #IMD",
    }
    adapter = SocialAdapter()
    report = adapter.parse_payload([post_ist])[0]

    assert report.timestamp.tzinfo == timezone.utc
    assert report.timestamp == datetime(2026, 9, 4, 10, 0, 0, tzinfo=timezone.utc)


def test_social_adapter_missing_optional_data():
    """Verify posts with missing optional fields (media, location, language) parse cleanly."""
    minimal_post = {
        "post_id": "soc_min_01",
        "created_at": "2026-09-04T10:00:00Z",
        "text": "Rain in Noida #IMD",
    }
    adapter = SocialAdapter()
    report = adapter.parse_payload([minimal_post])[0]

    assert report.media_urls == []
    assert report.latitude is None
    assert report.longitude is None
    assert report.city is None


def test_social_adapter_invalid_inputs():
    """Verify SocialAdapter raises IngestionError on malformed inputs."""
    adapter = SocialAdapter()

    assert adapter.parse_payload(None) == []

    # Non-dict item
    with pytest.raises(IngestionError, match="must be a dict"):
        adapter.parse_payload(["not_a_dict"])  # type: ignore[list-item]

    # Missing text
    with pytest.raises(IngestionError, match="missing required non-empty 'text'"):
        adapter.parse_payload([{"post_id": "123", "created_at": "2026-09-04T10:00:00Z"}])

    # Missing source_id
    with pytest.raises(IngestionError, match="missing required 'source_id'"):
        adapter.parse_payload([{"text": "Rain in Noida", "created_at": "2026-09-04T10:00:00Z"}])

    # Missing timestamp
    with pytest.raises(IngestionError, match="missing required timestamp"):
        adapter.parse_payload([{"post_id": "123", "text": "Rain in Noida"}])

    # Invalid coordinates
    with pytest.raises(IngestionError, match="Invalid social post coordinates"):
        adapter.parse_payload(
            [
                {
                    "post_id": "123",
                    "text": "Rain",
                    "created_at": "2026-09-04T10:00:00Z",
                    "latitude": 95.0,
                    "longitude": 77.0,
                }
            ]
        )


# =====================================================================
# TEST GROUP 7 — NEWS RSS ADAPTER (RSS 2.0 & ATOM OFFLINE TESTS)
# =====================================================================


def test_news_rss_adapter_rss20_offline_parsing():
    """Verify parsing of offline RSS 2.0 XML with title, description, link, pubDate, and enclosure."""
    rss_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
        <channel>
            <title>Weather News India</title>
            <link>https://example.com/news</link>
            <description>Latest weather alerts</description>
            <language>en</language>
            <item>
                <title>IMD issues Red Alert for extreme rainfall in Mumbai</title>
                <description>Continuous downpour has caused heavy flooding across Mumbai lowlands. &lt;a href="#"&gt;Read more&lt;/a&gt;</description>
                <link>https://example.com/news/mumbai-flood-alert</link>
                <pubDate>Fri, 04 Sep 2026 09:30:00 GMT</pubDate>
                <guid>news_item_2001</guid>
                <enclosure url="https://example.com/news/flood.jpg" type="image/jpeg"/>
            </item>
        </channel>
    </rss>"""

    adapter = NewsRssAdapter()
    reports = adapter.parse_feed_xml(rss_xml)

    assert len(reports) == 1
    report = reports[0]

    assert isinstance(report, WeatherReport)
    assert report.source == "news_rss"
    assert report.source_type == "news"
    assert report.source_id == "news_item_2001"
    assert report.timestamp == datetime(2026, 9, 4, 9, 30, tzinfo=timezone.utc)
    assert "IMD issues Red Alert" in report.text
    assert "Continuous downpour" in report.text
    assert "<a href" not in report.text
    assert report.url == "https://example.com/news/mumbai-flood-alert"
    assert "https://example.com/news/flood.jpg" in report.media_urls


def test_news_rss_adapter_atom_offline_parsing():
    """Verify parsing of offline Atom XML with entry, summary, link href, id, and updated tags."""
    atom_xml = """<?xml version="1.0" encoding="utf-8"?>
    <feed xmlns="http://www.w3.org/2005/Atom">
        <title>India Weather Wire</title>
        <entry>
            <id>atom_entry_3001</id>
            <title>Severe Heatwave Conditions Persist Across Rajasthan</title>
            <summary>Temperatures cross 45C in Barmer with severe heatwave warnings.</summary>
            <link href="https://example.com/atom/rajasthan-heatwave"/>
            <updated>2026-09-04T11:00:00Z</updated>
        </entry>
    </feed>"""

    adapter = NewsRssAdapter()
    reports = adapter.parse_feed_xml(atom_xml)

    assert len(reports) == 1
    report = reports[0]

    assert report.source_id == "atom_entry_3001"
    assert report.source_type == "news"
    assert report.timestamp == datetime(2026, 9, 4, 11, 0, tzinfo=timezone.utc)
    assert "Severe Heatwave Conditions" in report.text
    assert report.url == "https://example.com/atom/rajasthan-heatwave"


def test_news_rss_adapter_date_parsing_variations():
    """Verify parsing of RFC 822, RFC 1123, and ISO 8601 RSS date strings into UTC."""
    adapter = NewsRssAdapter()

    dt1 = adapter.parse_rss_date("Fri, 04 Sep 2026 09:30:00 GMT")
    assert dt1 == datetime(2026, 9, 4, 9, 30, tzinfo=timezone.utc)

    dt2 = adapter.parse_rss_date("Fri, 04 Sep 2026 15:00:00 +0530")
    assert dt2 == datetime(2026, 9, 4, 9, 30, tzinfo=timezone.utc)

    dt3 = adapter.parse_rss_date("2026-09-04T09:30:00Z")
    assert dt3 == datetime(2026, 9, 4, 9, 30, tzinfo=timezone.utc)


def test_news_rss_adapter_weather_relevance_filtering():
    """Verify that weather-related RSS articles are parsed while unrelated articles are filtered out."""
    mixed_rss = """<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
        <channel>
            <item>
                <title>Heavy monsoon rainfall causes waterlogging in Noida</title>
                <description>Roads flooded near Sector 62 underpass.</description>
                <pubDate>Fri, 04 Sep 2026 09:30:00 GMT</pubDate>
                <guid>rss_weather_1</guid>
            </item>
            <item>
                <title>Stock market hits new record high today</title>
                <description>Financial markets rally as technology stocks surge.</description>
                <pubDate>Fri, 04 Sep 2026 10:00:00 GMT</pubDate>
                <guid>rss_unrelated_1</guid>
            </item>
        </channel>
    </rss>"""

    adapter = NewsRssAdapter()
    reports = adapter.parse_feed_xml(mixed_rss, filter_weather_relevance=True)

    assert len(reports) == 1
    assert reports[0].source_id == "rss_weather_1"


def test_news_rss_adapter_report_id_determinism():
    """Verify parsing identical RSS articles twice produces identical report_ids."""
    rss_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
        <channel>
            <item>
                <title>Cyclone alert in coastal Odisha</title>
                <description>Strong winds expected today.</description>
                <pubDate>Fri, 04 Sep 2026 09:30:00 GMT</pubDate>
                <guid>rss_det_01</guid>
            </item>
        </channel>
    </rss>"""

    adapter = NewsRssAdapter()
    run1 = adapter.parse_feed_xml(rss_xml)[0]
    run2 = adapter.parse_feed_xml(rss_xml)[0]

    assert run1.report_id == run2.report_id


def test_news_rss_adapter_malformed_xml_handling():
    """Verify handling of malformed XML syntax and items missing dates/titles."""
    adapter = NewsRssAdapter()

    with pytest.raises(IngestionError, match="Malformed RSS XML feed"):
        adapter.parse_feed_xml("<unclosed_tag>rss item")

    no_date_rss = """<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
        <channel>
            <item>
                <title>Heavy rain in Noida</title>
                <description>Waterlogging on roads.</description>
            </item>
        </channel>
    </rss>"""
    assert adapter.parse_feed_xml(no_date_rss) == []


def test_social_media_adapter_alias():
    """Verify SocialMediaAdapter alias behaves identically to SocialAdapter."""
    adapter = SocialMediaAdapter()
    assert isinstance(adapter, SocialAdapter)
