from celery import shared_task
from django.utils import timezone
import logging
import numpy as np

from frontend.models import Simulation, Resultat
from weather.services.pvgis import get_pvgis_weather_data
from solar_calc.services.consumption_profiles import ConsumptionProfiles
from solar_calc.consumption_decomposer import decompose_consumption, get_decomposition_summary
from solar_calc.hourly_pattern_generator import generate_personalized_hourly_profile


logger = logging.getLogger(__name__)


# ==============================================================================
# TARIFS & CONSTANTES FINANCIÈRES (CRE Q1 2026)
# ==============================================================================

TARIF_ACHAT_KWH = 0.1940  # €/kWh TTC - Tarif réglementé Base EDF


# ==============================================================================
# COÛT INSTALLATION (grille dégressive + surcoûts)
# ==============================================================================

def get_cout_installation_kwc(puissance_kwc):
    """Coût par kWc selon la puissance (grille dégressive, prix marché France 2025-2026)."""
    if puissance_kwc <= 3:
        return 2200
    elif puissance_kwc <= 6:
        return 1900
    elif puissance_kwc <= 9:
        return 1700
    elif puissance_kwc <= 12:
        return 1500
    elif puissance_kwc <= 36:
        return 1400
    else:
        return 1300


def get_surcout_onduleur(type_onduleur):
    """Surcoût par kWc selon le type d'onduleur (base = string inclus)."""
    return {'string': 0, 'optimiseurs': 100, 'micro': 200}.get(type_onduleur, 0)


def get_surcout_toiture(type_toiture):
    """Surcoût par kWc selon le type de couverture (base = tuiles)."""
    return {'tuiles': 0, 'ardoise': 80, 'zinc': 60, 'tole': -80, 'beton': 150}.get(type_toiture, 0)


def calculer_cout_installation(puissance_kwc, type_onduleur='string', type_toiture='tuiles'):
    """
    Calcule le coût total estimé de l'installation.

    Returns:
        dict: cout_kwc, cout_total, detail des composantes
    """
    cout_base = get_cout_installation_kwc(puissance_kwc)
    surcout_ond = get_surcout_onduleur(type_onduleur)
    surcout_toit = get_surcout_toiture(type_toiture)

    cout_kwc = cout_base + surcout_ond + surcout_toit
    cout_total = cout_kwc * puissance_kwc

    return {
        'cout_kwc': cout_kwc,
        'cout_total': round(cout_total, 0),
        'detail': {
            'base_kwc': cout_base,
            'surcout_onduleur': surcout_ond,
            'surcout_toiture': surcout_toit,
        }
    }


def get_tarif_injection(puissance_kwc):
    """Tarif injection surplus EDF OA selon puissance (Arrêté S21 - T1 2026)."""
    if puissance_kwc <= 9:
        return 0.04
    elif puissance_kwc <= 100:
        return 0.0617
    return 0.0536


def get_tarif_vente_totale(puissance_kwc):
    """
    Tarif de rachat en vente totale EDF OA (CRE Q1 2026).
    Minimum 9 kWc pour être éligible.
    
    Returns:
        float: Tarif en €/kWh, ou 0 si non éligible
    """
    if puissance_kwc < 9:
        return 0  # Non éligible en vente totale
    elif puissance_kwc <= 36:
        return 0.0911
    elif puissance_kwc <= 100:
        return 0.0792
    return 0


def get_prime_autoconsommation(puissance_kwc):
    """
    Prime à l'autoconsommation selon puissance (CRE Q1 2026).
    Source : Open Data CRE, arrêté tarifaire en vigueur.
    
    ⚠️ CORRIGÉ : anciennes valeurs 370/280/200/100 remplacées
    par les tarifs actuels 80/80/140/70 €/kWc.
    """
    if puissance_kwc <= 3:
        return 80 * puissance_kwc     # Pa : 0.08 €/Wc
    elif puissance_kwc <= 9:
        return 80 * puissance_kwc     # Pa : 0.08 €/Wc
    elif puissance_kwc <= 36:
        return 140 * puissance_kwc    # Pb : 0.14 €/Wc
    elif puissance_kwc <= 100:
        return 70 * puissance_kwc     # Pb : 0.07 €/Wc
    return 0


