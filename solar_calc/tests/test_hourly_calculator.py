"""
Tests unitaires pour le calculateur horaire.
"""

import pytest
import numpy as np
from solar_calc.services.hourly_calculator import HourlyAutoconsumptionCalculator, HourlyResults


class TestHourlyCalculator:
    """Tests du calculateur horaire."""
    
    def test_calcul_simple(self):
        """Test avec données simplifiées."""
        # Création de données test (8760 heures)
        # Production constante de 0.5 kW
        production_horaire_kw = np.array([0.5] * 8760)
        # Consommation constante de 0.3 kW
        consommation_horaire_kw = np.array([0.3] * 8760)
        
        calculator = HourlyAutoconsumptionCalculator(puissance_kwc=4.0)
        
        results = calculator.calculate(
            production_horaire_kw=production_horaire_kw,
            consommation_horaire_kw=consommation_horaire_kw
        )
        
        # Vérifications
        # Production annuelle = 0.5 kW * 8760h = 4380 kWh
        assert results.production_annuelle_kwh == pytest.approx(4380, rel=0.01)
        # Consommation annuelle = 0.3 kW * 8760h = 2628 kWh
        assert results.consommation_annuelle_kwh == pytest.approx(2628, rel=0.01)
        # Autoconso = min(0.5, 0.3) * 8760 = 2628 kWh
        assert results.autoconsommation_kwh == pytest.approx(2628, rel=0.01)
        # Injection = (0.5 - 0.3) * 8760 = 1752 kWh
        assert results.injection_reseau_kwh == pytest.approx(1752, rel=0.01)
        # Taux autoconso = 2628 / 4380 * 100 = 60%
        assert results.taux_autoconsommation_pct == pytest.approx(60, rel=1)
        # Taux autoprod = 2628 / 2628 * 100 = 100%
        assert results.taux_autoproduction_pct == pytest.approx(100, rel=1)
    
    def test_autoconso_ne_depasse_pas_consommation(self):
        """L'autoconsommation ne peut pas dépasser la consommation."""
        # Production très élevée (5 kW constant)
        production_horaire_kw = np.array([5.0] * 8760)
        # Consommation faible (0.2 kW constant)
        consommation_horaire_kw = np.array([0.2] * 8760)
        
        calculator = HourlyAutoconsumptionCalculator(puissance_kwc=10.0)
        
        results = calculator.calculate(
            production_horaire_kw=production_horaire_kw,
            consommation_horaire_kw=consommation_horaire_kw
        )
        
        # L'autoconso doit être égale à la consommation (pas plus)
        assert results.autoconsommation_kwh <= results.consommation_annuelle_kwh
        assert results.autoconsommation_kwh == pytest.approx(results.consommation_annuelle_kwh, rel=0.01)
        
        # Vérifier que tout le surplus est inje