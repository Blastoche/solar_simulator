        
        logger.info(f"ðŸ› Spa {type_spa}: {conso_annuelle:.0f} kWh/an")
        
        return appareils
    
    # ========== VÃ‰HICULE Ã‰LECTRIQUE ==========
    
    def calculate_vehicule_electrique(self) -> List[Dict]:
        """Calcule la consommation vÃ©hicule Ã©lectrique."""
        appareils = []
        
        vehicules = self.data.get('vehicules', [])
        
        for i, ve in enumerate(vehicules):
            conso_100km = ve.get('conso_100km', 18)
            km_an = ve.get('km_an', 15000)
            type_recharge = ve.get('type_recharge', 'wallbox_7')
            pct_domicile = ve.get('pct_recharge_domicile', 100)
            
            # Rendements de charge
            rendements = {
                'prise': 0.85,
                'wallbox_7': 0.90,
                'wallbox_11': 0.92,
                'wallbox_22': 0.93,
            }
            rendement = rendements.get(type_recharge, 0.90)
            
            # Consommation vÃ©hicule
            conso_vehicule = (km_an / 100) * conso_100km
            
            # Part rechargÃ©e Ã  domicile
            conso_domicile = conso_vehicule * (pct_domicile / 100)
            
            # Pertes de charge
            conso_compteur = conso_domicile / rendement
            
            appareils.append({
                'categorie': 'vehicule',
                'type_appareil': 've',
                'nom_affichage': f'VÃ©hicule Ã©lectrique ({conso_100km} kWh/100km, {km_an} km/an)',
                'km_an': km_an,
                'conso_100km': conso_100km,
                'rendement_charge': rendement,
                'pct_recharge_domicile': pct_domicile,
                'consommation_annuelle': conso_compteur,
                'consommation_mensuelle': [conso_compteur / 12] * 12,
            })
            
            logger.info(f"ðŸš—âš¡ VE ({conso_100km} kWh/100km, {km_an} km/an): {conso_compteur:.0f} kWh/an")
        
        return appareils
    
    # ========== CALCUL TOTAL EXPERT ==========
    
    def calculate_total_expert(self) -> Dict:
        """Calcul complet mode expert."""
        
        # Appareils dÃ©taillÃ©s
        self.appareils = []
        
        # RÃ©frigÃ©ration
        self.appareils.extend(self.calculate_refrigeration())
        
        # Lavage
        self.appareils.extend(self.calculate_lavage())
        
        # Four
        self.appareils.extend(self.calculate_four_expert())
        
        # Audiovisuel
        self.appareils.extend(self.calculate_audiovisuel_expert())
        
        # Ã‰clairage
        self.appareils.extend(self.calculate_eclairage_expert())
        
        # Piscine
        self.appareils.extend(self.calculate_piscine())
        
        # Spa
        self.appareils.extend(self.calculate_spa())
        
        # VÃ©hicule Ã©lectrique
        self.appareils.extend(self.calculate_vehicule_electrique())
        
        # Chauffage (du parent)
        chauffage = self.calculate_chauffage()
        
        # ECS (du parent)
        ecs = self.calculate_ecs()
        
        # Cuisson (du parent - plaques uniquement)
        cuisson = self.calculate_forfait_cuisson()
        
        # Calculer totaux
        total_appareils = sum(app['consommation_annuelle'] for app in self.appareils)
        total_annuel = chauffage['annuel'] + ecs['annuel'] + cuisson['annuel'] + total_appareils
        
        # RÃ©partition
        repartition = {
            'chauffage': {
                'kwh': chauffage['annuel'],
                'pourcentage': round((chauffage['annuel'] / total_annuel * 100) if total_annuel > 0 else 0)
            },
            'ecs': {
                'kwh': ecs['annuel'],
                'pourcentage': round((ecs['annuel'] / total_annuel * 100) if total_annuel > 0 else 0)
            },
            'cuisson': {
                'kwh': cuisson['annuel'],
                'pourcentage': round((cuisson['annuel'] / total_annuel * 100) if total_annuel > 0 else 0)
            },
        }
        
        # Grouper appareils par catÃ©gorie pour rÃ©partition
        for categorie in ['refrigeration', 'lavage', 'audiovisuel', 'eclairage', 'piscine', 'spa', 'vehicule']:
            conso_cat = sum(app['consommation_annuelle'] for app in self.appareils if app['categorie'] == categorie)
            if conso_cat > 0:
                repartition[categorie] = {
                    'kwh': conso_cat,
                    'pourcentage': round((conso_cat / total_annuel * 100) if total_annuel > 0 else 0)
                }
        
        # Moyenne attendue
        moyenne_attendue = self._calculate_expected_consumption()
        ecart_pct = ((total_annuel - moyenne_attendue) / moyenne_attendue * 100) if moyenne_attendue > 0 else 0
        
        # Mensuel
        monthly = [0] * 12
        for mois in range(12):
            monthly[mois] = chauffage['mensuel'][mois] + ecs['mensuel'][mois] + cuisson['mensuel'][mois]
            for app in self.appareils:
                if app.get('consommation_mensuelle'):
                    monthly[mois] += app['consommation_mensuelle'][mois]
        
        logger.info(f"ðŸ“Š TOTAL EXPERT: {total_annuel:.0f} kWh/an ({len(self.appareils)} appareils dÃ©taillÃ©s)")
        
        return {
            'total_annuel': round(total_annuel, 0),
            'mensuel': [round(m, 0) for m in monthly],
            'moyenne_attendue': round(moyenne_attendue, 0),
            'ecart_pct': round(ecart_pct, 1),
            'repartition': repartition,
            'appareils': self.appareils,
            'details_postes': {
                'chauffage': chauffage['details'],
                'ecs': ecs['details'],
                'cuisson': cuisson['details'],
            }
        }
    
    # ========== OPTIMISATION HP/HC ==========
    
    def calculate_optimisation_hphc(self, total_annuel: float) -> Dict:
        """Calcule l'optimisation possible HP/HC selon profil."""
        profil = self.data.get('profil_usage', 'actif_absent')
        
        # % HC selon profil (estimation rÃ©aliste)
        pct_hc_profils = {
            'actif_absent': 37,
            'teletravail_partiel': 32,
            'teletravail_complet': 27,
            'retraite': 22,
        }
        
        pct_hc_actuel = pct_hc_profils.get(profil, 30)
        
        # Optimisation possible en programmant les appareils
        # (chauffe-eau, lave-linge, lave-vaisselle, VE en HC)
        pct_hc_optimal = min(pct_hc_actuel + 15, 55)  # Max 55%
        
        # Calcul Ã©conomie
        hc_actuel_kwh = total_annuel * (pct_hc_actuel / 100)
        hp_actuel_kwh = total_annuel - hc_actuel_kwh
        
        hc_optimal_kwh = total_annuel * (pct_hc_optimal / 100)
        hp_optimal_kwh = total_annuel - hc_optimal_kwh
        
        # Tarifs 2024
        prix_hp = 0.2700
        prix_hc = 0.2068
        
        cout_actuel = (hp_actuel_kwh * prix_hp) + (hc_actuel_kwh * prix_hc)
        cout_optimal = (hp_optimal_kwh * prix_hp) + (hc_optimal_kwh * prix_hc)
        
        economie = cout_actuel - cout_optimal
        
        return {
            'pct_hc_actuel': pct_hc_actuel,
            'pct_hc_optimal': pct_hc_optimal,
            'economie_annuelle': round(economie, 2),
            'profil': profil,
        }
    
    # ========== PROJECTION 10 ANS ==========
    
    def calculate_projection_10ans(self, total_annuel: float, cout_actuel: float) -> List[Dict]:
        """Projection consommation et coÃ»ts sur 10 ans."""
        inflation_energie = 0.05  # 5% par an
        evolution_conso = -0.01  # -1% par an (amÃ©lioration)
