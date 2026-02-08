            donnees_horaires=df if include_hourly_data else None
        )


def calculate_autoconsumption_for_power(
    puissance_kwc: float,
    production_horaire_kw: np.ndarray,
    consommation_horaire_kw: np.ndarray
) -> HourlyResults:
    """
    Fonction helper pour calculer l'autoconsommation pour une puissance donnÃ©e.
    
    Cette fonction est pratique pour l'optimiseur qui testera plusieurs puissances.
    
    Args:
        puissance_kwc: Puissance en kWc
        production_horaire_kw: Production horaire (8760 valeurs)
        consommation_horaire_kw: Consommation horaire (8760 valeurs)
    
    Returns:
        HourlyResults: RÃ©sultats du calcul
    """
    calculator = HourlyAutoconsumptionCalculator(puissance_kwc)
    return calculator.calculate(production_horaire_kw, consommation_horaire_kw)
