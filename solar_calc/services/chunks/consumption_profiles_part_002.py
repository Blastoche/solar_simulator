        # Compteurs pour le rapport
        total_shifted = 0
        
        for day in range(365):
            day_start = day * 24
            
            # Heures Ã  vider (nuit profonde + soirÃ©e tardive)
            # On Ã©vite :
            # - 6h-8h (matin, prÃ©paration)
            # - 18h-20h (retour maison, prÃ©paration dÃ®ner)
            source_hours = list(range(0, 6)) + list(range(21, 24))
            
            # Heures solaires optimales (pic de production)
            target_hours = list(range(10, 16))  # 10h-16h
            
            # Calculer la consommation dÃ©plaÃ§able
            source_consumption = sum(optimized[day_start + h] for h in source_hours)
            to_shift = source_consumption * shift_ratio
            
            # RÃ©duire les heures sources proportionnellement
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
                'SÃ¨che-linge',
                'Chauffe-eau Ã©lectrique',
                'Charge vÃ©hicule Ã©lectrique',
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
        GÃ©nÃ¨re un profil de consommation horaire PERSONNALISÃ‰ basÃ© sur :
        - Le profil type (actif_absent, teletravail, etc.)
        - Les VRAIS appareils de l'utilisateur avec leurs heures d'utilisation
        
        Args:
            profile_type: Type de profil de base ('actif_absent', 'teletravail', 'retraite', 'famille')
            consommation_totale: Consommation annuelle totale en kWh
            appareils_data: Dictionnaire avec les appareils rÃ©els de l'utilisateur
            optimized: Si True, utilise les heures optimales au lieu des heures habituelles
        
        Returns:
            np.ndarray: Pattern de 8760 valeurs (kW) personnalisÃ© et normalisÃ©
        
        Example:
            >>> appareils = {
            ...     'ecs': {'type': 'chauffe_eau_electrique', 'heure_habituelle': 2, 'heure_optimale': 12},
            ...     'lave_linge': {'present': True, 'heure_habituelle': 20, 'heure_optimale': 12}
            ... }
            >>> pattern = ConsumptionProfiles.generate_personalized_pattern(
            ...     'actif_absent', 5000, appareils, optimized=False
            ... )
        """
        
        # 1. GÃ©nÃ©rer le profil de base (comportement gÃ©nÃ©ral)
        base_pattern = cls.generate_yearly_pattern(profile_type, add_randomness=False)
        
        # 2. CrÃ©er un pattern pour les appareils spÃ©cifiques
        # Ce pattern contiendra les pics de consommation des appareils identifiÃ©s
        specific_pattern = np.zeros(8760)
        
        # Estimer la part de consommation "de base" vs "appareils programmables"
        # Base = frigo, Ã©clairage, box, veilles, etc. (environ 40% de la conso)
        # Appareils = tout ce qui est programmable (environ 60%)
        base_consumption_ratio = 0.40
        
        # 3. Ajouter les pics de chaque appareil
        
        # === CHAUFFE-EAU Ã‰LECTRIQUE ===
        if 'ecs' in appareils_data:
            ecs = appareils_data['ecs']
            if ecs.get('type') in ['chauffe_eau_electrique', 'electrique']:
                # CaractÃ©ristiques moyennes chauffe-eau Ã©lectrique
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
            
            # RÃ©partir les cycles sur la semaine
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
        
        # === SÃˆCHE-LINGE ===
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
        
        # === VÃ‰HICULE Ã‰LECTRIQUE ===
        if 'vehicule_electrique' in appareils_data and appareils_data['vehicule_electrique'].get('present'):
            puissance_kw = 3.7  # Wallbox 16A monophasÃ©
