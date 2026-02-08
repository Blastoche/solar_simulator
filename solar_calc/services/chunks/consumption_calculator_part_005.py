        
        return cout_base - cout_hphc  # Positif = Ã©conomie avec HP/HC


def calculate_consumption_from_form(form_data: Dict) -> Dict:
    """
    Fonction helper pour calculer la consommation depuis un formulaire.
    
    Args:
        form_data: DonnÃ©es du formulaire
    
    Returns:
        RÃ©sultats du calcul
    """
    calculator = ConsumptionCalculator(form_data)
    return calculator.calculate_total()
