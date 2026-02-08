                        consommation_totale=consommation_annuelle,
                        appareils_data=appareils_data,
                        optimized=False  # Version normale (pas optimisÃ©e)
                    )
                except (json.JSONDecodeError, KeyError, TypeError, AttributeError) as e:
                    logger.warning(f"âš ï¸ Erreur parsing appareils_json : {e}. Fallback sur profil gÃ©nÃ©rique")
                    # Fallback sur profil gÃ©nÃ©rique
                    pattern_brut = ConsumptionProfiles.generate_yearly_pattern(
                        profile_type=profile_type,
                        add_randomness=True
                    )
                    consommation_horaire_kw = pattern_brut / pattern_brut.sum() * consommation_annuelle
            else:
                # CAS 2 : Pas de dÃ©tails â†’ Profil GÃ‰NÃ‰RIQUE
                logger.info(f"â„¹ï¸ Utilisation profil gÃ©nÃ©rique (pas d'appareils dÃ©taillÃ©s)")
                
                pattern_brut = ConsumptionProfiles.generate_yearly_pattern(
                    profile_type=profile_type,
                    add_randomness=True
                )
                
                # Normaliser pour correspondre Ã  la consommation annuelle
                consommation_horaire_kw = pattern_brut / pattern_brut.sum() * consommation_annuelle
            
            # VÃ©rifier qu'on a bien 8760 valeurs
            if len(consommation_horaire_kw) != 8760:
                logger.error(f"âŒ Profil consommation invalide : {len(consommation_horaire_kw)} valeurs au lieu de 8760")
                # Fallback sur ratio fixe
                autoconso_ratio = 70.0
                autoconso_kwh = production_annuelle * (autoconso_ratio / 100)
                injection_kwh = production_annuelle - autoconso_kwh
            else:
                # Calculer l'autoconsommation RÃ‰ELLE heure par heure
                hourly_calc = HourlyAutoconsumptionCalculator(puissance_kwc=self.puissance_kw)
                
                hourly_results = hourly_calc.calculate(
                    production_horaire_kw=df_calc['production_kw'].values,  # numpy array 8760 valeurs
                    consommation_horaire_kw=consommation_horaire_kw  # numpy array 8760 valeurs
                )
                
                # Utiliser les rÃ©sultats RÃ‰ELS
                autoconso_ratio = hourly_results.taux_autoconsommation_pct
                autoconso_kwh = hourly_results.autoconsommation_kwh
                injection_kwh = hourly_results.injection_reseau_kwh
                autoproduction_ratio = hourly_results.taux_autoproduction_pct
                
                logger.info(f"âœ… Autoconsommation RÃ‰ELLE calculÃ©e (heure par heure)")
                logger.info(f"ðŸ“Š Taux autoconsommation : {autoconso_ratio:.1f}%")
                logger.info(f"ðŸ  Taux autoproduction : {autoproduction_ratio:.1f}%")
        
        except Exception as e:
            logger.error(f"âŒ Erreur calcul autoconsommation : {e}")
            # Fallback sur ratio fixe en cas d'erreur
            autoconso_ratio = 70.0
            autoconso_kwh = production_annuelle * (autoconso_ratio / 100)
            injection_kwh = production_annuelle - autoconso_kwh
            autoproduction_ratio = 0.0    
            
            logger.info(f"ðŸ“ˆ Production annuelle : {production_annuelle:.2f} kWh")
            logger.info(f"âš¡ Autoconsommation : {autoconso_kwh:.2f} kWh ({autoconso_ratio:.1f}%)")
            logger.info(f"ðŸ“¤ Injection rÃ©seau : {injection_kwh:.2f} kWh")
        
        return {
            'annuelle': round(production_annuelle, 2),
            'monthly': production_monthly,
            'daily': production_hourly,
            'autoconso_ratio': autoconso_ratio,
            'autoproduction_ratio': autoproduction_ratio if 'autoproduction_ratio' in locals() else 0.0,
            'autoconso_kwh': autoconso_kwh,
            'injection': round(injection_kwh, 2),
        }
    
    def _calculate_from_dict(self, weather_data: dict):
        """
        Calcule la production depuis un dict (ancien format).
        
        Args:
            weather_data: Dict avec 'monthly' et 'hourly'
        
        Returns:
            Dict avec les rÃ©sultats de production
        """
        monthly_irradiance = weather_data.get('monthly', [1.0] * 12)
        hourly_irradiance = weather_data.get('hourly', [0.5] * 24)
        
        # Ajustement selon l'orientation
        orientation_factor = self._get_orientation_factor()
        
        # Calcul production mensuelle (kWh)
        production_monthly = []
        for irr in monthly_irradiance:
            # Production = Puissance Ã— Irradiance Ã— Rendement Ã— Facteur orientation
            # Irradiance en kWh/mÂ²/jour, sur 30 jours en moyenne
            kwh = (self.puissance_kw * irr * 30 * self.rendement_global * orientation_factor)
            production_monthly.append(round(kwh, 2))
        
        # Production annuelle
        production_annuelle = sum(production_monthly)
        
        # Profil horaire moyen (kWh)
        production_hourly = [
            round((self.puissance_kw * (irr / 1000) * self.rendement_global * orientation_factor), 3)
            for irr in hourly_irradiance
        ]
        
        # Autoconsommation (par dÃ©faut 70%)
        autoconso_ratio = 70.0
        autoconso_kwh = production_annuelle * (autoconso_ratio / 100)
        injection_kwh = production_annuelle - autoconso_kwh
        
        logger.info(f"ðŸ“ˆ Production annuelle : {production_annuelle:.2f} kWh")
        logger.info(f"âš¡ Autoconsommation : {autoconso_ratio}%")
        
        return {
            'annuelle': round(production_annuelle, 2),
            'monthly': production_monthly,
            'daily': production_hourly,
            'autoconso_ratio': autoconso_ratio,
            'injection': round(injection_kwh, 2),
        }
        
    def calculate_consumption(self, consommation_annuelle=None):
        """
        Calcule la consommation Ã©lectrique.
        
        Args:
            consommation_annuelle: Consommation annuelle en kWh (si None, utilise 3500 par dÃ©faut)
        """
        logger.info("âš¡ Calcul de la consommation...")
        
        # Utiliser la consommation fournie ou valeur par dÃ©faut
        if consommation_annuelle is None:
            consommation_annuelle = getattr(self.installation, 'consommation_annuelle', 3500.0)
        
        consumption_annuelle = float(consommation_annuelle)
        
        # Distribution mensuelle (lÃ©gÃ¨re variation saisonniÃ¨re)
        # Plus Ã©levÃ©e en hiver (chauffage, Ã©clairage)
        monthly_factors = [
            1.1,  # Jan (chauffage)
            1.05, # FÃ©v
            0.95, # Mar
            0.85, # Avr
            0.75, # Mai
            0.70, # Juin (+ clim)
            0.75, # Juil
            0.75, # AoÃ»t
            0.80, # Sep
            0.90, # Oct
            1.05, # Nov
            1.15, # DÃ©c (chauffage)
        ]
        
        consumption_monthly = []
        for factor in monthly_factors:
            kwh = (consumption_annuelle / 12) * factor
            consumption_monthly.append(round(kwh, 2))
        
        # Profil horaire (24h)
        # Pic le matin (6-9h) et soir (18-22h)
        hourly_factors = [
            0.3, 0.2, 0.2, 0.2, 0.3, 0.6,  # 00-06
            1.0, 0.9, 0.7, 0.5, 0.5, 0.4,  # 06-12
            0.4, 0.4, 0.5, 0.6, 0.9, 1.0,  # 12-18
            0.8, 0.7, 0.5, 0.4, 0.4, 0.3,  # 18-24
        ]
        
        consumption_hourly = []
        for factor in hourly_factors:
            kwh = (consumption_annuelle / 8760) * factor  # 8760 = 24 Ã— 365
            consumption_hourly.append(round(kwh, 3))
        
        logger.info(f"ðŸ“‰ Consommation annuelle : {consumption_annuelle:.2f} kWh")
        
        return {
            'annuelle': consumption_annuelle,
            'monthly': consumption_monthly,
            'daily': consumption_hourly,
        }
    
    
    def calculate_financial(self, production, consumption):
        """
        Calcule les donnÃ©es financiÃ¨res.
        
        Args:
            production: Dict de production (rÃ©sultat de calculate_production)
            consumption: Dict de consommation (rÃ©sultat de calculate_consumption)
        
        Returns:
            Dict avec:
            - economie_annuelle: Ã‰conomie annuelle en â‚¬
            - roi: Retour sur investissement sur 25 ans en â‚¬
            - taux_rentabilite: Taux de rentabilitÃ© en %
        """
        
        logger.info("ðŸ’° Calcul financier...")
        
        # ParamÃ¨tres Ã©conomiques
        prix_kwh = 0.25  # â‚¬/kWh moyen en France
