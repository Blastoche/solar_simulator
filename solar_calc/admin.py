"""
Configuration de l'interface d'administration Django pour solar_calc.
"""

# solar_calc/admin.py
from django.contrib import admin

# Modèles Django ORM
from frontend.models import Installation, Resultat, Simulation
from solar_calc.models import ConsumptionProfileModel, SimulationModel, SolarInstallationModel

# Dataclasses (si utilisées dans l’admin pour calculs ou affichages)
from .dataclasses import SolarInstallation, ConsumptionProfile


@admin.register(SolarInstallationModel)
class SolarInstallationAdmin(admin.ModelAdmin):
    """
    Interface admin pour les installations solaires.
    """
    list_display = [
        'nom',
        'user',
        'puissance_crete_kwc',
        'nombre_panneaux',
        'orientation_azimut',
        'inclinaison_degres',
        'latitude',
        'longitude',
        'created_at',
    ]
    list_filter = ['type_onduleur', 'created_at']
    search_fields = ['nom', 'user__username', 'adresse']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Informations générales', {
            'fields': ('user', 'nom')
        }),
        ('Géolocalisation', {
            'fields': ('latitude', 'longitude', 'altitude', 'adresse')
        }),
        ('Configuration panneaux', {
            'fields': (
                'nombre_panneaux',
                'puissance_panneau_wc',
                'orientation_azimut',
                'inclinaison_degres',
                'facteur_ombrage',
            )
        }),
        ('Onduleur', {
            'fields': ('type_onduleur', 'puissance_onduleur_kw')
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
        
    )
    
    def has_delete_permission(self, request, obj=None):
        """Empêcher la suppression accidentelle"""
        return request.user.is_superuser

    def puissance_crete_kwc(self, obj):
        """Affiche la puissance crête calculée."""
        return f"{obj.puissance_crete_kwc:.2f} kWc"
    puissance_crete_kwc.short_description = "Puissance crête"


@admin.register(ConsumptionProfileModel)
class ConsumptionProfileAdmin(admin.ModelAdmin):
    """
    Interface admin pour les profils de consommation.
    """
    list_display = [
        'nom',
        'user',
        'surface_habitable',
        'nb_personnes',
        'dpe',
        'consommation_annuelle_kwh',
        'created_at',
    ]
    list_filter = ['dpe', 'type_chauffage', 'type_ecs', 'created_at']
    search_fields = ['nom', 'user__username']
    readonly_fields = ['created_at', 'updated_at', 'consommation_annuelle_kwh']
    
    fieldsets = (
        ('Informations générales', {
            'fields': ('user', 'nom')
        }),
        ('Logement', {
            'fields': (
                'annee_construction',
                'surface_habitable',
                'nb_personnes',
                'dpe',
            )
        }),
        ('Systèmes énergétiques', {
            'fields': ('type_chauffage', 'type_ecs')
        }),
        ('Appareils', {
            'fields': ('appareils_json',),
            'classes': ('collapse',)
        }),
        ('Résultats', {
            'fields': ('consommation_annuelle_kwh',),
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(SimulationModel)
class SimulationAdmin(admin.ModelAdmin):
    """
    Interface admin pour les simulations.
    """
    list_display = [
        'id',
        'user',
        'installation',
        'production_annuelle_kwh',
        'consommation_annuelle_kwh',
        'taux_autoconsommation_pct',
        'economie_annuelle_estimee',
        'status',
        'created_at',
    ]
    list_filter = ['status', 'created_at']
    search_fields = ['user__username', 'installation__nom']
    readonly_fields = ['created_at', 'completed_at', 'economie_annuelle_estimee']
    
    fieldsets = (
        ('Configuration', {
            'fields': ('user', 'installation', 'profil_consommation')
        }),
        ('Production', {
            'fields': (
                'production_annuelle_kwh',
                'production_specifique_kwh_kwc',
            )
        }),
        ('Consommation', {
            'fields': ('consommation_annuelle_kwh',)
        }),
        ('Autoconsommation', {
            'fields': (
                'autoconsommation_kwh',
                'injection_reseau_kwh',
                'achat_reseau_kwh',
                'taux_autoconsommation_pct',
                'taux_autoproduction_pct',
            )
        }),
        ('Économies', {
            'fields': ('economie_annuelle_estimee',)
        }),
        ('Données', {
            'fields': ('donnees_horaires_url',),
            'classes': ('collapse',)
        }),
        ('Statut', {
            'fields': ('status', 'created_at', 'completed_at')
        }),
    )
    
    def economie_annuelle_estimee(self, obj):
        """Affiche l'économie estimée."""
        return f"{obj.economie_annuelle_estimee:.2f} €"
    economie_annuelle_estimee.short_description = "Économie annuelle"