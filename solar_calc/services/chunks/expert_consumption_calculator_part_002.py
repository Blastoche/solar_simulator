                    'nombre': nombre,
                    'classe_energetique': classe,
                    'consommation_annuelle': conso_annuelle,
                    'consommation_mensuelle': [conso_annuelle / 12] * 12,
                })
                
                logger.info(f"â„ï¸ Frigo {type_frigo} {classe} (Ã—{nombre}): {conso_annuelle:.0f} kWh/an")
        
        # CongÃ©lateurs
        congelateurs = self.data.get('congelateurs', [])
        for i, congelateur in enumerate(congelateurs):
            type_cong = congelateur.get('type')
            nombre = congelateur.get('nombre', 1)
            classe = congelateur.get('classe', 'A+')
            
            if type_cong and type_cong != 'aucun':
                conso_base = self.CONSO_CONGELATEURS.get(type_cong, 300)
                facteur_classe = self.FACTEURS_CLASSE.get(classe, 1.0)
                conso_annuelle = conso_base * facteur_classe * nombre
                
                appareils.append({
                    'categorie': 'refrigeration',
                    'type_appareil': f'congelateur_{type_cong}',
                    'nom_affichage': f'CongÃ©lateur {type_cong.title()} {classe}',
                    'nombre': nombre,
                    'classe_energetique': classe,
                    'consommation_annuelle': conso_annuelle,
                    'consommation_mensuelle': [conso_annuelle / 12] * 12,
                })
                
                logger.info(f"ðŸ§Š CongÃ©lateur {type_cong} {classe} (Ã—{nombre}): {conso_annuelle:.0f} kWh/an")
        
        return appareils
    
    # ========== LAVAGE ==========
    
    def calculate_lavage(self) -> List[Dict]:
        """Calcule la consommation lave-linge, lave-vaisselle, sÃ¨che-linge."""
        appareils = []
        
        # Lave-linge
        if self.data.get('lave_linge_actif', True):
            classe = self.data.get('lave_linge_classe', 'A++')
            cycles_sem = self.data.get('lave_linge_cycles', 4)
            
            conso_cycle = self.CONSO_LAVE_LINGE.get(classe, 0.80)
            conso_annuelle = conso_cycle * cycles_sem * 52
            
            appareils.append({
                'categorie': 'lavage',
                'type_appareil': 'lave_linge',
                'nom_affichage': f'Lave-linge {classe}',
                'classe_energetique': classe,
                'cycles_semaine': cycles_sem,
                'consommation_annuelle': conso_annuelle,
                'consommation_mensuelle': [conso_annuelle / 12] * 12,
            })
            
            logger.info(f"ðŸ§º Lave-linge {classe} ({cycles_sem} cycles/sem): {conso_annuelle:.0f} kWh/an")
        
        # Lave-vaisselle
        if self.data.get('lave_vaisselle_actif', True):
            classe = self.data.get('lave_vaisselle_classe', 'A++')
            cycles_sem = self.data.get('lave_vaisselle_cycles', 5)
            
            conso_cycle = self.CONSO_LAVE_VAISSELLE.get(classe, 1.10)
            conso_annuelle = conso_cycle * cycles_sem * 52
            
            appareils.append({
                'categorie': 'lavage',
                'type_appareil': 'lave_vaisselle',
                'nom_affichage': f'Lave-vaisselle {classe}',
                'classe_energetique': classe,
                'cycles_semaine': cycles_sem,
                'consommation_annuelle': conso_annuelle,
                'consommation_mensuelle': [conso_annuelle / 12] * 12,
            })
            
            logger.info(f"ðŸ½ï¸ Lave-vaisselle {classe} ({cycles_sem} cycles/sem): {conso_annuelle:.0f} kWh/an")
        
        # SÃ¨che-linge
        if self.data.get('seche_linge_actif', False):
            type_seche = self.data.get('seche_linge_type', 'pompe_chaleur_A++')
            cycles_sem = self.data.get('seche_linge_cycles', 3)
            
            conso_cycle = self.CONSO_SECHE_LINGE.get(type_seche, 2.0)
            conso_annuelle = conso_cycle * cycles_sem * 52
            
            appareils.append({
                'categorie': 'lavage',
                'type_appareil': 'seche_linge',
                'nom_affichage': f'SÃ¨che-linge {type_seche.replace("_", " ").title()}',
                'cycles_semaine': cycles_sem,
                'consommation_annuelle': conso_annuelle,
                'consommation_mensuelle': [conso_annuelle / 12] * 12,
            })
            
            logger.info(f"ðŸ‘• SÃ¨che-linge {type_seche} ({cycles_sem} cycles/sem): {conso_annuelle:.0f} kWh/an")
        
        return appareils
    
    # ========== FOUR ==========
    
    def calculate_four_expert(self) -> List[Dict]:
        """Calcule la consommation du four en mode expert."""
        appareils = []
        
        type_four = self.data.get('type_four', 'four_electrique')
        usage = self.data.get('usage_four', 'occasionnel')
        
        if type_four and type_four != 'aucun':
            conso_base = self.CONSO_FOUR_BASE.get(type_four, 150)
            facteur_usage = self.FACTEURS_USAGE_FOUR.get(usage, 1.0)
            conso_annuelle = conso_base * facteur_usage
            
            # Mapping propre des noms de four (CORRECTION ICI)
            noms_four = {
                'four_electrique': 'Four Ã‰lectrique',
                'four_combine': 'Four CombinÃ©',
                'four_gaz': 'Four Gaz',
            }
            nom_four = noms_four.get(type_four, type_four.replace('_', ' ').title())
            
            # Mapping usage
            noms_usage = {
                'occasionnel': 'occasionnel',
                'regulier': 'rÃ©gulier',
                'intensif': 'intensif',
            }
            nom_usage = noms_usage.get(usage, usage)
            
            appareils.append({
                'categorie': 'cuisson',
                'type_appareil': type_four,
                'nom_affichage': f'{nom_four} ({nom_usage})',  # â† CORRIGÃ‰ : Plus de "Four Four" !
                'nombre': 1,
                'consommation_annuelle': conso_annuelle,
            })
            
            logger.info(f"ðŸ³ {nom_four} ({nom_usage}): {conso_annuelle:.0f} kWh/an")
        
        return appareils
    
    # ========== AUDIOVISUEL DÃ‰TAILLÃ‰ ==========
    
    def calculate_audiovisuel_expert(self) -> List[Dict]:
        """Calcule la consommation audiovisuelle dÃ©taillÃ©e."""
        appareils = []
        
        # TVs
        tvs = self.data.get('tvs', [])
        for i, tv in enumerate(tvs):
            taille = tv.get('taille', 'moyen')
            techno = tv.get('techno', 'led')
            heures_jour = tv.get('heures_jour', 4)
            
            puissance = self.PUISSANCE_TV.get(taille, 80)
            facteur_techno = self.FACTEURS_TECHNO_TV.get(techno, 1.0)
            puissance_reelle = puissance * facteur_techno
            
            conso_annuelle = puissance_reelle * heures_jour * 365 / 1000
            
            appareils.append({
                'categorie': 'audiovisuel',
                'type_appareil': f'tv_{taille}_{techno}',
                'nom_affichage': f'TV {taille} {techno.upper()} ({heures_jour}h/j)',
                'puissance_w': int(puissance_reelle),
                'heures_jour': heures_jour,
                'consommation_annuelle': conso_annuelle,
                'consommation_mensuelle': [conso_annuelle / 12] * 12,
            })
            
            logger.info(f"ðŸ“º TV {taille} {techno} ({heures_jour}h/j): {conso_annuelle:.0f} kWh/an")
        
        # Box internet
        type_box = self.data.get('type_box', 'seule')
        eteinte_nuit = self.data.get('box_eteinte_nuit', False)
        
        conso_box = self.CONSO_BOX.get(type_box, 150)
        if eteinte_nuit:
            conso_box *= 0.7
        
        appareils.append({
            'categorie': 'audiovisuel',
            'type_appareil': f'box_{type_box}',
            'nom_affichage': f'Box internet {"+ dÃ©codeur" if type_box == "avec_decodeur" else ""}',
            'consommation_annuelle': conso_box,
            'consommation_mensuelle': [conso_box / 12] * 12,
        })
        
        logger.info(f"ðŸ“¶ Box {type_box}: {conso_box:.0f} kWh/an")
        
        # Ordinateurs
        nb_fixes = self.data.get('nb_ordis_fixes', 0)
        nb_portables = self.data.get('nb_ordis_portables', 0)
        heures_ordi = self.data.get('heures_ordi', 6)
        
        if nb_fixes > 0:
            conso_fixes = self.PUISSANCE_ORDI['fixe'] * nb_fixes * heures_ordi * 365 / 1000
            appareils.append({
