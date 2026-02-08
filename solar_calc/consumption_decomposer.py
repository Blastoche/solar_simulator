"""
Module de décomposition de la consommation électrique par poste.

Décompose la consommation totale déclarée en différents postes
selon DPE, équipements, et nombre de personnes.

Basé sur les données ADEME 2022.
"""

import logging
import json

logger = logging.getLogger(__name__)


def decompose_consumption(profil):
    """
    Décompose la consommation totale en postes énergétiques.
    
    Args:
        profil (ConsumptionProfileModel): Profil de consommation
        
    Returns:
        dict: Décomposition {'chauffage': XXX, 'ecs': XXX, ...}
    """
    conso_totale = profil.consommation_annuelle_kwh
    conso_restante = conso_totale
    
    decomposition = {
        'chauffage': 0,
        'ecs': 0,
        'cuisson': 0,
        'electromenager': 0,
        'eclairage': 0,
        'multimedia': 0,
        'vehicule_electrique': 0,
        'piscine': 0,
    }
    
    # Charger appareils_json
    appareils_data = {}
    if profil.appareils_json:
        try:
            appareils_data = json.loads(profil.appareils_json)
        except Exception as e:
            logger.warning(f"Erreur lecture appareils_json: {e}")
    
    # ========== 1. VÉHICULE ÉLECTRIQUE (fixe) ==========
    # Estimation : 15 000 km/an à 17 kWh/100km = 2550 kWh/an
    if appareils_data.get('appareils', {}).get('vehicule_electrique', {}).get('present'):
        decomposition['vehicule_electrique'] = 2500
        conso_restante -= 2500
        logger.info(f"Véhicule électrique détecté : +2500 kWh/an")
    
    # ========== 2. PISCINE (fixe) ==========
    # Estimation : pompe filtration 8h/jour × 5 mois = ~2000 kWh/an
    if appareils_data.get('appareils', {}).get('piscine', {}).get('present'):
        decomposition['piscine'] = 2000
        conso_restante -= 2000
        logger.info(f"Piscine détectée : +2000 kWh/an")
    
    # ========== 3. CHAUFFAGE (selon DPE + surface + type) ==========
    if profil.type_chauffage in ['electrique', 'pompe_a_chaleur']:
        dpe = profil.get_effective_dpe() or 'D'
        surface = profil.surface_habitable
        
        # kWh EP/m²/an pour le chauffage seul (≈63% du DPE total selon ADEME)
        # Source : ADEME - Chiffres clés du climat 2022
        dpe_chauffage_values = {
            'A': 32,   # 50 × 0.63
            'B': 57,   # 90 × 0.63
            'C': 91,   # 145 × 0.63
            'D': 135,  # 215 × 0.63
            'E': 183,  # 290 × 0.63
            'F': 236,  # 375 × 0.63
            'G': 315   # 500 × 0.63
        }
        
        chauffage_ep = dpe_chauffage_values.get(dpe, 135) * surface
        
        if profil.type_chauffage == 'electrique':
            # Conversion énergie primaire → finale (coefficient 2.3 pour élec)
            decomposition['chauffage'] = chauffage_ep / 2.3
        elif profil.type_chauffage == 'pompe_a_chaleur':
            # PAC : COP moyen de 3
            decomposition['chauffage'] = (chauffage_ep / 2.3) / 3
        
        # Limiter au maximum disponible (max 70% de la conso restante)
        decomposition['chauffage'] = min(decomposition['chauffage'], conso_restante * 0.70)
        conso_restante -= decomposition['chauffage']
        
        logger.info(f"Chauffage {profil.type_chauffage} - DPE {dpe} - {surface}m² : {decomposition['chauffage']:.0f} kWh/an")
    
    # ========== 4. ECS (selon nb personnes + type) ==========
    nb_personnes = profil.nb_personnes
    
    # Convertir nb_personnes si c'est une string (ex: "3-4 personnes")
    if isinstance(nb_personnes, str):
        if "5" in nb_personnes or "+" in nb_personnes:
            nb_personnes = 5
        elif "3" in nb_personnes or "4" in nb_personnes:
            nb_personnes = 3.5
        elif "2" in nb_personnes:
            nb_personnes = 2
        else:
            nb_personnes = 1
    
    if profil.type_ecs == 'electrique':
        # Ballon électrique : 900 kWh/personne/an (source ADEME)
        decomposition['ecs'] = 900 * nb_personnes
    elif profil.type_ecs == 'thermodynamique':
        # Ballon thermodynamique : COP moyen 2.5
        decomposition['ecs'] = (900 * nb_personnes) / 2.5
    
    # Limiter au maximum disponible (max 50% de la conso restante)
    decomposition['ecs'] = min(decomposition['ecs'], conso_restante * 0.50)
    conso_restante -= decomposition['ecs']
    
    logger.info(f"ECS {profil.type_ecs} pour {nb_personnes} pers : {decomposition['ecs']:.0f} kWh/an")
    
    # ========== 5. RÉPARTIR LE RESTE ==========
    # Ratios selon ADEME pour les usages spécifiques électricité
    # Source : ADEME - Chiffres clés du climat 2022
    if conso_restante > 0:
        ratios_reste = {
            'cuisson': 0.25,        # 25% - Plaques, four
            'electromenager': 0.35, # 35% - Frigo, congélo, lave-linge, etc.
            'eclairage': 0.20,      # 20% - Éclairage intérieur/extérieur
            'multimedia': 0.20      # 20% - TV, box, informatique
        }
        
        for poste, ratio in ratios_reste.items():
            decomposition[poste] = conso_restante * ratio
    
    # Logging final
    total_decompose = sum(decomposition.values())
    logger.info(f"✅ Décomposition totale : {total_decompose:.0f} kWh/an (cible: {profil.consommation_annuelle_kwh:.0f})")
    
    return decomposition


def get_decomposition_summary(decomposition):
    """
    Génère un résumé textuel de la décomposition.
    
    Args:
        decomposition (dict): Résultat de decompose_consumption()
        
    Returns:
        str: Résumé formaté
    """
    total = sum(decomposition.values())
    
    lines = ["📊 Décomposition de la consommation :"]
    for poste, valeur in decomposition.items():
        if valeur > 0:
            pct = (valeur / total * 100) if total > 0 else 0
            poste_label = poste.replace('_', ' ').title()
            lines.append(f"  • {poste_label} : {valeur:.0f} kWh/an ({pct:.1f}%)")
    
    lines.append(f"  TOTAL : {total:.0f} kWh/an")
    
    return "\n".join(lines)
