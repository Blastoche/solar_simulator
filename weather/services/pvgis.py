"""
Client API PVGIS pour récupérer les données d'irradiation solaire.

Documentation PVGIS : https://joint-research-centre.ec.europa.eu/pvgis-online-tool/pvgis-data-download_en
API Documentation : https://joint-research-centre.ec.europa.eu/pvgis-tools/pvgis-user-manual_en
"""

import requests
import pandas as pd
import json
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


class PVGISClient:
    """
    Client pour l'API PVGIS (Photovoltaic Geographical Information System).
    
    PVGIS est une API gratuite du JRC (Joint Research Centre) de la Commission Européenne.
    Elle fournit des données d'irradiation solaire pour l'Europe, l'Afrique, l'Asie et les Amériques.
    """
    
    # URL de base de l'API PVGIS
    BASE_URL = "https://re.jrc.ec.europa.eu/api/v5_2"
    
    # Bases de données disponibles
    DATABASES = {
        'PVGIS-SARAH2': 'Europe, Afrique, Asie (2005-2020)',
        'PVGIS-SARAH': 'Europe, Afrique (2005-2016)',
        'PVGIS-NSRDB': 'Amériques (1998-2020)',
        'PVGIS-ERA5': 'Mondial (2005-2020)',
        'PVGIS-COSMO': 'Europe (2007-2016)',
    }
    
    def __init__(self, timeout: int = 30):
        """
        Initialise le client PVGIS.
        
        Args:
            timeout: Timeout des requêtes HTTP en secondes
        """
        self.timeout = timeout
        self.session = requests.Session()
    
    def get_tmy_data(
        self,
        latitude: float,
        longitude: float,
        database: str = 'PVGIS-SARAH2',
        **kwargs
    ) -> Dict:
        """
        Récupère les données TMY (Typical Meteorological Year).
        
        Le TMY représente une année météorologique typique basée sur des données historiques.
        C'est idéal pour les simulations de production solaire.
        
        Args:
            latitude: Latitude en degrés décimaux (-90 à 90)
            longitude: Longitude en degrés décimaux (-180 à 180)
            database: Base de données PVGIS à utiliser
            **kwargs: Paramètres supplémentaires (startyear, endyear, etc.)
            
        Returns:
            dict: Données TMY avec irradiation horaire
            
        Raises:
            requests.RequestException: Erreur lors de l'appel API
            ValueError: Coordonnées invalides
        """
        # Validation des coordonnées
        if not -90 <= latitude <= 90:
            raise ValueError(f"Latitude invalide: {latitude} (doit être entre -90 et 90)")
        if not -180 <= longitude <= 180:
            raise ValueError(f"Longitude invalide: {longitude} (doit être entre -180 et 180)")
        
        # Paramètres de la requête
        params = {
            'lat': latitude,
            'lon': longitude,
            'outputformat': 'json',
            'browser': '0',  # Pas de redirection navigateur
        }
        
        # Ajouter la base de données si supportée
        if database in self.DATABASES:
            params['raddatabase'] = database
        
        # Ajouter les paramètres supplémentaires
        params.update(kwargs)
        
        # Endpoint TMY
        url = f"{self.BASE_URL}/tmy"
        
        logger.info(f"Appel PVGIS TMY pour {latitude}, {longitude} (database: {database})")
        
        try:
            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            
            logger.info(f"Données PVGIS TMY reçues avec succès")
            return data
            
        except requests.exceptions.Timeout:
            logger.error(f"Timeout lors de l'appel PVGIS (>{self.timeout}s)")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Erreur lors de l'appel PVGIS: {e}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Erreur de parsing JSON: {e}")
            raise ValueError("Réponse PVGIS invalide (pas du JSON)")
    
    def parse_tmy_to_dataframe(self, tmy_data: Dict) -> pd.DataFrame:
        """
        Parse les données TMY en DataFrame pandas.
        
        Args:
            tmy_data: Données TMY depuis get_tmy_data()
            
        Returns:
            pd.DataFrame: DataFrame avec colonnes horaires (8760 lignes)
        """
        # Extraire les données horaires
        hourly_data = tmy_data.get('outputs', {}).get('tmy_hourly', [])
        
        if not hourly_data:
            raise ValueError("Pas de données horaires dans la réponse PVGIS")
        
        # Convertir en DataFrame
        df = pd.DataFrame(hourly_data)
        
        # Créer un timestamp à partir de year, month, day, hour
        df['timestamp'] = pd.to_datetime(
            df[['year', 'month', 'day', 'hour']].rename(columns={'hour': 'hour'})
        )
        
        # Renommer les colonnes pour correspondre à notre modèle
        column_mapping = {
            'G(h)': 'ghi',           # Global Horizontal Irradiance
            'Gb(n)': 'dni',          # Direct Normal Irradiance
            'Gd(h)': 'dhi',          # Diffuse Horizontal Irradiance
            'T2m': 'temperature',    # Température à 2m
            'WS10m': 'vitesse_vent', # Vitesse du vent à 10m
            'RH': 'humidite',        # Humidité relative
            'SP': 'pression',        # Pression de surface
        }
        
        df = df.rename(columns=column_mapping)
        
        # Sélectionner les colonnes pertinentes
        columns = ['timestamp', 'ghi', 'dni', 'dhi', 'temperature', 'vitesse_vent']
        available_columns = [col for col in columns if col in df.columns]
        df = df[available_columns]
        
        # Vérifier qu'on a bien 8760 heures
        if len(df) != 8760:
            logger.warning(f"Nombre d'heures incorrect: {len(df)} (attendu: 8760)")
        
        return df
    
    def get_monthly_radiation(
        self,
        latitude: float,
        longitude: float,
        angle: float = 0,
        aspect: float = 0,
        database: str = 'PVGIS-SARAH2',
        **kwargs
    ) -> Dict:
        """
        Récupère les données de rayonnement mensuelles.
        
        Args:
            latitude: Latitude en degrés
            longitude: Longitude en degrés
            angle: Angle d'inclinaison (0-90)
            aspect: Orientation (0=sud, -90=est, 90=ouest)
            database: Base de données PVGIS
            
        Returns:
            dict: Données mensuelles
        """
        params = {
            'lat': latitude,
            'lon': longitude,
            'angle': angle,
            'aspect': aspect,
            'outputformat': 'json',
            'browser': '0',
        }
        
        if database in self.DATABASES:
            params['raddatabase'] = database
        
        params.update(kwargs)
        
        url = f"{self.BASE_URL}/MRcalc"
        
        logger.info(f"Appel PVGIS monthly radiation pour {latitude}, {longitude}")
        
        try:
            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Erreur lors de l'appel PVGIS monthly: {e}")
            raise
    
    def calculate_annual_irradiation(self, df: pd.DataFrame) -> float:
        """
        Calcule l'irradiation annuelle totale depuis un DataFrame.
        
        Args:
            df: DataFrame avec colonne 'ghi' en W/m²
            
        Returns:
            float: Irradiation annuelle en kWh/m²
        """
        if 'ghi' not in df.columns:
            raise ValueError("Colonne 'ghi' manquante dans le DataFrame")
        
        # Somme de l'irradiance horaire (W/m²) sur 8760h
        # Divisé par 1000 pour convertir Wh → kWh
        irradiation_annuelle = df['ghi'].sum() / 1000
        
        return round(irradiation_annuelle, 2)
    
    def get_location_info(self, latitude: float, longitude: float) -> Dict:
        """
        Récupère les informations d'une localisation (pays, région, etc.).
        
        Args:
            latitude: Latitude
            longitude: Longitude
            
        Returns:
            dict: Informations de localisation
        """
        # PVGIS ne fournit pas directement ces infos, on peut les déduire
        # ou utiliser une API de géocodage (Google Maps, Nominatim, etc.)
        # Pour l'instant, on retourne une info basique
        
        # Déterminer la région approximative
        region = "Unknown"
        if -20 <= latitude <= 70 and -30 <= longitude <= 60:
            region = "Europe/Afrique/Asie"
        elif -60 <= latitude <= 70 and -170 <= longitude <= -30:
            region = "Amériques"
        
        return {
            'latitude': latitude,
            'longitude': longitude,
            'region': region,
        }


