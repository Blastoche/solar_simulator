# solar_calc/services/calculator.py
"""
Calculatrice pour les simulations solaires.
"""

import logging
from datetime import datetime
import json

logger = logging.getLogger(__name__)


class SimulationCalculator:
    """Classe pour calculer la production et consommation solaire"""
    
    def __init__(self, installation):
        """
        Initialise la calculatrice avec les paramètres de l'installation.
        
        Args:
            installation: Objet Installation Django
        """
        self.installation = installation
        self.puissance_kw = installation.puissance_kw
        self.orientation = installation.orientation
        self.inclinaison = installation.inclinaison
        
        # Coefficients de rendement
        self.rendement_panneaux = 0.20  # 20%
        self.rendement_onduleur = 0.98  # 98%
        self.rendement_cablage = 0.99   # 99%
        self.rendement_global = self.rendement_panneaux * self.rendement_onduleur * self.rendement_cablage
        
        logger.info(f"✅ Calculatrice initialisée pour {self.puissance_kw}kWc")
    
    
    def calculate_production(self, weather_data):
        """
        Calcule la production solaire basée sur les données météorologiques.
        
        Args:
            weather_data: Dict avec les données PVGIS
                {
                    'monthly': [float, ...],  # 12 valeurs (kWh/m²/jour)
                    'hourly': [float, ...]    # 24 valeurs (W/m²)
                }
        
        Returns:
            Dict avec:
            - annuelle: Production annuelle en kWh
            - monthly: Liste de 12 valeurs mensuelles
            - daily: Profil horaire moyen (24 valeurs)
            - autoconso_ratio: Ratio d'autoconsommation (%)
            - injection: Énergie injectée au réseau (kWh)
        """
        
        logger.info("📊 Calcul de la production solaire...")
        
        # Données par défaut si pas de données PVGIS
        if not weather_data:
            weather_data = self._get_default_irradiance()
        
        monthly_irradiance = weather_data.get('monthly', [1.0] * 12)
        hourly_irradiance = weather_data.get('hourly', [0.5] * 24)
        
        # Ajustement selon l'orientation
        orientation_factor = self._get_orientation_factor()
        
        # Calcul production mensuelle (kWh)
        production_monthly = []
        for irr in monthly_irradiance:
            # Production = Puissance × Irradiance × Rendement × Facteur orientation
            # Irradiance en kWh/m²/jour, sur 30 jours en moyenne
            kwh = (self.puissance_kw * irr * 30 * self.rendement_global * orientation_factor)
            production_monthly.append(round(kwh, 2))
        
        # Production annuelle
        production_annuelle = sum(production_monthly)
        
        # Profil horaire moyen (kWh)
        production_hourly = [
            round((self.puissance_kw * (irr / 1000) * self.rendement_global * orientation_factor), 3)
            for irr in hourly_irradiance
        ]
        
        # Autoconsommation (par défaut 70%)
        autoconso_ratio = 70.0
        autoconso_kwh = production_annuelle * (autoconso_ratio / 100)
        injection_kwh = production_annuelle - autoconso_kwh
        
        logger.info(f"📈 Production annuelle: {production_annuelle:.2f} kWh")
        logger.info(f"⚡ Autoconsommation: {autoconso_ratio}%")
        
        return {
            'annuelle': round(production_annuelle, 2),
            'monthly': production_monthly,
            'daily': production_hourly,
            'autoconso_ratio': autoconso_ratio,
            'injection': round(injection_kwh, 2),
        }
    
    
    def calculate_consumption(self):
        """
        Calcule la consommation électrique estimée.
        
        Returns:
            Dict avec:
            - annuelle: Consommation annuelle en kWh
            - monthly: Liste de 12 valeurs mensuelles
            - daily: Profil horaire (24 valeurs)
        """
        
        logger.info("⚡ Calcul de la consommation...")
        
        # Consommation estimée par défaut : 3 500 kWh/an (France moyenne)
        consumption_annuelle = 3500.0
        
        # Distribution mensuelle (légère variation saisonnière)
        # Plus élevée en hiver (chauffage, éclairage)
        monthly_factors = [
            1.1,  # Jan (chauffage)
            1.05, # Fév
            0.95, # Mar
            0.85, # Avr
            0.75, # Mai
            0.70, # Juin (+ clim)
            0.75, # Juil
            0.75, # Août
            0.80, # Sep
            0.90, # Oct
            1.05, # Nov
            1.15, # Déc (chauffage)
        ]
        
        consumption_monthly = []
        for factor in monthly_factors:
            kwh = (consumption_annuelle / 12) * factor
            consumption_monthly.append(round(kwh, 2))
        
        # Profil horaire (24h)
        # Pic le matin (6-9h) et soir (18-22h)
        hourly_factors = [
            0.3, 0.2, 0.2, 0.2, 0.3, 0.6,  # 00-06
            1.0, 0.9, 0.7, 0.5, 0.5, 0.4,  # 06-12
            0.4, 0.4, 0.5, 0.6, 0.9, 1.0,  # 12-18
            0.8, 0.7, 0.5, 0.4, 0.4, 0.3,  # 18-24
        ]
        
        consumption_hourly = []
        for factor in hourly_factors:
            kwh = (consumption_annuelle / 8760) * factor  # 8760 = 24 × 365
            consumption_hourly.append(round(kwh, 3))
        
        logger.info(f"📉 Consommation annuelle: {consumption_annuelle:.2f} kWh")
        
        return {
            'annuelle': consumption_annuelle,
            'monthly': consumption_monthly,
            'daily': consumption_hourly,
        }
    
    
    def calculate_financial(self, production, consumption):
        """
        Calcule les données financières.
        
        Args:
            production: Dict de production (résultat de calculate_production)
            consumption: Dict de consommation (résultat de calculate_consumption)
        
        Returns:
            Dict avec:
            - economie_annuelle: Économie annuelle en €
            - roi: Retour sur investissement sur 25 ans en €
            - taux_rentabilite: Taux de rentabilité en %
        """
        
        logger.info("💰 Calcul financier...")
        
        # Paramètres économiques
        prix_kwh = 0.25  # €/kWh moyen en France
        prix_autoconso = 0.25  # €/kWh consommé localement
        prix_injection = 0.08  # €/kWh injecté au réseau
        
        # Cout d'investissement (environ 1500-2000€ par kWc)
        cout_installation = self.puissance_kw * 1800  # €
        
        # Économie annuelle
        economie_autoconso = production['annuelle'] * (production['autoconso_ratio'] / 100) * prix_autoconso
        economie_injection = production['injection'] * prix_injection
        economie_annuelle = economie_autoconso + economie_injection
        
        # ROI sur 25 ans
        roi_25ans = (economie_annuelle * 25) - cout_installation
        
        # Taux de rentabilité annuel
        taux_rentabilite = (economie_annuelle / cout_installation) * 100 if cout_installation > 0 else 0
        
        logger.info(f"💵 Économie annuelle: {economie_annuelle:.2f}€")
        logger.info(f"💶 ROI 25 ans: {roi_25ans:.2f}€")
        logger.info(f"📊 Taux rentabilité: {taux_rentabilite:.2f}%")
        
        return {
            'economie_annuelle': round(economie_annuelle, 2),
            'roi': round(roi_25ans, 2),
            'taux_rentabilite': round(taux_rentabilite, 2),
        }
    
    
    def _get_orientation_factor(self):
        """
        Retourne le facteur d'orientation (0-1).
        
        - Sud = 1.0 (optimal)
        - SE/SW = 0.95
        - E/W = 0.85
        - NE/NW = 0.70
        - N = 0.50
        """
        
        factors = {
            'S': 1.0,
            'SE': 0.95,
            'SW': 0.95,
            'E': 0.85,
            'W': 0.85,
            'NE': 0.70,
            'NW': 0.70,
            'N': 0.50,
        }
        
        return factors.get(self.orientation, 0.85)
    
    
    def _get_default_irradiance(self):
        """
        Retourne des données d'irradiance par défaut (France moyenne).
        """
        
        return {
            'monthly': [
                1.2,  # Jan
                1.4,  # Fév
                2.0,  # Mar
                2.5,  # Avr
                3.0,  # Mai
                3.2,  # Juin
                3.1,  # Juil
                2.8,  # Août
                2.2,  # Sep
                1.6,  # Oct
                1.3,  # Nov
                1.1,  # Déc
            ],
            'hourly': [
                0,    # 00h
                0,    # 01h
                0,    # 02h
                0,    # 03h
                0,    # 04h
                50,   # 05h
                200,  # 06h
                400,  # 07h
                600,  # 08h
                750,  # 09h
                850,  # 10h
                900,  # 11h
                950,  # 12h
                900,  # 13h
                850,  # 14h
                750,  # 15h
                600,  # 16h
                400,  # 17h
                200,  # 18h
                50,   # 19h
                0,    # 20h
                0,    # 21h
                0,    # 22h
                0,    # 23h
            ]
        }
