# solar_calc/tasks.py
from celery import shared_task
from django.utils import timezone
import logging

from frontend.models import Simulation, Resultat
from .services.calculator import SimulationCalculator
from weather.services.pvgis import get_pvgis_weather_data

logger = logging.getLogger(__name__)

@shared_task(bind=True)
def run_simulation_task(self, simulation_id):
    """Exécuter la simulation de manière asynchrone"""
    
    try:
        simulation = Simulation.objects.get(id=simulation_id)
        simulation.status = 'running'
        simulation.started_at = timezone.now()
        simulation.save()
        
        installation = simulation.installation
        calculator = SimulationCalculator(installation)
        
        # ===== ÉTAPE 1: Données météo (20%) =====
        self.update_state(
            state='PROGRESS',
            meta={'percentage': 20, 'message': '📡 Récupération des données météorologiques...'}
        )
        
        # CORRECTION : Utiliser la bonne fonction
        from weather.services.pvgis import get_pvgis_weather_data
        
        weather_df, metadata = get_pvgis_weather_data(
            latitude=installation.latitude,
            longitude=installation.longitude,
            use_cache=True
        )
        logger.info(f"Sim {simulation_id}: Données météo récupérées - {len(weather_df)} heures")
        
        # ===== ÉTAPE 2: Production (50%) =====
        self.update_state(
            state='PROGRESS',
            meta={'percentage': 50, 'message': '☀️ Calcul de production solaire...'}
        )
        
        # Votre SimulationCalculator doit maintenant accepter un DataFrame
        production = calculator.calculate_production(weather_df)
        logger.info(f"Sim {simulation_id}: Production calculée = {production['annuelle']} kWh")
        
        # ===== ÉTAPE 3: Consommation (70%) =====
        self.update_state(
            state='PROGRESS',
            meta={'percentage': 70, 'message': '⚡ Calcul de consommation...'}
        )
        
        # Récupérer la consommation depuis l'installation
        consommation_annuelle = getattr(installation, 'consommation_annuelle', 6000)
        consumption = calculator.calculate_consumption(consommation_annuelle=consommation_annuelle)
        
        logger.info(f"Sim {simulation_id}: Consommation calculée = {consumption['annuelle']} kWh")
        
        # ===== ÉTAPE 4: Financier (90%) =====
        self.update_state(
            state='PROGRESS',
            meta={'percentage': 90, 'message': '💰 Calculs financiers...'}
        )
        
        financial = calculator.calculate_financial(production, consumption)
        logger.info(f"Sim {simulation_id}: ROI calculé = {financial['roi']}€")
        
        # ===== ÉTAPE 5: Sauvegarde (100%) =====
        resultat = Resultat.objects.create(
            production_annuelle_kwh=production['annuelle'],
            production_mensuelle_kwh=production['monthly'],
            production_horaire_kwh=production['daily'],
            consommation_annuelle_kwh=consumption['annuelle'],
            consommation_mensuelle_kwh=consumption['monthly'],
            consommation_horaire_kwh=consumption['daily'],
            autoconsommation_ratio=production['autoconso_ratio'],
            injection_reseau_kwh=production['injection'],
            economie_annuelle_euros=financial['economie_annuelle'],
            roi_25ans_euros=financial['roi'],
            taux_rentabilite_pct=financial['taux_rentabilite'],
        )
        
        simulation.resultat = resultat
        simulation.status = 'success'
        simulation.completed_at = timezone.now()
        simulation.save()
        
        logger.info(f"Sim {simulation_id}: ✅ SUCCÈS")
        
        return {
            'percentage': 100,
            'message': '✅ Simulation terminée !',
            'resultat_id': str(resultat.id)
        }
        
    except Exception as e:
        logger.error(f"Sim {simulation_id}: ❌ ERREUR - {str(e)}", exc_info=True)
        
        simulation = Simulation.objects.get(id=simulation_id)
        simulation.status = 'failed'
        simulation.error_message = str(e)
        simulation.completed_at = timezone.now()
        simulation.save()
        
        raise
