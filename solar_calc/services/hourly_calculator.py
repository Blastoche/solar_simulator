"""
Calculateur d'autoconsommation horaire.

Ce module calcule l'autoconsommation réelle heure par heure en croisant :
- Production horaire (8760 points PVGIS)
- Consommation horaire (profil utilisateur)

App Django: solar_calc
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class HourlyResults:
    """Résultats du calcul horaire d'autoconsommation."""
    
    # Totaux annuels
    production_annuelle_kwh: float
    consommation_annuelle_kwh: float
    autoconsommation_kwh: float
    injection_reseau_kwh: float
    achat_reseau_kwh: float
    
    # Taux
    taux_autoconsommation_pct: float  # Part de la prod consommée localement
    taux_autoproduction_pct: float    # Part de la conso couverte par la prod
    
    # Production spécifique
    production_specifique_kwh_kwc: float
    
    # Données détaillées
    production_mensuelle_kwh: List[float]
    consommation_mensuelle_kwh: List[float]
    autoconsommation_mensuelle_kwh: List[float]
    
    # DataFrame horaire complet (optionnel pour analyse)
    donnees_horaires: pd.DataFrame = None


class HourlyAutoconsumptionCalculator:
    """
    Calculateur d'autoconsommation basé sur les profils horaires réels.
    
    Méthode :
    - Pour chaque heure H de l'année (8760 heures) :
        - Autoconso[H] = min(Production[H], Consommation[H])
        - Injection[H] = max(0, Production[H] - Consommation[H])
        - Achat[H] = max(0, Consommation[H] - Production[H])
    
    Cette approche donne des résultats précis basés sur les courbes réelles
    de production et de consommation.
    """
    
    def __init__(self, puissance_kwc: float):
        """
        Initialise le calculateur.
        
        Args:
            puissance_kwc: Puissance installée en kWc
        """
        self.puissance_kwc = puissance_kwc
        logger.info(f"✅ HourlyCalculator initialisé pour {puissance_kwc} kWc")
    
    def calculate(
        self,
        production_horaire_kw: np.ndarray,  # 8760 valeurs
        consommation_horaire_kw: np.ndarray,  # 8760 valeurs
        include_hourly_data: bool = False
    ) -> HourlyResults:
        """
        Calcule l'autoconsommation heure par heure.
        
        Args:
            production_horaire_kw: Production horaire (8760 valeurs en kW)
            consommation_horaire_kw: Consommation horaire (8760 valeurs en kW)
            include_hourly_data: Si True, inclut le DataFrame horaire complet
        
        Returns:
            HourlyResults: Résultats complets du calcul
        """
        logger.info("🔄 Calcul autoconsommation horaire...")
        
        # Vérifications
        if len(production_horaire_kw) != 8760:
            raise ValueError(
                f"Production doit avoir 8760 valeurs (année complète), "
                f"reçu {len(production_horaire_kw)}"
            )
        
        if len(consommation_horaire_kw) != 8760:
            raise ValueError(
                f"Consommation doit avoir 8760 valeurs (année complète), "
                f"reçu {len(consommation_horaire_kw)}"
            )
        
        # Créer le DataFrame horaire
        df = pd.DataFrame({
            'production_kw': production_horaire_kw,
            'consommation_kw': consommation_horaire_kw
        })
        
        # Calcul heure par heure
        # Autoconsommation = ce qui est produit ET consommé simultanément
        df['autoconso_kw'] = df[['production_kw', 'consommation_kw']].min(axis=1)
        
        # Injection = surplus de production (non consommé)
        df['injection_kw'] = df.apply(
            lambda row: max(0, row['production_kw'] - row['consommation_kw']),
            axis=1
        )
        
        # Achat réseau = déficit de consommation (non couvert par prod)
        df['achat_kw'] = df.apply(
            lambda row: max(0, row['consommation_kw'] - row['production_kw']),
            axis=1
        )
        
        # ===== TOTAUX ANNUELS =====
        production_totale = df['production_kw'].sum()
        consommation_totale = df['consommation_kw'].sum()
        autoconso_totale = df['autoconso_kw'].sum()
        injection_totale = df['injection_kw'].sum()
        achat_total = df['achat_kw'].sum()
        
        # ===== TAUX =====
        # Taux d'autoconsommation = part de la production qui est consommée localement
        # (Important pour dimensionner : éviter sur-dimensionnement)
        taux_autoconso = (
            (autoconso_totale / production_totale * 100) 
            if production_totale > 0 else 0
        )
        
        # Taux d'autoproduction = part de la consommation couverte par la production
        # (Important pour autonomie énergétique)
        taux_autoprod = (
            (autoconso_totale / consommation_totale * 100) 
            if consommation_totale > 0 else 0
        )
        
        # ===== PRODUCTION SPÉCIFIQUE =====
        production_specifique = production_totale / self.puissance_kwc
        
        # ===== DONNÉES MENSUELLES =====
        # Créer un index temporel pour agréger par mois
        df['timestamp'] = pd.date_range(
            start='2023-01-01',  # Année fictive pour TMY
            periods=8760,
            freq='h'
        )
        df['month'] = df['timestamp'].dt.month
        
        # Agréger par mois
        monthly_prod = df.groupby('month')['production_kw'].sum()
        monthly_conso = df.groupby('month')['consommation_kw'].sum()
        monthly_autoconso = df.groupby('month')['autoconso_kw'].sum()
        
        # S'assurer d'avoir 12 mois
        production_mensuelle = []
        consommation_mensuelle = []
        autoconsommation_mensuelle = []
        
        for month in range(1, 13):
            production_mensuelle.append(
                round(monthly_prod.get(month, 0), 2)
            )
            consommation_mensuelle.append(
                round(monthly_conso.get(month, 0), 2)
            )
            autoconsommation_mensuelle.append(
                round(monthly_autoconso.get(month, 0), 2)
            )
        
        # ===== LOGS =====
        logger.info(f"📊 Production annuelle : {production_totale:.2f} kWh")
        logger.info(f"📊 Consommation annuelle : {consommation_totale:.2f} kWh")
        logger.info(f"⚡ Autoconsommation : {autoconso_totale:.2f} kWh ({taux_autoconso:.1f}%)")
        logger.info(f"🏠 Autoproduction : {taux_autoprod:.1f}%")
        logger.info(f"📤 Injection réseau : {injection_totale:.2f} kWh")
        logger.info(f"📥 Achat réseau : {achat_total:.2f} kWh")
        
        # ===== RÉSULTATS =====
        return HourlyResults(
            production_annuelle_kwh=round(production_totale, 2),
            consommation_annuelle_kwh=round(consommation_totale, 2),
            autoconsommation_kwh=round(autoconso_totale, 2),
            injection_reseau_kwh=round(injection_totale, 2),
            achat_reseau_kwh=round(achat_total, 2),
            taux_autoconsommation_pct=round(taux_autoconso, 2),
            taux_autoproduction_pct=round(taux_autoprod, 2),
            production_specifique_kwh_kwc=round(production_specifique, 2),
            production_mensuelle_kwh=production_mensuelle,
            consommation_mensuelle_kwh=consommation_mensuelle,
            autoconsommation_mensuelle_kwh=autoconsommation_mensuelle,
            donnees_horaires=df if include_hourly_data else None
        )


def calculate_autoconsumption_for_power(
    puissance_kwc: float,
    production_horaire_kw: np.ndarray,
    consommation_horaire_kw: np.ndarray
) -> HourlyResults:
    """
    Fonction helper pour calculer l'autoconsommation pour une puissance donnée.
    
    Cette fonction est pratique pour l'optimiseur qui testera plusieurs puissances.
    
    Args:
        puissance_kwc: Puissance en kWc
        production_horaire_kw: Production horaire (8760 valeurs)
        consommation_horaire_kw: Consommation horaire (8760 valeurs)
    
    Returns:
        HourlyResults: Résultats du calcul
    """
    calculator = HourlyAutoconsumptionCalculator(puissance_kwc)
    return calculator.calculate(production_horaire_kw, consommation_horaire_kw)
