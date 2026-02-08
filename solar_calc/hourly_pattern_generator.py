"""
Générateur de patterns horaires personnalisés.

Génère des profils de consommation horaire (8760h) selon les équipements,
le profil d'occupation, et les optimisations souhaitées.
"""

import numpy as np
import json
import logging

logger = logging.getLogger(__name__)


def generate_personalized_hourly_profile(profil, decomposition, optimized=False):
    """
    Génère un profil horaire personnalisé (8760 heures).
    
    Args:
        profil: ConsumptionProfileModel
        decomposition (dict): Décomposition par poste (de decompose_consumption)
        optimized (bool): Si True, optimise les appareils programmables pour heures solaires
        
    Returns:
        np.array: Profile horaire (8760 valeurs en kWh)
    """
    from solar_calc.consumption_profiles import ConsumptionProfiles
    
    mode = "OPTIMISÉ" if optimized else "ACTUEL"
    logger.info(f"🔧 Génération profil {mode} pour {profil.nom}")
    
    # Pattern de base selon profil d'occupation
    base_pattern = ConsumptionProfiles.generate_yearly_pattern(
        profile_type=profil.profile_type,
        add_randomness=False
    )
    
    # Profil horaire final
    profile_horaire = np.zeros(8760)
    
    # Charger appareils_json
    appareils_data = {}
    if profil.appareils_json:
        try:
            appareils_data = json.loads(profil.appareils_json)
        except Exception as e:
            logger.warning(f"Erreur lecture appareils_json: {e}")
    
    # ========== CHAUFFAGE ==========
    if decomposition['chauffage'] > 0:
        pattern_chauffage = modulate_heating_by_occupation(
            base_pattern,
            profil.profile_type,
            profil.get_effective_dpe()
        )
        pattern_chauffage = pattern_chauffage / pattern_chauffage.sum() * decomposition['chauffage']
        profile_horaire += pattern_chauffage
        logger.info(f"  ├─ Chauffage : {decomposition['chauffage']:.0f} kWh/an")
    
    # ========== ECS ==========
    if decomposition['ecs'] > 0:
        ecs_config = appareils_data.get('ecs', {})
        
        if optimized and profil.type_ecs == 'thermodynamique':
            # ECS optimisé → Heures solaires (12h-15h)
            heure_optimale = ecs_config.get('heure_optimale', 13)
            pattern_ecs = generate_ecs_optimized_pattern(heure_optimale)
            logger.info(f"  ├─ ECS thermodynamique OPTIMISÉ à {heure_optimale}h : {decomposition['ecs']:.0f} kWh/an")
        else:
            # ECS standard → Suit la présence (douches matin/soir)
            pattern_ecs = modulate_ecs_by_occupation(base_pattern, profil.profile_type)
            logger.info(f"  ├─ ECS standard (présence) : {decomposition['ecs']:.0f} kWh/an")
        
        pattern_ecs = pattern_ecs / pattern_ecs.sum() * decomposition['ecs']
        profile_horaire += pattern_ecs
    
    # ========== APPAREILS PROGRAMMABLES ==========
    appareils_config = appareils_data.get('appareils', {})
    
    # Lave-linge
    if 'lave_linge' in appareils_config and appareils_config['lave_linge'].get('present'):
        config = appareils_config['lave_linge']
        heure = config.get('heure_optimale' if optimized else 'heure_habituelle', 20)
        cycles = config.get('cycles_par_semaine', 3)
        pattern_ll = generate_appliance_pattern('lave_linge', heure, cycles)
        profile_horaire += pattern_ll
        logger.info(f"  ├─ Lave-linge à {heure}h ({cycles}×/sem) : {pattern_ll.sum():.0f} kWh/an")
    
    # Lave-vaisselle
    if 'lave_vaisselle' in appareils_config and appareils_config['lave_vaisselle'].get('present'):
        config = appareils_config['lave_vaisselle']
        heure = config.get('heure_optimale' if optimized else 'heure_habituelle', 21)
        cycles = config.get('cycles_par_semaine', 4)
        pattern_lv = generate_appliance_pattern('lave_vaisselle', heure, cycles)
        profile_horaire += pattern_lv
        logger.info(f"  ├─ Lave-vaisselle à {heure}h ({cycles}×/sem) : {pattern_lv.sum():.0f} kWh/an")
    
    # Sèche-linge
    if 'seche_linge' in appareils_config and appareils_config['seche_linge'].get('present'):
        config = appareils_config['seche_linge']
        heure = config.get('heure_optimale' if optimized else 'heure_habituelle', 20)
        cycles = config.get('cycles_par_semaine', 2)
        pattern_sl = generate_appliance_pattern('seche_linge', heure, cycles)
        profile_horaire += pattern_sl
        logger.info(f"  ├─ Sèche-linge à {heure}h ({cycles}×/sem) : {pattern_sl.sum():.0f} kWh/an")
    
    # Véhicule électrique
    if 'vehicule_electrique' in appareils_config and appareils_config['vehicule_electrique'].get('present'):
        config = appareils_config['vehicule_electrique']
        heure = config.get('heure_optimale' if optimized else 'heure_habituelle', 19)
        pattern_ve = generate_ev_charging_pattern(heure, decomposition['vehicule_electrique'])
        profile_horaire += pattern_ve
        logger.info(f"  ├─ Véhicule électrique à {heure}h : {pattern_ve.sum():.0f} kWh/an")
    
    # Piscine
    if 'piscine' in appareils_config and appareils_config['piscine'].get('present'):
        config = appareils_config['piscine']
        heure = config.get('heure_optimale' if optimized else 'heure_habituelle', 10)
        pattern_piscine = generate_pool_pattern(heure, decomposition['piscine'])
        profile_horaire += pattern_piscine
        logger.info(f"  ├─ Piscine à {heure}h : {pattern_piscine.sum():.0f} kWh/an")
    
    # ========== AUTRES USAGES (suivent le profil de base) ==========
    # Cuisson
    if decomposition['cuisson'] > 0:
        pattern_cuisson = base_pattern.copy()
        pattern_cuisson = pattern_cuisson / pattern_cuisson.sum() * decomposition['cuisson']
        profile_horaire += pattern_cuisson
    
    # Électroménager (hors programmables déjà comptés)
    if decomposition['electromenager'] > 0:
        pattern_electro = base_pattern.copy()
        pattern_electro = pattern_electro / pattern_electro.sum() * decomposition['electromenager']
        profile_horaire += pattern_electro
    
    # Éclairage
    if decomposition['eclairage'] > 0:
        pattern_eclairage = generate_lighting_pattern(base_pattern)
        pattern_eclairage = pattern_eclairage / pattern_eclairage.sum() * decomposition['eclairage']
        profile_horaire += pattern_eclairage
    
    # Multimédia
    if decomposition['multimedia'] > 0:
        pattern_multimedia = base_pattern.copy()
        pattern_multimedia = pattern_multimedia / pattern_multimedia.sum() * decomposition['multimedia']
        profile_horaire += pattern_multimedia
    
    total_genere = profile_horaire.sum()
    logger.info(f"✅ Profil {mode} généré : {total_genere:.0f} kWh/an")
    
    return profile_horaire


