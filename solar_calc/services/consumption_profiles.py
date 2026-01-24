"""
Profils de consommation horaire par type d'usage.

Ce module fournit des profils de consommation réalistes basés sur
différents types d'usage (actif, télétravail, retraité, famille).

App Django: solar_calc
"""

import numpy as np
from typing import Dict


class ConsumptionProfiles:
    """
    Profils de consommation électrique par type d'utilisateur.
    
    Chaque profil définit la consommation relative par heure (0-1).
    Structure : 24 heures divisées en 4 périodes :
    - Nuit : 0h-5h (6 heures)
    - Matin : 6h-8h (3 heures)  
    - Journée : 9h-17h (9 heures)
    - Soir : 18h-23h (6 heures)
    """
    
    # Profils par type d'usage
    PROFILES = {
        'actif_absent': {
            'description': 'Actif absent en journée (travail externe)',
            'semaine': {
                'nuit': [0.3, 0.3, 0.3, 0.3, 0.3, 0.4],        # 0h-5h (6 valeurs)
                'matin': [0.7, 1.2, 1.0],                       # 6h-8h (3 valeurs)
                'journee': [0.6, 0.5, 0.4, 0.4, 0.4, 0.5, 0.6, 0.7, 0.8],  # 9h-17h (9 valeurs)
                'soir': [0.9, 1.5, 1.3, 1.1, 0.9, 0.6]         # 18h-23h (6 valeurs) ✅ CORRIGÉ
            },
            'weekend': {
                'nuit': [0.3, 0.3, 0.3, 0.3, 0.3, 0.4],
                'matin': [0.6, 0.8, 0.9],
                'journee': [0.7, 0.8, 0.7, 0.8, 0.7, 0.6, 0.6, 0.7, 0.8],
                'soir': [0.9, 1.2, 1.0, 0.8, 0.6, 0.5]         # ✅ CORRIGÉ
            }
        },
        
        'teletravail': {
            'description': 'Télétravail ou présence journée',
            'semaine': {
                'nuit': [0.3, 0.3, 0.3, 0.3, 0.3, 0.4],
                'matin': [0.7, 1.0, 0.9],
                'journee': [0.6, 0.6, 0.5, 0.6, 0.6, 0.7, 0.7, 0.8, 0.8],  # Présent
                'soir': [0.9, 1.3, 1.1, 0.9, 0.7, 0.5]         # ✅ CORRIGÉ
            },
            'weekend': {
                'nuit': [0.3, 0.3, 0.3, 0.3, 0.3, 0.4],
                'matin': [0.6, 0.8, 0.9],
                'journee': [0.7, 0.8, 0.7, 0.8, 0.7, 0.6, 0.6, 0.7, 0.8],
                'soir': [0.9, 1.2, 1.0, 0.8, 0.6, 0.5]         # ✅ CORRIGÉ
            }
        },
        
        'retraite': {
            'description': 'Retraité présent toute la journée',
            'semaine': {
                'nuit': [0.3, 0.3, 0.3, 0.3, 0.3, 0.4],
                'matin': [0.6, 0.8, 0.7],
                'journee': [0.7, 0.7, 0.6, 0.7, 0.7, 0.7, 0.6, 0.7, 0.8],  # Toujours présent
                'soir': [0.9, 1.1, 0.9, 0.7, 0.6, 0.5]         # ✅ CORRIGÉ
            },
            'weekend': {
                'nuit': [0.3, 0.3, 0.3, 0.3, 0.3, 0.4],
                'matin': [0.6, 0.8, 0.7],
                'journee': [0.7, 0.7, 0.6, 0.7, 0.7, 0.7, 0.6, 0.7, 0.8],
                'soir': [0.9, 1.1, 0.9, 0.7, 0.6, 0.5]         # ✅ CORRIGÉ
            }
        },
        
        'famille': {
            'description': 'Famille avec enfants (pics matin/soir)',
            'semaine': {
                'nuit': [0.3, 0.3, 0.3, 0.3, 0.3, 0.5],        # Réveil plus tôt
                'matin': [0.9, 1.3, 1.2],                       # Rush matinal
                'journee': [0.6, 0.5, 0.4, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9],
                'soir': [1.0, 1.6, 1.4, 1.2, 1.0, 0.7]         # Rush soir ✅ CORRIGÉ
            },
            'weekend': {
                'nuit': [0.3, 0.3, 0.3, 0.3, 0.3, 0.4],
                'matin': [0.7, 0.9, 1.0],
                'journee': [0.8, 0.9, 0.8, 0.9, 0.8, 0.7, 0.7, 0.8, 0.9],
                'soir': [1.0, 1.3, 1.1, 0.9, 0.7, 0.6]         # ✅ CORRIGÉ
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
        
        # Vérification de sécurité
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
        Génère un pattern annuel (8760h) avec weekends et variation.
        
        Args:
            profile_type: Type de profil
            add_randomness: Ajouter variation aléatoire ±10%
            random_seed: Graine pour reproductibilité (optionnel)
        
        Returns:
            np.ndarray: Pattern de 8760 valeurs
        """
        if random_seed is not None:
            np.random.seed(random_seed)
        
        yearly = []
        
        for day in range(365):
            # Déterminer si weekend
            # Jour 0 = Lundi (arbitraire)
            is_weekend = (day % 7) in [5, 6]  # Samedi, Dimanche
            
            # Pattern du jour
            daily = cls.get_daily_pattern(profile_type, is_weekend)
            
            # Ajouter variation aléatoire
            if add_randomness:
                variation = np.random.uniform(0.90, 1.10, 24)
                daily = daily * variation
            
            yearly.extend(daily.tolist())
        
        return np.array(yearly)
    
    @classmethod
    def get_available_profiles(cls) -> Dict[str, str]:
        """Retourne la liste des profils disponibles."""
        return {
            key: value['description']
            for key, value in cls.PROFILES.items()
        }
    
    @classmethod
    def validate_profiles(cls) -> Dict[str, bool]:
        """
        Valide que tous les profils ont exactement 24 valeurs.
        
        Returns:
            Dict avec le statut de validation de chaque profil
        """
        validation = {}
        
        for profile_name in cls.PROFILES.keys():
            try:
                # Tester weekday
                pattern_weekday = cls.get_daily_pattern(profile_name, False)
                # Tester weekend
                pattern_weekend = cls.get_daily_pattern(profile_name, True)
                
                validation[profile_name] = (
                    len(pattern_weekday) == 24 and 
                    len(pattern_weekend) == 24
                )
            except Exception as e:
                validation[profile_name] = False
                print(f"Erreur pour {profile_name}: {e}")
        
        return validation


# Fonction helper pour compatibilité
def get_consumption_pattern(profile_type: str = 'actif_absent') -> np.ndarray:
    """
    Fonction helper pour génération rapide.
    
    Args:
        profile_type: Type de profil
    
    Returns:
        np.ndarray: Pattern annuel (8760 valeurs)
    """
    return ConsumptionProfiles.generate_yearly_pattern(profile_type)


# Auto-validation au chargement du module
if __name__ == '__main__':
    print("🔍 Validation des profils de consommation...")
    validation = ConsumptionProfiles.validate_profiles()
    
    all_valid = all(validation.values())
    
    if all_valid:
        print("✅ Tous les profils sont valides (24 valeurs)")
    else:
        print("❌ Certains profils sont invalides:")
        for profile, is_valid in validation.items():
            status = "✅" if is_valid else "❌"
            print(f"  {status} {profile}")
    
    # Afficher les profils disponibles
    print("\n📋 Profils disponibles:")
    for key, desc in ConsumptionProfiles.get_available_profiles().items():
        print(f"  • {key}: {desc}")