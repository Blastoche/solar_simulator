from django.contrib import admin
from .models import BatterySystem, BatteryLog


@admin.register(BatterySystem)
class BatterySystemAdmin(admin.ModelAdmin):
    list_display = [
        'installation',
        'capacite_kwh',
        'autoconso_gain_pct',
        'cycles_annuels',
        'duree_vie_annees',
        'roi_annees',
        'created_at'
    ]
    list_filter = ['created_at', 'duree_vie_annees']
    readonly_fields = [
        'cycles_annuels',
        'duree_vie_annees',
        'autoconso_gain_pct',
        'economie_annuelle',
        'roi_annees',
        'created_at',
        'updated_at'
    ]
    
    fieldsets = (
        ('Lien', {
            'fields': ('installation',)
        }),
        ('Caractéristiques', {
            'fields': (
                'capacite_kwh',
                'capacite_utilisable_kwh',
                'puissance_max_kw',
                'efficacite',
                'cycles_garantis',
                'dod_max'
            )
        }),
        ('Résultats', {
            'fields': (
                'cycles_annuels',
                'duree_vie_annees',
                'autoconso_gain_pct'
            )
        }),
        ('Financier', {
            'fields': (
                'cout_installation',
                'economie_annuelle',
                'roi_annees'
            )
        }),
    )


@admin.register(BatteryLog)
class BatteryLogAdmin(admin.ModelAdmin):
    list_display = ['battery', 'hour', 'soc_pct', 'charge_kwh', 'discharge_kwh']
    list_filter = ['battery']