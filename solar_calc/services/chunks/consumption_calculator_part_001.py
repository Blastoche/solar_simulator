# solar_calc/services/consumption_calculator.py
"""
Service de calcul de consommation Ã©lectrique basÃ© sur le profil du foyer.

Utilise :
- DPE pour le chauffage
- Zone climatique (H1/H2/H3)
- Nombre de personnes
- Surface habitable
- Appareils Ã©lectriques
"""

import logging
from typing import Dict, List, Tuple
import numpy as np

logger = logging.getLogger(__name__)


class ConsumptionCalculator:
    """
    Calculateur de consommation Ã©lectrique pour un foyer.
    """
    
    # Besoins Ã©nergÃ©tiques selon DPE (kWh/mÂ²/an) pour chauffage
    BESOINS_DPE = {
        'A': 35,   # < 50 kWh/mÂ²/an
        'B': 70,   # 50-90
        'C': 120,  # 91-150
        'D': 190,  # 151-230
        'E': 280,  # 231-330
        'F': 390,  # 331-450
        'G': 500,  # > 450
    }
    
    # Facteurs selon zone climatique
    FACTEURS_ZONE = {
        'H1': 1.20,  # Nord (plus froid)
        'H2': 1.00,  # Centre (rÃ©fÃ©rence)
        'H3': 0.75,  # Sud (plus doux)
    }
    
    # Coefficients de conversion Ã©nergie primaire â†’ finale
    # Le DPE est exprimÃ© en Ã©nergie PRIMAIRE
    # Il faut diviser par ces coefficients pour obtenir l'Ã©nergie FINALE rÃ©ellement consommÃ©e
    COEFFICIENTS_PRIMAIRE_FINALE = {
        'electrique': 2.58,  # Ancien coef (avant RE2020: 2.3)
        'pompe_chaleur': 2.58,
        'pompe_a_chaleur': 2.58,
        'PAC': 2.58, # PAC = Ã©lectricitÃ©    
        'gaz': 1.0,          # Gaz naturel
        'fioul': 1.0,        # Fioul
        'bois': 0.6,         # Bois/biomasse
        'reseau_chaleur': 1.0,  # RÃ©seau de chaleur (variable selon source)
    }
    
    # Tarifs Ã©lectricitÃ© 2024 (â‚¬ TTC) - Source : CRE janvier 2024
    # Tarif Base (prix unique 24h/24)
    TARIFS_BASE_2024 = {
        '3kVA': {'abonnement': 136.12, 'prix_kwh': 0.2516},
        '6kVA': {'abonnement': 151.20, 'prix_kwh': 0.2516},
        '9kVA': {'abonnement': 189.48, 'prix_kwh': 0.2516},
        '12kVA': {'abonnement': 228.48, 'prix_kwh': 0.2516},
        '15kVA': {'abonnement': 266.76, 'prix_kwh': 0.2516},
    }
    
    # Tarif HP/HC (Heures Pleines / Heures Creuses)
    TARIFS_HPHC_2024 = {
        '6kVA': {'abonnement': 156.12, 'prix_hp': 0.2700, 'prix_hc': 0.2068},
        '9kVA': {'abonnement': 198.24, 'prix_hp': 0.2700, 'prix_hc': 0.2068},
        '12kVA': {'abonnement': 242.88, 'prix_hp': 0.2700, 'prix_hc': 0.2068},
        '15kVA': {'abonnement': 282.00, 'prix_hp': 0.2700, 'prix_hc': 0.2068},
    }
    
    # Plages Heures Creuses standard Enedis (22h-6h)
    # 8 heures consÃ©cutives la nuit
    PLAGES_HC_STANDARD = {
        'debut': 22,  # 22h
        'fin': 6,     # 6h du matin
        'duree': 8    # 8 heures
    }
    
    # Facteurs selon annÃ©e de construction (isolation)
    FACTEURS_ISOLATION = [
        (2013, 0.85, 'RT2012'),
        (2005, 1.00, 'RT2005'),
        (1988, 1.15, 'RT1988'),
        (1974, 1.30, 'RT1974'),
        (0, 1.50, 'Avant 1974'),
    ]
    
    def __init__(self, data: Dict):
        """
        Initialise le calculateur.
        
        Args:
            data: Dictionnaire avec tous les paramÃ¨tres
                {
                    'surface': 120,
                    'nb_personnes': 4,
                    'dpe': 'D',
                    'annee_construction': 1995,
                    'latitude': 48.8566,
                    'longitude': 2.3522,
                    'type_chauffage': 'electrique',
                    'temperature_consigne': 19,
                    'type_vmc': 'simple_flux',
                    'type_ecs': 'ballon_electrique',
                    'capacite_ecs': 200,
                    ...
                }
        """
        self.data = data
        self.surface = data.get('surface', 100)
        self.nb_personnes = data.get('nb_personnes', 2)
        self.dpe = data.get('dpe', 'D')
        self.annee_construction = data.get('annee_construction', 2000)
        
        # DÃ©tection automatique de la zone climatique
        self.zone_climatique = self._detect_zone_climatique()
        
        logger.info(
            f"ðŸ“Š Init calculateur: {self.surface}mÂ², {self.nb_personnes} pers, "
            f"DPE {self.dpe}, Zone {self.zone_climatique}"
        )
    
    def _detect_zone_climatique(self) -> str:
        """
        DÃ©tecte la zone climatique H1/H2/H3 selon latitude.
        
        Carte simplifiÃ©e :
        - H1 (Nord) : lat > 48.5Â°
        - H2 (Centre) : 44Â° < lat â‰¤ 48.5Â°
        - H3 (Sud) : lat â‰¤ 44Â°
        """
        lat = self.data.get('latitude')
        
        if lat is None:
            logger.warning("Latitude non fournie, zone H2 par dÃ©faut")
            return 'H2'
        
        if lat > 48.5:
            return 'H1'  # Nord (Lille, Strasbourg)
        elif lat > 44.0:
            return 'H2'  # Centre (Paris, Lyon)
        else:
            return 'H3'  # Sud (Marseille, Toulouse)
    
    def calculate_chauffage(self) -> Dict:
        """
        Calcule la consommation de chauffage.
        
        BasÃ© sur :
        - DPE (besoins Ã©nergÃ©tiques du bÃ¢timent)
        - Zone climatique
        - AnnÃ©e de construction (isolation)
        - Type de chauffage (Ã©lectrique, PAC, autre)
        - VMC (simple/double flux)
        - TempÃ©rature de consigne
        
        Returns:
            {
                'annuel': 8500,  # kWh/an
                'mensuel': [1200, 1100, 900, ...],  # 12 valeurs
                'details': {...}
            }
        """
        type_chauffage = self.data.get('type_chauffage', 'electrique')
        
        # âœ… Normaliser les variantes de pompe Ã  chaleur
        if type_chauffage in ['pompe_chaleur', 'pompe_a_chaleur', 'PAC']:
            type_chauffage = 'pac'

        # Si non Ã©lectrique, consommation Ã©lectrique = 0
        if type_chauffage not in ['electrique', 'pac']:
            logger.info(f"Chauffage {type_chauffage} (non Ã©lectrique)")
            return {
                'annuel': 0,
                'mensuel': [0] * 12,
                'details': {'type': type_chauffage, 'electrique': False}
            }
        
        # 1. Besoin de base selon DPE (Ã©nergie PRIMAIRE)
        besoin_dpe_primaire = self.BESOINS_DPE[self.dpe] * self.surface
        logger.debug(f"  Besoin DPE {self.dpe} (primaire): {besoin_dpe_primaire:.0f} kWh")
        
        # 1b. Conversion Ã©nergie primaire â†’ finale
        # IMPORTANT : Le DPE est en Ã©nergie PRIMAIRE, il faut convertir en FINALE
        coef_conversion = self.COEFFICIENTS_PRIMAIRE_FINALE.get(type_chauffage, 2.58)
        besoin_base = besoin_dpe_primaire / coef_conversion
        logger.debug(f"  Conversion primaireâ†’finale (Ã·{coef_conversion}): {besoin_base:.0f} kWh")
        
        # 2. Correction zone climatique
        facteur_zone = self.FACTEURS_ZONE[self.zone_climatique]
        besoin_base *= facteur_zone
        logger.debug(f"  AprÃ¨s zone {self.zone_climatique} (Ã—{facteur_zone}): {besoin_base:.0f} kWh")
        
        # 3. Correction selon annÃ©e construction (isolation)
        facteur_iso = self._get_facteur_isolation()
        besoin_base *= facteur_iso
