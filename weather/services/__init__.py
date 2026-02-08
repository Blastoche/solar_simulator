"""
Services pour l'app weather.
"""

from .pvgis import (
    PVGISClient,
    fetch_pvgis_data_with_cache,
    get_pvgis_weather_data,
    get_normalized_weather_data,  # ← AJOUTÉ
)

__all__ = [
    'PVGISClient',
    'fetch_pvgis_data_with_cache',
    'get_pvgis_weather_data',      # Ancien (rétrocompatibilité)
    'get_normalized_weather_data',  # ← AJOUTÉ (nouveau avec contrat)
]