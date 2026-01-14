# frontend/admin.py
"""
Configuration de l'interface d'administration Django pour l'application frontend.
Version minimaliste compatible.
"""

from django.contrib import admin
from .models import (
    Installation,
    Simulation,
    Resultat,
    AppareillectriqueCategory,
    AppareilElectrique,
    ConsommationCalculee,
    AppareilUtilisateur,
)


# ============================================================================
# ADMIN MODÈLES PRINCIPAUX (Simulation Solaire)
# ============================================================================

@admin.register(Installation)
class InstallationAdmin(admin.ModelAdmin):
    """Administration des installations solaires"""
    list_display = ['id', 'adresse', 'puissance_kw', 'orientation']
    search_fields = ['adresse', 'id']
    list_filter = ['orientation']


@admin.register(Simulation)
class SimulationAdmin(admin.ModelAdmin):
    """Administration des simulations"""
    list_display = ['id', 'installation', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['id']
    date_hierarchy = 'created_at'


@admin.register(Resultat)
class ResultatAdmin(admin.ModelAdmin):
    """Administration des résultats de simulation"""
    list_display = ['simulation', 'production_annuelle_kwh', 'consommation_annuelle_kwh']
    search_fields = ['simulation__id']


# ============================================================================
# ADMIN CALCULATEUR DE CONSOMMATION
# ============================================================================

@admin.register(AppareillectriqueCategory)
class AppareillectriqueCategoryAdmin(admin.ModelAdmin):
    """Administration des catégories d'appareils"""
    list_display = ['icon', 'nom', 'ordre', 'pourcentage_moyen', 'nb_appareils']
    list_editable = ['ordre']
    ordering = ['ordre', 'nom']
    prepopulated_fields = {'slug': ('nom',)}
    
    def nb_appareils(self, obj):
        """Nombre d'appareils dans cette catégorie"""
        return obj.appareils.count()
    nb_appareils.short_description = 'Nb appareils'


@admin.register(AppareilElectrique)
class AppareilElectriqueAdmin(admin.ModelAdmin):
    """Administration des appareils électriques"""
    list_display = [
        'nom',
        'category',
        'puissance_nominale_w',
        'consommation_annuelle_kwh',
        'mode_rapide',
        'actif'
    ]
    list_filter = ['category', 'mode_rapide', 'actif']
    search_fields = ['nom', 'description']
    list_editable = ['actif']
    ordering = ['category__ordre', 'ordre', 'nom']
    prepopulated_fields = {'slug': ('nom',)}
    
    fieldsets = (
        ('Informations générales', {
            'fields': ('category', 'nom', 'slug', 'description', 'ordre', 'actif')
        }),
        ('Caractéristiques électriques', {
            'fields': ('puissance_nominale_w', 'puissance_veille_w', 'consommation_annuelle_kwh')
        }),
        ('Usage typique', {
            'fields': ('heures_jour_defaut', 'jours_semaine_defaut', 'variations_mensuelles')
        }),
        ('Affichage', {
            'fields': ('mode_rapide', 'mode_expert')
        }),
    )
    
    readonly_fields = ['consommation_annuelle_kwh']


@admin.register(ConsommationCalculee)
class ConsommationCalculeeAdmin(admin.ModelAdmin):
    """Administration des consommations calculées"""
    list_display = [
        'id',
        'created_at',
        'nb_personnes',
        'surface_habitable',
        'dpe',
        'consommation_annuelle_totale',
        'mode_calcul'
    ]
    list_filter = ['dpe', 'zone_climatique', 'type_chauffage', 'mode_calcul', 'created_at']
    search_fields = ['id']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    
    fieldsets = (
        ('Logement', {
            'fields': ('surface_habitable', 'nb_personnes', 'dpe', 'annee_construction')
        }),
        ('Localisation', {
            'fields': ('latitude', 'longitude', 'zone_climatique')
        }),
        ('Chauffage', {
            'fields': ('type_chauffage', 'temperature_consigne', 'type_vmc')
        }),
        ('ECS', {
            'fields': ('type_ecs', 'capacite_ecs_litres')
        }),
        ('Résultats', {
            'fields': (
                'consommation_annuelle_totale',
                'consommation_moyenne_attendue',
                'ecart_pourcentage'
            )
        }),
    )
    
    readonly_fields = ['created_at', 'zone_climatique']


@admin.register(AppareilUtilisateur)
class AppareilUtilisateurAdmin(admin.ModelAdmin):
    """Administration des appareils utilisateur"""
    list_display = [
        'appareil',
        'consommation',
        'quantite',
        'consommation_annuelle_kwh'
    ]
    list_filter = ['appareil__category']
    search_fields = ['appareil__nom']
    
    readonly_fields = ['consommation_annuelle_kwh']