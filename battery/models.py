from django.db import models
from frontend.models import Simulation  # ← Votre modèle existant

from .pricing import get_battery_price
from .services.sizing import recommend_battery_size

class BatterySystem(models.Model):
    """
    Système de stockage par batterie.
    """
    
    # Lien vers simulation
    installation = models.OneToOneField(
        'solar_calc.SolarInstallationModel',
        on_delete=models.CASCADE,
        related_name='battery'
    )
    
    # Caractéristiques techniques
    capacite_kwh = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        help_text="Capacité totale (kWh)"
    )
    
    capacite_utilisable_kwh = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        help_text="Capacité utilisable = capacite × 0.9"
    )
    
    puissance_max_kw = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        help_text="Puissance max charge/décharge (kW)"
    )
    
    efficacite = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=0.95,
        help_text="Rendement charge/décharge (0.90-0.98)"
    )
    
    # Durée de vie
    cycles_garantis = models.IntegerField(
        default=6000,
        help_text="Cycles garantis (6000 typique)"
    )
    
    dod_max = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=0.90,
        help_text="Depth of Discharge max (0.90)"
    )
    
    # Résultats simulation
    cycles_annuels = models.IntegerField(
        null=True,
        blank=True,
        help_text="Cycles/an calculés"
    )
    
    duree_vie_annees = models.IntegerField(
        null=True,
        blank=True,
        help_text="Durée de vie estimée"
    )
    
    autoconso_gain_pct = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Gain autoconso (%)"
    )
    
    # Financier
    cout_installation = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Coût batterie (€)"
    )
    
    economie_annuelle = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Économies annuelles (€)"
    )
    
    roi_annees = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="ROI (années)"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'battery_systems'
        verbose_name = 'Batterie'
        verbose_name_plural = 'Batteries'
    
    def __str__(self):
        return f"Batterie {self.capacite_kwh}kWh - Installation {self.installation.nom}"


    # NOUVELLE MÉTHODE SAVE
    def save(self, *args, **kwargs):
        """
        Surcharge save pour calculer automatiquement :
        - Prix réaliste selon marché France 2025
        - Capacité utilisable (90% de la capacité totale)
        """
        # 1. Calculer capacité utilisable si pas définie
        if not self.capacite_utilisable_kwh:
            self.capacite_utilisable_kwh = float(self.capacite_kwh) * 0.9
        
        # 2. Calculer prix réaliste si non fourni ou à 0
        if not self.cout_installation or self.cout_installation == 0:
            try:
                prix_data = get_battery_price(
                    float(self.capacite_kwh),
                    marque='standard'
                )
                self.cout_installation = prix_data['prix_total_ttc']
            except Exception as e:
                # Fallback : 750€/kWh (prix moyen marché)
                self.cout_installation = float(self.capacite_kwh) * 750
        
        super().save(*args, **kwargs)
    
    # MÉTHODES UTILITAIRES
    def get_market_price_breakdown(self):
        """Décomposition du prix marché"""
        return get_battery_price(float(self.capacite_kwh), marque='standard')
    
    def get_alternative_prices(self):
        """Prix des 3 gammes"""
        from .pricing import compare_battery_brands
        return compare_battery_brands(float(self.capacite_kwh))
    
    def calculate_roi(self):
        """Calcule le ROI"""
        if self.economie_annuelle and self.economie_annuelle > 0:
            roi = float(self.cout_installation) / float(self.economie_annuelle)
            self.roi_annees = round(roi, 2)
            return self.roi_annees
        return None
    
    def calculate_lifetime_cycles(self):
        """Calcule la durée de vie"""
        if self.cycles_annuels and self.cycles_annuels > 0:
            duree = self.cycles_garantis / self.cycles_annuels
            self.duree_vie_annees = round(duree)
            return self.duree_vie_annees
        return None

class BatteryLog(models.Model):
    """
    Log horaire (optionnel, pour analyse détaillée).
    """
    
    battery = models.ForeignKey(
        BatterySystem,
        on_delete=models.CASCADE,
        related_name='logs'
    )
    
    hour = models.IntegerField(help_text="Heure (0-8759)")
    soc_kwh = models.DecimalField(max_digits=6, decimal_places=3)
    soc_pct = models.DecimalField(max_digits=5, decimal_places=2)
    charge_kwh = models.DecimalField(max_digits=6, decimal_places=3)
    discharge_kwh = models.DecimalField(max_digits=6, decimal_places=3)
    
    class Meta:
        db_table = 'battery_logs'
        indexes = [
            models.Index(fields=['battery', 'hour']),
        ]