"""
Profils de consommation horaire par type d'usage.

Ce module fournit des profils de consommation rÃ©alistes basÃ©s sur
diffÃ©rents types d'usage (actif, tÃ©lÃ©travail, retraitÃ©, famille).

App Django: solar_calc
"""

import numpy as np
from typing import Tuple, Dict


class ConsumptionProfiles:
    """
    Profils de consommation Ã©lectrique par type d'utilisateur.
    
    Chaque profil dÃ©finit la consommation relative par heure (0-1).
    Structure : 24 heures divisÃ©es en 4 pÃ©riodes :
    - Nuit : 0h-5h (6 heures)
    - Matin : 6h-8h (3 heures)  
    - JournÃ©e : 9h-17h (9 heures)
    - Soir : 18h-23h (6 heures)
    """
    
    # Profils par type d'usage
    PROFILES = {
        'actif_absent': {
            'description': 'Actif absent en journÃ©e (travail externe)',
            'semaine': {
                'nuit': [0.3, 0.3, 0.3, 0.3, 0.3, 0.4],        # 0h-5h (6 valeurs)
                'matin': [0.7, 1.2, 1.0],                       # 6h-8h (3 valeurs)
                'journee': [0.6, 0.5, 0.4, 0.4, 0.4, 0.5, 0.6, 0.7, 0.8],  # 9h-17h (9 valeurs)
                'soir': [0.9, 1.5, 1.3, 1.1, 0.9, 0.6]         # 18h-23h (6 valeurs) âœ… CORRIGÃ‰
            },
            'weekend': {
                'nuit': [0.3, 0.3, 0.3, 0.3, 0.3, 0.4],
                'matin': [0.6, 0.8, 0.9],
                'journee': [0.7, 0.8, 0.7, 0.8, 0.7, 0.6, 0.6, 0.7, 0.8],
                'soir': [0.9, 1.2, 1.0, 0.8, 0.6, 0.5]         # âœ… CORRIGÃ‰
            }
        },
        
        'teletravail': {
            'description': 'TÃ©lÃ©travail ou prÃ©sence journÃ©e',
            'semaine': {
                'nuit': [0.3, 0.3, 0.3, 0.3, 0.3, 0.4],
                'matin': [0.7, 1.0, 0.9],
                'journee': [0.6, 0.6, 0.5, 0.6, 0.6, 0.7, 0.7, 0.8, 0.8],  # PrÃ©sent
                'soir': [0.9, 1.3, 1.1, 0.9, 0.7, 0.5]         # âœ… CORRIGÃ‰
            },
            'weekend': {
                'nuit': [0.3, 0.3, 0.3, 0.3, 0.3, 0.4],
                'matin': [0.6, 0.8, 0.9],
                'journee': [0.7, 0.8, 0.7, 0.8, 0.7, 0.6, 0.6, 0.7, 0.8],
                'soir': [0.9, 1.2, 1.0, 0.8, 0.6, 0.5]         # âœ… CORRIGÃ‰
            }
        },
        
        'retraite': {
            'description': 'RetraitÃ© prÃ©sent toute la journÃ©e',
            'semaine': {
                'nuit': [0.3, 0.3, 0.3, 0.3, 0.3, 0.4],
                'matin': [0.6, 0.8, 0.7],
                'journee': [0.7, 0.7, 0.6, 0.7, 0.7, 0.7, 0.6, 0.7, 0.8],  # Toujours prÃ©sent
                'soir': [0.9, 1.1, 0.9, 0.7, 0.6, 0.5]         # âœ… CORRIGÃ‰
            },
            'weekend': {
                'nuit': [0.3, 0.3, 0.3, 0.3, 0.3, 0.4],
                'matin': [0.6, 0.8, 0.7],
                'journee': [0.7, 0.7, 0.6, 0.7, 0.7, 0.7, 0.6, 0.7, 0.8],
                'soir': [0.9, 1.1, 0.9, 0.7, 0.6, 0.5]         # âœ… CORRIGÃ‰
            }
        },
        
        'famille': {
            'description': 'Famille avec enfants (pics matin/soir)',
            'semaine': {
                'nuit': [0.3, 0.3, 0.3, 0.3, 0.3, 0.5],        # RÃ©veil plus tÃ´t
                'matin': [0.9, 1.3, 1.2],                       # Rush matinal
                'journee': [0.6, 0.5, 0.4, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9],
                'soir': [1.0, 1.6, 1.4, 1.2, 1.0, 0.7]         # Rush soir âœ… CORRIGÃ‰
            },
            'weekend': {
                'nuit': [0.3, 0.3, 0.3, 0.3, 0.3, 0.4],
                'matin': [0.7, 0.9, 1.0],
                'journee': [0.8, 0.9, 0.8, 0.9, 0.8, 0.7, 0.7, 0.8, 0.9],
                'soir': [1.0, 1.3, 1.1, 0.9, 0.7, 0.6]         # âœ… CORRIGÃ‰
            }
        }
    }
    
    @classmethod
    def get_daily_pattern(cls, profile_type: str, is_weekend: bool) -> np.ndarray:
        """
        Retourne le pattern journalier (24 valeurs).
        
        Args:
            profile_type: Type de profil ('actif_absent', 'teletravail', etc.)
            is_weekend: True si weekend
        
        Returns:
            np.ndarray: Pattern de 24 valeurs
        """
        if profile_type not in cls.PROFILES:
            profile_type = 'actif_absent'
        
        profile = cls.PROFILES[profile_type]
        day_type = 'weekend' if is_weekend else 'semaine'
        day_config = profile[day_type]
        
        # Assembler 24h
        pattern = (
            day_config['nuit'] +      # 0h-5h (6 valeurs)
            day_config['matin'] +     # 6h-8h (3 valeurs)
            day_config['journee'] +   # 9h-17h (9 valeurs)
            day_config['soir']        # 18h-23h (6 valeurs)
        )
        
        pattern_array = np.array(pattern)
        
        # VÃ©rification de sÃ©curitÃ©
        assert len(pattern_array) == 24, f"Pattern should have 24 values, got {len(pattern_array)}"
        
        return pattern_array
    
    @classmethod
    def generate_yearly_pattern(
        cls,
        profile_type: str = 'actif_absent',
        add_randomness: bool = True,
        random_seed: int = None
    ) -> np.ndarray:
        """
        GÃ©nÃ¨re un pattern annuel (8760h) avec weekends et variation.
        
        Args:
            profile_type: Type de profil
            add_randomness: Ajouter variation alÃ©atoire Â±10%
            random_seed: Graine pour reproductibilitÃ© (optionnel)
        
        Returns:
            np.ndarray: Pattern de 8760 valeurs
        """
        if random_seed is not None:
            np.random.seed(random_seed)
        
        yearly = []
        
        for day in range(365):
            # DÃ©terminer si weekend
            # Jour 0 = Lundi (arbitraire)
            is_weekend = (day % 7) in [5, 6]  # Samedi, Dimanche
            
            # Pattern du jour
            daily = cls.get_daily_pattern(profile_type, is_weekend)
            
            # Ajouter variation alÃ©atoire
            if add_randomness:
                variation = np.random.uniform(0.90, 1.10, 24)
                daily = daily * variation
            
            yearly.extend(daily.tolist())
        
        return np.array(yearly)

    @classmethod
    def optimize_for_solar(
        cls, 
        base_pattern: np.ndarray,
        optimization_level: str = 'standard'
    ) -> Tuple[np.ndarray, Dict]:
        """
        Optimise un profil de consommation pour maximiser l'autoconsommation solaire.
        
        DÃ©place les consommations programmables (Ã©lectromÃ©nager, charge ECS, VE)
        vers les heures de production solaire (10h-16h).
        
        Args:
            base_pattern: Profil de base (8760 valeurs en kW)
            optimization_level: 'standard' (30%), 'agressif' (50%), 'maximal' (70%)
        
        Returns:
            Tuple[np.ndarray, Dict]: (profil_optimisÃ©, dÃ©tails_optimisation)
        
        Example:
            >>> pattern = ConsumptionProfiles.generate_yearly_pattern('actif_absent')
            >>> optimized, details = ConsumptionProfiles.optimize_for_solar(pattern)
            >>> print(f"Ã‰nergie dÃ©placÃ©e : {details['energy_shifted_kwh']:.0f} kWh/an")
        """
        optimized = base_pattern.copy()
        
        # Pourcentage de consommation Ã  dÃ©placer selon le niveau
        shift_ratios = {
            'standard': 0.30,   # 30% des appareils programmables
            'agressif': 0.50,   # 50%
            'maximal': 0.70     # 70%
        }
        shift_ratio = shift_ratios.get(optimization_level, 0.30)
        
