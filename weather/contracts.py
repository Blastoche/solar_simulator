"""
Contrats de données pour le module weather.
Définit les structures de données garanties par le module.
"""

from dataclasses import dataclass
from typing import Dict, Any
import pandas as pd


@dataclass
class WeatherMetadata:
    """
    Métadonnées accompagnant les données météo.
    
    Attributes:
        source: Source des données ('api', 'cache', 'fallback')
        irradiation_annuelle: Irradiation totale (kWh/m²/an)
        latitude: Latitude du site
        longitude: Longitude du site
        api_version: Version API utilisée (ex: 'PVGIS 5.3')
        retrieved_at: Timestamp de récupération
        cached_until: Date expiration cache (optionnel)
    """
    source: str
    irradiation_annuelle: float
    latitude: float
    longitude: float
    api_version: str
    retrieved_at: str
    cached_until: str = None


def validate_weather_dataframe(df: pd.DataFrame) -> bool:
    """
    Valide qu'un DataFrame météo respecte le contrat.
    
    Contrat :
        - 8760 lignes exactement
        - Colonnes obligatoires : ['timestamp', 'ghi', 'temperature']
        - Colonnes optionnelles : ['dni', 'dhi', 'vitesse_vent', ...]
        - Pas de valeurs manquantes sur colonnes obligatoires
        - GHI >= 0
    
    Args:
        df: DataFrame à valider
    
    Returns:
        True si valide
    
    Raises:
        ValueError: Si non-conforme au contrat
    """
    # Vérifier nombre de lignes
    if len(df) != 8760:
        raise ValueError(f"DataFrame doit avoir 8760 lignes, a {len(df)}")
    
    # Vérifier colonnes obligatoires
    required_cols = ['timestamp', 'ghi', 'temperature']
    missing = set(required_cols) - set(df.columns)
    if missing:
        raise ValueError(f"Colonnes manquantes : {missing}")
    
    # Vérifier pas de NaN
    if df[required_cols].isna().any().any():
        raise ValueError("Valeurs manquantes détectées dans colonnes obligatoires")
    
    # Vérifier GHI >= 0
    if (df['ghi'] < 0).any():
        raise ValueError("GHI contient des valeurs négatives")
    
    return True


def create_weather_metadata(
    source: str,
    df: pd.DataFrame,
    latitude: float,
    longitude: float,
    api_version: str = "PVGIS 5.3",
    retrieved_at: str = None,
    cached_until: str = None
) -> WeatherMetadata:
    """
    Crée les métadonnées standardisées.
    
    Args:
        source: 'api', 'cache', ou 'fallback'
        df: DataFrame avec données météo
        latitude: Latitude
        longitude: Longitude
        api_version: Version API
        retrieved_at: Timestamp ISO
        cached_until: Expiration cache ISO
    
    Returns:
        WeatherMetadata
    """
    from datetime import datetime
    
    # Calculer irradiation annuelle
    irradiation = df['ghi'].sum() / 1000  # W/m² → kWh/m²
    
    if retrieved_at is None:
        retrieved_at = datetime.now().isoformat()
    
    return WeatherMetadata(
        source=source,
        irradiation_annuelle=round(irradiation, 2),
        latitude=latitude,
        longitude=longitude,
        api_version=api_version,
        retrieved_at=retrieved_at,
        cached_until=cached_until
    )