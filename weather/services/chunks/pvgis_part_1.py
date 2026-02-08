"""
Client API PVGIS pour rÃ©cupÃ©rer les donnÃ©es d'irradiation solaire.

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
    
    PVGIS est une API gratuite du JRC (Joint Research Centre) de la Commission EuropÃ©enne.
    Elle fournit des donnÃ©es d'irradiation solaire pour l'Europe, l'Afrique, l'Asie et les AmÃ©riques.
    
    Version API : 5.3 (derniÃ¨re version stable)
    """
    
    # URL de base de l'API PVGIS 5.3
    BASE_URL = "https://re.jrc.ec.europa.eu/api/v5_3"
    
    # Bases de donnÃ©es disponibles (pour les endpoints qui les supportent)
    DATABASES = {
        'PVGIS-SARAH2': 'Europe, Afrique, Asie (2005-2020) - RecommandÃ©',
        'PVGIS-SARAH3': 'Europe, Afrique, Asie (2005-2022) - Plus rÃ©cent',
        'PVGIS-NSRDB': 'AmÃ©riques (1998-2020)',
        'PVGIS-ERA5': 'Mondial (2005-2020)',
        'PVGIS-COSMO': 'Europe (2007-2016)',
    }
    
    def __init__(self, timeout: int = 60):
        """
        Initialise le client PVGIS.
        
        Args:
            timeout: Timeout des requÃªtes HTTP en secondes (augmentÃ© Ã  60s car PVGIS peut Ãªtre lent)
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
        RÃ©cupÃ¨re les donnÃ©es TMY (Typical Meteorological Year).
        
        Le TMY reprÃ©sente une annÃ©e mÃ©tÃ©orologique typique basÃ©e sur des donnÃ©es historiques.
        C'est idÃ©al pour les simulations de production solaire.
        
        IMPORTANT : L'endpoint TMY de PVGIS 5.3 ne supporte PAS le paramÃ¨tre 'raddatabase'.
        Les donnÃ©es TMY utilisent automatiquement la meilleure base de donnÃ©es disponible 
        pour la localisation (SARAH2/3 pour l'Europe).
        
        Args:
            latitude: Latitude en degrÃ©s dÃ©cimaux (-90 Ã  90)
            longitude: Longitude en degrÃ©s dÃ©cimaux (-180 Ã  180)
            usehorizon: Utiliser l'horizon calculÃ© (1) ou non (0)
            userhorizon: Liste des hauteurs d'horizon (optionnel)
            **kwargs: ParamÃ¨tres supplÃ©mentaires (startyear, endyear, etc.)
            
        Returns:
            dict: DonnÃ©es TMY avec irradiation horaire
            
        Raises:
            requests.RequestException: Erreur lors de l'appel API
            ValueError: CoordonnÃ©es invalides
        """
        # Validation des coordonnÃ©es
        if not -90 <= latitude <= 90:
            raise ValueError(f"Latitude invalide: {latitude} (doit Ãªtre entre -90 et 90)")
        if not -180 <= longitude <= 180:
            raise ValueError(f"Longitude invalide: {longitude} (doit Ãªtre entre -180 et 180)")
        
        # ParamÃ¨tres de base pour PVGIS 5.3 TMY
        params = {
            'lat': latitude,
            'lon': longitude,
            'outputformat': 'json',
        }
        
        # Ajouter usehorizon (recommandÃ© pour plus de prÃ©cision)
        if usehorizon in [0, 1]:
            params['usehorizon'] = usehorizon
        
        # Horizon utilisateur personnalisÃ© (optionnel)
        if userhorizon:
            params['userhorizon'] = ','.join(map(str, userhorizon))
        
        # Filtrer les paramÃ¨tres non supportÃ©s par TMY
        # TMY ne supporte PAS : raddatabase, startyear, endyear
        forbidden_params = ['raddatabase', 'startyear', 'endyear', 'database']
        filtered_kwargs = {k: v for k, v in kwargs.items() if k not in forbidden_params}
        params.update(filtered_kwargs)
        
        # Endpoint TMY
        url = f"{self.BASE_URL}/tmy"
        
        logger.info(f"Appel PVGIS 5.3 TMY pour {latitude}, {longitude}")
        logger.debug(f"URL: {url}")
        logger.debug(f"ParamÃ¨tres: {params}")
        
        try:
            response = self.session.get(url, params=params, timeout=self.timeout)
            
            # Log de la requÃªte complÃ¨te
            logger.debug(f"URL complÃ¨te: {response.url}")
            
            response.raise_for_status()
            
            data = response.json()
            
            logger.info(f"DonnÃ©es PVGIS TMY reÃ§ues avec succÃ¨s")
            
            # VÃ©rifier la structure de la rÃ©ponse
            if 'outputs' not in data or 'tmy_hourly' not in data.get('outputs', {}):
                logger.warning("Structure de rÃ©ponse inattendue")
                logger.debug(f"ClÃ©s de rÃ©ponse: {data.keys()}")
            
            return data
            
        except requests.exceptions.Timeout:
            logger.error(f"Timeout lors de l'appel PVGIS (>{self.timeout}s)")
            raise
        except requests.exceptions.HTTPError as e:
            logger.error(f"Erreur HTTP {e.response.status_code}: {e}")
            logger.error(f"URL: {e.response.url}")
            logger.error(f"RÃ©ponse: {e.response.text[:500]}")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Erreur lors de l'appel PVGIS: {e}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Erreur de parsing JSON: {e}")
            logger.error(f"RÃ©ponse brute: {response.text[:500]}")
            raise ValueError("RÃ©ponse PVGIS invalide (pas du JSON)")
    
    def parse_tmy_to_dataframe(self, tmy_data: Dict) -> pd.DataFrame:
        """
        Parse les donnÃ©es TMY en DataFrame pandas.
        
        Compatible avec PVGIS 5.3 qui peut avoir une structure lÃ©gÃ¨rement diffÃ©rente.
        
        Args:
            tmy_data: DonnÃ©es TMY depuis get_tmy_data()
            
        Returns:
            pd.DataFrame: DataFrame avec colonnes horaires (8760 lignes)
        """
        # Extraire les donnÃ©es horaires
        hourly_data = tmy_data.get('outputs', {}).get('tmy_hourly', [])
        
        if not hourly_data:
            # Essayer d'autres structures possibles
            if 'hourly' in tmy_data.get('outputs', {}):
                hourly_data = tmy_data['outputs']['hourly']
            else:
                logger.error(f"ClÃ©s disponibles: {tmy_data.get('outputs', {}).keys()}")
                raise ValueError("Pas de donnÃ©es horaires dans la rÃ©ponse PVGIS")
        
        # Convertir en DataFrame
        df = pd.DataFrame(hourly_data)
        
        logger.info(f"Colonnes reÃ§ues de PVGIS: {df.columns.tolist()}")
        
        # CrÃ©er timestamp Ã  partir des colonnes disponibles
        # PVGIS 5.3 peut utiliser 'time(UTC)' ou des colonnes sÃ©parÃ©es
        if 'time(UTC)' in df.columns:
            # Format : '20050101:0010' ou '2005-01-01 00:10'
            df['timestamp'] = pd.to_datetime(df['time(UTC)'], format='%Y%m%d:%H%M', errors='coerce')
            if df['timestamp'].isna().all():
                # Essayer un autre format
                df['timestamp'] = pd.to_datetime(df['time(UTC)'], errors='coerce')
        elif all(col in df.columns for col in ['year', 'month', 'day', 'hour']):
            # Colonnes sÃ©parÃ©es
            df['timestamp'] = pd.to_datetime(df[['year', 'month', 'day', 'hour']])
        else:
            logger.warning("Impossible de crÃ©er timestamp automatiquement")
            # CrÃ©er un timestamp sÃ©quentiel
            df['timestamp'] = pd.date_range(
                start='2005-01-01 00:00',
                periods=len(df),
                freq='H'
