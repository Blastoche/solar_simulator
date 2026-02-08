        logger.debug(f"  AprÃ¨s isolation (Ã—{facteur_iso}): {besoin_base:.0f} kWh")
        
        # 4. Altitude (optionnel)
        altitude = self.data.get('altitude', 0)
        if altitude > 0:
            facteur_altitude = 1 + (altitude / 200) * 0.05
            besoin_base *= facteur_altitude
            logger.debug(f"  AprÃ¨s altitude {altitude}m (Ã—{facteur_altitude:.2f}): {besoin_base:.0f} kWh")
        
        # 5. Type de chauffage (rendement/COP)
        if type_chauffage == 'pac':
            # Pompe Ã  chaleur : COP moyen de 3.0
            # Besoin Ã©nergÃ©tique / COP = consommation Ã©lectrique
            conso_elec = besoin_base / 3.0
            logger.debug(f"  PAC (COP 3.0): {conso_elec:.0f} kWh Ã©lec")
        else:  # Ã‰lectrique direct
            conso_elec = besoin_base
            logger.debug(f"  Ã‰lectrique direct: {conso_elec:.0f} kWh")
        
        # 6. VMC double flux Ã©conomise 15%
        type_vmc = self.data.get('type_vmc', 'aucune')
        if type_vmc == 'double_flux':
            conso_elec *= 0.85
            logger.debug(f"  VMC double flux (-15%): {conso_elec:.0f} kWh")
        
        # 7. TempÃ©rature de consigne (+7% par Â°C au-dessus de 19Â°C)
        temp_consigne = self.data.get('temperature_consigne', 19.0)
        if temp_consigne > 19:
            facteur_temp = 1 + (temp_consigne - 19) * 0.07
            conso_elec *= facteur_temp
            logger.debug(f"  TempÃ©rature {temp_consigne}Â°C (Ã—{facteur_temp:.2f}): {conso_elec:.0f} kWh")
        
        # 8. RÃ©partition mensuelle (plus en hiver)
        monthly = self._distribute_heating_monthly(conso_elec)
        
        logger.info(f"ðŸ”¥ Chauffage: {conso_elec:.0f} kWh/an")
        
        return {
            'annuel': round(conso_elec, 0),
            'mensuel': monthly,
            'details': {
                'type': type_chauffage,
                'dpe': self.dpe,
                'zone': self.zone_climatique,
                'temperature': temp_consigne,
                'vmc': type_vmc,
            }
        }
    
    def _get_facteur_isolation(self) -> float:
        """Retourne le facteur d'isolation selon l'annÃ©e de construction"""
        annee = self.annee_construction
        
        for annee_seuil, facteur, nom in self.FACTEURS_ISOLATION:
            if annee >= annee_seuil:
                logger.debug(f"    Isolation {nom} (â‰¥{annee_seuil}): facteur {facteur}")
                return facteur
        
        return 1.50  # Par dÃ©faut
    
    def _distribute_heating_monthly(self, total: float) -> List[float]:
        """
        RÃ©partit le chauffage sur 12 mois (plus en hiver).
        
        Args:
            total: Consommation annuelle totale (kWh)
        
        Returns:
            Liste de 12 valeurs mensuelles
        """
        # Facteurs mensuels de base (hiver > Ã©tÃ©)
        # BasÃ© sur les degrÃ©s-jours unifiÃ©s (DJU) moyens en France
        factors_h2 = [
            1.5,  # Jan - Froid
            1.4,  # FÃ©v - Froid
            1.2,  # Mar - Frais
            0.8,  # Avr - Doux
            0.3,  # Mai - Doux
            0.0,  # Juin - Chaud
            0.0,  # Juil - Chaud
            0.0,  # AoÃ»t - Chaud
            0.2,  # Sep - Doux
            0.6,  # Oct - Frais
            1.1,  # Nov - Frais
            1.4,  # DÃ©c - Froid
        ]
        
        # Ajuster selon la zone
        if self.zone_climatique == 'H1':  # Nord : hivers plus longs/froids
            factors = [f * 1.1 for f in factors_h2]
        elif self.zone_climatique == 'H3':  # Sud : hivers plus doux
            factors = [f * 0.7 for f in factors_h2]
        else:  # H2
            factors = factors_h2
        
        # Normaliser pour que la somme = total
        sum_factors = sum(factors)
        monthly = [round(total * (f / sum_factors), 0) for f in factors]
        
        return monthly
    
    def calculate_ecs(self) -> Dict:
        """
        Calcule la consommation d'eau chaude sanitaire (ECS).
        
        BasÃ© sur :
        - Nombre de personnes (50L/pers/jour Ã  50Â°C)
        - Type de chauffe-eau (Ã©lectrique, thermodynamique, etc.)
        - CapacitÃ© du ballon (optionnel)
        
        Returns:
            {
                'annuel': 2500,
                'mensuel': [210, 210, ...],
                'details': {...}
            }
        """
        nb_pers = self.nb_personnes
        type_ecs = self.data.get('type_ecs', 'ballon_electrique')
        
        # Si non Ã©lectrique
        if type_ecs in ['gaz', 'solaire']:
            logger.info(f"ECS {type_ecs} (non Ã©lectrique)")
            return {
                'annuel': 0,
                'mensuel': [0] * 12,
                'details': {'type': type_ecs, 'electrique': False}
            }
        
        # Consommation de base
        # 50 litres/pers/jour Ã  chauffer de 15Â°C Ã  50Â°C
        # Ã‰nergie = Volume Ã— Î”T Ã— 1.16 Wh/L/Â°C
        # = 50L Ã— 35Â°C Ã— 1.16 = 2030 Wh/jour/pers
        # = 2.03 kWh/jour/pers
        # = 741 kWh/an/pers
        
        conso_base_annuelle = nb_pers * 741  # kWh/an
        
        # COP selon type
        if type_ecs == 'thermodynamique':
            # Chauffe-eau thermodynamique : COP moyen 2.5
            conso_elec = conso_base_annuelle / 2.5
            logger.debug(f"  Thermodynamique (COP 2.5): {conso_elec:.0f} kWh")
        else:  # Ballon Ã©lectrique classique
            conso_elec = conso_base_annuelle
            logger.debug(f"  Ballon Ã©lectrique: {conso_elec:.0f} kWh")
        
        # Ajustement selon capacitÃ© (optionnel)
        capacite = self.data.get('capacite_ecs')
        if capacite:
            # Ballons surdimensionnÃ©s ont plus de pertes thermiques
            if capacite > nb_pers * 50:
                facteur_pertes = 1.1  # +10% de pertes
                conso_elec *= facteur_pertes
                logger.debug(f"  SurdimensionnÃ© ({capacite}L pour {nb_pers} pers): +10%")
        
        # RÃ©partition mensuelle (lÃ©gÃ¨rement plus en hiver)
        monthly_base = conso_elec / 12
        monthly = []
        for mois in range(1, 13):
            # Hiver : +10%, Ã‰tÃ© : -10%
            if mois in [1, 2, 3, 11, 12]:  # Hiver
                monthly.append(round(monthly_base * 1.1, 0))
            elif mois in [6, 7, 8]:  # Ã‰tÃ©
                monthly.append(round(monthly_base * 0.9, 0))
            else:  # Intersaison
                monthly.append(round(monthly_base, 0))
        
        logger.info(f"ðŸš¿ ECS: {conso_elec:.0f} kWh/an")
        
        return {
            'annuel': round(conso_elec, 0),
            'mensuel': monthly,
            'details': {
                'type': type_ecs,
                'nb_personnes': nb_pers,
                'capacite': capacite,
            }
        }
    
    def calculate_forfait_electromenager(self) -> Dict:
        """
        Calcul forfaitaire de l'Ã©lectromÃ©nager (mode rapide).
        
        BasÃ© sur :
        - Nombre de personnes
        - Ã‚ge des appareils (classe Ã©nergÃ©tique)
        
        Returns:
            {
                'annuel': 1800,
                'mensuel': [150, 150, ...],
                'details': {...}
            }
        """
        # Base : 800 kWh/personne/an (Ã©lectromÃ©nager classique)
        conso_base = self.nb_personnes * 800
        
        # Ajustement selon Ã¢ge des appareils
        age_appareils = self.data.get('age_appareils', 'moyen')
