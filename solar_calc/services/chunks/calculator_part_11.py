        prix_autoconso = 0.25  # â‚¬/kWh consommÃ© localement
        prix_injection = 0.08  # â‚¬/kWh injectÃ© au rÃ©seau
        
        # Cout d'investissement (environ 1500-2000â‚¬ par kWc)
        cout_installation = self.puissance_kw * 1800  # â‚¬
        
        # Ã‰conomie annuelle
        economie_autoconso = production['annuelle'] * (production['autoconso_ratio'] / 100) * prix_autoconso
        economie_injection = production['injection'] * prix_injection
        economie_annuelle = economie_autoconso + economie_injection
        
        # ROI sur 25 ans
        roi_25ans = (economie_annuelle * 25) - cout_installation
        
        # Taux de rentabilitÃ© annuel
        taux_rentabilite = (economie_annuelle / cout_installation) * 100 if cout_installation > 0 else 0
        
        logger.info(f"ðŸ’µ Ã‰conomie annuelle : {economie_annuelle:.2f}â‚¬")
        logger.info(f"ðŸ’¶ ROI 25 ans : {roi_25ans:.2f}â‚¬")
        logger.info(f"ðŸ“Š Taux rentabilitÃ© : {taux_rentabilite:.2f}%")
        
        return {
            'economie_annuelle': round(economie_annuelle, 2),
            'roi': round(roi_25ans, 2),
            'taux_rentabilite': round(taux_rentabilite, 2),
        }
    
    
    def _get_orientation_factor(self):
        """
        Retourne le facteur d'orientation (0-1).
        
        - Sud = 1.0 (optimal)
        - SE/SW = 0.95
        - E/W = 0.85
        - NE/NW = 0.70
        - N = 0.50
        """
        
        factors = {
            'S': 1.0,
            'SE': 0.95,
            'SW': 0.95,
            'E': 0.85,
            'W': 0.85,
            'NE': 0.70,
            'NW': 0.70,
            'N': 0.50,
        }
        
        return factors.get(self.orientation, 0.85)
    
    
    def _get_inclinaison_factor(self):
        """
        Retourne le facteur d'inclinaison (0-1).
        
        - 30-35Â° = 1.0 (optimal en France)
        - 0Â° (plat) = 0.85
        - 45Â° = 0.95
        - 90Â° (vertical) = 0.70
        """
        inclinaison = self.inclinaison
        
        if inclinaison is None:
            return 1.0
        
        # Courbe optimale autour de 30-35Â°
        if 25 <= inclinaison <= 40:
            return 1.0
        elif inclinaison < 25:
            # Facteur diminue quand on s'approche de 0Â° (plat)
            return 0.85 + (inclinaison / 25) * 0.15
        else:
            # Facteur diminue pour angles > 40Â°
            return max(0.70, 1.0 - (inclinaison - 40) / 100)
    
    
    def _get_default_hourly_pattern(self, avg_power_kw):
        """
        GÃ©nÃ¨re un profil horaire par dÃ©faut (courbe en cloche).
        
        Args:
            avg_power_kw: Puissance moyenne (kW)
        
        Returns:
            Liste de 24 valeurs (kW)
        """
        hourly_pattern = []
        for hour in range(24):
            if 6 <= hour <= 19:
                # Courbe sinusoÃ¯dale entre 6h et 19h
                angle = (hour - 6) / 13 * np.pi
                factor = np.sin(angle)
                hourly_pattern.append(round(avg_power_kw * factor * 2, 3))
            else:
                hourly_pattern.append(0.0)
        
        return hourly_pattern
    
    
    def _get_default_irradiance(self):
        """
        Retourne des donnÃ©es d'irradiance par dÃ©faut (France moyenne).
        """
        
        return {
            'monthly': [
                1.2,  # Jan
                1.4,  # FÃ©v
                2.0,  # Mar
                2.5,  # Avr
                3.0,  # Mai
                3.2,  # Juin
                3.1,  # Juil
                2.8,  # AoÃ»t
                2.2,  # Sep
                1.6,  # Oct
                1.3,  # Nov
                1.1,  # DÃ©c
            ],
            'hourly': [
                0,    # 00h
                0,    # 01h
                0,    # 02h
                0,    # 03h
                0,    # 04h
                50,   # 05h
                200,  # 06h
                400,  # 07h
                600,  # 08h
                750,  # 09h
                850,  # 10h
                900,  # 11h
                950,  # 12h
                900,  # 13h
                850,  # 14h
                750,  # 15h
                600,  # 16h
                400,  # 17h
                200,  # 18h
                50,   # 19h
                0,    # 20h
                0,    # 21h
                0,    # 22h
                0,    # 23h
            ]
        }
    # ===== MÃ‰THODES AVEC CONTRATS GARANTIS =====
    
    def calculate_production_normalized(self, weather_data) -> ProductionResult:
        """
        Calcule la production avec contrat garanti.
        
        CONTRAT :
            Input : DataFrame mÃ©tÃ©o 8760h ou dict
            Output : ProductionResult avec tous les champs garantis
        
        Args:
            weather_data: DataFrame PVGIS ou dict
        
        Returns:
            ProductionResult avec structure garantie
        
        Example:
            >>> result = calc.calculate_production_normalized(weather_df)
            >>> print(result.annuelle)  # 5903.36
            >>> print(len(result.monthly))  # 12
        """
        # Appeler la fonction existante
        result_dict = self.calculate_production(weather_data)
        
        # Valider
        validate_production_result(result_dict)
        
        # Calculer production spÃ©cifique
        specifique = round(result_dict['annuelle'] / self.puissance_kw, 2)
        
        # CrÃ©er objet structurÃ©
        return ProductionResult(
            annuelle=result_dict['annuelle'],
            specifique=specifique,
            monthly=result_dict['monthly'],
            daily=result_dict['daily'],
            autoconso_ratio=result_dict['autoconso_ratio'],
            injection=result_dict['injection'],
            performance_ratio=self.rendement_global
        )
    
    def calculate_consumption_normalized(
        self, 
        consommation_annuelle: float = None
    ) -> ConsumptionResult:
        """
        Calcule la consommation avec contrat garanti.
        
        CONTRAT :
            Input : consommation annuelle (kWh) optionnelle
            Output : ConsumptionResult avec structure garantie
        
