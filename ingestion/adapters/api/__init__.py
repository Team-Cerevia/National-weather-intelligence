"""API adapters package for weather data ingestion."""

from ingestion.adapters.api.imd_adapter import ImdAdapter
from ingestion.adapters.api.open_meteo_adapter import OpenMeteoAdapter

__all__ = ["OpenMeteoAdapter", "ImdAdapter"]