def fetch_pvgis_data_with_cache(
    latitude: float,
    longitude: float,
    database: str = 'PVGIS-SARAH2',
    use_cache: bool = True,
    cache_days: int = 30
) -> Tuple[pd.DataFrame, Dict]:
    """
    Récupère les données PVGIS avec système de cache Django.
    
    Args:
        latitude: Latitude
        longitude: Longitude
        database: Base de données PVGIS
        use_cache: Utiliser le cache Django
        cache_days: Durée de validité du cache en jours
        
    Returns:
        Tuple[pd.DataFrame, Dict]: (DataFrame météo, métadonnées)
    """
    from ..models import Location, PVGISData
    
    # Créer ou récupérer la localisation
    location, _ = Location.objects.get_or_create(
        latitude=round(latitude, 4),
        longitude=round(longitude, 4),
        defaults={'altitude': 0}
    )
    
    # Chercher dans le cache
    if use_cache:
        cached = PVGISData.objects.filter(
            location=location,
            database=database,
            is_valid=True,
            expires_at__gt=timezone.now()
        ).first()
        
        if cached:
            logger.info(f"Données PVGIS trouvées en cache pour {location}")
            data = cached.get_data_dict()
            client = PVGISClient()
            df = client.parse_tmy_to_dataframe(data)
            
            metadata = {
                'source': 'cache',
                'cached_at': cached.created_at,
                'irradiation_annuelle': cached.irradiation_annuelle_kwh_m2,
            }
            
            return df, metadata
    
    # Appel API PVGIS
    logger.info(f"Appel API PVGIS pour {location}")
    client = PVGISClient()
    data = client.get_tmy_data(latitude, longitude, database)
    df = client.parse_tmy_to_dataframe(data)
    
    # Calculer l'irradiation annuelle
    irradiation_annuelle = client.calculate_annual_irradiation(df)
    temperature_moyenne = df['temperature'].mean() if 'temperature' in df.columns else None
    
    # Sauvegarder en cache
    expires_at = timezone.now() + timedelta(days=cache_days)
    
    pvgis_cache = PVGISData.objects.create(
        location=location,
        database=database,
        raw_data=json.dumps(data),
        irradiation_annuelle_kwh_m2=irradiation_annuelle,
        temperature_moyenne_annuelle=round(temperature_moyenne, 2) if temperature_moyenne else None,
        expires_at=expires_at,
    )
    
    logger.info(f"Données PVGIS sauvegardées en cache (expire: {expires_at})")
    
    metadata = {
        'source': 'api',
        'database': database,
        'irradiation_annuelle': irradiation_annuelle,
        'temperature_moyenne': temperature_moyenne,
    }
    
    return df, metadata


# Fonction helper pour utilisation facile
def get_pvgis_weather_data(
    latitude: float,
    longitude: float,
    use_cache: bool = True
) -> pd.DataFrame:
    """
    Fonction simplifiée pour récupérer les données météo PVGIS.
    
    Args:
        latitude: Latitude
        longitude: Longitude
        use_cache: Utiliser le cache
        
    Returns:
        pd.DataFrame: Données météo horaires (8760 lignes)
    """
    df, metadata = fetch_pvgis_data_with_cache(latitude, longitude, use_cache=use_cache)
    
    logger.info(
        f"Données PVGIS récupérées: {len(df)} heures, "
        f"irradiation: {metadata['irradiation_annuelle']:.0f} kWh/m²/an"
    )
    
    return df