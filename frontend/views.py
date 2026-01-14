"""
Vues pour l'application frontend (site public).
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import HttpResponse
from django.views.decorators.http import require_http_methods
from django.views.generic import TemplateView, CreateView, DetailView
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.utils import timezone
from celery.result import AsyncResult
import logging

from solar_calc.dataclasses.production import SolarInstallation
from solar_calc.dataclasses.consumption import ConsumptionProfile
from solar_calc.services.simulation import SimulationService
from solar_calc.tasks import run_simulation_task

from .models import Installation, Simulation, Resultat
from .frontend_forms import InstallationForm
#from .services.pdf_service import generate_pdf_report

from solar_calc.services.consumption_calculator import ConsumptionCalculator, calculate_consumption_from_form
from solar_calc.services.expert_consumption_calculator import ExpertConsumptionCalculator
from .models import ConsommationCalculee, AppareilConsommation, AppareillectriqueCategory 

logger = logging.getLogger(__name__)


# ============== PAGES STATIQUES ==============
# ✅ Tes anciennes vues, converties en Class-Based Views

class HomeView(TemplateView):
    """
    Page d'accueil / Landing page.
    """
    template_name = 'home.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page'] = 'home'
        return context


class MentionsView(TemplateView):
    """Page mentions légales."""
    template_name = 'frontend/legal/mentions.html'


class CGVView(TemplateView):
    """Page CGV."""
    template_name = 'frontend/legal/cgv.html'


class PrivacyView(TemplateView):
    """Page politique de confidentialité."""
    template_name = 'frontend/legal/privacy.html'


class SimulateurAvanceView(TemplateView):
    """
    Formulaire de simulation avancée (payante).
    À implémenter plus tard.
    """
    template_name = 'frontend/simulateur_avance.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page'] = 'simulateur_avance'
        return context


# ============== FORMULAIRE & SIMULATION ==============
# 🆕 Remplace ton ancien simulateur_gratuit()

class SimulationFormView(CreateView):
    """
    Formulaire de simulation gratuite (simplifié).
    Remplace l'ancienne fonction simulateur_gratuit().
    """
    model = Installation
    form_class = InstallationForm
    template_name = 'frontend/simulation/form.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page'] = 'simulateur_gratuit'
        return context
    
    def form_valid(self, form):
        """
        Appelé si le formulaire est valide.
        Crée l'installation et lance la simulation.
        """
        try:
            installation = form.save(commit=False)
            installation.user = self.request.user if self.request.user.is_authenticated else None
            installation.save()
            
            # Créer la simulation
            simulation = Simulation.objects.create(installation=installation)
            
            # Lancer la tâche Celery
            task = run_simulation_task.delay(simulation.id)
            simulation.task_id = task.id
            simulation.save()
            
            logger.info(f"✅ Simulation créée: {simulation.id}")
            
            # Pour les requêtes AJAX, retourner JSON
            if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return HttpResponse({
                    'status': 'success',
                    'simulation_id': str(simulation.id),
                    'redirect_url': reverse_lazy('frontend:simulation_progress', 
                                                  kwargs={'simulation_id': simulation.id})
                })
            
            # Pour les requêtes classiques, rediriger
            messages.success(self.request, 'Simulation lancée !')
            return redirect('frontend:simulation_progress', simulation_id=simulation.id)
        
        except Exception as e:
            logger.error(f"❌ Erreur création simulation: {str(e)}", exc_info=True)
            messages.error(self.request, f"Erreur: {str(e)}")
            return self.form_invalid(form)
    
    def form_invalid(self, form):
        """Retourner les erreurs du formulaire"""
        errors = {field: str(error[0]) for field, error in form.errors.items()}
        
        # Pour les requêtes AJAX
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return HttpResponse({'status': 'error', 'errors': errors}, status=400)
        
        # Pour les requêtes classiques
        return super().form_invalid(form)


# ============== PROGRESSION ==============
# 🆕 Nouveau : suivi de la progression

class SimulationProgressView(DetailView):
    """
    Page affichant la barre de progression de la simulation.
    """
    model = Simulation
    template_name = 'frontend/simulation/progress.html'
    pk_url_kwarg = 'simulation_id'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['task_id'] = self.object.task_id
        context['page'] = 'simulation_progress'
        return context


@require_http_methods(["GET"])
def simulation_progress_api(request, task_id):
    """
    API HTMX pour obtenir la progression en temps réel.
    Appelée toutes les 2 secondes par la page de progression.
    """
    try:
        task_result = AsyncResult(task_id)
        
        if task_result.state == 'PENDING':
            percentage = 0
            message = '⏳ Démarrage de la simulation...'
        elif task_result.state == 'PROGRESS':
            percentage = task_result.result.get('percentage', 0)
            message = task_result.result.get('message', 'En cours...')
        elif task_result.state == 'SUCCESS':
            percentage = 100
            message = '✅ Simulation terminée !'
        elif task_result.state == 'FAILURE':
            percentage = 0
            message = f'❌ Erreur: {str(task_result.result)}'
        else:
            percentage = 0
            message = f'État: {task_result.state}'
        
        html = render_to_string('frontend/simulation/progress_bar.html', {
            'percentage': percentage,
            'message': message,
            'state': task_result.state,
        })
        
        # CORRECTION : Retourner du HTML pur, pas du JSON
        return HttpResponse(html, content_type='text/html')
    
    except Exception as e:
        logger.error(f"❌ Erreur progression API: {str(e)}", exc_info=True)
        return HttpResponse(
            '<div class="text-red-600">Erreur de communication</div>',
            content_type='text/html',
            status=500
        )
    except Exception as e:
        logger.error(f"❌ Erreur progression API: {str(e)}", exc_info=True)
        return HttpResponse({
            'html': '<div class="text-red-600">Erreur de communication</div>',
            'percentage': 0,
            'state': 'ERROR'
        }, status=500)


# ============== RÉSULTATS ==============
# 🆕 Remplace ton ancien simulation_results()

class SimulationResultsView(DetailView):
    """
    Affichage des résultats d'une simulation.
    Remplace l'ancienne fonction simulation_results().
    """
    model = Simulation
    template_name = 'frontend/simulation/results.html'
    pk_url_kwarg = 'simulation_id'
    context_object_name = 'simulation'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page'] = 'simulation_results'
        
        simulation = self.object
        
        # Vérifier que la simulation est terminée
        if simulation.status != 'success':
            context['error'] = f"Simulation non terminée: {simulation.status}"
            return context
        
        if simulation.resultat:
            resultat = simulation.resultat
            
            # Données anciennes (ta logique métier)
            context['installation'] = simulation.installation
            context['profil'] = {
                'consommation_annuelle': resultat.consommation_annuelle_kwh,
            }
            
            # Données pour Plotly (nouveaux graphiques)
            context['monthly_chart'] = {
                'x': list(range(1, 13)),
                'production': resultat.production_mensuelle_kwh,
                'consommation': resultat.consommation_mensuelle_kwh,
            }
            
            context['daily_chart'] = {
                'x': list(range(0, 24)),
                'production': resultat.production_horaire_kwh,
                'consommation': resultat.consommation_horaire_kwh,
            }
        
        return context


# ============== EXPORTS ==============
# 🆕 Nouveaux : téléchargements

def simulation_pdf_download(request, simulation_id):
    """
    Télécharger le rapport PDF de la simulation.
    """
    try:
        simulation = get_object_or_404(Simulation, id=simulation_id)
        
        if not simulation.resultat:
            messages.error(request, 'Pas de résultats pour cette simulation')
            return redirect('frontend:simulation_results', simulation_id=simulation_id)
        
        pdf_bytes = generate_pdf_report(simulation)
        
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="simulation_{simulation.id}.pdf"'
        
        logger.info(f"📥 PDF téléchargé: {simulation.id}")
        
        return response
    
    except Exception as e:
        logger.error(f"❌ Erreur PDF: {str(e)}", exc_info=True)
        messages.error(request, 'Erreur lors de la génération du PDF')
        return redirect('frontend:simulation_results', simulation_id=simulation_id)


def simulation_excel_download(request, simulation_id):
    """
    Télécharger les résultats en Excel.
    À implémenter avec openpyxl.
    """
    messages.info(request, 'Export Excel à venir')
    return redirect('frontend:simulation_results', simulation_id=simulation_id)


# ============== VUES COMPATIBILITÉ ==============
# ✅ Anciennes vues function-based (pour compatibilité temporaire)

def home(request):
    """
    DEPRECATED: Utilise HomeView à la place.
    Gardé pour compatibilité.
    """
    return HomeView.as_view()(request)


def simulateur_gratuit(request):
    """
    DEPRECATED: Utilise SimulationFormView à la place.
    Gardé pour compatibilité.
    """
    return SimulationFormView.as_view()(request)


def simulation_results(request, simulation_id):
    """
    DEPRECATED: Utilise SimulationResultsView à la place.
    Gardé pour compatibilité.
    """
    return SimulationResultsView.as_view()(request, simulation_id=simulation_id)
from django.views.generic import TemplateView, DetailView
from django.shortcuts import redirect
from django.contrib import messages

class ConsumptionCalculatorView(TemplateView):
    """Formulaire de calcul de consommation"""
    template_name = 'frontend/consumption/calculator.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Récupérer les catégories et appareils (pour mode expert futur)
        categories = AppareillectriqueCategory.objects.prefetch_related('appareils').all()
        context['categories'] = categories
        
        return context


def consumption_calculate(request):
    """Calcule la consommation et affiche le résultat"""
    if request.method != 'POST':
        return redirect('frontend:consumption_calculator')
    
    try:
        # Récupérer les données du formulaire
        data = {
            'surface': float(request.POST.get('surface', 100)),
            'nb_personnes': int(request.POST.get('nb_personnes', 2)),
            'dpe': request.POST.get('dpe', 'D'),
            'annee_construction': int(request.POST.get('annee_construction', 2000)) if request.POST.get('annee_construction') else None,
            'latitude': float(request.POST.get('latitude', 48.8566)),
            'longitude': float(request.POST.get('longitude', 2.3522)),
            'type_chauffage': request.POST.get('type_chauffage', 'electrique'),
            'temperature_consigne': float(request.POST.get('temperature_consigne', 19)),
            'type_vmc': request.POST.get('type_vmc', 'aucune'),
            'type_ecs': request.POST.get('type_ecs', 'ballon_electrique'),
            'capacite_ecs': int(request.POST.get('capacite_ecs', 200)) if request.POST.get('capacite_ecs') else None,
            'age_appareils': request.POST.get('age_appareils', 'moyen'),
            'type_cuisson': request.POST.get('type_cuisson', 'induction'),
            'type_eclairage': request.POST.get('type_eclairage', 'LED'),
            # Nouveaux champs V2
            'usage_audiovisuel': request.POST.get('usage_audiovisuel', 'courant'),
            'puissance_compteur': request.POST.get('puissance_compteur', '6kVA'),
            'type_contrat': request.POST.get('type_contrat', 'base'),
        }   
        
        # Calculer
        calculator = ConsumptionCalculator(data)
        result = calculator.calculate_total()
        
        # Sauvegarder en base
        consommation = ConsommationCalculee.objects.create(
            surface_habitable=data['surface'],
            nb_personnes=data['nb_personnes'],
            dpe=data['dpe'],
            annee_construction=data['annee_construction'],
            latitude=data['latitude'],
            longitude=data['longitude'],
            zone_climatique=calculator.zone_climatique,
            type_chauffage=data['type_chauffage'],
            temperature_consigne=data['temperature_consigne'],
            type_vmc=data['type_vmc'],
            type_ecs=data['type_ecs'],
            capacite_ecs_litres=data['capacite_ecs'],
            mode_calcul='rapide',
            consommation_annuelle_totale=result['total_annuel'],
            consommation_moyenne_attendue=result['moyenne_attendue'],
            ecart_pourcentage=result['ecart_pct'],
            repartition_postes=result['repartition'],
            consommation_mensuelle=result['mensuel'],
        )
        
        logger.info(f"✅ Consommation calculée : {consommation.id}")
        
        # Calculer les détails financiers
        financier = calculator.calculate_financial_details(result['total_annuel'])

        # Stocker dans la session
        request.session['financier'] = financier

        logger.info(f"💰 Coût total: {financier['cout_total']}€/an")

        # Retourner vers la page résultat
        return redirect('frontend:consumption_result', consommation_id=consommation.pk)
        
    except Exception as e:
        logger.error(f"❌ Erreur calcul consommation : {str(e)}", exc_info=True)
        messages.error(request, f"Erreur lors du calcul : {str(e)}")
        return redirect('frontend:consumption_calculator')


class ConsumptionResultView(DetailView):
    """Affiche le résultat du calcul de consommation"""
    model = ConsommationCalculee
    template_name = 'frontend/consumption/result.html'
    pk_url_kwarg = 'consommation_id'
    context_object_name = 'consommation'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        consommation = self.object
    
        # Message de comparaison
        context['comparaison'] = consommation.get_message_comparaison()
    
        # Récupérer le financier de la session
        financier = self.request.session.get('financier', None)
        if financier:
            context['financier'] = financier
            logger.info(f"Financier passé au contexte: {financier['type']}")
    
        return context


class ConsumptionDetailsView(DetailView):
    """Affiche les détails avec graphiques"""
    model = ConsommationCalculee
    template_name = 'frontend/consumption/details.html'
    pk_url_kwarg = 'consommation_id'
    context_object_name = 'consommation'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Récupérer le financier de la session
        financier = self.request.session.get('financier', None)
        if financier:
            context['financier'] = financier
            logger.info(f"Financier passé au contexte details: {financier['type']}")
        
        return context



# ==============================================================================
# VUE FORMULAIRE MODE EXPERT
# ==============================================================================

def consumption_calculator_expert(request):
    """
    Affiche le formulaire mode expert (12 étapes).
    GET : Affiche le formulaire
    """
    return render(request, 'frontend/calculator_expert.html')


# ==============================================================================
# VUE CALCUL MODE EXPERT
# ==============================================================================

def consumption_calculate_expert(request):
    """
    Traite le formulaire mode expert et calcule la consommation détaillée.
    POST uniquement.
    """
    if request.method != 'POST':
        return redirect('frontend:consumption_calculator_expert')
    
    try:
        # ========== RÉCUPÉRATION DONNÉES FORMULAIRE ==========
        
        data = {}
        
        # === ÉTAPE 1 : LOGEMENT ===
        data['surface'] = float(request.POST.get('surface', 100))
        data['nb_personnes'] = int(request.POST.get('nb_personnes', 2))
        data['dpe'] = request.POST.get('dpe', 'D')
        data['latitude'] = float(request.POST.get('latitude', 48.8566))
        data['longitude'] = float(request.POST.get('longitude', 2.3522))
        
        # Année construction
        annee_type = request.POST.get('annee_type', 'exacte')
        if annee_type == 'exacte':
            data['annee_construction'] = int(request.POST.get('annee_construction_exacte', 2005))
        else:
            data['annee_construction'] = int(request.POST.get('annee_construction_plage', 2005))
        
        # === ÉTAPE 2 : CHAUFFAGE ===
        data['type_chauffage'] = request.POST.get('type_chauffage', 'electrique')
        data['temperature_consigne'] = float(request.POST.get('temperature_consigne', 19))
        data['type_vmc'] = request.POST.get('type_vmc', 'aucune')
        
        # === ÉTAPE 3 : EAU CHAUDE ===
        data['type_ecs'] = request.POST.get('type_ecs', 'ballon_electrique')
        data['capacite_ecs'] = int(request.POST.get('capacite_ecs', 200))
        
        # === ÉTAPE 4 : CUISSON ===
        data['type_cuisson'] = request.POST.get('type_cuisson', 'induction')
        
        # === ÉTAPE 5 : RÉFRIGÉRATION ===
        
        # Frigos (peut y en avoir plusieurs)
        frigos = []
        i = 0
        while True:
            type_frigo = request.POST.get(f'frigo_type_{i}')
            if not type_frigo or type_frigo == '':
                break
            
            frigos.append({
                'type': type_frigo,
                'classe': request.POST.get(f'frigo_classe_{i}', 'A++'),
                'nombre': int(request.POST.get(f'frigo_nombre_{i}', 1)),
            })
            i += 1
            if i > 10:  # Limite sécurité
                break
        
        data['frigos'] = frigos if frigos else [{'type': '', 'classe': 'A++', 'nombre': 0}]
        
        # Congélateurs
        congelateurs = []
        i = 0
        while True:
            type_cong = request.POST.get(f'congelateur_type_{i}')
            if not type_cong or type_cong == '':
                break
            
            congelateurs.append({
                'type': type_cong,
                'classe': request.POST.get(f'congelateur_classe_{i}', 'A++'),
                'nombre': int(request.POST.get(f'congelateur_nombre_{i}', 1)),
            })
            i += 1
            if i > 10:
                break
        
        data['congelateurs'] = congelateurs if congelateurs else [{'type': '', 'classe': 'A++', 'nombre': 0}]
        
        # === ÉTAPE 6 : LAVAGE ===
        data['lave_linge_actif'] = request.POST.get('lave_linge_actif') == '1'
        data['lave_linge_classe'] = request.POST.get('lave_linge_classe', 'A++')
        data['lave_linge_cycles'] = int(request.POST.get('lave_linge_cycles', 4))
        
        data['lave_vaisselle_actif'] = request.POST.get('lave_vaisselle_actif') == '1'
        data['lave_vaisselle_classe'] = request.POST.get('lave_vaisselle_classe', 'A++')
        data['lave_vaisselle_cycles'] = int(request.POST.get('lave_vaisselle_cycles', 5))
        
        data['seche_linge_actif'] = request.POST.get('seche_linge_actif') == '1'
        data['seche_linge_type'] = request.POST.get('seche_linge_type', 'pompe_chaleur_A++')
        data['seche_linge_cycles'] = int(request.POST.get('seche_linge_cycles', 3))
        
        # === ÉTAPE 7 : FOUR ===
        data['type_four'] = request.POST.get('type_four', 'four_electrique')
        data['usage_four'] = request.POST.get('usage_four', 'occasionnel')
        
        # === ÉTAPE 8 : AUDIOVISUEL ===
        
        # TVs
        tvs = []
        i = 0
        while True:
            taille = request.POST.get(f'tv_taille_{i}')
            if not taille:
                break
            
            tvs.append({
                'taille': taille,
                'techno': request.POST.get(f'tv_techno_{i}', 'led'),
                'heures_jour': float(request.POST.get(f'tv_heures_{i}', 4)),
            })
            i += 1
            if i > 10:
                break
        
        data['tvs'] = tvs if tvs else [{'taille': 'moyen', 'techno': 'led', 'heures_jour': 4}]
        
        # Box
        data['type_box'] = request.POST.get('type_box', 'seule')
        data['box_eteinte_nuit'] = request.POST.get('box_eteinte_nuit') == '1'
        
        # Ordinateurs
        data['nb_ordis_fixes'] = int(request.POST.get('nb_ordis_fixes', 0))
        data['nb_ordis_portables'] = int(request.POST.get('nb_ordis_portables', 0))
        data['heures_ordi'] = float(request.POST.get('heures_ordi', 6))
        
        # Console
        data['console_actif'] = request.POST.get('console_actif') == '1'
        data['type_console'] = request.POST.get('type_console', 'actuelle')
        data['heures_console'] = float(request.POST.get('heures_console', 2))
        
        # === ÉTAPE 9 : ÉCLAIRAGE ===
        data['nb_led'] = int(request.POST.get('nb_led', 20))
        data['nb_halogene'] = int(request.POST.get('nb_halogene', 0))
        data['heures_eclairage'] = float(request.POST.get('heures_eclairage', 5))
        
        # === ÉTAPE 10 : ÉQUIPEMENTS SPÉCIAUX ===
        
        # Piscine
        data['piscine_active'] = request.POST.get('piscine_active') == '1'
        if data['piscine_active']:
            # Mode saisie puissance
            mode_pompe = request.POST.get('piscine_pompe_mode', 'connue')
            if mode_pompe == 'connue':
                puissance = request.POST.get('piscine_puissance_pompe')
                data['piscine_puissance_pompe'] = int(puissance) if puissance else None
            else:
                type_pompe = request.POST.get('piscine_type_pompe', 'standard')
                data['piscine_type_pompe'] = type_pompe
                data['piscine_puissance_pompe'] = None
            
            data['piscine_heures_filtration'] = int(request.POST.get('piscine_heures_filtration', 8))
            data['piscine_mois_debut'] = int(request.POST.get('piscine_mois_debut', 5))
            data['piscine_mois_fin'] = int(request.POST.get('piscine_mois_fin', 9))
            
            data['piscine_chauffage_actif'] = request.POST.get('piscine_chauffage_actif') == '1'
            if data['piscine_chauffage_actif']:
                data['piscine_type_chauffage'] = request.POST.get('piscine_type_chauffage', 'pac')
                data['piscine_puissance_chauffage'] = int(request.POST.get('piscine_puissance_chauffage', 2000))
                data['piscine_heures_chauffage'] = int(request.POST.get('piscine_heures_chauffage', 4))
            
            data['piscine_robot_actif'] = request.POST.get('piscine_robot_actif') == '1'
        
        # Spa
        data['spa_actif'] = request.POST.get('spa_actif') == '1'
        if data['spa_actif']:
            data['type_spa'] = request.POST.get('type_spa', 'rigide')
            data['spa_utilisation'] = request.POST.get('spa_utilisation', 'annee')
            data['spa_toute_annee'] = data['spa_utilisation'] == 'annee'
            data['spa_temp_maintenue'] = request.POST.get('spa_temp_maintenue') == '1'
            data['spa_couverture'] = request.POST.get('spa_couverture') == '1'
        
        # Véhicule électrique
        vehicules = []
        ve_actif = request.POST.get('ve_actif') == '1'
        if ve_actif:
            # Pour l'instant on gère 1 VE, mais structure extensible
            vehicules.append({
                'conso_100km': float(request.POST.get('ve_conso_100km', 18)),
                'km_an': int(request.POST.get('ve_km_an', 15000)),
                'type_recharge': request.POST.get('ve_type_recharge', 'wallbox_7'),
                'pct_recharge_domicile': int(request.POST.get('ve_pct_domicile', 100)),
            })
        
        data['vehicules'] = vehicules
        
        # === ÉTAPE 11 : PROFIL D'USAGE ===
        data['profil_usage'] = request.POST.get('profil_usage', 'actif_absent')
        
        # Heures lever/coucher (format HH:MM)
        heure_lever_str = request.POST.get('heure_lever', '07:00')
        heure_coucher_str = request.POST.get('heure_coucher', '23:00')
        
        # Convertir en heures (0-23)
        try:
            data['heure_lever'] = int(heure_lever_str.split(':')[0])
            data['heure_coucher'] = int(heure_coucher_str.split(':')[0])
        except:
            data['heure_lever'] = 7
            data['heure_coucher'] = 23
        
        # === ÉTAPE 12 : CONTRAT ===
        data['puissance_compteur'] = request.POST.get('puissance_compteur', '6kVA')
        data['type_contrat'] = request.POST.get('type_contrat', 'base')
        
        # ========== CALCUL ==========
        
        logger.info(f"🔬 Calcul mode expert : {data['surface']}m², {data['nb_personnes']} pers")
        
        # Créer le calculateur expert
        calculator = ExpertConsumptionCalculator(data)
        
        # Lancer le calcul
        result = calculator.calculate_total_expert()
        
        # Calculs financiers
        financier = calculator.calculate_financial_details(result['total_annuel'])
        
        # Optimisation HP/HC
        optim_hphc = calculator.calculate_optimisation_hphc(result['total_annuel'])
        
        # Projection 10 ans
        projection = calculator.calculate_projection_10ans(result['total_annuel'], financier['cout_total'])
        

        # ========== SAUVEGARDE BDD ==========
        
        # Créer l'objet ConsommationCalculee
        consommation = ConsommationCalculee.objects.create(
            # Logement
            surface_habitable=data['surface'],
            nb_personnes=data['nb_personnes'],
            dpe=data['dpe'],
            annee_construction=data['annee_construction'],
            latitude=data['latitude'],
            longitude=data['longitude'],
            
            # Chauffage
            type_chauffage=data['type_chauffage'],
            temperature_consigne=data['temperature_consigne'],
            type_vmc=data['type_vmc'],
            
            # ECS
            type_ecs=data['type_ecs'],
            capacite_ecs_litres=data['capacite_ecs'],
            
            # Résultats
            consommation_annuelle_totale=result['total_annuel'],
            consommation_mensuelle=result['mensuel'],
            consommation_moyenne_attendue=result.get('moyenne_attendue', 0),
            ecart_pourcentage=result.get('ecart_pct', 0),
            repartition_postes=result['repartition'],
            
            # Financier
            cout_annuel=financier['cout_total'],
            
            # Mode expert
            mode_calcul='expert',
            profil_usage=data['profil_usage'],
            heure_lever=data['heure_lever'],
            heure_coucher=data['heure_coucher'],
            pct_hc_actuel=optim_hphc.get('pct_hc_actuel', 0),
            pct_hc_optimal=optim_hphc.get('pct_hc_optimal', 0),
            economie_optimisation_hphc=optim_hphc.get('economie_annuelle', 0),
            projection_10ans=projection,
        )
        
        # Créer les appareils détaillés
        for appareil_data in result['appareils']:
            AppareilConsommation.objects.create(
                consommation=consommation,
                categorie=appareil_data['categorie'],
                type_appareil=appareil_data['type_appareil'],
                nom_affichage=appareil_data.get('nom_affichage', ''),
                nombre=appareil_data.get('nombre', 1),
                classe_energetique=appareil_data.get('classe_energetique', ''),
                puissance_w=appareil_data.get('puissance_w'),
                cycles_semaine=appareil_data.get('cycles_semaine'),
                heures_jour=appareil_data.get('heures_jour'),
                mois_debut=appareil_data.get('mois_debut'),
                mois_fin=appareil_data.get('mois_fin'),
                km_an=appareil_data.get('km_an'),
                conso_100km=appareil_data.get('conso_100km'),
                rendement_charge=appareil_data.get('rendement_charge'),
                pct_recharge_domicile=appareil_data.get('pct_recharge_domicile'),
                consommation_annuelle=appareil_data['consommation_annuelle'],
                consommation_mensuelle=appareil_data.get('consommation_mensuelle', []),
            )
        
        logger.info(f"✅ Consommation mode expert sauvegardée : {consommation.pk}")
        
        # Stocker les données financières en session (non sauvegardées en BDD)
        request.session[f'financier_{consommation.pk}'] = financier
        request.session[f'optim_hphc_{consommation.pk}'] = optim_hphc
        
        # Message succès
        messages.success(request, f"✅ Analyse experte terminée : {result['total_annuel']:.0f} kWh/an")
        
        # Redirection vers résultat
        return redirect('frontend:consumption_result_expert', consommation_id=consommation.pk)
        
    except Exception as e:
        logger.error(f"❌ Erreur calcul mode expert : {e}", exc_info=True)
        messages.error(request, f"Erreur lors du calcul : {str(e)}")
        return redirect('frontend:consumption_calculator_expert')


# ==============================================================================
# VUE RÉSULTAT MODE EXPERT
# ==============================================================================

class ConsumptionExpertResultView(DetailView):
    """
    Affiche les résultats détaillés du mode expert.
    """
    model = ConsommationCalculee
    template_name = 'frontend/result_expert.html'
    context_object_name = 'consommation'
    pk_url_kwarg = 'consommation_id'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        consommation = self.object
        
        # Récupérer les appareils
        appareils = consommation.appareils.all().order_by('categorie', '-consommation_annuelle')
        
        # Grouper par catégorie
        appareils_par_categorie = {}
        for appareil in appareils:
            cat = appareil.get_categorie_display()
            if cat not in appareils_par_categorie:
                appareils_par_categorie[cat] = []
            appareils_par_categorie[cat].append(appareil)
        
        # Récupérer données financières et optimisation depuis session
        financier = self.request.session.get(f'financier_{consommation.pk}', {})
        optim_hphc = self.request.session.get(f'optim_hphc_{consommation.pk}', {})
        
        context.update({
            'appareils': appareils,
            'appareils_par_categorie': appareils_par_categorie,
            'nb_appareils': appareils.count(),
            'financier': financier,
            'optim_hphc': optim_hphc,
        })
        
        return context


# À REMPLACER dans frontend/views.py
# VERSION CORRIGÉE avec gestion des champs vides

import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import DetailView
from django.contrib import messages
from solar_calc.services.expert_consumption_calculator import ExpertConsumptionCalculator
from .models import ConsommationCalculee, AppareilConsommation

logger = logging.getLogger(__name__)


# ==============================================================================
# FONCTION HELPER POUR CONVERSION SÉCURISÉE
# ==============================================================================

def safe_int(value, default=0):
    """Convertit une valeur en int de manière sécurisée."""
    if value is None or value == '':
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def safe_float(value, default=0.0):
    """Convertit une valeur en float de manière sécurisée."""
    if value is None or value == '':
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


# ==============================================================================
# VUE FORMULAIRE MODE EXPERT
# ==============================================================================

def consumption_calculator_expert(request):
    """
    Affiche le formulaire mode expert (12 étapes).
    GET : Affiche le formulaire
    """
    return render(request, 'frontend/calculator_expert.html')


# ==============================================================================
# VUE CALCUL MODE EXPERT (VERSION CORRIGÉE)
# ==============================================================================

def consumption_calculate_expert(request):
    """
    Traite le formulaire mode expert et calcule la consommation détaillée.
    POST uniquement.
    VERSION CORRIGÉE avec gestion des champs vides.
    """
    if request.method != 'POST':
        return redirect('frontend:consumption_calculator_expert')
    
    try:
        # ========== RÉCUPÉRATION DONNÉES FORMULAIRE (SÉCURISÉE) ==========
        
        data = {}
        
        # === ÉTAPE 1 : LOGEMENT ===
        data['surface'] = safe_float(request.POST.get('surface'), 100)
        data['nb_personnes'] = safe_int(request.POST.get('nb_personnes'), 2)
        data['dpe'] = request.POST.get('dpe', 'D')
        data['latitude'] = safe_float(request.POST.get('latitude'), 48.8566)
        data['longitude'] = safe_float(request.POST.get('longitude'), 2.3522)
        
        # Année construction
        annee_type = request.POST.get('annee_type', 'exacte')
        if annee_type == 'exacte':
            data['annee_construction'] = safe_int(request.POST.get('annee_construction_exacte'), 2005)
        else:
            data['annee_construction'] = safe_int(request.POST.get('annee_construction_plage'), 2005)
        
        # === ÉTAPE 2 : CHAUFFAGE ===
        data['type_chauffage'] = request.POST.get('type_chauffage', 'electrique')
        data['temperature_consigne'] = safe_float(request.POST.get('temperature_consigne'), 19)
        data['type_vmc'] = request.POST.get('type_vmc', 'aucune')
        
        # === ÉTAPE 3 : EAU CHAUDE ===
        data['type_ecs'] = request.POST.get('type_ecs', 'ballon_electrique')
        data['capacite_ecs'] = safe_int(request.POST.get('capacite_ecs'), 200)
        
        # === ÉTAPE 4 : CUISSON ===
        data['type_cuisson'] = request.POST.get('type_cuisson', 'induction')
        
        # === ÉTAPE 5 : RÉFRIGÉRATION ===
        
        # Frigos (peut y en avoir plusieurs)
        frigos = []
        for i in range(10):  # Maximum 10 frigos
            type_frigo = request.POST.get(f'frigo_type_{i}')
            if type_frigo and type_frigo != '':
                frigos.append({
                    'type': type_frigo,
                    'classe': request.POST.get(f'frigo_classe_{i}', 'A++'),
                    'nombre': safe_int(request.POST.get(f'frigo_nombre_{i}'), 1),
                })
        
        # Si aucun frigo n'a été ajouté, on met un frigo par défaut vide
        data['frigos'] = frigos if frigos else [{'type': '', 'classe': 'A++', 'nombre': 0}]
        
        # Congélateurs
        congelateurs = []
        for i in range(10):  # Maximum 10 congélateurs
            type_cong = request.POST.get(f'congelateur_type_{i}')
            if type_cong and type_cong != '':
                congelateurs.append({
                    'type': type_cong,
                    'classe': request.POST.get(f'congelateur_classe_{i}', 'A++'),
                    'nombre': safe_int(request.POST.get(f'congelateur_nombre_{i}'), 1),
                })
        
        data['congelateurs'] = congelateurs if congelateurs else [{'type': '', 'classe': 'A++', 'nombre': 0}]
        
        # === ÉTAPE 6 : LAVAGE ===
        data['lave_linge_actif'] = request.POST.get('lave_linge_actif') == '1'
        data['lave_linge_classe'] = request.POST.get('lave_linge_classe', 'A++')
        data['lave_linge_cycles'] = safe_int(request.POST.get('lave_linge_cycles'), 4)
        
        data['lave_vaisselle_actif'] = request.POST.get('lave_vaisselle_actif') == '1'
        data['lave_vaisselle_classe'] = request.POST.get('lave_vaisselle_classe', 'A++')
        data['lave_vaisselle_cycles'] = safe_int(request.POST.get('lave_vaisselle_cycles'), 5)
        
        data['seche_linge_actif'] = request.POST.get('seche_linge_actif') == '1'
        data['seche_linge_type'] = request.POST.get('seche_linge_type', 'pompe_chaleur_A++')
        data['seche_linge_cycles'] = safe_int(request.POST.get('seche_linge_cycles'), 3)
        
        # === ÉTAPE 7 : FOUR ===
        data['type_four'] = request.POST.get('type_four', 'four_electrique')
        data['usage_four'] = request.POST.get('usage_four', 'occasionnel')
        
        # === ÉTAPE 8 : AUDIOVISUEL ===
        
        # TVs
        tvs = []
        for i in range(10):  # Maximum 10 TVs
            taille = request.POST.get(f'tv_taille_{i}')
            if taille:
                tvs.append({
                    'taille': taille,
                    'techno': request.POST.get(f'tv_techno_{i}', 'led'),
                    'heures_jour': safe_float(request.POST.get(f'tv_heures_{i}'), 4),
                })
        
        # Au moins 1 TV par défaut si aucune n'est définie
        data['tvs'] = tvs if tvs else [{'taille': 'moyen', 'techno': 'led', 'heures_jour': 4}]
        
        # Box
        data['type_box'] = request.POST.get('type_box', 'seule')
        data['box_eteinte_nuit'] = request.POST.get('box_eteinte_nuit') == '1'
        
        # Ordinateurs
        data['nb_ordis_fixes'] = safe_int(request.POST.get('nb_ordis_fixes'), 0)
        data['nb_ordis_portables'] = safe_int(request.POST.get('nb_ordis_portables'), 0)
        data['heures_ordi'] = safe_float(request.POST.get('heures_ordi'), 6)
        
        # Console
        data['console_actif'] = request.POST.get('console_actif') == '1'
        data['type_console'] = request.POST.get('type_console', 'actuelle')
        data['heures_console'] = safe_float(request.POST.get('heures_console'), 2)
        
        # === ÉTAPE 9 : ÉCLAIRAGE ===
        data['nb_led'] = safe_int(request.POST.get('nb_led'), 20)
        data['nb_halogene'] = safe_int(request.POST.get('nb_halogene'), 0)
        data['heures_eclairage'] = safe_float(request.POST.get('heures_eclairage'), 5)
        
        # === ÉTAPE 10 : ÉQUIPEMENTS SPÉCIAUX ===
        
        # Piscine
        data['piscine_active'] = request.POST.get('piscine_active') == '1'
        if data['piscine_active']:
            # Mode saisie puissance
            mode_pompe = request.POST.get('piscine_pompe_mode', 'connue')
            if mode_pompe == 'connue':
                puissance = request.POST.get('piscine_puissance_pompe')
                data['piscine_puissance_pompe'] = safe_int(puissance, None)
            else:
                type_pompe = request.POST.get('piscine_type_pompe', 'standard')
                data['piscine_type_pompe'] = type_pompe
                data['piscine_puissance_pompe'] = None
            
            data['piscine_heures_filtration'] = safe_int(request.POST.get('piscine_heures_filtration'), 8)
            data['piscine_mois_debut'] = safe_int(request.POST.get('piscine_mois_debut'), 5)
            data['piscine_mois_fin'] = safe_int(request.POST.get('piscine_mois_fin'), 9)
            
            data['piscine_chauffage_actif'] = request.POST.get('piscine_chauffage_actif') == '1'
            if data['piscine_chauffage_actif']:
                data['piscine_type_chauffage'] = request.POST.get('piscine_type_chauffage', 'pac')
                data['piscine_puissance_chauffage'] = safe_int(request.POST.get('piscine_puissance_chauffage'), 2000)
                data['piscine_heures_chauffage'] = safe_int(request.POST.get('piscine_heures_chauffage'), 4)
            
            data['piscine_robot_actif'] = request.POST.get('piscine_robot_actif') == '1'
        
        # Spa
        data['spa_actif'] = request.POST.get('spa_actif') == '1'
        if data['spa_actif']:
            data['type_spa'] = request.POST.get('type_spa', 'rigide')
            data['spa_utilisation'] = request.POST.get('spa_utilisation', 'annee')
            data['spa_toute_annee'] = data['spa_utilisation'] == 'annee'
            data['spa_temp_maintenue'] = request.POST.get('spa_temp_maintenue') == '1'
            data['spa_couverture'] = request.POST.get('spa_couverture') == '1'
        
        # Véhicule électrique
        vehicules = []
        ve_actif = request.POST.get('ve_actif') == '1'
        if ve_actif:
            vehicules.append({
                'conso_100km': safe_float(request.POST.get('ve_conso_100km'), 18),
                'km_an': safe_int(request.POST.get('ve_km_an'), 15000),
                'type_recharge': request.POST.get('ve_type_recharge', 'wallbox_7'),
                'pct_recharge_domicile': safe_int(request.POST.get('ve_pct_domicile'), 100),
            })
        
        data['vehicules'] = vehicules
        
        # === ÉTAPE 11 : PROFIL D'USAGE ===
        data['profil_usage'] = request.POST.get('profil_usage', 'actif_absent')
        
        # Heures lever/coucher (format HH:MM)
        heure_lever_str = request.POST.get('heure_lever', '07:00')
        heure_coucher_str = request.POST.get('heure_coucher', '23:00')
        
        # Convertir en heures (0-23)
        try:
            data['heure_lever'] = int(heure_lever_str.split(':')[0])
        except:
            data['heure_lever'] = 7
        
        try:
            data['heure_coucher'] = int(heure_coucher_str.split(':')[0])
        except:
            data['heure_coucher'] = 23
        
        # === ÉTAPE 12 : CONTRAT ===
        data['puissance_compteur'] = request.POST.get('puissance_compteur', '6kVA')
        data['type_contrat'] = request.POST.get('type_contrat', 'base')
        
        # ========== CALCUL ==========
        
        logger.info(f"🔬 Calcul mode expert : {data['surface']}m², {data['nb_personnes']} pers")
        
        # Créer le calculateur expert
        calculator = ExpertConsumptionCalculator(data)
        
        # Lancer le calcul
        result = calculator.calculate_total_expert()
        
        # Calculs financiers
        financier = calculator.calculate_financial_details(result['total_annuel'])
        
        # Optimisation HP/HC
        optim_hphc = calculator.calculate_optimisation_hphc(result['total_annuel'])
        
        # Projection 10 ans
        projection = calculator.calculate_projection_10ans(result['total_annuel'], financier['cout_total'])
        
        # ========== SAUVEGARDE BDD ==========
        
        # Créer l'objet ConsommationCalculee
        consommation = ConsommationCalculee.objects.create(
            # Logement
            surface_habitable=data['surface'],  # ← CORRIGÉ
            nb_personnes=data['nb_personnes'],
            dpe=data['dpe'],
            annee_construction=data['annee_construction'],
            latitude=data['latitude'],
            longitude=data['longitude'],
            
            # Chauffage
            type_chauffage=data['type_chauffage'],
            temperature_consigne=data['temperature_consigne'],
            type_vmc=data['type_vmc'],
            
            # ECS
            type_ecs=data['type_ecs'],
            capacite_ecs_litres=data['capacite_ecs'],  # ← CORRIGÉ

            # Cuisson
            type_cuisson=data.get('type_cuisson', ''),

            # Résultats
            consommation_annuelle_totale=result['total_annuel'],  # ← CORRIGÉ
            consommation_mensuelle=result['mensuel'],
            consommation_moyenne_attendue=result.get('moyenne_attendue', 0),  # ← CORRIGÉ
            ecart_pourcentage=result.get('ecart_pct', 0),
            repartition_postes=result['repartition'],  # ← CORRIGÉ
            
            # Mode expert
            mode_calcul='expert',
            profil_usage=data['profil_usage'],
            heure_lever=data['heure_lever'],
            heure_coucher=data['heure_coucher'],
            pct_hc_actuel=optim_hphc.get('pct_hc_actuel', 0),
            pct_hc_optimal=optim_hphc.get('pct_hc_optimal', 0),
            economie_optimisation_hphc=optim_hphc.get('economie_annuelle', 0),
            projection_10ans=projection,

            # Contrat
            puissance_compteur=data.get('puissance_compteur', ''),
            type_contrat=data.get('type_contrat', 'base'),
        )
        
        # Créer les appareils détaillés
        # Prix moyen kWh (peut varier selon type_contrat)
        if data.get('type_contrat') == 'hphc':
            prix_moyen_kwh = 0.2384  # Moyenne HP/HC
        else:
            prix_moyen_kwh = 0.2516  # Tarif base
        
        for appareil_data in result['appareils']:
            # Calculer le coût annuel de l'appareil
            cout_appareil = appareil_data['consommation_annuelle'] * prix_moyen_kwh
            
            AppareilConsommation.objects.create(
                consommation=consommation,
                categorie=appareil_data['categorie'],
                type_appareil=appareil_data['type_appareil'],
                nom_affichage=appareil_data.get('nom_affichage', ''),
                nombre=appareil_data.get('nombre', 1),
                classe_energetique=appareil_data.get('classe_energetique', ''),
                puissance_w=appareil_data.get('puissance_w'),
                cycles_semaine=appareil_data.get('cycles_semaine'),
                heures_jour=appareil_data.get('heures_jour'),
                mois_debut=appareil_data.get('mois_debut'),
                mois_fin=appareil_data.get('mois_fin'),
                km_an=appareil_data.get('km_an'),
                conso_100km=appareil_data.get('conso_100km'),
                rendement_charge=appareil_data.get('rendement_charge'),
                pct_recharge_domicile=appareil_data.get('pct_recharge_domicile'),
                consommation_annuelle=appareil_data['consommation_annuelle'],
                consommation_mensuelle=appareil_data.get('consommation_mensuelle', []),
                cout_annuel=cout_appareil,  # ← AJOUTÉ : Calculer le coût !
            )
        
        logger.info(f"✅ Consommation mode expert sauvegardée : {consommation.pk}")
        
        # Stocker les données financières en session (non sauvegardées en BDD)
        request.session[f'financier_{consommation.pk}'] = financier
        request.session[f'optim_hphc_{consommation.pk}'] = optim_hphc
        
        # Message succès
        messages.success(request, f"✅ Analyse experte terminée : {result['total_annuel']:.0f} kWh/an")
        
        # Redirection vers résultat
        return redirect('frontend:consumption_result_expert', consommation_id=consommation.pk)
        
    except Exception as e:
        logger.error(f"❌ Erreur calcul mode expert : {e}", exc_info=True)
        messages.error(request, f"Erreur lors du calcul : {str(e)}")
        return redirect('frontend:consumption_calculator_expert')


# ==============================================================================
# VUE RÉSULTAT MODE EXPERT
# ==============================================================================

class ConsumptionExpertResultView(DetailView):
    """
    Affiche les résultats détaillés du mode expert.
    """
    model = ConsommationCalculee
    template_name = 'frontend/result_expert.html'
    context_object_name = 'consommation'
    pk_url_kwarg = 'consommation_id'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        consommation = self.object
        
        # Récupérer les appareils
        appareils = consommation.appareils.all().order_by('categorie', '-consommation_annuelle')
        
        # Grouper par catégorie
        appareils_par_categorie = {}
        for appareil in appareils:
            cat = appareil.get_categorie_display()
            if cat not in appareils_par_categorie:
                appareils_par_categorie[cat] = []
            appareils_par_categorie[cat].append(appareil)
        
        # Récupérer données financières et optimisation depuis session
        financier = self.request.session.get(f'financier_{consommation.pk}', {})
        optim_hphc = self.request.session.get(f'optim_hphc_{consommation.pk}', {})
        
        context.update({
            'appareils': appareils,
            'appareils_par_categorie': appareils_par_categorie,
            'nb_appareils': appareils.count(),
            'financier': financier,
            'optim_hphc': optim_hphc,
        })
        
        return context


# ==============================================================================
# VUE DÉTAILS MODE EXPERT
# ==============================================================================

class ConsumptionExpertDetailsView(DetailView):
    """
    Affiche les détails approfondis (tableaux, graphiques mensuels, etc.).
    """
    model = ConsommationCalculee
    template_name = 'frontend/details_expert.html'
    context_object_name = 'consommation'
    pk_url_kwarg = 'consommation_id'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        consommation = self.object
        
        # Appareils
        appareils = consommation.appareils.all().order_by('-consommation_annuelle')
        
        # Données financières
        financier = self.request.session.get(f'financier_{consommation.pk}', {})
        optim_hphc = self.request.session.get(f'optim_hphc_{consommation.pk}', {})
        
        context.update({
            'appareils': appareils,
            'financier': financier,
            'optim_hphc': optim_hphc,
        })
        
        return context
