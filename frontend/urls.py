"""
URLs pour l'application frontend.
"""

# frontend/urls.py
from django.urls import path
from . import views

app_name = 'frontend'

urlpatterns = [
    # Pages statiques
    path('', views.HomeView.as_view(), name='home'),
    path('mentions/', views.MentionsView.as_view(), name='mentions'),
    path('cgv/', views.CGVView.as_view(), name='cgv'),
    path('confidentialite/', views.PrivacyView.as_view(), name='privacy'),
    
    # Simulation
    path('simulation/', views.SimulationFormView.as_view(), name='simulation_create'),
    path('simulation/<uuid:simulation_id>/progression/', 
         views.SimulationProgressView.as_view(), 
         name='simulation_progress'),
    path('simulation/<uuid:simulation_id>/resultats/', 
         views.SimulationResultsView.as_view(), 
         name='simulation_results'),
    
    # API HTMX
    path('api/progression/<str:task_id>/', 
         views.simulation_progress_api, 
         name='simulation_progress_api'),
    
    # Exports
    path('simulation/<uuid:simulation_id>/pdf/', 
         views.simulation_pdf_download, 
         name='simulation_pdf_download'),
    path('simulation/<uuid:simulation_id>/excel/', 
         views.simulation_excel_download, 
         name='simulation_excel_download'),
    
    # Simulateur avancé (futur)
    path('simulateur-avance/', 
         views.SimulateurAvanceView.as_view(), 
         name='simulateur_avance'),

     # Calculateur de consommation
     path('consommation/calculateur/', 
          views.ConsumptionCalculatorView.as_view(), 
          name='consumption_calculator'),
     path('consommation/calculer/', 
          views.consumption_calculate, 
          name='consumption_calculate'),
     path('consommation/<int:consommation_id>/resultat/', 
     views.ConsumptionResultView.as_view(), 
     name='consumption_result'),
path('consommation/<int:consommation_id>/details/', 
     views.ConsumptionDetailsView.as_view(), 
     name='consumption_details'),

     # === MODE EXPERT ===
    path('consommation/expert/calculateur/', views.consumption_calculator_expert, name='consumption_calculator_expert'),
    path('consommation/expert/calculer/', views.consumption_calculate_expert, name='consumption_calculate_expert'),
    path('consommation/expert/<int:consommation_id>/resultat/', views.ConsumptionExpertResultView.as_view(), name='consumption_result_expert'),
    path('consommation/expert/<int:consommation_id>/details/', views.ConsumptionExpertDetailsView.as_view(), name='consumption_expert_details'),
]
