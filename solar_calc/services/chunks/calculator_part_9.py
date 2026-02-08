# solar_calc/services/calculator.py
"""
Calculatrice pour les simulations solaires.
Version corrigÃ©e pour accepter DataFrame pandas depuis PVGIS.
"""

import logging
from datetime import datetime
import json
import pandas as pd
import numpy as np

from solar_calc.contracts import (
    ProductionResult,
    ConsumptionResult,
    FinancialResult,
    validate_production_result,
    validate_consumption_result
)

from solar_calc.services.hourly_calculator import HourlyAutoconsumptionCalculator
from solar_calc.services.consumption_profiles import ConsumptionProfiles

logger = logging.getLogger(__name__)


class SimulationCalculator:
    """Classe pour calculer la production et consommation solaire"""
    
    def __init__(self, installation):
        """
        Initialise la calculatrice avec les paramÃ¨tres de l'installation.
        
        Args:
            installation: Objet Installation Django
        """

        # ===== INITIALISATION DES ATTRIBUTS (IMPORTANT !) =====
        self.installation = installation
        self.puissance_kw = installation.puissance_kw
        self.orientation = installation.orientation
        self.inclinaison = installation.inclinaison

        # Coefficients de rendement systÃ¨me (Performance Ratio)
        # Le rendement panneau est DÃ‰JÃ€ inclus dans la puissance crÃªte (kWc)

        self.rendement_onduleur = 0.95      # 95% (pertes onduleur + conversion DC/AC)
        self.rendement_cablage = 0.98       # 98% (pertes cÃ¢blage DC et AC)
        self.rendement_salissure = 0.95     # 95% (salissure panneaux)
        self.rendement_mismatch = 0.98      # 98% (diffÃ©rences entre panneaux)
        self.rendement_disponibilite = 0.98 # 98% (pannes, maintenance)

        # Performance Ratio total = ~85% (rÃ©aliste pour France)
        self.rendement_global = (
            self.rendement_onduleur * 
            self.rendement_cablage * 
            self.rendement_salissure * 
            self.rendement_mismatch * 
            self.rendement_disponibilite
        )
        
        logger.info(f"âœ… Calculatrice initialisÃ©e pour {self.puissance_kw}kWc")
    
    
    def calculate_production(self, weather_data):
        """
        Calcule la production solaire basÃ©e sur les donnÃ©es mÃ©tÃ©orologiques.
        
        Args:
            weather_data: Peut Ãªtre :
                - DataFrame pandas avec colonnes 'ghi', 'temperature' (depuis PVGIS)
                - Dict avec 'monthly' et 'hourly' (ancien format)
        
        Returns:
            Dict avec:
            - annuelle: Production annuelle en kWh
            - monthly: Liste de 12 valeurs mensuelles
            - daily: Profil horaire moyen (24 valeurs)
            - autoconso_ratio: Ratio d'autoconsommation (%)
            - injection: Ã‰nergie injectÃ©e au rÃ©seau (kWh)
        """
        
        logger.info("ðŸ“Š Calcul de la production solaire...")
        
        # VÃ©rifier le type de weather_data
        if isinstance(weather_data, pd.DataFrame):
            # Nouveau format : DataFrame pandas depuis PVGIS
            logger.info(f"âœ… DonnÃ©es PVGIS reÃ§ues : {len(weather_data)} heures")
            return self._calculate_from_dataframe(weather_data)
        
        elif isinstance(weather_data, dict):
            # Ancien format : dict avec monthly/hourly
            logger.info("âš ï¸ Format dict dÃ©tectÃ© (ancien format)")
            return self._calculate_from_dict(weather_data)
        
        else:
            # DonnÃ©es invalides ou manquantes
            logger.warning(f"âš ï¸ Type de donnÃ©es invalide : {type(weather_data)}")
            logger.info("ðŸ“Š Utilisation des donnÃ©es par dÃ©faut")
            default_data = self._get_default_irradiance()
            return self._calculate_from_dict(default_data)
    
    
    def _calculate_from_dataframe(self, df: pd.DataFrame):
        """
        Calcule la production depuis un DataFrame PVGIS.
        
        Args:
            df: DataFrame avec colonnes 'ghi' (W/mÂ²), 'temperature' (Â°C), 'timestamp'
        
        Returns:
            Dict avec les rÃ©sultats de production
        """
        # VÃ©rifier les colonnes nÃ©cessaires
        if 'ghi' not in df.columns:
            logger.error(f"âŒ Colonne 'ghi' manquante. Colonnes disponibles : {df.columns.tolist()}")
            raise ValueError("DataFrame doit contenir la colonne 'ghi'")
        
        # Ajustement selon l'orientation et l'inclinaison
        orientation_factor = self._get_orientation_factor()
        inclinaison_factor = self._get_inclinaison_factor()
        
        # Calculer la production horaire (kW)
        # GHI en W/mÂ² â†’ convertir en kW avec surface panneau
        # Puissance crÃªte = 1000 W/mÂ² Ã  25Â°C
        # Production = (GHI / 1000) Ã— Puissance_kWc Ã— Rendements Ã— Facteurs
        
        df_calc = df.copy()
        df_calc['production_kw'] = (
            (df_calc['ghi'] / 1000) *  # Normaliser Ã  STC (1000 W/mÂ²)
            self.puissance_kw *
            self.rendement_global *
            orientation_factor *
            inclinaison_factor
        )
        
        # Ajustement tempÃ©rature (performance baisse de 0.4% par Â°C au-dessus de 25Â°C)
        if 'temperature' in df_calc.columns:
            temp_factor = 1 - 0.004 * (df_calc['temperature'] - 25)
            temp_factor = temp_factor.clip(lower=0.7, upper=1.1)  # Limiter entre 70% et 110%
            df_calc['production_kw'] *= temp_factor
        
        # Production annuelle totale (kWh)
        production_annuelle = df_calc['production_kw'].sum()
        
        # AgrÃ©ger par mois (si timestamp existe)
        if 'timestamp' in df_calc.columns:
            df_calc['timestamp'] = pd.to_datetime(df_calc['timestamp'])
            df_calc['month'] = df_calc['timestamp'].dt.month
            production_monthly_series = df_calc.groupby('month')['production_kw'].sum()
            
            # S'assurer d'avoir 12 mois
            production_monthly = []
            for month in range(1, 13):
                if month in production_monthly_series.index:
                    production_monthly.append(round(production_monthly_series[month], 2))
                else:
                    production_monthly.append(0.0)
        else:
            # Pas de timestamp, distribuer uniformÃ©ment
            logger.warning("âš ï¸ Pas de timestamp, distribution uniforme mensuelle")
            monthly_value = production_annuelle / 12
            production_monthly = [round(monthly_value, 2)] * 12
        
        # Profil horaire moyen (24h) - moyenne de chaque heure sur toute l'annÃ©e
        if 'timestamp' in df_calc.columns:
            df_calc['hour'] = df_calc['timestamp'].dt.hour
            production_hourly_series = df_calc.groupby('hour')['production_kw'].mean()
            
            production_hourly = []
            for hour in range(24):
                if hour in production_hourly_series.index:
                    production_hourly.append(round(production_hourly_series[hour], 3))
                else:
                    production_hourly.append(0.0)
        else:
            # Profil par dÃ©faut (courbe en cloche)
            production_hourly = self._get_default_hourly_pattern(production_annuelle / 8760)
        
        # ===== CALCUL AUTOCONSOMMATION HORAIRE PERSONNALISÃ‰ =====
        
    # RÃ©cupÃ©rer les paramÃ¨tres de consommation
    consommation_annuelle = getattr(self.installation, 'consommation_annuelle', 3500.0)
    profile_type = getattr(self.installation, 'profile_type', 'actif_absent')

    # VÃ©rifier si on a des donnÃ©es d'appareils dÃ©taillÃ©es
    appareils_json = getattr(self.installation, 'appareils_json', None)

    logger.info(f"ðŸ“Š GÃ©nÃ©ration profil consommation ({profile_type}, {consommation_annuelle:.0f} kWh/an)")

    # GÃ©nÃ©rer le profil de consommation horaire
        try:
            if appareils_json:
                # CAS 1 : On a les dÃ©tails des appareils â†’ Profil PERSONNALISÃ‰
                try:
                    appareils_data = json.loads(appareils_json)
                    logger.info(f"âœ… Utilisation profil personnalisÃ© avec {len(appareils_data.get('appareils', {}))} appareils")
                    
                    consommation_horaire_kw = ConsumptionProfiles.generate_personalized_pattern(
                        profile_type=profile_type,