# ==============================================================================
# OPTIMISEUR DE CONFIGURATION
# ==============================================================================

def optimize_power(
    production_1kwc,
    consommation_horaire,
    consommation_annuelle,
    objectif='rentabilite',
    min_power=0.5,
    max_power=12.0,
    step=0.5,
    type_onduleur='string',
    type_toiture='tuiles',
):
    """
    Optimise la puissance en testant plusieurs configurations
    avec le vrai profil horaire heure par heure.
    
    Args:
        production_1kwc: Production horaire pour 1 kWc (8760 valeurs)
        consommation_horaire: Consommation horaire (8760 valeurs)
        consommation_annuelle: Consommation annuelle totale (kWh)
        objectif: 'rentabilite', 'autonomie', 'equilibre', 'revente'
        min_power/max_power: Plage de puissances à tester (kWc)
        step: Pas de test (kWc)
    
    Returns:
        dict avec puissance_optimale, all_configs, best_config
    """
    prod_1kwc = production_1kwc.values if hasattr(production_1kwc, 'values') else production_1kwc
    
    # ── Ajustement plage pour vente totale (min 9 kWc) ──
    if objectif == 'revente':
        min_power = max(min_power, 9.0)
        # max_power déjà calculé depuis la surface dans la tâche principale
        logger.info(f"💰 Mode VENTE TOTALE — plage ajustée: {min_power} → {max_power} kWc")
    
    all_configs = []
    best_score = -float('inf')
    best_config = None
    
    puissances = np.arange(min_power, max_power + step / 2, step)
    
    logger.info(f"\n{'='*80}")
    logger.info(f"🔍 OPTIMISATION MULTI-PUISSANCE ({objectif.upper()})")
    logger.info(f"   Plage: {min_power} → {max_power} kWc (pas {step})")
    logger.info(f"   {len(puissances)} configurations à tester")
    logger.info(f"{'='*80}")
    
    for p_test in puissances:
        p_test = round(p_test, 1)
        
        # Production horaire pour cette puissance
        prod_horaire = prod_1kwc * p_test
        prod_annuelle = float(prod_horaire.sum())
        
        # Investissement
        cout_detail_opt = calculer_cout_installation(p_test, type_onduleur, type_toiture)
        cout_brut = cout_detail_opt['cout_total']
        
        if objectif == 'revente':
            # ─── VENTE TOTALE : 100% injection, pas d'autoconsommation ───
            autoconso_kwh = 0.0
            injection_kwh = prod_annuelle
            autoconso_ratio = 0.0
            autoprod_ratio = 0.0
            
            tarif_vt = get_tarif_vente_totale(p_test)
            revenu_vente = prod_annuelle * tarif_vt
            
            # Pas de prime en vente totale
            prime = 0
            cout_net = cout_brut
            
            # L'économie = revenu de la vente (pas d'économie sur la facture)
            economie_annuelle = revenu_vente
            
            roi_annees = cout_net / economie_annuelle if economie_annuelle > 0 else 999
            eco_25ans = economie_annuelle * 25 - cout_net  # 25 ans mais contrat = 20 ans
            
            # Score vente totale : maximiser le bénéfice net sur 20 ans
            revenu_20ans = revenu_vente * 20
            benefice_20ans = revenu_20ans - cout_net
            score = benefice_20ans / 1000  # Normaliser
            
            config = {
                'puissance_kwc': p_test,
                'production_annuelle': round(prod_annuelle, 0),
                'autoconso_kwh': 0,
                'autoconso_ratio': 0,
                'autoprod_ratio': 0,
                'injection_kwh': round(injection_kwh, 0),
                'economie_annuelle': round(economie_annuelle, 0),
                'cout_brut': round(cout_brut, 0),
                'prime': 0,
                'cout_net': round(cout_net, 0),
                'roi_annees': round(roi_annees, 1),
                'eco_25ans': round(eco_25ans, 0),
                'score': round(score, 4),
                # Champs spécifiques vente totale
                'tarif_vente_totale': tarif_vt,
                'revenu_vente_annuel': round(revenu_vente, 0),
                'revenu_20ans': round(revenu_20ans, 0),
                'benefice_20ans': round(benefice_20ans, 0),
            }
            
        else:
            # ─── AUTOCONSOMMATION : calcul classique ───
            autoconso_kwh = float(np.minimum(prod_horaire, consommation_horaire).sum())
            injection_kwh = prod_annuelle - autoconso_kwh
            
            autoconso_ratio = (autoconso_kwh / prod_annuelle * 100) if prod_annuelle > 0 else 0
            autoprod_ratio = (autoconso_kwh / consommation_annuelle * 100) if consommation_annuelle > 0 else 0
            
            tarif_inj = get_tarif_injection(p_test)
            economie_annuelle = autoconso_kwh * TARIF_ACHAT_KWH + injection_kwh * tarif_inj
            
            prime = get_prime_autoconsommation(p_test)
            cout_net = cout_brut - prime
            
            roi_annees = cout_net / economie_annuelle if economie_annuelle > 0 else 999
            eco_25ans = economie_annuelle * 25 - cout_net
            
            # ===== SCORING SELON OBJECTIF =====
            if objectif == 'rentabilite':
                score = 1.0 / roi_annees if roi_annees > 0 else 0
                
            elif objectif == 'autonomie':
                score = autoprod_ratio
                if autoconso_ratio < 25:
                    score *= 0.8
                    
            elif objectif == 'equilibre':
                score_roi = max(0, (15 - roi_annees)) / 15
                score_autoprod = min(autoprod_ratio / 50, 1.0)
                score_autoconso = min(autoconso_ratio / 60, 1.0)
                score = score_roi * 0.4 + score_autoprod * 0.3 + score_autoconso * 0.3
            else:
                score = 1.0 / roi_annees if roi_annees > 0 else 0
            
            config = {
                'puissance_kwc': p_test,
                'production_annuelle': round(prod_annuelle, 0),
                'autoconso_kwh': round(autoconso_kwh, 0),
                'autoconso_ratio': round(autoconso_ratio, 1),
                'autoprod_ratio': round(autoprod_ratio, 1),
                'injection_kwh': round(injection_kwh, 0),
                'economie_annuelle': round(economie_annuelle, 0),
                'cout_brut': round(cout_brut, 0),
                'prime': round(prime, 0),
                'cout_net': round(cout_net, 0),
                'roi_annees': round(roi_annees, 1),
                'eco_25ans': round(eco_25ans, 0),
                'score': round(score, 4),
            }
        
        all_configs.append(config)
        
        if score > best_score:
            best_score = score
            best_config = config
    
    # ── Logs tableau récapitulatif ──
    if objectif == 'revente':
        logger.info(f"\n{'─'*100}")
        logger.info(
            f"{'kWc':>5} │ {'Prod kWh':>9} │ {'Tarif €':>8} │ "
            f"{'Revenu/an':>10} │ {'Coût':>8} │ "
            f"{'ROI ans':>8} │ {'Bénéf 20a':>10} │ {'Score':>7}"
        )
        logger.info(f"{'─'*100}")
        
        for c in all_configs:
            marker = " ◀ OPTIMAL" if c['puissance_kwc'] == best_config['puissance_kwc'] else ""
            logger.info(
                f"{c['puissance_kwc']:>5.1f} │ {c['production_annuelle']:>9.0f} │ "
                f"{c.get('tarif_vente_totale', 0):>7.4f}€ │ "
                f"{c.get('revenu_vente_annuel', 0):>9.0f}€ │ {c['cout_net']:>7.0f}€ │ "
                f"{c['roi_annees']:>7.1f} │ {c.get('benefice_20ans', 0):>9.0f}€ │ "
                f"{c['score']:>7.4f}{marker}"
            )
    else:
        logger.info(f"\n{'─'*105}")
        logger.info(
            f"{'kWc':>5} │ {'Prod kWh':>9} │ {'AutoC kWh':>10} │ "
            f"{'AutoC %':>8} │ {'AutoP %':>8} │ {'Éco €/an':>9} │ "
            f"{'ROI ans':>8} │ {'Score':>7}"
        )
        logger.info(f"{'─'*105}")
        
        for c in all_configs:
            marker = " ◀ OPTIMAL" if c['puissance_kwc'] == best_config['puissance_kwc'] else ""
            logger.info(
                f"{c['puissance_kwc']:>5.1f} │ {c['production_annuelle']:>9.0f} │ "
                f"{c['autoconso_kwh']:>10.0f} │ {c['autoconso_ratio']:>7.1f}% │ "
                f"{c['autoprod_ratio']:>7.1f}% │ {c['economie_annuelle']:>8.0f}€ │ "
                f"{c['roi_annees']:>7.1f} │ {c['score']:>7.4f}{marker}"
            )
    
    logger.info(f"{'─'*105}")
    logger.info(f"✅ PUISSANCE OPTIMALE ({objectif}): {best_config['puissance_kwc']} kWc")
    logger.info(f"   → Production: {best_config['production_annuelle']:.0f} kWh/an")
    if objectif == 'revente':
        logger.info(f"   → Revenu vente: {best_config.get('revenu_vente_annuel', 0):.0f} €/an")
        logger.info(f"   → Bénéfice 20 ans: {best_config.get('benefice_20ans', 0):.0f} €")
    else:
        logger.info(f"   → Autoconsommation: {best_config['autoconso_ratio']:.1f}%")
        logger.info(f"   → Autoproduction: {best_config['autoprod_ratio']:.1f}%")
    logger.info(f"   → ROI: {best_config['roi_annees']:.1f} ans")
    logger.info(f"   → Économies: {best_config['economie_annuelle']:.0f} €/an")
    logger.info(f"{'='*80}\n")
    
    return {
        'puissance_optimale': best_config['puissance_kwc'],
        'all_configs': all_configs,
        'best_config': best_config,
    }


