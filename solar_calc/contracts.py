"""
Contrats de données pour le module solar_calc.
Définit les structures garanties par les calculs.
"""

from dataclasses import dataclass
from typing import List, Dict, Any
import pandas as pd


@dataclass
class ProductionResult:
    """
    Résultat standardisé d'un calcul de production.
    
    Attributes:
        annuelle: Production annuelle totale (kWh)
        specifique: Production spécifique (kWh/kWc)
        monthly: Liste de 12 valeurs mensuelles (kWh)
        daily: Profil horaire moyen (24 valeurs en kW)
        autoconso_ratio: Taux d'autoconsommation (%)
        injection: Énergie injectée au réseau (kWh)
        performance_ratio: PR appliqué (0-1)
    """
    annuelle: float
    specifique: float
    monthly: List[float]
    daily: List[float]
    autoconso_ratio: float
    injection: float
    performance_ratio: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit en dictionnaire pour compatibilité."""
        return {
            'annuelle': self.annuelle,
            'specifique': self.specifique,
            'monthly': self.monthly,
            'daily': self.daily,
            'autoconso_ratio': self.autoconso_ratio,
            'injection': self.injection,
            'performance_ratio': self.performance_ratio,
        }


@dataclass
class ConsumptionResult:
    """
    Résultat standardisé d'un calcul de consommation.
    
    Attributes:
        annuelle: Consommation annuelle totale (kWh)
        monthly: Liste de 12 valeurs mensuelles (kWh)
        daily: Profil horaire moyen (24 valeurs en kW)
        source: Source du calcul ('formulaire', 'expert', 'defaut')
    """
    annuelle: float
    monthly: List[float]
    daily: List[float]
    source: str = 'formulaire'
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit en dictionnaire pour compatibilité."""
        return {
            'annuelle': self.annuelle,
            'monthly': self.monthly,
            'daily': self.daily,
            'source': self.source,
        }


@dataclass
class FinancialResult:
    """
    Résultat standardisé d'une analyse financière.
    
    Attributes:
        economie_annuelle: Économie annuelle (€)
        roi_25ans: ROI sur 25 ans (€)
        taux_rentabilite: Taux de rentabilité annuel (%)
        cout_installation: Coût initial (€)
        payback_years: Temps de retour (années)
    """
    economie_annuelle: float
    roi_25ans: float
    taux_rentabilite: float
    cout_installation: float
    payback_years: float = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit en dictionnaire pour compatibilité."""
        return {
            'economie_annuelle': self.economie_annuelle,
            'roi': self.roi_25ans,
            'taux_rentabilite': self.taux_rentabilite,
            'cout_installation': self.cout_installation,
            'payback_years': self.payback_years,
        }
    
    def __post_init__(self):
        """Calcule le payback si possible."""
        if self.payback_years is None and self.economie_annuelle > 0:
            self.payback_years = round(
                self.cout_installation / self.economie_annuelle, 
                1
            )


@dataclass
class SimulationResult:
    """
    Résultat complet d'une simulation.
    Agrège production, consommation et finance.
    """
    production: ProductionResult
    consumption: ConsumptionResult
    financial: FinancialResult
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit tout en dictionnaire."""
        return {
            'production': self.production.to_dict(),
            'consumption': self.consumption.to_dict(),
            'financial': self.financial.to_dict(),
        }


def validate_production_result(result: Dict[str, Any]) -> bool:
    """
    Valide qu'un résultat de production respecte le contrat.
    
    Contrat :
        - 'annuelle' : float > 0
        - 'monthly' : list de 12 floats
        - 'daily' : list de 24 floats
        - 'autoconso_ratio' : float entre 0 et 100
    
    Args:
        result: Dictionnaire à valider
    
    Returns:
        True si valide
    
    Raises:
        ValueError: Si non-conforme
    """
    required = ['annuelle', 'monthly', 'daily', 'autoconso_ratio']
    missing = set(required) - set(result.keys())
    if missing:
        raise ValueError(f"Clés manquantes dans production : {missing}")
    
    if result['annuelle'] <= 0:
        raise ValueError("Production annuelle doit être > 0")
    
    if len(result['monthly']) != 12:
        raise ValueError(f"monthly doit avoir 12 valeurs, a {len(result['monthly'])}")
    
    if len(result['daily']) != 24:
        raise ValueError(f"daily doit avoir 24 valeurs, a {len(result['daily'])}")
    
    if not (0 <= result['autoconso_ratio'] <= 100):
        raise ValueError(f"autoconso_ratio doit être entre 0-100, est {result['autoconso_ratio']}")
    
    return True


def validate_consumption_result(result: Dict[str, Any]) -> bool:
    """
    Valide qu'un résultat de consommation respecte le contrat.
    
    Args:
        result: Dictionnaire à valider
    
    Returns:
        True si valide
    
    Raises:
        ValueError: Si non-conforme
    """
    required = ['annuelle', 'monthly', 'daily']
    missing = set(required) - set(result.keys())
    if missing:
        raise ValueError(f"Clés manquantes dans consommation : {missing}")
    
    if result['annuelle'] <= 0:
        raise ValueError("Consommation annuelle doit être > 0")
    
    if len(result['monthly']) != 12:
        raise ValueError(f"monthly doit avoir 12 valeurs, a {len(result['monthly'])}")
    
    if len(result['daily']) != 24:
        raise ValueError(f"daily doit avoir 24 valeurs, a {len(result['daily'])}")
    
    return True