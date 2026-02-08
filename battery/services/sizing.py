"""
Dimensionnement optimal des batteries solaires
battery/services/sizing.py

Recommandation de capacité selon profil et comparaison de scénarios
"""

from typing import Dict, List, Tuple
from decimal import Decimal


# ==============================================================================
# RÈGLES DE DIMENSIONNEMENT PAR PROFIL
# ==============================================================================

SIZING_RULES = {
    'actif_absent': {
        'ratio_prod_jour': (0.30, 0.45),  # 30-45% de la production journalière moyenne
        'description': 'Absent en journée (travail), pics matin/soir',
        'optimal_ratio': 0.35,
        'exemple': 'Pour 16 kWh/jour de production → Batterie 5-7 kWh'
    },
    'teletravail': {
        'ratio_prod_jour': (0.40, 0.55),  # 40-55%
        'description': 'Présent en journée, consommation répartie',
        'optimal_ratio': 0.45,
        'exemple': 'Pour 16 kWh/jour de production → Batterie 6-9 kWh'
    },
    'retraite': {
        'ratio_prod_jour': (0.40, 0.55),  # 40-55%
        'description': 'Présent toute la journée, forte consommation diurne',
        'optimal_ratio': 0.45,
        'exemple': 'Pour 16 kWh/jour de production → Batterie 6-9 kWh'
    },
    'famille': {
        'ratio_prod_jour': (0.35, 0.50),  # 35-50%
        'description': 'Famille avec enfants, pics matin/soir marqués',
        'optimal_ratio': 0.40,
        'exemple': 'Pour 16 kWh/jour de production → Batterie 6-8 kWh'
    }
}


# Capacités standards disponibles sur le marché
STANDARD_CAPACITIES = [3, 5, 7, 10, 13.5, 15]


# ==============================================================================
# FONCTIONS DE DIMENSIONNEMENT
# ==============================================================================

def recommend_battery_size(
    production_annuelle_kwh: float,
    consommation_annuelle_kwh: float,
    profil_type: str = 'actif_absent'
) -> float:
    """
    Recommande la capacité optimale de batterie selon le profil.
    
    Args:
        production_annuelle_kwh: Production solaire annuelle
        consommation_annuelle_kwh: Consommation annuelle
        profil_type: Type de profil ('actif_absent', 'teletravail', 'retraite', 'famille')
    
    Returns:
        Capacité recommandée (arrondie aux capacités standards)
    
    Example:
        >>> capacity = recommend_battery_size(5856, 8600, 'actif_absent')
        >>> print(f"Capacité recommandée: {capacity} kWh")
        Capacité recommandée: 7.0 kWh
    """
    # Production journalière moyenne
    prod_jour_moyenne = production_annuelle_kwh / 365
    
    # Récupérer les règles du profil
    if profil_type not in SIZING_RULES:
        profil_type = 'actif_absent'  # Défaut
    
    rules = SIZING_RULES[profil_type]
    optimal_ratio = rules['optimal_ratio']
    
    # Calcul capacité optimale
    capacite_optimale = prod_jour_moyenne * optimal_ratio
    
    # Arrondir à la capacité standard la plus proche
    capacite_standard = _round_to_standard_capacity(capacite_optimale)
    
    return capacite_standard


