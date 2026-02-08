            duree_h = 4  # Recharge moyenne
            jours_par_semaine = appareils_data['vehicule_electrique'].get('jours_par_semaine', 5)
            
            if optimized:
                heure = appareils_data['vehicule_electrique'].get('heure_optimale', 11)
            else:
                heure = appareils_data['vehicule_electrique'].get('heure_habituelle', 19)
            
            # Uniquement les jours de semaine gÃ©nÃ©ralement
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
            mois_utilisation = appareils_data['piscine'].get('mois_utilisation', 6)  # Mai Ã  octobre
            
            if optimized:
                heure = appareils_data['piscine'].get('heure_optimale', 11)
            else:
                heure = appareils_data['piscine'].get('heure_habituelle', 6)
            
            # Filtration seulement pendant la saison (approximatif : jours 120 Ã  300)
            debut_saison = 120  # ~Mai
            fin_saison = debut_saison + (mois_utilisation * 30)
            
            for day in range(debut_saison, min(fin_saison, 365)):
                for h in range(duree_h):
                    hour_index = day * 24 + (heure + h) % 24
                    specific_pattern[hour_index] += puissance_kw
        
        # 4. Combiner le profil de base avec les appareils spÃ©cifiques
        # Le profil de base reprÃ©sente la consommation "incompressible" (40%)
        # Les appareils spÃ©cifiques reprÃ©sentent la consommation programmable (60%)
        
        # Normaliser le profil de base pour qu'il reprÃ©sente 40% de la conso
        base_normalized = base_pattern / base_pattern.sum() * (consommation_totale * base_consumption_ratio)
        
        # Normaliser les appareils pour qu'ils reprÃ©sentent 60% de la conso
        if specific_pattern.sum() > 0:
            specific_normalized = specific_pattern / specific_pattern.sum() * (consommation_totale * (1 - base_consumption_ratio))
        else:
            # Si aucun appareil spÃ©cifique, tout va dans le profil de base
            specific_normalized = np.zeros(8760)
            base_normalized = base_pattern / base_pattern.sum() * consommation_totale
        
        # Combiner
        combined_pattern = base_normalized + specific_normalized
        
        # 5. VÃ©rification et ajustement final
        # S'assurer que la somme correspond exactement Ã  la consommation totale
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


# Fonction helper pour compatibilitÃ©
def get_consumption_pattern(profile_type: str = 'actif_absent') -> np.ndarray:
    """
    Fonction helper pour gÃ©nÃ©ration rapide.
    
    Args:
        profile_type: Type de profil
    
    Returns:
        np.ndarray: Pattern annuel (8760 valeurs)
    """
    return ConsumptionProfiles.generate_yearly_pattern(profile_type)


# Auto-validation au chargement du module
if __name__ == '__main__':
    print("ðŸ” Validation des profils de consommation...")
    validation = ConsumptionProfiles.validate_profiles()
    
    all_valid = all(validation.values())
    
    if all_valid:
        print("âœ… Tous les profils sont valides (24 valeurs)")
    else:
        print("âŒ Certains profils sont invalides:")
        for profile, is_valid in validation.items():
            status = "âœ…" if is_valid else "âŒ"
            print(f"  {status} {profile}")
    
    # Afficher les profils disponibles
    print("\nðŸ“‹ Profils disponibles:")
    for key, desc in ConsumptionProfiles.get_available_profiles().items():
        print(f"  â€¢ {key}: {desc}")
