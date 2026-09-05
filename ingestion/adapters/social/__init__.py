"""Social media and news ingestion adapters package."""

from ingestion.adapters.social.extractors import (
    detect_language,
    extract_hashtags,
    extract_media_urls,
    extract_urls,
)
from ingestion.adapters.social.news_rss_adapter import NewsRssAdapter
from ingestion.adapters.social.social_adapter import SocialAdapter

__all__ = [
    "SocialAdapter",
    "NewsRssAdapter",
    "extract_hashtags",
    "extract_urls",
    "extract_media_urls",
    "detect_language",
]