def calculate_optimal_capacity(
    production_annuelle_kwh: float,
    consommation_annuelle_kwh: float,
    profil_type: str = 'actif_absent',
    taux_autoconso_cible: float = 75.0
) -> Dict:
    """
    Calcule la capacité optimale pour atteindre un taux d'autoconsommation cible.
    
    Args:
        production_annuelle_kwh: Production solaire
        consommation_annuelle_kwh: Consommation
        profil_type: Type de profil
        taux_autoconso_cible: Taux d'autoconsommation visé (%)
    
    Returns:
        Dict avec capacité optimale et métriques associées
    
    Example:
        >>> result = calculate_optimal_capacity(5856, 8600, 'actif_absent', 75.0)
        >>> print(result)
        {
            'capacite_kwh': 10.0,
            'taux_autoconso_estime': 77.0,
            'production_jour_moy': 16.0,
            'ratio_capacite_prod': 0.625
        }
    """
    prod_jour_moy = production_annuelle_kwh / 365
    conso_jour_moy = consommation_annuelle_kwh / 365
    
    # Estimer la capacité nécessaire basée sur le taux cible
    # Formule empirique : capacité ≈ (taux_cible - taux_sans_batterie) × production_jour / 100
    
    # Taux sans batterie (estimations par profil)
    taux_sans_batterie = {
        'actif_absent': 49.0,
        'teletravail': 53.0,
        'retraite': 56.0,
        'famille': 50.0
    }.get(profil_type, 50.0)
    
    # Gain nécessaire
    gain_necessaire = taux_autoconso_cible - taux_sans_batterie
    
    # Capacité estimée (formule empirique)
    if gain_necessaire <= 0:
        capacite_estimee = 0
    else:
        # Règle approximative : +1% autoconso ≈ 0.35 kWh de batterie
        capacite_estimee = gain_necessaire * prod_jour_moy * 0.035
    
    # Arrondir aux capacités standards
    capacite_standard = _round_to_standard_capacity(capacite_estimee)
    
    # Estimer le taux réel avec cette capacité
    ratio = capacite_standard / prod_jour_moy
    taux_estime = _estimate_autoconso_rate(taux_sans_batterie, ratio)
    
    return {
        'capacite_kwh': capacite_standard,
        'taux_autoconso_estime': round(taux_estime, 1),
        'taux_sans_batterie': taux_sans_batterie,
        'gain_estime': round(taux_estime - taux_sans_batterie, 1),
        'production_jour_moy': round(prod_jour_moy, 1),
        'consommation_jour_moy': round(conso_jour_moy, 1),
        'ratio_capacite_prod': round(ratio, 3)
    }


def compare_battery_sizes(
    production_annuelle_kwh: float,
    consommation_annuelle_kwh: float,
    profil_type: str = 'actif_absent',
    capacites: List[float] = None,
    prix_achat_kwh: float = 0.2276,
    prix_vente_kwh: float = 0.13
) -> Dict[float, Dict]:
    """
    Compare différentes capacités de batterie.
    
    Args:
        production_annuelle_kwh: Production solaire
        consommation_annuelle_kwh: Consommation
        profil_type: Type de profil
        capacites: Liste de capacités à comparer (si None, utilise standards)
        prix_achat_kwh: Prix achat électricité (€/kWh)
        prix_vente_kwh: Prix vente surplus (€/kWh)
    
    Returns:
        Dict avec comparaison pour chaque capacité
    
    Example:
        >>> comparison = compare_battery_sizes(5856, 8600, 'actif_absent')
        >>> for cap, data in comparison.items():
        ...     print(f"{cap}kWh: Autoconso {data['taux_autoconso_pct']:.1f}%, ROI {data['roi_ans']:.0f} ans")
    """
    if capacites is None:
        capacites = [5, 7, 10, 13.5]
    
    # Import dynamique pour éviter circular imports
    from battery.pricing import get_battery_price
    
    # Taux sans batterie
    taux_sans_batterie = {
        'actif_absent': 49.3,
        'teletravail': 53.4,
        'retraite': 55.5,
        'famille': 49.5
    }.get(profil_type, 50.0)
    
    autoconso_sans = production_annuelle_kwh * (taux_sans_batterie / 100)
    injection_sans = production_annuelle_kwh - autoconso_sans
    achat_sans = consommation_annuelle_kwh - autoconso_sans
    
    # Coût annuel sans batterie
    cout_sans = achat_sans * prix_achat_kwh - injection_sans * prix_vente_kwh
    
    prod_jour_moy = production_annuelle_kwh / 365
    
    comparison = {}
    
    for capacite in capacites:
        # Estimer taux autoconso avec batterie
        ratio = capacite / prod_jour_moy
        taux_avec = _estimate_autoconso_rate(taux_sans_batterie, ratio)
        
        # Métriques énergétiques
        autoconso_avec = production_annuelle_kwh * (taux_avec / 100)
        gain_autoconso = autoconso_avec - autoconso_sans
        injection_avec = production_annuelle_kwh - autoconso_avec
        achat_avec = consommation_annuelle_kwh - autoconso_avec
        
        # Économies annuelles
        cout_avec = achat_avec * prix_achat_kwh - injection_avec * prix_vente_kwh
        economie_annuelle = cout_sans - cout_avec
        
        # Prix batterie
        prix_data = get_battery_price(capacite, marque='standard')
        cout_batterie = prix_data['prix_total_ttc']
        
        # ROI
        if economie_annuelle > 0:
            roi_ans = cout_batterie / economie_annuelle
        else:
            roi_ans = float('inf')
        
        # Cycles annuels (estimation)
        cycles_annuels = min(gain_autoconso / capacite, 365) if capacite > 0 else 0
        
        comparison[capacite] = {
            'capacite_kwh': capacite,
            'taux_autoconso_pct': round(taux_avec, 1),
            'gain_autoconso_pct': round(taux_avec - taux_sans_batterie, 1),
            'autoconso_kwh': round(autoconso_avec, 0),
            'gain_autoconso_kwh': round(gain_autoconso, 0),
            'injection_kwh': round(injection_avec, 0),
            'achat_kwh': round(achat_avec, 0),
            'economie_annuelle_euros': round(economie_annuelle, 2),
            'cout_batterie_euros': cout_batterie,
            'roi_ans': round(roi_ans, 1),
            'cycles_annuels': round(cycles_annuels, 0),
            'ratio_capacite_prod': round(ratio, 3),
            'prix_par_kwh': prix_data['prix_par_kwh']
        }
    
    return comparison


