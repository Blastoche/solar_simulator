from celery import shared_task
from django.utils import timezone
import logging
import numpy as np

from frontend.models import Simulation, Resultat
from weather.services.pvgis import get_pvgis_weather_data
# TODO: Ces imports sont désactivés car les classes n'existent pas encore
# from solar_calc.services import (
#     ConfigurationOptimizer,
#     ObjectifSimulation,
#     ModeSimulation
# )
from solar_calc.services.consumption_profiles import ConsumptionProfiles
from solar_calc.consumption_decomposer import decompose_consumption, get_decomposition_summary
from solar_calc.hourly_pattern_generator import generate_personalized_hourly_profile


logger = logging.getLogger(__name__)


@shared_task(bind=True)
def run_simulation_task(self, simulation_id):
    """Exécuter la simulation avec le nouveau système."""
    
    try:
        simulation = Simulation.objects.get(id=simulation_id)
        simulation.status = 'running'
        simulation.started_at = timezone.now()
        simulation.save()
        
        installation = simulation.installation
        
        # === ÉTAPE 1: Données météo (20%) ===
        self.update_state(
            state='PROGRESS',
            meta={'percentage': 20, 'message': '📡 Récupération données météo...'}
        )
        
        weather_df, metadata = get_pvgis_weather_data(
            latitude=installation.latitude,
            longitude=installation.longitude,
            use_cache=True
        )
        
        # === ÉTAPE 2: Calculer production de base pour 1 kWc (40%) ===
        self.update_state(
            state='PROGRESS',
            meta={'percentage': 40, 'message': '☀️ Calcul production solaire...'}
        )
        
        # Production pour 1 kWc (base pour optimisation)
        production_1kwc = (weather_df['ghi'] / 1000) * 0.85  # GHI + Performance Ratio
        
        # Ajustement température
        if 'temperature' in weather_df.columns:
            temp_factor = 1 - 0.004 * (weather_df['temperature'] - 25)
            temp_factor = temp_factor.clip(lower=0.7, upper=1.1)
            production_1kwc *= temp_factor
        
        # === ÉTAPE 3: Profil de consommation (60%) ===
        self.update_state(
            state='PROGRESS',
            meta={'percentage': 60, 'message': '⚡ Génération profil consommation...'}
        )
        
        # ========== GÉNÉRATION PROFIL HORAIRE PERSONNALISÉ ==========
        
        # 1. VÉRIFICATION OBLIGATOIRE DU PROFIL
        if not hasattr(installation, 'consumption_profile') or not installation.consumption_profile:
            error_msg = (
                f"❌ ERREUR : Aucun profil de consommation lié à l'installation {installation.id}. "
                f"Le profil est obligatoire pour lancer la simulation."
            )
            logger.error(error_msg)
            raise ValueError(error_msg)

        profil = installation.consumption_profile
        logger.info(f"✅ Profil détecté : '{profil.nom}'")
        logger.info(f"   - Consommation : {profil.consommation_annuelle_kwh:.0f} kWh/an")
        logger.info(f"   - DPE : {profil.get_effective_dpe()}")
        logger.info(f"   - Type : {profil.profile_type}")
        logger.info(f"   - Surface : {profil.surface_habitable:.0f} m²")

        # 2. DÉCOMPOSITION PAR POSTE
        decomposition = decompose_consumption(profil)
        logger.info("\n" + get_decomposition_summary(decomposition))

        # 3. GÉNÉRATION PROFIL ACTUEL (horaires habituels)
        logger.info("\n🔧 Génération profil ACTUEL (horaires habituels)...")
        consommation_actuel = generate_personalized_hourly_profile(
            profil=profil,
            decomposition=decomposition,
            optimized=False
        )

        # 4. GÉNÉRATION PROFIL OPTIMISÉ (heures solaires)
        logger.info("\n⚡ Génération profil OPTIMISÉ (heures solaires)...")
        consommation_optimise = generate_personalized_hourly_profile(
            profil=profil,
            decomposition=decomposition,
            optimized=True
        )

        # 5. UTILISER LE PROFIL ACTUEL POUR LES CALCULS (pour compatibilité)
        consommation_horaire = consommation_actuel
        consommation_annuelle = profil.consommation_annuelle_kwh
        
        # === ÉTAPE 4: Optimisation (80%) ===
        self.update_state(
            state='PROGRESS',
            meta={'percentage': 80, 'message': '🔍 Optimisation configuration...'}
        )
        
        # ====================================================================
        # TODO: OPTIMISATION DÉSACTIVÉE TEMPORAIREMENT
        # Les classes ConfigurationOptimizer, ObjectifSimulation et ModeSimulation
        # n'existent pas encore. À implémenter plus tard.
        # ====================================================================
        
        logger.warning("⚠️ Optimisation avancée non disponible - utilisation config par défaut")
        
        # Configuration par défaut (sans optimisation avancée)
        # On utilise directement les paramètres de l'installation
        puissance_kwc = installation.puissance_kw  
        orientation = installation.orientation  
        inclinaison = installation.inclinaison 
        
        # Calculer la production avec la puissance installée
        production_horaire = production_1kwc * puissance_kwc
        production_annuelle = production_horaire.sum()
        
        # ========== CALCULER AUTOCONSOMMATION POUR LES DEUX SCÉNARIOS ==========

        # SCÉNARIO ACTUEL (horaires habituels)
        autoconso_actuel_horaire = np.minimum(production_horaire, consommation_actuel)
        autoconso_actuel_kwh = autoconso_actuel_horaire.sum()
        autoconso_actuel_ratio = (autoconso_actuel_kwh / production_annuelle * 100) if production_annuelle > 0 else 0

        injection_actuel_kwh = production_annuelle - autoconso_actuel_kwh
        autoproduction_actuel_ratio = (autoconso_actuel_kwh / consommation_annuelle * 100) if consommation_annuelle > 0 else 0

        # SCÉNARIO OPTIMISÉ (heures solaires)
        autoconso_optimise_horaire = np.minimum(production_horaire, consommation_optimise)
        autoconso_optimise_kwh = autoconso_optimise_horaire.sum()
        autoconso_optimise_ratio = (autoconso_optimise_kwh / production_annuelle * 100) if production_annuelle > 0 else 0

        injection_optimise_kwh = production_annuelle - autoconso_optimise_kwh
        autoproduction_optimise_ratio = (autoconso_optimise_kwh / consommation_annuelle * 100) if consommation_annuelle > 0 else 0

        # ========== CALCULER LES ÉCONOMIES POUR LES DEUX SCÉNARIOS ==========

        # ========== TARIFS FÉVRIER 2026 ==========

        # Tarif achat réseau 
        TARIF_ACHAT_KWH = 0.1940  # €/kWh TTC - Tarif réglementé Base EDF

        # Tarif injection EDF OA selon puissance installation (Arrêté S21 - T1 2026)
        puissance_kwc = config_optimale.puissance_kwc  # ou installation.puissance_kw

        if puissance_kwc <= 9:
            TARIF_INJECTION_KWH = 0.04    # €/kWh - Résidentiel ≤9 kWc
            logger.info(f"💰 Tarif injection : 0,04 €/kWh (≤9 kWc)")
        elif puissance_kwc <= 36:
            TARIF_INJECTION_KWH = 0.0617  # €/kWh - 9-36 kWc
            logger.info(f"💰 Tarif injection : 0,0617 €/kWh (9-36 kWc)")
        elif puissance_kwc <= 100:
            TARIF_INJECTION_KWH = 0.0617  # €/kWh - 36-100 kWc
            logger.info(f"💰 Tarif injection : 0,0617 €/kWh (36-100 kWc)")
        else:
            # > 100 kWc : Appel d'offres (pas couvert par ce simulateur)
            TARIF_INJECTION_KWH = 0.0536  # €/kWh - Estimation (à vérifier)
            logger.warning(f"⚠️ Installation >100 kWc : tarif injection estimatif (AOS requis)")

        # Économies ACTUEL
        economie_autoconso_actuel = autoconso_actuel_kwh * TARIF_ACHAT_KWH
        revenu_injection_actuel = injection_actuel_kwh * TARIF_INJECTION_KWH
        economie_totale_actuel = economie_autoconso_actuel + revenu_injection_actuel

        # Économies OPTIMISÉ
        economie_autoconso_optimise = autoconso_optimise_kwh * TARIF_ACHAT_KWH
        revenu_injection_optimise = injection_optimise_kwh * TARIF_INJECTION_KWH
        economie_totale_optimise = economie_autoconso_optimise + revenu_injection_optimise

        # ========== CALCULER LES GAINS ==========

        gain_autoconso_kwh = autoconso_optimise_kwh - autoconso_actuel_kwh
        gain_autoconso_pct = autoconso_optimise_ratio - autoconso_actuel_ratio
        gain_economie_annuel = economie_totale_optimise - economie_totale_actuel
        gain_economie_25ans = gain_economie_annuel * 25

        # ========== LOGS RÉSULTATS COMPARATIFS ==========

        logger.info("\n" + "="*80)
        logger.info("📊 RÉSULTATS COMPARATIFS")
        logger.info("="*80)
        logger.info(f"SCÉNARIO ACTUEL (horaires habituels) :")
        logger.info(f"  • Autoconsommation : {autoconso_actuel_kwh:.0f} kWh ({autoconso_actuel_ratio:.1f}%)")
        logger.info(f"  • Injection réseau : {injection_actuel_kwh:.0f} kWh")
        logger.info(f"  • Économies totales : {economie_totale_actuel:.0f} €/an")
        logger.info(f"")
        logger.info(f"⚡ SCÉNARIO OPTIMISÉ (heures solaires) :")
        logger.info(f"  • Autoconsommation : {autoconso_optimise_kwh:.0f} kWh ({autoconso_optimise_ratio:.1f}%)")
        logger.info(f"  • Injection réseau : {injection_optimise_kwh:.0f} kWh")
        logger.info(f"  • Économies totales : {economie_totale_optimise:.0f} €/an")
        logger.info(f"")
        logger.info(f"💰 GAIN POTENTIEL AVEC OPTIMISATION :")
        logger.info(f"  • +{gain_autoconso_kwh:.0f} kWh autoconsommés (+{gain_autoconso_pct:.1f}%)")
        logger.info(f"  • +{gain_economie_annuel:.0f} €/an")
        logger.info(f"  • +{gain_economie_25ans:.0f} € sur 25 ans")
        logger.info("="*80 + "\n")

        # Compatibilité avec le reste du code (variables utilisées plus bas)
        autoconso_kwh = autoconso_actuel_kwh
        autoconso_ratio = autoconso_actuel_ratio
        injection_kwh = injection_actuel_kwh
        autoproduction_kwh = autoconso_actuel_kwh
        autoproduction_ratio = autoproduction_actuel_ratio
        economie_annuelle = economie_totale_actuel
        economie_25ans = economie_totale_actuel * 25
        
        # Économies (calcul simple)
        prix_kwh_autoconso = 0.2516  # Prix évité
        prix_kwh_injection = 0.04    # Prix revente
        economie_annuelle = (autoconso_kwh * prix_kwh_autoconso) + (injection_kwh * prix_kwh_injection)
        economie_25ans = economie_annuelle * 25
        
        # Créer un objet config_optimale compatible avec le reste du code
        class SimpleConfig:
            def __init__(self):
                self.puissance_kwc = puissance_kwc
                self.economie_annuelle_euros = economie_annuelle
                self.economie_25ans_euros = economie_25ans
                # Résultats
                self.results = type('obj', (object,), {
                    'production_annuelle_kwh': production_annuelle,
                    'production_mensuelle_kwh': production_horaire.values.reshape(365, 24).sum(axis=1).tolist()[:12],
                    'consommation_annuelle_kwh': consommation_annuelle,
                    'consommation_mensuelle_kwh': consommation_horaire.reshape(365, 24).sum(axis=1).tolist()[:12],
                    'taux_autoconsommation_pct': autoconso_ratio,
                    'taux_autoproduction_pct': autoproduction_ratio,
                    'injection_reseau_kwh': injection_kwh,
                })()
        
        config_optimale = SimpleConfig()
        objectif_str = getattr(installation, 'objectif', 'rentabilite')
        
        # === ÉTAPE 5: Sauvegarde (100%) ===
        self.update_state(
            state='PROGRESS',
            meta={'percentage': 100, 'message': '💾 Sauvegarde résultats...'}
        )
        
        results = config_optimale.results
        
        resultat = Resultat.objects.create(
            # Production
            production_annuelle_kwh=results.production_annuelle_kwh,
            production_mensuelle_kwh=results.production_mensuelle_kwh,
            production_horaire_kwh=[],
            
            # Consommation
            consommation_annuelle_kwh=results.consommation_annuelle_kwh,
            consommation_mensuelle_kwh=results.consommation_mensuelle_kwh,
            consommation_horaire_kwh=[],
            
            # ✅ SCÉNARIO ACTUEL
            autoconsommation_kwh_actuel=autoconso_actuel_kwh,
            autoconsommation_ratio_actuel=autoconso_actuel_ratio,
            economie_annuelle_actuel=economie_totale_actuel,
            
            # ✅ SCÉNARIO OPTIMISÉ
            autoconsommation_kwh_optimise=autoconso_optimise_kwh,
            autoconsommation_ratio_optimise=autoconso_optimise_ratio,
            economie_annuelle_optimise=economie_totale_optimise,
            
            # ✅ GAINS
            gain_autoconso_kwh=gain_autoconso_kwh,
            gain_autoconso_pct=gain_autoconso_pct,
            gain_economie_annuel=gain_economie_annuel,
            gain_economie_25ans=gain_economie_25ans,
            
            # Champs existants (compatibilité)
            autoconsommation_ratio=autoconso_actuel_ratio,  # Pour compatibilité
            taux_autoproduction_pct=autoproduction_actuel_ratio,
            injection_reseau_kwh=injection_actuel_kwh,
            economie_annuelle_euros=economie_totale_actuel,
            roi_25ans_euros=economie_25ans,
            taux_rentabilite_pct=(economie_25ans / (config_optimale.puissance_kwc * 1800) * 100),
            puissance_recommandee_kwc=config_optimale.puissance_kwc,
            objectif_optimisation=objectif_str,

            tarif_achat_kwh=TARIF_ACHAT_KWH,
            tarif_injection_kwh=TARIF_INJECTION_KWH,
        )

        
        simulation.resultat = resultat
        simulation.status = 'success'
        simulation.completed_at = timezone.now()
        simulation.save()
        
        logger.info(f"✅ Simulation {simulation_id} terminée - {config_optimale.puissance_kwc} kWc")
        
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