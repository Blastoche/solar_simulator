"""
Client API PVGIS pour récupérer les données d'irradiation solaire.

Documentation PVGIS 5.3 : https://joint-research-centre.ec.europa.eu/photovoltaic-geographical-information-system-pvgis/getting-started-pvgis/pvgis-user-manual_en
API Documentation : https://joint-research-centre.ec.europa.eu/pvgis-tools/api_en
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
    Client pour l'API PVGIS 5.3 (Photovoltaic Geographical Information System).
    
    PVGIS est une API gratuite du JRC (Joint Research Centre) de la Commission Européenne.
    Elle fournit des données d'irradiation solaire pour l'Europe, l'Afrique, l'Asie et les Amériques.
    
    Version API : 5.3 (dernière version stable)
    """
    
    # URL de base de l'API PVGIS 5.3
    BASE_URL = "https://re.jrc.ec.europa.eu/api/v5_3"
    
    # Bases de données disponibles (pour les endpoints qui les supportent)
    DATABASES = {
        'PVGIS-SARAH2': 'Europe, Afrique, Asie (2005-2020) - Recommandé',
        'PVGIS-SARAH3': 'Europe, Afrique, Asie (2005-2022) - Plus récent',
        'PVGIS-NSRDB': 'Amériques (1998-2020)',
        'PVGIS-ERA5': 'Mondial (2005-2020)',
        'PVGIS-COSMO': 'Europe (2007-2016)',
    }
    
    def __init__(self, timeout: int = 60):
        """
        Initialise le client PVGIS.
        
        Args:
            timeout: Timeout des requêtes HTTP en secondes (augmenté à 60s car PVGIS peut être lent)
        """
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'SolarSimulator/1.0 (Python; PVGIS Client)'
        })
    
    def get_tmy_data(
        self,
        latitude: float,
        longitude: float,
        usehorizon: int = 1,
        userhorizon: Optional[list] = None,
        **kwargs
    ) -> Dict:
        """
        Récupère les données TMY (Typical Meteorological Year).
        
        Le TMY représente une année météorologique typique basée sur des données historiques.
        C'est idéal pour les simulations de production solaire.
        
        IMPORTANT : L'endpoint TMY de PVGIS 5.3 ne supporte PAS le paramètre 'raddatabase'.
        Les données TMY utilisent automatiquement la meilleure base de données disponible 
        pour la localisation (SARAH2/3 pour l'Europe).
        
        Args:
            latitude: Latitude en degrés décimaux (-90 à 90)
            longitude: Longitude en degrés décimaux (-180 à 180)
            usehorizon: Utiliser l'horizon calculé (1) ou non (0)
            userhorizon: Liste des hauteurs d'horizon (optionnel)
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
        
        # Paramètres de base pour PVGIS 5.3 TMY
        params = {
            'lat': latitude,
            'lon': longitude,
            'outputformat': 'json',
        }
        
        # Ajouter usehorizon (recommandé pour plus de précision)
        if usehorizon in [0, 1]:
            params['usehorizon'] = usehorizon
        
        # Horizon utilisateur personnalisé (optionnel)
        if userhorizon:
            params['userhorizon'] = ','.join(map(str, userhorizon))
        
        # Filtrer les paramètres non supportés par TMY
        # TMY ne supporte PAS : raddatabase, startyear, endyear
        forbidden_params = ['raddatabase', 'startyear', 'endyear', 'database']
        filtered_kwargs = {k: v for k, v in kwargs.items() if k not in forbidden_params}
        params.update(filtered_kwargs)
        
        # Endpoint TMY
        url = f"{self.BASE_URL}/tmy"
        
        logger.info(f"Appel PVGIS 5.3 TMY pour {latitude}, {longitude}")
        logger.debug(f"URL: {url}")
        logger.debug(f"Paramètres: {params}")
        
        try:
            response = self.session.get(url, params=params, timeout=self.timeout)
            
            # Log de la requête complète
            logger.debug(f"URL complète: {response.url}")
            
            response.raise_for_status()
            
            data = response.json()
            
            logger.info(f"Données PVGIS TMY reçues avec succès")
            
            # Vérifier la structure de la réponse
            if 'outputs' not in data or 'tmy_hourly' not in data.get('outputs', {}):
                logger.warning("Structure de réponse inattendue")
                logger.debug(f"Clés de réponse: {data.keys()}")
            
            return data
            
        except requests.exceptions.Timeout:
            logger.error(f"Timeout lors de l'appel PVGIS (>{self.timeout}s)")
            raise
        except requests.exceptions.HTTPError as e:
            logger.error(f"Erreur HTTP {e.response.status_code}: {e}")
            logger.error(f"URL: {e.response.url}")
            logger.error(f"Réponse: {e.response.text[:500]}")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Erreur lors de l'appel PVGIS: {e}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Erreur de parsing JSON: {e}")
            logger.error(f"Réponse brute: {response.text[:500]}")
            raise ValueError("Réponse PVGIS invalide (pas du JSON)")
    
    def parse_tmy_to_dataframe(self, tmy_data: Dict) -> pd.DataFrame:
        """
        Parse les données TMY en DataFrame pandas.
        
        Compatible avec PVGIS 5.3 qui peut avoir une structure légèrement différente.
        
        Args:
            tmy_data: Données TMY depuis get_tmy_data()
            
        Returns:
            pd.DataFrame: DataFrame avec colonnes horaires (8760 lignes)
        """
        # Extraire les données horaires
        hourly_data = tmy_data.get('outputs', {}).get('tmy_hourly', [])
        
        if not hourly_data:
            # Essayer d'autres structures possibles
            if 'hourly' in tmy_data.get('outputs', {}):
                hourly_data = tmy_data['outputs']['hourly']
            else:
                logger.error(f"Clés disponibles: {tmy_data.get('outputs', {}).keys()}")
                raise ValueError("Pas de données horaires dans la réponse PVGIS")
        
        # Convertir en DataFrame
        df = pd.DataFrame(hourly_data)
        
        logger.info(f"Colonnes reçues de PVGIS: {df.columns.tolist()}")
        
        # Créer timestamp à partir des colonnes disponibles
        # PVGIS 5.3 peut utiliser 'time(UTC)' ou des colonnes séparées
        if 'time(UTC)' in df.columns:
            # Format : '20050101:0010' ou '2005-01-01 00:10'
            df['timestamp'] = pd.to_datetime(df['time(UTC)'], format='%Y%m%d:%H%M', errors='coerce')
            if df['timestamp'].isna().all():
                # Essayer un autre format
                df['timestamp'] = pd.to_datetime(df['time(UTC)'], errors='coerce')
        elif all(col in df.columns for col in ['year', 'month', 'day', 'hour']):
            # Colonnes séparées
            df['timestamp'] = pd.to_datetime(df[['year', 'month', 'day', 'hour']])
        else:
            logger.warning("Impossible de créer timestamp automatiquement")
            # Créer un timestamp séquentiel
            df['timestamp'] = pd.date_range(
                start='2005-01-01 00:00',
                periods=len(df),
                freq='H'
            )
        
        # Mapping des colonnes PVGIS vers nos noms standard
        # PVGIS 5.3 utilise ces noms
        column_mapping = {
            'G(h)': 'ghi',           # Global Horizontal Irradiance
            'Gb(n)': 'dni',          # Direct Normal Irradiance  
            'Gd(h)': 'dhi',          # Diffuse Horizontal Irradiance
            'T2m': 'temperature',    # Température à 2m
            'WS10m': 'vitesse_vent', # Vitesse du vent à 10m
            'RH': 'humidite',        # Humidité relative
            'SP': 'pression',        # Pression de surface
            'WD10m': 'direction_vent', # Direction du vent
            'IR(h)': 'infrarouge',   # Irradiance infrarouge
        }
        
        # Renommer uniquement les colonnes qui existent
        existing_mappings = {k: v for k, v in column_mapping.items() if k in df.columns}
        df = df.rename(columns=existing_mappings)
        
        # Sélectionner les colonnes pertinentes
        base_columns = ['timestamp']
        optional_columns = ['ghi', 'dni', 'dhi', 'temperature', 'vitesse_vent', 
                          'humidite', 'pression', 'direction_vent']
        
        available_columns = base_columns + [col for col in optional_columns if col in df.columns]
        df = df[available_columns]
        
        # Vérifier le nombre d'heures
        if len(df) != 8760:
            logger.warning(f"Nombre d'heures incorrect: {len(df)} (attendu: 8760)")
        
        logger.info(f"DataFrame créé avec {len(df)} heures et colonnes: {df.columns.tolist()}")
        
        return df
    
    def get_monthly_radiation(
        self,
        latitude: float,
        longitude: float,
        angle: float = 0,
        aspect: float = 0,
        raddatabase: str = 'PVGIS-SARAH3',
        **kwargs
    ) -> Dict:
        """
        Récupère les données de rayonnement mensuelles.
        
        NOTE: Cet endpoint SUPPORTE le paramètre raddatabase.
        
        Args:
            latitude: Latitude en degrés
            longitude: Longitude en degrés
            angle: Angle d'inclinaison (0-90)
            aspect: Orientation (0=sud, -90=est, 90=ouest)
            raddatabase: Base de données (SARAH2, SARAH3, etc.)
            
        Returns:
            dict: Données mensuelles
        """
        params = {
            'lat': latitude,
            'lon': longitude,
            'angle': angle,
            'aspect': aspect,
            'outputformat': 'json',
        }
        
        # MRcalc SUPPORTE raddatabase
        if raddatabase in self.DATABASES:
            params['raddatabase'] = raddatabase
        
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
        Récupère les informations d'une localisation.
        
        Args:
            latitude: Latitude
            longitude: Longitude
            
        Returns:
            dict: Informations de localisation
        """
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
    use_cache: bool = True,
    cache_days: int = 30
) -> Tuple[pd.DataFrame, Dict]:
    """
    Récupère les données PVGIS 5.3 avec système de cache Django.
    
    Args:
        latitude: Latitude
        longitude: Longitude
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
    
    # Database pour le cache (informatif seulement)
    database = 'PVGIS-SARAH3'
    
    # Chercher dans le cache
    if use_cache:
        cached = PVGISData.objects.filter(
            location=location,
            is_valid=True,
            expires_at__gt=timezone.now()
        ).first()
        
        if cached:
            logger.info(f"✅ Données PVGIS trouvées en cache pour {location}")
            data = cached.get_data_dict()
            
            if data:
                client = PVGISClient()
                try:
                    df = client.parse_tmy_to_dataframe(data)
                    
                    metadata = {
                        'source': 'cache',
                        'cached_at': cached.created_at,
                        'irradiation_annuelle': cached.irradiation_annuelle_kwh_m2,
                    }
                    
                    return df, metadata
                except Exception as e:
                    logger.warning(f"⚠️ Erreur parsing cache, nouvel appel API: {e}")
                    # Le cache est corrompu, on va réessayer avec l'API
    
    # Appel API PVGIS 5.3
    logger.info(f"🌐 Appel API PVGIS 5.3 pour {location}")
    client = PVGISClient()
    
    try:
        # Appel avec usehorizon pour meilleure précision
        data = client.get_tmy_data(latitude, longitude, usehorizon=1)
        df = client.parse_tmy_to_dataframe(data)
        
        # Calculer l'irradiation annuelle
        irradiation_annuelle = client.calculate_annual_irradiation(df)
        temperature_moyenne = df['temperature'].mean() if 'temperature' in df.columns else None
        
        # Sauvegarder en cache
        expires_at = timezone.now() + timedelta(days=cache_days)
        
        # Supprimer les anciens caches pour cette localisation
        PVGISData.objects.filter(location=location).delete()
        
        pvgis_cache = PVGISData.objects.create(
            location=location,
            database=database,
            raw_data=json.dumps(data),
            irradiation_annuelle_kwh_m2=irradiation_annuelle,
            temperature_moyenne_annuelle=round(temperature_moyenne, 2) if temperature_moyenne else None,
            expires_at=expires_at,
        )
        
        logger.info(f"💾 Données PVGIS sauvegardées en cache (expire: {expires_at.strftime('%Y-%m-%d')})")
        
        metadata = {
            'source': 'api',
            'database': 'PVGIS-TMY (SARAH3)',
            'irradiation_annuelle': irradiation_annuelle,
            'temperature_moyenne': temperature_moyenne,
        }
        
        return df, metadata
        
    except Exception as e:
        logger.error(f"❌ Erreur lors de l'appel PVGIS 5.3: {e}")
        raise


# Fonction helper pour utilisation facile
def get_pvgis_weather_data(
    latitude: float,
    longitude: float,
    use_cache: bool = True
) -> Tuple[pd.DataFrame, Dict]:
    """
    Fonction simplifiée pour récupérer les données météo PVGIS 5.3.
    
    Args:
        latitude: Latitude
        longitude: Longitude
        use_cache: Utiliser le cache
        
    Returns:
        Tuple[pd.DataFrame, Dict]: (DataFrame météo 8760h, métadonnées)
    """
    df, metadata = fetch_pvgis_data_with_cache(latitude, longitude, use_cache=use_cache)
    
    logger.info(
        f"📊 Données PVGIS 5.3 récupérées: {len(df)} heures, "
        f"irradiation: {metadata['irradiation_annuelle']:.0f} kWh/m²/an "
        f"(source: {metadata['source']})"
    )
    
    return df, metadata

