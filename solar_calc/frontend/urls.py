"""
URLs pour l'application frontend.
"""

from django.urls import path
from . import views

urlpatterns = [
    # Page d'accueil
    path('', views.home, name='home'),
    
    # Simulateurs
    path('simulateur/gratuit/', views.simulateur_gratuit, name='simulateur_gratuit'),
    path('simulateur/avancé/', views.simulateur_avance, name='simulateur_avance'),
    
    # Résultats
    path('simulation/<int:simulation_id>/', views.simulation_results, name='simulation_results'),
    
    # Pages légales
    path('mentions-legales/', views.mentions_legales, name='mentions_legales'),
    path('cgv/', views.cgv, name='cgv'),
    path('confidentialite/', views.confidentialite, name='confidentialite'),
]