        
        if age_appareils == 'recent':  # < 5 ans, classe A+++
            facteur = 0.85  # -15%
        elif age_appareils == 'ancien':  # > 10 ans
            facteur = 1.20  # +20%
        else:  # Moyen (5-10 ans)
            facteur = 1.00
        
        conso_elec = conso_base * facteur
        
        # RÃ©partition mensuelle uniforme
        monthly = [round(conso_elec / 12, 0)] * 12
        
        logger.info(f"ðŸ§º Ã‰lectromÃ©nager (forfait): {conso_elec:.0f} kWh/an")
        
        return {
            'annuel': round(conso_elec, 0),
            'mensuel': monthly,
            'details': {
                'mode': 'forfait',
                'age_appareils': age_appareils,
            }
        }
    
    def calculate_forfait_cuisson(self) -> Dict:
        """Calcul forfaitaire cuisson (mode rapide)"""
        nb_pers = self.nb_personnes
        type_cuisson = self.data.get('type_cuisson', 'induction')
        
        # Base : 350 kWh/pers/an
        conso_base = nb_pers * 350
        
        # Ajustement selon type
        if type_cuisson == 'gaz':
            conso_elec = 50  # Juste l'allumage
        elif type_cuisson == 'induction':
            conso_elec = conso_base * 0.9  # -10% (plus efficace)
        else:  # Ã‰lectrique classique
            conso_elec = conso_base
        
        monthly = [round(conso_elec / 12, 0)] * 12
        
        logger.info(f"ðŸ³ Cuisson: {conso_elec:.0f} kWh/an")
        
        return {
            'annuel': round(conso_elec, 0),
            'mensuel': monthly,
            'details': {'type': type_cuisson}
        }
    
    def calculate_forfait_audiovisuel(self) -> Dict:
        """
        Calcul forfaitaire audiovisuel avec 3 niveaux d'usage.
        
        Source : ADEME "RÃ©duire sa facture d'Ã©lectricitÃ© 2023"
        
        Usage modÃ©rÃ© : Petite TV (<42"), Box, 1 ordi
        Usage courant : TV moyenne (42-55"), Box, ordi, console occasionnelle
        Usage intensif : Grande TV (>65"), Console souvent, Home-cinÃ©ma, Veilles permanentes
        """
        nb_pers = self.nb_personnes
        usage = self.data.get('usage_audiovisuel', 'courant')
        
        # Consommation par personne selon usage (kWh/pers/an)
        conso_per_person = {
            'modere': 150,   # 300 kWh pour 2 pers
            'courant': 250,  # 500 kWh pour 2 pers
            'intensif': 400  # 800 kWh pour 2 pers
        }.get(usage, 250)  # Par dÃ©faut: courant
        
        conso_base = nb_pers * conso_per_person
        
        monthly = [round(conso_base / 12, 0)] * 12
        
        logger.info(f"ðŸ“º Audiovisuel ({usage}): {conso_base:.0f} kWh/an ({conso_per_person} kWh/pers)")
        
        return {
            'annuel': round(conso_base, 0),
            'mensuel': monthly,
            'details': {
                'mode': 'forfait',
                'usage': usage,
                'kwh_per_person': conso_per_person
            }
        }
    
    def calculate_forfait_eclairage(self) -> Dict:
        """Calcul forfaitaire Ã©clairage"""
        surface = self.surface
        
        # Base : 10 kWh/mÂ²/an (si LED)
        # 20 kWh/mÂ²/an (si halogÃ¨ne)
        type_eclairage = self.data.get('type_eclairage', 'LED')
        
        # Consommation selon type (kWh/mÂ²/an) - Source ADEME 2023
        if type_eclairage == 'LED':
            conso_base = surface * 5  # RÃ©duit de 10 Ã  5
        elif type_eclairage == 'halogen':
            conso_base = surface * 12  # RÃ©duit de 20 Ã  12
        else:  # Mixte
            conso_base = surface * 8
        
        # Plus en hiver (nuits longues)
        monthly = self._distribute_lighting_monthly(conso_base)
        
        logger.info(f"ðŸ’¡ Ã‰clairage: {conso_base:.0f} kWh/an")
        
        return {
            'annuel': round(conso_base, 0),
            'mensuel': monthly,
            'details': {'type': type_eclairage}
        }
    
    def _distribute_lighting_monthly(self, total: float) -> List[float]:
        """RÃ©partit l'Ã©clairage (plus en hiver)"""
        factors = [
            1.3, 1.3, 1.2, 1.0, 0.8, 0.7,  # Jan-Juin
            0.7, 0.8, 1.0, 1.2, 1.3, 1.3,  # Juil-DÃ©c
        ]
        sum_factors = sum(factors)
        return [round(total * (f / sum_factors), 0) for f in factors]
    
    def calculate_total(self) -> Dict:
        """
        Calcul complet de la consommation (mode rapide).
        
        Returns:
            {
                'total_annuel': 5280,
                'mensuel': [480, 450, 420, ...],
                'moyenne_attendue': 4500,
                'ecart_pct': 17.3,
                'repartition': {
                    'chauffage': {'kwh': 2400, 'pct': 45.5},
                    'ecs': {'kwh': 800, 'pct': 15.2},
                    ...
                },
                'details_postes': {
                    'chauffage': {...},
                    'ecs': {...},
                    ...
                }
            }
        """
        logger.info("ðŸ”¢ Calcul de la consommation totale (mode rapide)")
        
        # Calcul de chaque poste
        chauffage = self.calculate_chauffage()
        ecs = self.calculate_ecs()
        electromenager = self.calculate_forfait_electromenager()
        cuisson = self.calculate_forfait_cuisson()
        audiovisuel = self.calculate_forfait_audiovisuel()
        eclairage = self.calculate_forfait_eclairage()
        
        # Total annuel
        total_annuel = (
            chauffage['annuel'] +
            ecs['annuel'] +
            electromenager['annuel'] +
            cuisson['annuel'] +
            audiovisuel['annuel'] +
            eclairage['annuel']
        )
        
        # Consommation mensuelle
        monthly = []
        for i in range(12):
            monthly.append(
                chauffage['mensuel'][i] +
                ecs['mensuel'][i] +
                electromenager['mensuel'][i] +
                cuisson['mensuel'][i] +
                audiovisuel['mensuel'][i] +
                eclairage['mensuel'][i]
            )
        
        # Comparaison Ã  la moyenne
        moyenne_attendue = self._calculate_expected_consumption()
        ecart_pct = ((total_annuel - moyenne_attendue) / moyenne_attendue) * 100
        
        # RÃ©partition par poste
        repartition = {}
        for nom, resultat in [
            ('chauffage', chauffage),
            ('ecs', ecs),
            ('electromenager', electromenager),
            ('cuisson', cuisson),
            ('audiovisuel', audiovisuel),
            ('eclairage', eclairage),
        ]:
            kwh = resultat['annuel']
            pct = (kwh / total_annuel * 100) if total_annuel > 0 else 0
            repartition[nom] = {
                'kwh': kwh,
                'pourcentage': round(pct)  # Arrondi standard (0.5 â†’ sup)
            }
        
        logger.info(f"ðŸ“Š TOTAL: {total_annuel:.0f} kWh/an (vs moyenne {moyenne_attendue:.0f}, Ã©cart {ecart_pct:+.1f}%)")
        
        return {
