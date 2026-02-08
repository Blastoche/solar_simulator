            battery_result = BatterySimulationService.simulate(
                battery=battery,
                donnees_horaires=resultats_autoconso['donnees_horaires'],
                save_logs=False
            )
            
            # Calculer les impacts financiers
            financial = BatterySimulationService.calculate_financial(
                battery_result=battery_result,
                donnees_sans_batterie=resultats_autoconso,
                cout_batterie=float(battery.cout_installation)
            )
            
            # Mettre Ã  jour le systÃ¨me de batterie
            battery.cycles_annuels = battery_result['cycles_annuels']
            battery.duree_vie_annees = battery_result['duree_vie_ans']
            battery.autoconso_gain_pct = battery_result['gain_autoconso_pct']
            battery.economie_annuelle = financial['economie_annuelle']
            battery.roi_annees = financial['roi_annees']
            battery.save()
            
            # Ajouter les rÃ©sultats de la batterie
            resultats['battery'] = {
                **battery_result,
                'financial': financial,
                'system': battery
            }
            
            logger.info(
                f"ðŸ”‹ Batterie {battery.capacite_kwh}kWh : "
                f"ROI {financial['roi_annees']:.1f} ans"
            )
        
        # Stocker les rÃ©sultats
        self.results = resultats
        
        return resultats


def run_simulation_from_django_objects(
    django_installation,
    django_profile,
    use_real_weather: bool = True,
    irradiation_annuelle_fallback: float = None
) -> dict:
    """
    Fonction helper pour exÃ©cuter une simulation depuis des objets Django.
    
    Args:
        django_installation: ModÃ¨le Django SolarInstallationModel
        django_profile: ModÃ¨le Django ConsumptionProfileModel
        use_real_weather: Utiliser les donnÃ©es PVGIS (True) ou simplifiÃ©es (False)
        irradiation_annuelle_fallback: Irradiation de secours en kWh/mÂ²/an
        
    Returns:
        dict: RÃ©sultats de la simulation
        
    Example:
        >>> from solar_calc.models import SolarInstallationModel, ConsumptionProfileModel
        >>> installation = SolarInstallationModel.objects.first()
        >>> profile = ConsumptionProfileModel.objects.first()
        >>> results = run_simulation_from_django_objects(installation, profile)
        >>> print(f"Production: {results['production_annuelle_kwh']:.0f} kWh/an")
    """
    service = SimulationService()
    return service.run_simulation_complete(
        django_installation,
        django_profile,
        use_real_weather=use_real_weather,
        irradiation_annuelle_fallback=irradiation_annuelle_fallback
    )
