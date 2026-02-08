"""
Calculateur de consommation MODE EXPERT.
HÃ©rite du ConsumptionCalculator et ajoute les calculs dÃ©taillÃ©s par appareil.
"""

import logging
from typing import Dict, List, Tuple
from .consumption_calculator import ConsumptionCalculator

logger = logging.getLogger(__name__)


class ExpertConsumptionCalculator(ConsumptionCalculator):
    """
    Calculateur expert avec appareils dÃ©taillÃ©s.
    
    HÃ©rite de ConsumptionCalculator pour rÃ©utiliser :
    - Calcul chauffage
    - Calcul ECS
    - Calcul cuisson
    - Zone climatique
    - Facteurs DPE
    
    Ajoute :
    - Calculs dÃ©taillÃ©s Ã©lectromÃ©nager
    - Calculs dÃ©taillÃ©s audiovisuel
    - Calculs dÃ©taillÃ©s Ã©clairage
    - Piscine, spa, vÃ©hicule Ã©lectrique
    - Profils horaires
    - Optimisation HP/HC
    - Projection 10 ans
    """
    
    # ========== DONNÃ‰ES DE RÃ‰FÃ‰RENCE ==========
    
    # RÃ©frigÃ©rateurs (kWh/an base)
    CONSO_FRIGOS = {
        'simple': 250,
        'combine': 300,
        'americain': 500,
    }
    
    # CongÃ©lateurs (kWh/an base)
    CONSO_CONGELATEURS = {
        'coffre': 250,
        'armoire': 300,
    }
    
    # Facteurs classe Ã©nergÃ©tique
    FACTEURS_CLASSE = {
        'A+++': 0.70,
        'A++': 0.85,
        'A+': 1.00,
        'A': 1.15,
        'B': 1.30,
        'C': 1.40,
    }
    
    # Lave-linge (kWh/cycle)
    CONSO_LAVE_LINGE = {
        'A+++': 0.45,
        'A++': 0.60,
        'A+': 0.80,
        'A': 1.00,
        'B': 1.20,
    }
    
    # Lave-vaisselle (kWh/cycle)
    CONSO_LAVE_VAISSELLE = {
        'A+++': 0.70,
        'A++': 0.90,
        'A+': 1.10,
        'A': 1.40,
        'B': 1.60,
    }
    
    # SÃ¨che-linge (kWh/cycle)
    CONSO_SECHE_LINGE = {
        'pompe_chaleur_A+++': 1.5,
        'pompe_chaleur_A++': 2.0,
        'condensation_A+': 3.5,
        'evacuation': 4.5,
    }
    
    # Four (kWh/an base)
    CONSO_FOUR_BASE = {
        'micro_ondes': 100,
        'four_electrique': 150,
        'four_combine': 200,
    }
    
    FACTEURS_USAGE_FOUR = {
        'rarement': 1.0,
        'occasionnel': 2.0,
        'regulier': 3.0,
        'intensif': 4.0,
    }
    
    # TV (Watts selon taille)
    PUISSANCE_TV = {
        'petit': 50,    # < 32"
        'moyen': 80,    # 32-43"
        'grand': 120,   # 43-55"
        'tres_grand': 150,  # 55-65"
        'xxl': 200,     # > 65"
    }
    
    FACTEURS_TECHNO_TV = {
        'led': 1.0,
        'oled': 1.2,
    }
    
    # Box internet
    CONSO_BOX = {
        'seule': 150,
        'avec_decodeur': 200,
    }
    
    # Ordinateurs (Watts)
    PUISSANCE_ORDI = {
        'fixe': 200,
        'portable': 50,
    }
    
    # Consoles (Watts)
    PUISSANCE_CONSOLE = {
        'ancienne': 150,
        'actuelle': 200,
    }
    
    # Spa (kWh/an base)
    CONSO_SPA_BASE = {
        'gonflable': 2000,
        'rigide': 3000,
        'interieur': 4000,
    }
    
    # Profils horaires (coefficient par tranche horaire)
    PROFILS_HORAIRES = {
        'actif_absent': {
            'nuit': 0.1,      # 0-6h
            'matin': 0.8,     # 6-8h
            'journee': 0.2,   # 8-18h
            'soir': 1.0,      # 18-22h
            'fin_soir': 0.3,  # 22-24h
        },
        'teletravail_partiel': {
            'nuit': 0.1,
            'matin': 0.9,
            'journee': 0.5,   # PrÃ©sence partielle
            'soir': 1.0,
            'fin_soir': 0.4,
        },
        'teletravail_complet': {
            'nuit': 0.1,
            'matin': 0.9,
            'journee': 0.8,   # PrÃ©sence complÃ¨te
            'soir': 1.0,
            'fin_soir': 0.4,
        },
        'retraite': {
            'nuit': 0.1,
            'matin': 0.9,
            'journee': 0.7,   # PrÃ©sence forte
            'soir': 0.9,
            'fin_soir': 0.3,
        },
    }
    
    def __init__(self, data: Dict):
        """Initialise le calculateur expert."""
        super().__init__(data)
        
        # Stocker les appareils dÃ©taillÃ©s
        self.appareils = []
        
        logger.info(f"ðŸ”¬ Calculateur EXPERT initialisÃ© pour {self.surface}mÂ², {self.nb_personnes} pers")
    
    # ========== RÃ‰FRIGÃ‰RATION ==========
    
    def calculate_refrigeration(self) -> List[Dict]:
        """Calcule la consommation des frigos et congÃ©lateurs."""
        appareils = []
        
        # RÃ©frigÃ©rateurs
        frigos = self.data.get('frigos', [])
        for i, frigo in enumerate(frigos):
            type_frigo = frigo.get('type')
            nombre = frigo.get('nombre', 1)
            classe = frigo.get('classe', 'A+')
            
            if type_frigo and type_frigo != 'aucun':
                conso_base = self.CONSO_FRIGOS.get(type_frigo, 300)
                facteur_classe = self.FACTEURS_CLASSE.get(classe, 1.0)
                conso_annuelle = conso_base * facteur_classe * nombre
                
                appareils.append({
                    'categorie': 'refrigeration',
                    'type_appareil': f'frigo_{type_frigo}',
                    'nom_affichage': f'RÃ©frigÃ©rateur {type_frigo.title()} {classe}',