# ==============================================================================
# TÂCHE PRINCIPALE DE SIMULATION
# ==============================================================================

@shared_task(bind=True)
def run_simulation_task(self, simulation_id):
    """Exécuter la simulation avec optimisation multi-puissance."""
    
    try:
        simulation = Simulation.objects.get(id=simulation_id)
        simulation.status = 'running'
        simulation.started_at = timezone.now()
        simulation.save()
        
        installation = simulation.installation
        
        # ================================================================
        # ÉTAPE 1: Données météo (20%)
        # ================================================================
        self.update_state(
            state='PROGRESS',
            meta={'percentage': 20, 'message': '📡 Récupération données météo...'}
        )
        
        weather_df, metadata = get_pvgis_weather_data(
            latitude=installation.latitude,
            longitude=installation.longitude,
            use_cache=True
        )
        
        # ================================================================
        # ÉTAPE 2: Production de base pour 1 kWc (40%)
        # ================================================================
        self.update_state(
            state='PROGRESS',
            meta={'percentage': 40, 'message': '☀️ Calcul production solaire...'}
        )
        
        # Performance Ratio selon type d'onduleur
        type_onduleur = getattr(installation, 'type_onduleur', 'string') or 'string'
        PR_PAR_ONDULEUR = {'string': 0.85, 'micro': 0.84, 'optimiseurs': 0.86}
        performance_ratio = PR_PAR_ONDULEUR.get(type_onduleur, 0.85)
        logger.info(f"🔌 Onduleur: {type_onduleur} → PR = {performance_ratio}")
        
        # Production pour 1 kWc
        production_1kwc = (weather_df['ghi'] / 1000) * performance_ratio
        
        # Correction température
        if 'temperature' in weather_df.columns:
            temp_factor = 1 - 0.004 * (weather_df['temperature'] - 25)
            temp_factor = temp_factor.clip(lower=0.7, upper=1.1)
            production_1kwc *= temp_factor
        
        # Correction ombrage
        facteur_ombrage = getattr(installation, 'facteur_ombrage', 0) or 0
        if facteur_ombrage > 0:
            OMBRAGE_EFFECTIF = {'string': 1.0, 'micro': 0.5, 'optimiseurs': 0.5}
            coeff = OMBRAGE_EFFECTIF.get(type_onduleur, 1.0)
            perte = (facteur_ombrage / 100.0) * coeff
            production_1kwc *= (1 - perte)
            logger.info(f"🌳 Ombrage: {facteur_ombrage}% × {coeff} = -{perte*100:.1f}%")
        
        logger.info(f"☀️ Production 1 kWc: {float(production_1kwc.sum()):.0f} kWh/an")
        
        # ================================================================
        # ÉTAPE 3: Profils de consommation (60%)
        # ================================================================
        self.update_state(
            state='PROGRESS',
            meta={'percentage': 60, 'message': '⚡ Génération profil consommation...'}
        )
        
        if not hasattr(installation, 'consumption_profile') or not installation.consumption_profile:
            raise ValueError(
                f"❌ Aucun profil de consommation lié à l'installation {installation.id}."
            )

        profil = installation.consumption_profile
        logger.info(f"✅ Profil: '{profil.nom}' — {profil.consommation_annuelle_kwh:.0f} kWh/an")

        decomposition = decompose_consumption(profil)
        logger.info("\n" + get_decomposition_summary(decomposition))

        consommation_actuel = generate_personalized_hourly_profile(
            profil=profil, decomposition=decomposition, optimized=False
        )
        consommation_optimise = generate_personalized_hourly_profile(
            profil=profil, decomposition=decomposition, optimized=True
        )

        consommation_horaire = consommation_actuel
        consommation_annuelle = profil.consommation_annuelle_kwh
        
        # ================================================================
        # ÉTAPE 4: OPTIMISATION MULTI-PUISSANCE (80%)
        # ================================================================
        self.update_state(
            state='PROGRESS',
            meta={'percentage': 80, 'message': '🔍 Optimisation puissance...'}
        )
        
        objectif = getattr(installation, 'objectif', 'rentabilite') or 'rentabilite'
        puissance_utilisateur = installation.puissance_kw
        type_onduleur = getattr(installation, 'type_onduleur', 'string') or 'string'
        type_toiture = getattr(installation, 'type_toiture', 'tuiles') or 'tuiles'
        cout_personnalise = getattr(installation, 'cout_installation_personnalise', None)

        # Calcul max_power selon surface disponible
        surface_toiture_m2 = getattr(installation, 'surface_toiture_m2', None)
        puissance_utilisateur_float = float(puissance_utilisateur) if puissance_utilisateur else 12.0
        if surface_toiture_m2 and float(surface_toiture_m2) > 0:
            max_power_calc = float(surface_toiture_m2) / 6.5
            max_power_calc = min(max_power_calc, 500.0)
            max_power_calc = round(max_power_calc * 2) / 2
            # Garantir que l'optimiseur explore au moins jusqu'à la puissance utilisateur
            max_power_calc = max(max_power_calc, puissance_utilisateur_float)
        else:
            max_power_calc = puissance_utilisateur_float

        if objectif == 'revente':
            max_power_calc = max(max_power_calc, 9.0)

        logger.info(f"📐 Surface toiture: {surface_toiture_m2} m² → max puissance: {max_power_calc} kWc")

        optim = optimize_power(
            production_1kwc=production_1kwc,
            consommation_horaire=consommation_actuel,
            consommation_annuelle=consommation_annuelle,
            objectif=objectif,
            min_power=0.5,
            max_power=max_power_calc,
            step=0.5,
            type_onduleur=type_onduleur,
            type_toiture=type_toiture,
        )
        
        puissance_kwc = optim['puissance_optimale']
        best = optim['best_config']
        logger.info(
            f"📊 Utilisateur: {puissance_utilisateur} kWc → "
            f"Optimal: {puissance_kwc} kWc ({objectif})"
        )

        # La puissance affichée en étape 5 est une estimation AJAX (sans profil horaire).
        # On ne l'utilise que si l'utilisateur a coché "Personnaliser" (toggle-perso),
        puissance_personnalisee = getattr(installation, 'puissance_personnalisee', False)
        if puissance_utilisateur and puissance_personnalisee:
            puissance_kwc = float(puissance_utilisateur)
            logger.info(f"✏️ Puissance PERSONNALISÉE par l'utilisateur : {puissance_kwc} kWc")
        elif puissance_utilisateur and float(puissance_utilisateur) > 0:
            # Toujours respecter la puissance calculée par l'AJAX (déjà optimisée selon l'objectif)
            puissance_kwc = float(puissance_utilisateur)
            logger.info(f"✅ Puissance AJAX retenue : {puissance_kwc} kWc (optimiseur suggérait : {optim['puissance_optimale']} kWc)")
        else:
            logger.info(f"✅ Puissance OPTIMISEUR retenue : {puissance_kwc} kWc")
        
        # ================================================================
        # SIMULATION COMPLÈTE AVEC PUISSANCE OPTIMALE
        # ================================================================
        
        production_horaire = production_1kwc * puissance_kwc
        production_annuelle = float(production_horaire.sum())
        
        is_vente_totale = (objectif == 'revente')
        
        if is_vente_totale:
            # ══════════════════════════════════════════════════════════
            # MODE VENTE TOTALE — pas d'autoconsommation
            # ══════════════════════════════════════════════════════════
            
            autoconso_actuel_kwh = 0.0
            autoconso_actuel_ratio = 0.0
            injection_actuel_kwh = production_annuelle
            autoproduction_actuel_ratio = 0.0
            
            autoconso_optimise_kwh = 0.0
            autoconso_optimise_ratio = 0.0
            injection_optimise_kwh = production_annuelle
            autoproduction_optimise_ratio = 0.0
            
            # Revenus vente totale
            tarif_vt = get_tarif_vente_totale(puissance_kwc)
            revenu_vente_annuel = production_annuelle * tarif_vt
            
            economie_totale_actuel = revenu_vente_annuel
            economie_totale_optimise = revenu_vente_annuel  # Pas de différence actuel/optimisé
            
            # Pas de gains optimisation (pas d'autoconso à optimiser)
            gain_autoconso_kwh = 0.0
            gain_autoconso_pct = 0.0
            gain_economie_annuel = 0.0
            gain_economie_25ans = 0.0
            
            # Investissement (pas de prime en vente totale)
            if cout_personnalise and cout_personnalise > 0:
                cout_brut = cout_personnalise
                logger.info(f"💶 Coût PERSONNALISÉ (devis) : {cout_brut:.0f} €")
            else:
                cout_detail = calculer_cout_installation(puissance_kwc, type_onduleur, type_toiture)
                cout_brut = cout_detail['cout_total']
                logger.info(
                    f"💶 Coût ESTIMÉ : {cout_detail['cout_kwc']} €/kWc × {puissance_kwc} kWc = {cout_brut:.0f} € "
                    f"(base {cout_detail['detail']['base_kwc']} + ond {cout_detail['detail']['surcout_onduleur']} "
                    f"+ toit {cout_detail['detail']['surcout_toiture']})"
                )
            prime = 0
            cout_net = cout_brut
            
            # ROI et bénéfice
            roi_annees = cout_net / revenu_vente_annuel if revenu_vente_annuel > 0 else 999
            economie_25ans = revenu_vente_annuel * 25 - cout_net
            
            # Infos supplémentaires pour les logs
            cout_elec_annuel = consommation_annuelle * TARIF_ACHAT_KWH
            bilan_net_annuel = revenu_vente_annuel - cout_elec_annuel
            
            logger.info(f"\n{'='*80}")
            logger.info(f"💰 RÉSULTATS VENTE TOTALE — {puissance_kwc} kWc")
            logger.info(f"{'='*80}")
            logger.info(f"PRODUCTION   : {production_annuelle:.0f} kWh/an")
            logger.info(f"TARIF RACHAT : {tarif_vt:.4f} €/kWh (garanti 20 ans)")
            logger.info(f"REVENU VENTE : {revenu_vente_annuel:.0f} €/an")
            logger.info(f"FACTURE ÉLEC : {cout_elec_annuel:.0f} €/an (inchangée)")
            logger.info(f"BILAN NET    : {bilan_net_annuel:+.0f} €/an")
            logger.info(f"INVEST       : {cout_brut:.0f}€ (pas de prime) | ROI {roi_annees:.1f} ans")
            logger.info(f"REVENU 20 ANS: {revenu_vente_annuel * 20:.0f} €")
            logger.info(f"BÉNÉF 25 ANS : {economie_25ans:.0f} €")
            logger.info(f"{'='*80}\n")
            
        else:
            # ══════════════════════════════════════════════════════════
            # MODE AUTOCONSOMMATION — calcul classique
            # ══════════════════════════════════════════════════════════
            
            # Scénario ACTUEL
            ac_actuel = np.minimum(production_horaire, consommation_actuel)
            autoconso_actuel_kwh = float(ac_actuel.sum())
            autoconso_actuel_ratio = (autoconso_actuel_kwh / production_annuelle * 100) if production_annuelle > 0 else 0
            injection_actuel_kwh = production_annuelle - autoconso_actuel_kwh
            autoproduction_actuel_ratio = (autoconso_actuel_kwh / consommation_annuelle * 100) if consommation_annuelle > 0 else 0

            # Scénario OPTIMISÉ
            ac_optimise = np.minimum(production_horaire, consommation_optimise)
            autoconso_optimise_kwh = float(ac_optimise.sum())
            autoconso_optimise_ratio = (autoconso_optimise_kwh / production_annuelle * 100) if production_annuelle > 0 else 0
            injection_optimise_kwh = production_annuelle - autoconso_optimise_kwh
            autoproduction_optimise_ratio = (autoconso_optimise_kwh / consommation_annuelle * 100) if consommation_annuelle > 0 else 0

            # Calculs financiers
            tarif_injection = get_tarif_injection(puissance_kwc)

            economie_totale_actuel = (
                autoconso_actuel_kwh * TARIF_ACHAT_KWH +
                injection_actuel_kwh * tarif_injection
            )
            economie_totale_optimise = (
                autoconso_optimise_kwh * TARIF_ACHAT_KWH +
                injection_optimise_kwh * tarif_injection
            )

            # Gains optimisation
            gain_autoconso_kwh = autoconso_optimise_kwh - autoconso_actuel_kwh
            gain_autoconso_pct = autoconso_optimise_ratio - autoconso_actuel_ratio
            gain_economie_annuel = economie_totale_optimise - economie_totale_actuel
            gain_economie_25ans = gain_economie_annuel * 25

            # Investissement
            if cout_personnalise and cout_personnalise > 0:
                cout_brut = cout_personnalise
                logger.info(f"💶 Coût PERSONNALISÉ (devis) : {cout_brut:.0f} €")
            else:
                cout_detail = calculer_cout_installation(puissance_kwc, type_onduleur, type_toiture)
                cout_brut = cout_detail['cout_total']
                logger.info(
                    f"💶 Coût ESTIMÉ : {cout_detail['cout_kwc']} €/kWc × {puissance_kwc} kWc = {cout_brut:.0f} € "
                    f"(base {cout_detail['detail']['base_kwc']} + ond {cout_detail['detail']['surcout_onduleur']} "
                    f"+ toit {cout_detail['detail']['surcout_toiture']})"
                )
            prime = get_prime_autoconsommation(puissance_kwc)
            cout_net = cout_brut - prime
            economie_25ans = economie_totale_actuel * 25 - cout_net
            roi_annees = cout_net / economie_totale_actuel if economie_totale_actuel > 0 else 999

            logger.info(f"\n{'='*80}")
            logger.info(f"📊 RÉSULTATS — {puissance_kwc} kWc ({objectif})")
            logger.info(f"{'='*80}")
            logger.info(f"ACTUEL   : autoconso {autoconso_actuel_ratio:.1f}% | autoprod {autoproduction_actuel_ratio:.1f}% | {economie_totale_actuel:.0f} €/an")
            logger.info(f"OPTIMISÉ : autoconso {autoconso_optimise_ratio:.1f}% | autoprod {autoproduction_optimise_ratio:.1f}% | {economie_totale_optimise:.0f} €/an")
            logger.info(f"INVEST   : {cout_brut:.0f}€ brut - {prime:.0f}€ prime = {cout_net:.0f}€ net | ROI {roi_annees:.1f} ans | Bénéf 25ans {economie_25ans:.0f}€")
            logger.info(f"{'='*80}\n")

        # ================================================================
        # PROFILS MOYENS POUR GRAPHIQUES
        # ================================================================
        
        prod_vals = production_horaire.values if hasattr(production_horaire, 'values') else production_horaire
        prod_hourly_avg = [round(float(prod_vals[h::24].mean()), 3) for h in range(24)]
        conso_hourly_avg = [round(float(consommation_horaire[h::24].mean()), 3) for h in range(24)]
        
        jours_par_mois = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        prod_monthly, conso_monthly = [], []
        idx = 0
        for jours in jours_par_mois:
            h = jours * 24
            prod_monthly.append(round(float(prod_vals[idx:idx+h].sum()), 1))
            conso_monthly.append(round(float(consommation_horaire[idx:idx+h].sum()), 1))
            idx += h

        # ================================================================
        # ÉTAPE 5: Sauvegarde (100%)
        # ================================================================
        self.update_state(
            state='PROGRESS',
            meta={'percentage': 100, 'message': '💾 Sauvegarde résultats...'}
        )
        print(f">>> OBJECTIF AVANT CRÉATION RESULTAT: {objectif}", flush=True)
        resultat = Resultat.objects.create(
            # Production
            production_annuelle_kwh=production_annuelle,
            production_mensuelle_kwh=prod_monthly,
            production_horaire_kwh=prod_hourly_avg,
            
            # Consommation
            consommation_annuelle_kwh=consommation_annuelle,
            consommation_mensuelle_kwh=conso_monthly,
            consommation_horaire_kwh=conso_hourly_avg,
            
            # Scénario actuel
            autoconsommation_kwh_actuel=autoconso_actuel_kwh,
            autoconsommation_ratio_actuel=autoconso_actuel_ratio,
            economie_annuelle_actuel=economie_totale_actuel,
            
            # Scénario optimisé
            autoconsommation_kwh_optimise=autoconso_optimise_kwh,
            autoconsommation_ratio_optimise=autoconso_optimise_ratio,
            economie_annuelle_optimise=economie_totale_optimise,
            
            # Gains
            gain_autoconso_kwh=gain_autoconso_kwh,
            gain_autoconso_pct=gain_autoconso_pct,
            gain_economie_annuel=gain_economie_annuel,
            gain_economie_25ans=gain_economie_25ans,
            
            # Champs compatibilité
            autoconsommation_ratio=autoconso_actuel_ratio,
            taux_autoproduction_pct=autoproduction_actuel_ratio,
            injection_reseau_kwh=injection_actuel_kwh,
            economie_annuelle_euros=economie_totale_actuel,
            roi_25ans_euros=economie_25ans,
            taux_rentabilite_pct=(economie_25ans / cout_net * 100) if cout_net > 0 else 0,
            puissance_recommandee_kwc=puissance_kwc,
            objectif=objectif,
        )

        simulation.resultat = resultat
        simulation.status = 'success'
        simulation.completed_at = timezone.now()
        simulation.save()
        
        logger.info(f"✅ Simulation {simulation_id} terminée — {puissance_kwc} kWc ({objectif})")
        
        return {
            'percentage': 100,
            'message': '✅ Simulation terminée !',
            'resultat_id': str(resultat.id)
        }
        
    except Exception as e:
        logger.error(f"❌ Erreur simulation {simulation_id}: {e}", exc_info=True)
        
        simulation = Simulation.objects.get(id=simulation_id)
        simulation.status = 'failed'
        simulation.error_message = str(e)
        simulation.completed_at = timezone.now()
        simulation.save()
        
        raise