# ========== FONCTIONS DE GÉNÉRATION DE PATTERNS ==========

def modulate_heating_by_occupation(base_pattern, profile_type, dpe):
    """Génère pattern chauffage selon occupation et DPE."""
    pattern = base_pattern.copy()
    
    # Ajouter saisonnalité (plus en hiver)
    seasonal = np.ones(8760)
    for h in range(8760):
        month = (h // 730) % 12 + 1  # Mois approximatif (1-12)
        if month in [11, 12, 1, 2, 3]:  # Hiver
            seasonal[h] = 2.0
        elif month in [6, 7, 8]:  # Été
            seasonal[h] = 0.3
        else:  # Mi-saison
            seasonal[h] = 1.2
    
    pattern = pattern * seasonal
    
    # Si actif absent : réduire chauffage en journée
    if profile_type == 'actif_absent':
        for h in range(8760):
            hour_of_day = h % 24
            if 9 <= hour_of_day <= 17:  # Journée
                pattern[h] *= 0.3  # Réduit à 30%
    
    return pattern


def modulate_ecs_by_occupation(base_pattern, profile_type):
    """Génère pattern ECS selon occupation (douches matin/soir)."""
    pattern = np.zeros(8760)
    
    for h in range(8760):
        hour_of_day = h % 24
        day_of_week = (h // 24) % 7
        
        if profile_type == 'actif_absent':
            # Douche matin (7h-8h) et soir (19h-20h)
            if hour_of_day in [7, 19]:
                pattern[h] = 1.0
        elif profile_type == 'teletravail':
            # Douche matin + usage cuisine midi
            if hour_of_day in [7, 12, 19]:
                pattern[h] = 0.8
        elif profile_type == 'retraite':
            # Usage étalé dans la journée
            if 7 <= hour_of_day <= 20:
                pattern[h] = 0.5
        elif profile_type == 'famille':
            # Multiple pics (matin, midi week-end, soir)
            if hour_of_day in [7, 8, 19, 20]:
                pattern[h] = 1.0
            if day_of_week in [5, 6] and hour_of_day == 12:  # Week-end midi
                pattern[h] = 0.7
    
    return pattern


def generate_ecs_optimized_pattern(heure_optimale):
    """ECS optimisé : préchauffage aux heures solaires."""
    pattern = np.zeros(8760)
    
    for h in range(8760):
        hour_of_day = h % 24
        
        # Préchauffage autour de l'heure optimale (±2h)
        if heure_optimale - 1 <= hour_of_day <= heure_optimale + 2:
            pattern[h] = 1.0
        # Maintien faible pour usage soir
        elif hour_of_day in [19, 20]:
            pattern[h] = 0.3
    
    return pattern


def generate_appliance_pattern(appareil, heure, cycles_par_semaine):
    """Génère pattern pour un appareil programmable."""
    # Consommation par cycle (kWh)
    conso_par_cycle = {
        'lave_linge': 1.0,
        'lave_vaisselle': 1.2,
        'seche_linge': 3.0,
    }
    
    conso = conso_par_cycle.get(appareil, 1.0)
    duree_cycle = 2  # heures
    
    pattern = np.zeros(8760)
    nb_cycles_an = int(cycles_par_semaine * 52)
    
    # Répartir les cycles sur l'année
    for i in range(nb_cycles_an):
        jour = int(i * 365 / nb_cycles_an)
        heure_debut = jour * 24 + int(heure)
        
        if heure_debut < 8760 - duree_cycle:
            for offset in range(duree_cycle):
                pattern[heure_debut + offset] = conso / duree_cycle
    
    return pattern


def generate_ev_charging_pattern(heure, conso_annuelle):
    """Génère pattern de charge véhicule électrique."""
    pattern = np.zeros(8760)
    duree_charge = 4  # heures
    
    # Charge quotidienne (50% des jours en moyenne)
    nb_charges = 365 // 2
    conso_par_charge = conso_annuelle / nb_charges
    
    for i in range(nb_charges):
        jour = i * 2  # Un jour sur deux
        heure_debut = jour * 24 + int(heure)
        
        if heure_debut < 8760 - duree_charge:
            for offset in range(duree_charge):
                pattern[heure_debut + offset] = conso_par_charge / duree_charge
    
    return pattern


def generate_pool_pattern(heure, conso_annuelle):
    """Génère pattern piscine (filtration quotidienne en saison)."""
    pattern = np.zeros(8760)
    duree_filtration = 8  # heures
    
    # Piscine active mai-septembre (5 mois ≈ 150 jours)
    jours_actifs = 150
    conso_par_jour = conso_annuelle / jours_actifs
    
    for jour in range(120, 270):  # Mai à septembre approximativement
        heure_debut = jour * 24 + int(heure)
        
        if heure_debut < 8760 - duree_filtration:
            for offset in range(duree_filtration):
                pattern[heure_debut + offset] = conso_par_jour / duree_filtration
    
    return pattern


def generate_lighting_pattern(base_pattern):
    """Génère pattern éclairage (actif surtout tôt matin et soir)."""
    pattern = np.zeros(8760)
    
    for h in range(8760):
        hour_of_day = h % 24
        month = (h // 730) % 12 + 1
        
        # Plus d'éclairage en hiver (jours courts)
        winter_factor = 1.5 if month in [11, 12, 1, 2] else 1.0
        
        # Éclairage le soir principalement
        if 6 <= hour_of_day <= 8:  # Matin
            pattern[h] = 0.5 * winter_factor
        elif 18 <= hour_of_day <= 23:  # Soir
            pattern[h] = 1.0 * winter_factor
        elif 0 <= hour_of_day <= 1:  # Nuit
            pattern[h] = 0.3
    
    # Moduler par présence
    pattern = pattern * base_pattern
    
    return pattern
