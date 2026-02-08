            dict: RÃ©sultats dÃ©taillÃ©s incluant :
                - production_annuelle_kwh
                - consommation_annuelle_kwh
                - autoconsommation_kwh
                - injection_reseau_kwh
                - achat_reseau_kwh
                - taux_autoconsommation_pct
                - taux_autoproduction_pct
                - donnees_horaires (DataFrame complet)
        """
        # Normaliser les timestamps pour assurer la correspondance
        # Les donnÃ©es PVGIS et de consommation peuvent avoir des annÃ©es diffÃ©rentes
        # On les force toutes Ã  la mÃªme annÃ©e de rÃ©fÃ©rence (2016)
        production_copy = production_horaire.copy()
        production_copy['timestamp'] = pd.date_range(
            start='2016-01-01',
            periods=len(production_copy),
            freq='h'
        )
        
        consommation_copy = consommation_horaire.copy()
        consommation_copy['timestamp'] = pd.date_range(
            start='2016-01-01',
            periods=len(consommation_copy),
            freq='h'
        )
        
        # Fusionner les deux DataFrames sur le timestamp
        df = pd.merge(
            production_copy[['timestamp', 'puissance_ac_kw']],
            consommation_copy[['timestamp', 'consommation_kw']],
            on='timestamp',
            how='inner'
        )
        
        # Calculer les flux Ã©nergÃ©tiques heure par heure
        # Autoconsommation = minimum entre production et consommation
        df['autoconso_kw'] = df.apply(
            lambda row: min(row['puissance_ac_kw'], row['consommation_kw']),
            axis=1
        )
        
        # Injection = surplus de production
        df['injection_kw'] = df.apply(
            lambda row: max(0, row['puissance_ac_kw'] - row['consommation_kw']),
            axis=1
        )
        
        # Achat = dÃ©ficit de production
        df['achat_kw'] = df.apply(
            lambda row: max(0, row['consommation_kw'] - row['puissance_ac_kw']),
            axis=1
        )
        
        # Calculer les totaux annuels
        production_totale = df['puissance_ac_kw'].sum()
        consommation_totale = df['consommation_kw'].sum()
        autoconso_totale = df['autoconso_kw'].sum()
        injection_totale = df['injection_kw'].sum()
        achat_total = df['achat_kw'].sum()
        
        # Calculer les taux
        # Taux d'autoconsommation = part de la production qui est consommÃ©e localement
        taux_autoconso = (
            (autoconso_totale / production_totale * 100) 
            if production_totale > 0 else 0
        )
        
        # Taux d'autoproduction = part de la consommation couverte par la production
        taux_autoprod = (
            (autoconso_totale / consommation_totale * 100) 
            if consommation_totale > 0 else 0
        )
        
        return {
            'production_annuelle_kwh': round(production_totale, 2),
            'consommation_annuelle_kwh': round(consommation_totale, 2),
            'autoconsommation_kwh': round(autoconso_totale, 2),
            'injection_reseau_kwh': round(injection_totale, 2),
            'achat_reseau_kwh': round(achat_total, 2),
            'taux_autoconsommation_pct': round(taux_autoconso, 2),
            'taux_autoproduction_pct': round(taux_autoprod, 2),
            'donnees_horaires': df
        }

    def run_simulation_complete(
        self,
        django_installation,
        django_profile,
        use_real_weather: bool = True,
        irradiation_annuelle_fallback: float = None,
        with_battery: bool = False,
        battery_capacity: float = None
    ) -> dict:
        """
        ExÃ©cute une simulation complÃ¨te de l'installation solaire.
        
        Workflow :
        1. CrÃ©ation des objets installation et profil de consommation
        2. RÃ©cupÃ©ration des donnÃ©es mÃ©tÃ©o (PVGIS ou simplifiÃ©es)
        3. Calcul de la production horaire
        4. GÃ©nÃ©ration du profil de consommation horaire
        5. Calcul de l'autoconsommation
        6. Simulation avec batterie si demandÃ©
        
        Args:
            django_installation: ModÃ¨le Django de l'installation
            django_profile: ModÃ¨le Django du profil de consommation
            use_real_weather: Si True, utilise PVGIS, sinon donnÃ©es simplifiÃ©es
            irradiation_annuelle_fallback: Irradiation de secours si PVGIS Ã©choue
            with_battery: Active la simulation avec batterie
            battery_capacity: CapacitÃ© de la batterie en kWh
            
        Returns:
            ict: RÃ©sultats avec mÃ©triques annuelles
            - production_annuelle_kwh
            - consommation_annuelle_kwh
            - autoconso_annuelle_kwh
            - taux_autoconsommation_pct
            - taux_autoproduction_pct
            - injection_annuelle_kwh
            - achat_annuel_kwh
        """
        # CrÃ©er les objets de simulation
        installation = self.creer_installation_depuis_django(django_installation)
        profil_conso = self.creer_profil_consommation_depuis_django(django_profile)
        
        # RÃ©cupÃ©rer ou gÃ©nÃ©rer les donnÃ©es mÃ©tÃ©o
        if use_real_weather:
            try:
                from weather.services import get_pvgis_weather_data
                df_meteo, metadata = get_pvgis_weather_data(
                    django_installation.latitude,
                    django_installation.longitude,
                    use_cache=True
                )
                donnees_meteo = df_meteo
                logger.info("âœ… DonnÃ©es PVGIS rÃ©cupÃ©rÃ©es avec succÃ¨s")
            except Exception as e:
                logger.warning(
                    f"âš ï¸ PVGIS indisponible, utilisation des donnÃ©es simplifiÃ©es: {e}"
                )
                donnees_meteo = self.generer_donnees_meteo_simplifiees(
                    django_installation.latitude,
                    irradiation_annuelle_fallback
                )
        else:
            donnees_meteo = self.generer_donnees_meteo_simplifiees(
                django_installation.latitude,
                irradiation_annuelle_fallback
            )

        # Simuler la production solaire
        production_horaire = installation.simuler_annee(donnees_meteo)
        
        # GÃ©nÃ©rer le profil de consommation
        consommation_horaire = profil_conso.generer_profil_horaire()
        
        # Calculer l'autoconsommation
        resultats_autoconso = self.calculer_autoconsommation(
            production_horaire,
            consommation_horaire
        )
        
        # Calculer la production spÃ©cifique (kWh/kWc)
        production_specifique = (
            resultats_autoconso['production_annuelle_kwh'] / 
            installation.puissance_crete_totale_kwc
        )
        
        # Assembler les rÃ©sultats
        resultats = {
            'production_annuelle_kwh': resultats_autoconso['production_annuelle_kwh'],
            'production_specifique_kwh_kwc': round(production_specifique, 2),
            'consommation_annuelle_kwh': resultats_autoconso['consommation_annuelle_kwh'],
            'autoconsommation_kwh': resultats_autoconso['autoconsommation_kwh'],
            'injection_reseau_kwh': resultats_autoconso['injection_reseau_kwh'],
            'achat_reseau_kwh': resultats_autoconso['achat_reseau_kwh'],
            'taux_autoconsommation_pct': resultats_autoconso['taux_autoconsommation_pct'],
            'taux_autoproduction_pct': resultats_autoconso['taux_autoproduction_pct'],
            'donnees_horaires': resultats_autoconso['donnees_horaires']
        }
        
        # Simulation avec batterie si demandÃ©
        if with_battery:
            from battery.services.battery_simulation import BatterySimulationService
            from battery.models import BatterySystem
            
            # CrÃ©er ou rÃ©cupÃ©rer le systÃ¨me de batterie
            battery, created = BatterySystem.objects.get_or_create(
                simulation_id=django_installation.simulation.id,
                defaults={
                    'capacite_kwh': battery_capacity or 10.0,
                    'capacite_utilisable_kwh': (battery_capacity or 10.0) * 0.9,
                    'puissance_max_kw': (battery_capacity or 10.0) * 0.5,
                    'cout_installation': (battery_capacity or 10.0) * 800
                }
            )
            
            # Simuler le comportement de la batterie