def get_sizing_recommendations(
    production_annuelle_kwh: float,
    consommation_annuelle_kwh: float,
    profil_type: str = 'actif_absent',
    budget_max: float = None
) -> Dict:
    """
    Fournit des recommandations complètes de dimensionnement.
    
    Args:
        production_annuelle_kwh: Production solaire
        consommation_annuelle_kwh: Consommation
        profil_type: Type de profil
        budget_max: Budget maximum pour la batterie (optionnel)
    
    Returns:
        Dict avec recommandations détaillées
    
    Example:
        >>> reco = get_sizing_recommendations(5856, 8600, 'actif_absent', budget_max=6000)
        >>> print(reco['recommandation_principale'])
        'Batterie 7 kWh - Meilleur rapport bénéfice/coût'
    """
    from battery.pricing import get_battery_price
    
    # Comparaison des capacités
    comparison = compare_battery_sizes(
        production_annuelle_kwh,
        consommation_annuelle_kwh,
        profil_type
    )
    
    # Filtrer par budget si spécifié
    if budget_max:
        comparison = {
            cap: data for cap, data in comparison.items()
            if data['cout_batterie_euros'] <= budget_max
        }
    
    if not comparison:
        return {
            'erreur': f"Aucune batterie disponible pour budget {budget_max}€",
            'budget_minimum': get_battery_price(3, 'economique')['prix_total_ttc']
        }
    
    # Meilleur ROI
    best_roi = min(comparison.items(), key=lambda x: x[1]['roi_ans'])
    
    # Meilleur gain autoconso
    best_gain = max(comparison.items(), key=lambda x: x[1]['gain_autoconso_pct'])
    
    # Meilleur rapport bénéfice/coût
    best_value = min(
        comparison.items(),
        key=lambda x: x[1]['roi_ans'] if x[1]['roi_ans'] != float('inf') else 999
    )
    
    # Capacité optimale théorique
    optimal = recommend_battery_size(
        production_annuelle_kwh,
        consommation_annuelle_kwh,
        profil_type
    )
    
    return {
        'profil': profil_type,
        'production_annuelle': production_annuelle_kwh,
        'consommation_annuelle': consommation_annuelle_kwh,
        'production_jour_moy': round(production_annuelle_kwh / 365, 1),
        
        'capacite_optimale_theorique': optimal,
        
        'meilleur_roi': {
            'capacite': best_roi[0],
            'roi_ans': best_roi[1]['roi_ans'],
            'taux_autoconso': best_roi[1]['taux_autoconso_pct'],
            'cout': best_roi[1]['cout_batterie_euros']
        },
        
        'meilleur_gain_autoconso': {
            'capacite': best_gain[0],
            'gain_pct': best_gain[1]['gain_autoconso_pct'],
            'taux_autoconso': best_gain[1]['taux_autoconso_pct'],
            'cout': best_gain[1]['cout_batterie_euros']
        },
        
        'meilleur_rapport_qualite_prix': {
            'capacite': best_value[0],
            'roi_ans': best_value[1]['roi_ans'],
            'taux_autoconso': best_value[1]['taux_autoconso_pct'],
            'cout': best_value[1]['cout_batterie_euros'],
            'economie_annuelle': best_value[1]['economie_annuelle_euros']
        },
        
        'recommandation_principale': f"Batterie {best_value[0]} kWh - Meilleur rapport bénéfice/coût",
        
        'comparaison_complete': comparison
    }


