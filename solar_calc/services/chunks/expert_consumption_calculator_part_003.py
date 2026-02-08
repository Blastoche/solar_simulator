                'categorie': 'audiovisuel',
                'type_appareil': 'ordinateur_fixe',
                'nom_affichage': f'Ordinateur fixe (Ã—{nb_fixes}, {heures_ordi}h/j)',
                'nombre': nb_fixes,
                'puissance_w': self.PUISSANCE_ORDI['fixe'],
                'heures_jour': heures_ordi,
                'consommation_annuelle': conso_fixes,
                'consommation_mensuelle': [conso_fixes / 12] * 12,
            })
            logger.info(f"ðŸ’» Ordis fixes (Ã—{nb_fixes}, {heures_ordi}h/j): {conso_fixes:.0f} kWh/an")
        
        if nb_portables > 0:
            conso_portables = self.PUISSANCE_ORDI['portable'] * nb_portables * heures_ordi * 365 / 1000
            appareils.append({
                'categorie': 'audiovisuel',
                'type_appareil': 'ordinateur_portable',
                'nom_affichage': f'Ordinateur portable (Ã—{nb_portables}, {heures_ordi}h/j)',
                'nombre': nb_portables,
                'puissance_w': self.PUISSANCE_ORDI['portable'],
                'heures_jour': heures_ordi,
                'consommation_annuelle': conso_portables,
                'consommation_mensuelle': [conso_portables / 12] * 12,
            })
            logger.info(f"ðŸ’» Ordis portables (Ã—{nb_portables}, {heures_ordi}h/j): {conso_portables:.0f} kWh/an")
        
        # Console
        if self.data.get('console_actif', False):
            type_console = self.data.get('type_console', 'actuelle')
            heures_console = self.data.get('heures_console', 2)
            
            puissance_console = self.PUISSANCE_CONSOLE.get(type_console, 200)
            conso_console = puissance_console * heures_console * 365 / 1000
            
            appareils.append({
                'categorie': 'audiovisuel',
                'type_appareil': f'console_{type_console}',
                'nom_affichage': f'Console {type_console} ({heures_console}h/j)',
                'puissance_w': puissance_console,
                'heures_jour': heures_console,
                'consommation_annuelle': conso_console,
                'consommation_mensuelle': [conso_console / 12] * 12,
            })
            logger.info(f"ðŸŽ® Console {type_console} ({heures_console}h/j): {conso_console:.0f} kWh/an")
        
        return appareils
    
    # ========== Ã‰CLAIRAGE DÃ‰TAILLÃ‰ ==========
    
    def calculate_eclairage_expert(self) -> List[Dict]:
        """Calcule la consommation Ã©clairage dÃ©taillÃ©e."""
        appareils = []
        
        nb_led = self.data.get('nb_led', 0)
        nb_halogene = self.data.get('nb_halogene', 0)
        heures_jour = self.data.get('heures_eclairage', 5)
        
        if nb_led > 0:
            conso_led = nb_led * 10 * heures_jour * 365 / 1000
            appareils.append({
                'categorie': 'eclairage',
                'type_appareil': 'led',
                'nom_affichage': f'Ampoules LED (Ã—{nb_led}, {heures_jour}h/j)',
                'nombre': nb_led,
                'puissance_w': 10,
                'heures_jour': heures_jour,
                'consommation_annuelle': conso_led,
                'consommation_mensuelle': self._distribute_lighting_monthly(conso_led),
            })
            logger.info(f"ðŸ’¡ LED (Ã—{nb_led}, {heures_jour}h/j): {conso_led:.0f} kWh/an")
        
        if nb_halogene > 0:
            conso_halogene = nb_halogene * 50 * heures_jour * 365 / 1000
            appareils.append({
                'categorie': 'eclairage',
                'type_appareil': 'halogene',
                'nom_affichage': f'Ampoules halogÃ¨ne (Ã—{nb_halogene}, {heures_jour}h/j)',
                'nombre': nb_halogene,
                'puissance_w': 50,
                'heures_jour': heures_jour,
                'consommation_annuelle': conso_halogene,
                'consommation_mensuelle': self._distribute_lighting_monthly(conso_halogene),
            })
            logger.info(f"ðŸ’¡ HalogÃ¨ne (Ã—{nb_halogene}, {heures_jour}h/j): {conso_halogene:.0f} kWh/an")
        
        return appareils
    
    # ========== PISCINE ==========
    
    def calculate_piscine(self) -> List[Dict]:
        """Calcule la consommation piscine."""
        appareils = []
        
        if not self.data.get('piscine_active', False):
            return appareils
        
        # Pompe filtration
        puissance_pompe = self.data.get('piscine_puissance_pompe')
        if not puissance_pompe:
            # Type prÃ©dÃ©fini
            type_pompe = self.data.get('piscine_type_pompe', 'standard')
            puissances = {'petite': 600, 'standard': 1000, 'grande': 1500}
            puissance_pompe = puissances.get(type_pompe, 1000)
        
        heures_filtration = self.data.get('piscine_heures_filtration', 8)
        mois_debut = self.data.get('piscine_mois_debut', 5)  # Mai
        mois_fin = self.data.get('piscine_mois_fin', 9)  # Septembre
        
        # Calcul nombre de jours
        nb_mois = (mois_fin - mois_debut + 1) if mois_fin >= mois_debut else (12 - mois_debut + mois_fin + 1)
        nb_jours = nb_mois * 30  # Approximation
        
        conso_pompe = puissance_pompe * heures_filtration * nb_jours / 1000
        
        mensuel = [0] * 12
        for mois in range(mois_debut - 1, mois_fin):
            mensuel[mois % 12] = conso_pompe / nb_mois
        
        appareils.append({
            'categorie': 'piscine',
            'type_appareil': 'pompe_filtration',
            'nom_affichage': f'Pompe piscine {puissance_pompe}W ({heures_filtration}h/j)',
            'puissance_w': puissance_pompe,
            'heures_jour': heures_filtration,
            'mois_debut': mois_debut,
            'mois_fin': mois_fin,
            'consommation_annuelle': conso_pompe,
            'consommation_mensuelle': mensuel,
        })
        
        logger.info(f"ðŸŠ Pompe piscine {puissance_pompe}W ({heures_filtration}h/j, {nb_mois} mois): {conso_pompe:.0f} kWh/an")
        
        # Chauffage piscine (si prÃ©sent)
        if self.data.get('piscine_chauffage_actif', False):
            type_chauffage = self.data.get('piscine_type_chauffage')
            puissance_chauffage = self.data.get('piscine_puissance_chauffage', 2000)
            heures_chauffage = self.data.get('piscine_heures_chauffage', 4)
            
            conso_chauffage = puissance_chauffage * heures_chauffage * nb_jours / 1000
            
            mensuel_chauf = [0] * 12
            for mois in range(mois_debut - 1, mois_fin):
                mensuel_chauf[mois % 12] = conso_chauffage / nb_mois
            
            appareils.append({
                'categorie': 'piscine',
                'type_appareil': f'chauffage_{type_chauffage}',
                'nom_affichage': f'Chauffage piscine {puissance_chauffage}W',
                'puissance_w': puissance_chauffage,
                'heures_jour': heures_chauffage,
                'mois_debut': mois_debut,
                'mois_fin': mois_fin,
                'consommation_annuelle': conso_chauffage,
                'consommation_mensuelle': mensuel_chauf,
            })
            
            logger.info(f"ðŸ”¥ Chauffage piscine {puissance_chauffage}W: {conso_chauffage:.0f} kWh/an")
        
        # Robot (si prÃ©sent)
        if self.data.get('piscine_robot_actif', False):
            conso_robot = 200 * 2 * 52 / 1000  # 200W Ã— 2h/semaine Ã— 52 semaines
            
            appareils.append({
                'categorie': 'piscine',
                'type_appareil': 'robot',
                'nom_affichage': 'Robot nettoyeur piscine',
                'puissance_w': 200,
                'consommation_annuelle': conso_robot,
                'consommation_mensuelle': [conso_robot / 12] * 12,
            })
            
            logger.info(f"ðŸ¤– Robot piscine: {conso_robot:.0f} kWh/an")
        
        return appareils
    
    # ========== SPA ==========
    
    def calculate_spa(self) -> List[Dict]:
        """Calcule la consommation spa/jacuzzi."""
        appareils = []
        
        if not self.data.get('spa_actif', False):
            return appareils
        
        type_spa = self.data.get('type_spa', 'rigide')
        conso_base = self.CONSO_SPA_BASE.get(type_spa, 3000)
        
        # Facteurs multiplicateurs
        facteur_saison = 1.0 if self.data.get('spa_toute_annee', True) else 0.5
        facteur_temp = 1.0 if self.data.get('spa_temp_maintenue', True) else 0.6
        facteur_couverture = 0.7 if self.data.get('spa_couverture', True) else 1.0
        
        conso_annuelle = conso_base * facteur_saison * facteur_temp * facteur_couverture
        
        appareils.append({
            'categorie': 'spa',
            'type_appareil': type_spa,
            'nom_affichage': f'Spa {type_spa}',
            'consommation_annuelle': conso_annuelle,
            'consommation_mensuelle': [conso_annuelle / 12] * 12,
        })
