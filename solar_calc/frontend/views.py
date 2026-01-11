"""
Vues pour l'application frontend (site public).
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from solar_calc.dataclasses.production import SolarInstallation
from solar_calc.dataclasses.consumption import ConsumptionProfile
from solar_calc.services.simulation import SimulationService

from django.contrib.auth.models import User


def home(request):
    """
    Page d'accueil / Landing page.
    """
    context = {
        'page': 'home',
    }
    return render(request, 'home.html', context)


def simulateur_gratuit(request):
    """
    Formulaire de simulation gratuite (simplifié).
    """
    if request.method == 'POST':
        # TODO: Traiter le formulaire
        messages.success(request, 'Simulation lancée !')
        return redirect('simulation_results', simulation_id=1)
    
    context = {
        'page': 'simulateur_gratuit',
    }
    return render(request, 'simulateur_gratuit.html', context)


def simulateur_avance(request):
    """
    Formulaire de simulation avancée (payante).
    """
    context = {
        'page': 'simulateur_avance',
    }
    return render(request, 'simulateur_avance.html', context)


def simulation_results(request, simulation_id):
    """
    Affichage des résultats d'une simulation.
    """
    # Récupérer la simulation
    simulation = get_object_or_404(Simulation, id=simulation_id)
    
    context = {
        'simulation': simulation,
        'installation': simulation.installation,
        'profil': simulation.profil_consommation,
    }
    return render(request, 'results.html', context)


def mentions_legales(request):
    """Page mentions légales."""
    return render(request, 'mentions_legales.html')


def cgv(request):
    """Page CGV."""
    return render(request, 'cgv.html')


def confidentialite(request):
    """Page politique de confidentialité."""
    return render(request, 'confidentialite.html')