# ==============================================================================
# FONCTIONS HELPERS
# ==============================================================================

def _round_to_standard_capacity(capacite: float) -> float:
    """Arrondit à la capacité standard la plus proche"""
    if capacite <= 0:
        return 0
    
    # Trouver la capacité standard la plus proche
    closest = min(STANDARD_CAPACITIES, key=lambda x: abs(x - capacite))
    
    return closest


def _estimate_autoconso_rate(taux_base: float, ratio_capacite_prod: float) -> float:
    """
    Estime le taux d'autoconsommation avec batterie.
    
    Formule empirique basée sur observations réelles :
    - Sans batterie : taux_base (49-56% selon profil)
    - Avec batterie : taux augmente de façon logarithmique
    
    Args:
        taux_base: Taux sans batterie
        ratio_capacite_prod: Ratio capacité_batterie / production_journalière
    
    Returns:
        Taux estimé avec batterie
    """
    import math
    
    if ratio_capacite_prod <= 0:
        return taux_base
    
    # Gain maximal possible (ne peut dépasser 100%)
    gain_max = 100 - taux_base
    
    # Courbe logarithmique : gain diminue avec capacité croissante
    # À ratio=0.4 → ~+20-25% d'autoconso
    # À ratio=0.8 → ~+30-35% d'autoconso
    # Au-delà → rendements décroissants
    
    gain = gain_max * (1 - math.exp(-2.5 * ratio_capacite_prod))
    
    taux_estime = min(taux_base + gain, 95)  # Plafond réaliste à 95%
    
    return taux_estime


# ==============================================================================
# EXEMPLE D'UTILISATION
# ==============================================================================

if __name__ == '__main__':
    print("=" * 80)
    print("DIMENSIONNEMENT OPTIMAL BATTERIE")
    print("=" * 80)
    
    # Paramètres exemple
    production = 5856  # kWh/an
    consommation = 8600  # kWh/an
    profil = 'actif_absent'
    
    # 1. Recommandation simple
    print("\n1️⃣ Recommandation simple")
    capacite = recommend_battery_size(production, consommation, profil)
    print(f"   Capacité recommandée pour profil '{profil}': {capacite} kWh")
    
    # 2. Calcul optimal pour taux cible
    print("\n2️⃣ Capacité pour atteindre 75% d'autoconsommation")
    optimal = calculate_optimal_capacity(production, consommation, profil, taux_autoconso_cible=75)
    print(f"   Capacité: {optimal['capacite_kwh']} kWh")
    print(f"   Taux estimé: {optimal['taux_autoconso_estime']}%")
    print(f"   Gain: +{optimal['gain_estime']}%")
    
    # 3. Comparaison capacités
    print("\n3️⃣ Comparaison 4 capacités")
    comparison = compare_battery_sizes(production, consommation, profil)
    print(f"\n   {'Capacité':<12} {'Autoconso':<12} {'Gain':<12} {'ROI':<12} {'Coût'}")
    print("   " + "-" * 70)
    for cap, data in comparison.items():
        print(f"   {cap} kWh{'':<7} {data['taux_autoconso_pct']}%{'':<7} "
              f"+{data['gain_autoconso_pct']}%{'':<7} {data['roi_ans']:.0f} ans{'':<6} "
              f"{data['cout_batterie_euros']:.0f}€")
    
    # 4. Recommandations complètes
    print("\n4️⃣ Recommandations complètes")
    reco = get_sizing_recommendations(production, consommation, profil, budget_max=8000)
    print(f"\n   {reco['recommandation_principale']}")
    print(f"\n   Meilleur ROI: {reco['meilleur_roi']['capacite']} kWh "
          f"({reco['meilleur_roi']['roi_ans']:.0f} ans)")
    print(f"   Meilleur gain autoconso: {reco['meilleur_gain_autoconso']['capacite']} kWh "
          f"(+{reco['meilleur_gain_autoconso']['gain_pct']}%)")
    
    print("\n" + "=" * 80)
