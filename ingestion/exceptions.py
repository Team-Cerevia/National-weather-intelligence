"""Domain-specific exceptions for weather intelligence data ingestion."""


class IngestionError(Exception):
    """Raised when an ingestion failure occurs (network, HTTP, timeout, malformed payload)."""

    pass
