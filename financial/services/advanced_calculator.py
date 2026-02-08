"""
Calculs financiers avancés pour les simulations solaires.
Projections sur 25 ans avec inflation, TURPE, aides, etc.
"""

import logging
from typing import Dict, List, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class FinancialProjection:
    """Projection financière année par année."""
    annee: int
    facture_sans_solaire: float
    facture_avec_solaire: float
    economie_annuelle: float
    economie_cumulee: float
    rachat_surplus: float
    investissement_restant: float


class AdvancedFinancialCalculator:
    """
    Calculateur financier avancé avec projections 25 ans.
    """
    
    # Constantes France 2025 (Source: photovoltaique.info)
    PRIX_KWH_BASE = 0.2516  # €/kWh TTC (tarif réglementé base 2025)
    PRIX_KWH_HP = 0.27      # €/kWh TTC (heures pleines)
    PRIX_KWH_HC = 0.2068    # €/kWh TTC (heures creuses)
    INFLATION_ELECTRICITE = 0.03  # 3% par an (moyenne historique)
    
    # TURPE 2025 - Part fixe annuelle selon puissance (simplifié)
    # Source: https://www.photovoltaique.info/fr/tarifs-dachat-et-autoconsommation/couts-reglementaires/couts-dacces-au-reseau-turpe/
    TURPE_FIXE_6KVA = 51.17  # €/an pour 6 kVA (cas le plus courant)
    TURPE_FIXE_9KVA = 63.26  # €/an pour 9 kVA
    TURPE_FIXE_12KVA = 75.35 # €/an pour 12 kVA
    
    # Tarif rachat surplus (Source: arrêté tarifaire 2025)
    # https://www.photovoltaique.info/fr/tarifs-dachat-et-autoconsommation/tarifs-dachat/
    PRIX_RACHAT_SURPLUS_0_9 = 0.04    # €/kWh (≤9 kWc)
    PRIX_RACHAT_SURPLUS_9_100 = 0.07  # €/kWh (9-100 kWc)
    
    COUT_INSTALLATION_PAR_KWC = 1800  # €/kWc (moyenne 2025, estimation)
    
    # Primes autoconsommation (en €/kWc) - Source : https://www.photovoltaique.info
    # Tarifs 2026 Q1 (Arrêté S21 - 17e trimestre - janvier à mars 2026)
    PRIMES_AUTOCONSO = {
        (0, 9): 80,       # ≤9 kWc : 0.08€/Wc = 80€/kWc
        (9, 36): 140,     # 9-36 kWc : 0.14€/Wc = 140€/kWc
        (36, 100): 70,    # 36-100 kWc : 0.07€/Wc = 70€/kWc
    }
    
    def __init__(
        self,
        puissance_kwc: float,
        production_annuelle: float,
        consommation_annuelle: float,
        autoconso_ratio: float,
        injection_reseau: float
    ):
        """
        Initialise le calculateur.
        
        Args:
            puissance_kwc: Puissance installée (kWc)
            production_annuelle: Production annuelle (kWh)
            consommation_annuelle: Consommation annuelle (kWh)
            autoconso_ratio: Taux d'autoconsommation (0-100)
            injection_reseau: Énergie injectée (kWh)
        """
        self.puissance_kwc = puissance_kwc
        self.production_annuelle = production_annuelle
        self.consommation_annuelle = consommation_annuelle
        self.autoconso_ratio = autoconso_ratio / 100  # Convertir en ratio
        self.injection_reseau = injection_reseau
        self.energie_autoconsommee = production_annuelle * self.autoconso_ratio
        
    def calculate_25_years_projection(self) -> List[FinancialProjection]:
        """
        Calcule la projection financière sur 25 ans.
        
        Returns:
            Liste de projections année par année
        """
        projections = []
        economie_cumulee = 0
        cout_installation = self.puissance_kwc * self.COUT_INSTALLATION_PAR_KWC
        prime_autoconso = self._calculate_prime_autoconso()
        
        # Déduire la prime de l'investissement initial
        investissement_initial = cout_installation - prime_autoconso
        
        for annee in range(1, 26):
            # Prix électricité augmente avec inflation
            prix_kwh = self.PRIX_KWH_BASE * (1 + self.INFLATION_ELECTRICITE) ** (annee - 1)
            
            # Déterminer TURPE fixe selon puissance
            if self.puissance_kwc <= 6:
                turpe_annuel = self.TURPE_FIXE_6KVA
            elif self.puissance_kwc <= 9:
                turpe_annuel = self.TURPE_FIXE_9KVA
            else:
                turpe_annuel = self.TURPE_FIXE_12KVA
            
            # Facture SANS solaire (augmente chaque année)
            facture_sans_solaire = (self.consommation_annuelle * prix_kwh) + turpe_annuel
            
            # Facture AVEC solaire
            # Ce qu'on achète encore au réseau
            energie_achetee = self.consommation_annuelle - self.energie_autoconsommee
            facture_avec_solaire = (energie_achetee * prix_kwh) + turpe_annuel
            
            # Revenu vente surplus (selon puissance)
            if self.puissance_kwc <= 9:
                prix_rachat = self.PRIX_RACHAT_SURPLUS_0_9
            else:
                prix_rachat = self.PRIX_RACHAT_SURPLUS_9_100
            
            rachat_surplus = self.injection_reseau * prix_rachat
            
            # Économie annuelle
            economie_annuelle = (facture_sans_solaire - facture_avec_solaire) + rachat_surplus
            economie_cumulee += economie_annuelle
            
            # Investissement restant à amortir
            investissement_restant = investissement_initial - economie_cumulee
            
            projections.append(FinancialProjection(
                annee=annee,
                facture_sans_solaire=round(facture_sans_solaire, 2),
                facture_avec_solaire=round(facture_avec_solaire, 2),
                economie_annuelle=round(economie_annuelle, 2),
                economie_cumulee=round(economie_cumulee, 2),
                rachat_surplus=round(rachat_surplus, 2),
                investissement_restant=round(investissement_restant, 2)
            ))
        
        return projections
    
    def _calculate_prime_autoconso(self) -> float:
        """
        Calcule la prime à l'autoconsommation selon la puissance.
        
        Returns:
            Montant de la prime (€)
        """
        for (min_kwc, max_kwc), prime_par_kwc in self.PRIMES_AUTOCONSO.items():
            if min_kwc < self.puissance_kwc <= max_kwc:
                return self.puissance_kwc * prime_par_kwc
        
        # Si > 100 kWc, pas de prime
        return 0
    
    def get_summary_metrics(self) -> Dict[str, float]:
        """
        Calcule les métriques résumées.
        
        Returns:
            Dictionnaire avec métriques clés
        """
        projections = self.calculate_25_years_projection()
        
        # Trouver année de retour sur investissement
        payback_year = None
        for proj in projections:
            if proj.investissement_restant <= 0:
                payback_year = proj.annee
                break
        
        cout_installation = self.puissance_kwc * self.COUT_INSTALLATION_PAR_KWC
        prime = self._calculate_prime_autoconso()
        
        return {
            'cout_installation': round(cout_installation, 2),
            'prime_autoconso': round(prime, 2),
            'investissement_net': round(cout_installation - prime, 2),
            'economie_annuelle_an1': round(projections[0].economie_annuelle, 2),
            'economie_annuelle_an25': round(projections[24].economie_annuelle, 2),
            'economie_totale_25ans': round(projections[24].economie_cumulee, 2),
            'payback_years': payback_year if payback_year else 25,
            'taux_rentabilite': round((projections[24].economie_cumulee / (cout_installation - prime)) * 100 / 25, 2)
        }
    
    def get_projection_table_data(self) -> List[Dict]:
        """
        Retourne les données pour le tableau de projection.
        Format optimisé pour affichage PDF.
        
        Returns:
            Liste de dictionnaires (années sélectionnées)
        """
        projections = self.calculate_25_years_projection()
        
        # Sélectionner années clés : 1, 2, 3, 5, 10, 15, 20, 25
        annees_cles = [1, 2, 3, 5, 10, 15, 20, 25]
        
        # Ajouter l'année d'amortissement si pas déjà présente
        payback_year = None
        for proj in projections:
            if proj.investissement_restant <= 0:
                payback_year = proj.annee
                break
        
        # Années à afficher (inclure payback si pas dans la liste)
        annees_a_afficher = annees_cles.copy()
        if payback_year and payback_year not in annees_a_afficher:
            annees_a_afficher.append(payback_year)
            annees_a_afficher.sort()
        
        return [
            {
                'annee': proj.annee,
                'facture_sans': proj.facture_sans_solaire,
                'facture_avec': proj.facture_avec_solaire,
                'surplus': proj.rachat_surplus,
                'economie': proj.economie_annuelle,
                'cumul': proj.economie_cumulee,
                'status': '✅' if proj.investissement_restant <= 0 else '⏳'
            }
            for proj in projections
            if proj.annee in annees_a_afficher
        ]


def calculate_co2_impact(production_annuelle: float) -> Dict[str, float]:
    """
    Calcule l'impact environnemental en CO2.
    
    Args:
        production_annuelle: Production solaire annuelle (kWh)
    
    Returns:
        Dictionnaire avec équivalents CO2
    """
    # Facteur d'émission mix électrique français
    CO2_PAR_KWH = 0.0557  # kg CO2/kWh (mix FR 2024)
    
    co2_evite_annuel = production_annuelle * CO2_PAR_KWH
    co2_evite_25ans = co2_evite_annuel * 25
    
    # Équivalents
    km_voiture = co2_evite_25ans / 0.12  # 120g CO2/km pour voiture moyenne
    arbres_equivalent = co2_evite_25ans / 25  # 1 arbre absorbe ~25kg CO2/an
    
    return {
        'co2_evite_annuel_kg': round(co2_evite_annuel, 1),
        'co2_evite_25ans_tonnes': round(co2_evite_25ans / 1000, 2),
        'equivalent_km_voiture': round(km_voiture, 0),
        'equivalent_arbres': round(arbres_equivalent, 0)
    }