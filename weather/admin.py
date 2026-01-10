"""
Configuration de l'interface d'administration Django pour weather.
"""

from django.contrib import admin
from .models import Location, PVGISData, WeatherData, APICache


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    """Interface admin pour les localisations."""
    list_display = ['nom', 'latitude', 'longitude', 'altitude', 'created_at']
    search_fields = ['nom', 'latitude', 'longitude']
    list_filter = ['created_at']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(PVGISData)
class PVGISDataAdmin(admin.ModelAdmin):
    """Interface admin pour les données PVGIS."""
    list_display = [
        'location',
        'database',
        'irradiation_annuelle_kwh_m2',
        'temperature_moyenne_annuelle',
        'is_valid',
        'created_at',
    ]
    list_filter = ['database', 'is_valid', 'created_at']
    search_fields = ['location__nom']
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('Localisation', {
            'fields': ('location',)
        }),
        ('Paramètres', {
            'fields': ('database', 'year_min', 'year_max')
        }),
        ('Statistiques', {
            'fields': ('irradiation_annuelle_kwh_m2', 'temperature_moyenne_annuelle')
        }),
        ('Cache', {
            'fields': ('is_valid', 'expires_at')
        }),
        ('Données brutes', {
            'fields': ('raw_data',),
            'classes': ('collapse',)
        }),
        ('Métadonnées', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )


@admin.register(WeatherData)
class WeatherDataAdmin(admin.ModelAdmin):
    """Interface admin pour les données météo horaires."""
    list_display = [
        'timestamp',
        'location',
        'source',
        'ghi',
        'temperature',
        'created_at',
    ]
    list_filter = ['source', 'timestamp', 'created_at']
    search_fields = ['location__nom']
    date_hierarchy = 'timestamp'
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('Informations', {
            'fields': ('location', 'timestamp', 'source')
        }),
        ('Irradiation', {
            'fields': ('ghi', 'dni', 'dhi')
        }),
        ('Météo', {
            'fields': ('temperature', 'vitesse_vent', 'humidite', 'pression', 'couverture_nuageuse')
        }),
    )


@admin.register(APICache)
class APICacheAdmin(admin.ModelAdmin):
    """Interface admin pour le cache API."""
    list_display = [
        'cache_key_short',
        'api_source',
        'hit_count',
        'created_at',
        'expires_at',
        'is_expired_status',
    ]
    list_filter = ['api_source', 'created_at']
    search_fields = ['cache_key']
    readonly_fields = ['created_at', 'hit_count']
    
    def cache_key_short(self, obj):
        """Affiche une version courte de la clé."""
        return obj.cache_key[:50] + '...' if len(obj.cache_key) > 50 else obj.cache_key
    cache_key_short.short_description = "Clé de cache"
    
    def is_expired_status(self, obj):
        """Affiche le statut d'expiration."""
        return "Expiré" if obj.is_expired() else "Valide"
    is_expired_status.short_description = "Statut"