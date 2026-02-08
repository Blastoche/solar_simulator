"""
Profils de consommation horaire par type d'usage.

Ce module fournit des profils de consommation réalistes basés sur
différents types d'usage (actif, télétravail, retraité, famille).

App Django: solar_calc
"""

import numpy as np
from typing import Tuple, Dict


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
    def optimize_for_solar(
        cls, 
        base_pattern: np.ndarray,
        optimization_level: str = 'standard'
    ) -> Tuple[np.ndarray, Dict]:
        """
        Optimise un profil de consommation pour maximiser l'autoconsommation solaire.
        
        Déplace les consommations programmables (électroménager, charge ECS, VE)
        vers les heures de production solaire (10h-16h).
        
        Args:
            base_pattern: Profil de base (8760 valeurs en kW)
            optimization_level: 'standard' (30%), 'agressif' (50%), 'maximal' (70%)
        
        Returns:
            Tuple[np.ndarray, Dict]: (profil_optimisé, détails_optimisation)
        
        Example:
            >>> pattern = ConsumptionProfiles.generate_yearly_pattern('actif_absent')
            >>> optimized, details = ConsumptionProfiles.optimize_for_solar(pattern)
            >>> print(f"Énergie déplacée : {details['energy_shifted_kwh']:.0f} kWh/an")
        """
        optimized = base_pattern.copy()
        
        # Pourcentage de consommation à déplacer selon le niveau
        shift_ratios = {
            'standard': 0.30,   # 30% des appareils programmables
            'agressif': 0.50,   # 50%
            'maximal': 0.70     # 70%
        }
        shift_ratio = shift_ratios.get(optimization_level, 0.30)
        
        # Compteurs pour le rapport
        total_shifted = 0
        
        for day in range(365):
            day_start = day * 24
            
            # Heures à vider (nuit profonde + soirée tardive)
            # On évite :
            # - 6h-8h (matin, préparation)
            # - 18h-20h (retour maison, préparation dîner)
            source_hours = list(range(0, 6)) + list(range(21, 24))
            
            # Heures solaires optimales (pic de production)
            target_hours = list(range(10, 16))  # 10h-16h
            
            # Calculer la consommation déplaçable
            source_consumption = sum(optimized[day_start + h] for h in source_hours)
            to_shift = source_consumption * shift_ratio
            
            # Réduire les heures sources proportionnellement
            reduction_per_hour = to_shift / len(source_hours)
            for h in source_hours:
                optimized[day_start + h] = max(0, optimized[day_start + h] - reduction_per_hour)
            
            # Augmenter les heures cibles (pic solaire)
            boost_per_hour = to_shift / len(target_hours)
            for h in target_hours:
                optimized[day_start + h] += boost_per_hour
            
            total_shifted += to_shift
        
        # Rapport d'optimisation
        details = {
            'energy_shifted_kwh': round(total_shifted, 2),
            'shift_ratio': shift_ratio * 100,  # En pourcentage
            'optimization_level': optimization_level,
            'source_hours': '0h-6h, 21h-24h',
            'target_hours': '10h-16h',
            'appareils_types': [
                'Lave-linge',
                'Lave-vaisselle',
                'Sèche-linge',
                'Chauffe-eau électrique',
                'Charge véhicule électrique',
                'Filtration piscine'
            ]
        }
        
        return optimized, details

    @classmethod
    def generate_personalized_pattern(
        cls,
        profile_type: str,
        consommation_totale: float,
        appareils_data: Dict,
        optimized: bool = False
    ) -> np.ndarray:
        """
        Génère un profil de consommation horaire PERSONNALISÉ basé sur :
        - Le profil type (actif_absent, teletravail, etc.)
        - Les VRAIS appareils de l'utilisateur avec leurs heures d'utilisation
        
        Args:
            profile_type: Type de profil de base ('actif_absent', 'teletravail', 'retraite', 'famille')
            consommation_totale: Consommation annuelle totale en kWh
            appareils_data: Dictionnaire avec les appareils réels de l'utilisateur
            optimized: Si True, utilise les heures optimales au lieu des heures habituelles
        
        Returns:
            np.ndarray: Pattern de 8760 valeurs (kW) personnalisé et normalisé
        
        Example:
            >>> appareils = {
            ...     'ecs': {'type': 'chauffe_eau_electrique', 'heure_habituelle': 2, 'heure_optimale': 12},
            ...     'lave_linge': {'present': True, 'heure_habituelle': 20, 'heure_optimale': 12}
            ... }
            >>> pattern = ConsumptionProfiles.generate_personalized_pattern(
            ...     'actif_absent', 5000, appareils, optimized=False
            ... )
        """
        
        # 1. Générer le profil de base (comportement général)
        base_pattern = cls.generate_yearly_pattern(profile_type, add_randomness=False)
        
        # 2. Créer un pattern pour les appareils spécifiques
        # Ce pattern contiendra les pics de consommation des appareils identifiés
        specific_pattern = np.zeros(8760)
        
        # Estimer la part de consommation "de base" vs "appareils programmables"
        # Base = frigo, éclairage, box, veilles, etc. (environ 40% de la conso)
        # Appareils = tout ce qui est programmable (environ 60%)
        base_consumption_ratio = 0.40
        
        # 3. Ajouter les pics de chaque appareil
        
        # === CHAUFFE-EAU ÉLECTRIQUE ===
        if 'ecs' in appareils_data:
            ecs = appareils_data['ecs']
            if ecs.get('type') in ['chauffe_eau_electrique', 'electrique']:
                # Caractéristiques moyennes chauffe-eau électrique
                puissance_kw = 2.5  # 2500W
                duree_h = 4  # 4h de chauffe par jour
                
                # Choisir l'heure selon le mode
                if optimized:
                    heure = ecs.get('heure_optimale', 12)
                else:
                    heure = ecs.get('heure_habituelle', 2)
                
                # Ajouter le pic chaque jour
                for day in range(365):
                    for h in range(duree_h):
                        hour_index = day * 24 + (heure + h) % 24
                        specific_pattern[hour_index] += puissance_kw
        
        # === CHAUFFE-EAU THERMODYNAMIQUE ===
        if 'ecs' in appareils_data:
            ecs = appareils_data['ecs']
            if ecs.get('type') == 'thermodynamique':
                puissance_kw = 1.2  # Moins de puissance (COP ~2.5)
                duree_h = 3
                
                if optimized:
                    heure = ecs.get('heure_optimale', 12)
                else:
                    heure = ecs.get('heure_habituelle', 2)
                
                for day in range(365):
                    for h in range(duree_h):
                        hour_index = day * 24 + (heure + h) % 24
                        specific_pattern[hour_index] += puissance_kw
        
        # === LAVE-LINGE ===
        if 'lave_linge' in appareils_data and appareils_data['lave_linge'].get('present'):
            puissance_kw = 2.0  # 2000W
            duree_h = 2
            cycles_par_semaine = appareils_data['lave_linge'].get('cycles_par_semaine', 4)
            
            if optimized:
                heure = appareils_data['lave_linge'].get('heure_optimale', 12)
            else:
                heure = appareils_data['lave_linge'].get('heure_habituelle', 20)
            
            # Répartir les cycles sur la semaine
            jours_utilisation = [0, 2, 4, 6][:int(cycles_par_semaine)]  # Lundi, mercredi, vendredi, dimanche
            
            for week in range(52):
                for jour in jours_utilisation:
                    day = week * 7 + jour
                    if day < 365:
                        for h in range(duree_h):
                            hour_index = day * 24 + (heure + h) % 24
                            specific_pattern[hour_index] += puissance_kw
        
        # === LAVE-VAISSELLE ===
        if 'lave_vaisselle' in appareils_data and appareils_data['lave_vaisselle'].get('present'):
            puissance_kw = 1.8  # 1800W
            duree_h = 2.5
            cycles_par_semaine = appareils_data['lave_vaisselle'].get('cycles_par_semaine', 5)
            
            if optimized:
                heure = appareils_data['lave_vaisselle'].get('heure_optimale', 13)
            else:
                heure = appareils_data['lave_vaisselle'].get('heure_habituelle', 21)
            
            jours_utilisation = [0, 1, 2, 3, 4, 5, 6][:int(cycles_par_semaine)]
            
            for week in range(52):
                for jour in jours_utilisation:
                    day = week * 7 + jour
                    if day < 365:
                        for h in range(int(duree_h)):
                            hour_index = day * 24 + (heure + h) % 24
                            specific_pattern[hour_index] += puissance_kw
        
        # === SÈCHE-LINGE ===
        if 'seche_linge' in appareils_data and appareils_data['seche_linge'].get('present'):
            puissance_kw = 2.5  # 2500W
            duree_h = 1.5
            cycles_par_semaine = appareils_data['seche_linge'].get('cycles_par_semaine', 3)
            
            if optimized:
                heure = appareils_data['seche_linge'].get('heure_optimale', 14)
            else:
                heure = appareils_data['seche_linge'].get('heure_habituelle', 22)
            
            jours_utilisation = [0, 2, 4][:int(cycles_par_semaine)]
            
            for week in range(52):
                for jour in jours_utilisation:
                    day = week * 7 + jour
                    if day < 365:
                        for h in range(int(duree_h)):
                            hour_index = day * 24 + (heure + h) % 24
                            specific_pattern[hour_index] += puissance_kw
        
        # === VÉHICULE ÉLECTRIQUE ===
        if 'vehicule_electrique' in appareils_data and appareils_data['vehicule_electrique'].get('present'):
            puissance_kw = 3.7  # Wallbox 16A monophasé
            duree_h = 4  # Recharge moyenne
            jours_par_semaine = appareils_data['vehicule_electrique'].get('jours_par_semaine', 5)
            
            if optimized:
                heure = appareils_data['vehicule_electrique'].get('heure_optimale', 11)
            else:
                heure = appareils_data['vehicule_electrique'].get('heure_habituelle', 19)
            
            # Uniquement les jours de semaine généralement
            jours_utilisation = [0, 1, 2, 3, 4][:jours_par_semaine]
            
            for week in range(52):
                for jour in jours_utilisation:
                    day = week * 7 + jour
                    if day < 365:
                        for h in range(duree_h):
                            hour_index = day * 24 + (heure + h) % 24
                            specific_pattern[hour_index] += puissance_kw
        
        # === PISCINE - FILTRATION ===
        if 'piscine' in appareils_data and appareils_data['piscine'].get('present'):
            puissance_kw = 1.0  # Pompe de filtration
            duree_h = 8  # 8h de filtration par jour
            mois_utilisation = appareils_data['piscine'].get('mois_utilisation', 6)  # Mai à octobre
            
            if optimized:
                heure = appareils_data['piscine'].get('heure_optimale', 11)
            else:
                heure = appareils_data['piscine'].get('heure_habituelle', 6)
            
            # Filtration seulement pendant la saison (approximatif : jours 120 à 300)
            debut_saison = 120  # ~Mai
            fin_saison = debut_saison + (mois_utilisation * 30)
            
            for day in range(debut_saison, min(fin_saison, 365)):
                for h in range(duree_h):
                    hour_index = day * 24 + (heure + h) % 24
                    specific_pattern[hour_index] += puissance_kw
        
        # 4. Combiner le profil de base avec les appareils spécifiques
        # Le profil de base représente la consommation "incompressible" (40%)
        # Les appareils spécifiques représentent la consommation programmable (60%)
        
        # Normaliser le profil de base pour qu'il représente 40% de la conso
        base_normalized = base_pattern / base_pattern.sum() * (consommation_totale * base_consumption_ratio)
        
        # Normaliser les appareils pour qu'ils représentent 60% de la conso
        if specific_pattern.sum() > 0:
            specific_normalized = specific_pattern / specific_pattern.sum() * (consommation_totale * (1 - base_consumption_ratio))
        else:
            # Si aucun appareil spécifique, tout va dans le profil de base
            specific_normalized = np.zeros(8760)
            base_normalized = base_pattern / base_pattern.sum() * consommation_totale
        
        # Combiner
        combined_pattern = base_normalized + specific_normalized
        
        # 5. Vérification et ajustement final
        # S'assurer que la somme correspond exactement à la consommation totale
        final_pattern = combined_pattern / combined_pattern.sum() * consommation_totale
        
        return final_pattern


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