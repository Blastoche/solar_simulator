"""
Vues pour l'application frontend (site public).
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
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
from .forms import InstallationForm
from .services.pdf_service import generate_pdf_report

logger = logging.getLogger(__name__)


# ============== PAGES STATIQUES ==============
# ✅ Tes anciennes vues, converties en Class-Based Views

class HomeView(TemplateView):
    """
    Page d'accueil / Landing page.
    """
    template_name = 'frontend/home.html'
    
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
                return JsonResponse({
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
            return JsonResponse({'status': 'error', 'errors': errors}, status=400)
        
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
        
        return JsonResponse({
            'html': html,
            'percentage': percentage,
            'state': task_result.state
        })
    
    except Exception as e:
        logger.error(f"❌ Erreur progression API: {str(e)}", exc_info=True)
        return JsonResponse({
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
