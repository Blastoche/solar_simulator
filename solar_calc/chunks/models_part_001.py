"""
ModÃ¨les Django pour l'app solar_calc

Ces modÃ¨les Django (ORM) stockent les donnÃ©es en base de donnÃ©es.
Les modÃ¨les de calcul (dataclasses) sont dans solar_calc/models/
"""

from django.db import models
from django.contrib.auth import get_user_model
User = get_user_model()
from django.core.validators import MinValueValidator, MaxValueValidator
import json


class SolarInstallationModel(models.Model):
    """
    Configuration d'une installation solaire (stockage en base de donnÃ©es).
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='solar_installations')
    nom = models.CharField(max_length=200, verbose_name="Nom de l'installation")
    
    # GÃ©olocalisation
    latitude = models.FloatField(
        validators=[MinValueValidator(-90), MaxValueValidator(90)],
        verbose_name="Latitude"
    )
    longitude = models.FloatField(
        validators=[MinValueValidator(-180), MaxValueValidator(180)],
        verbose_name="Longitude"
    )
    altitude = models.FloatField(default=0, verbose_name="Altitude (m)")
    adresse = models.TextField(blank=True, null=True, verbose_name="Adresse")
    
    # Configuration panneaux
    nombre_panneaux = models.IntegerField(
        validators=[MinValueValidator(1)],
        verbose_name="Nombre de panneaux"
    )
    puissance_panneau_wc = models.FloatField(
        default=500,
        verbose_name="Puissance par panneau (Wc)"
    )
    orientation_azimut = models.FloatField(
        validators=[MinValueValidator(0), MaxValueValidator(360)],
        default=180,
        verbose_name="Orientation (azimut en degrÃ©s)"
    )
    inclinaison_degres = models.FloatField(
        validators=[MinValueValidator(0), MaxValueValidator(90)],
        default=30,
        verbose_name="Inclinaison (degrÃ©s)"
    )
    facteur_ombrage = models.FloatField(
        validators=[MinValueValidator(0), MaxValueValidator(1)],
        default=1.0,
        verbose_name="Facteur d'ombrage (0-1)"
    )
    
    # Onduleur
    type_onduleur = models.CharField(
        max_length=50,
        choices=[
            ('central', 'Onduleur central'),
            ('micro_onduleur', 'Micro-onduleurs'),
            ('optimiseurs', 'Onduleur + optimiseurs'),
        ],
        default='central',
        verbose_name="Type d'onduleur"
    )
    puissance_onduleur_kw = models.FloatField(
        validators=[MinValueValidator(0.5)],
        verbose_name="Puissance onduleur (kW)"
    )
    
    # MÃ©tadonnÃ©es
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Installation Solaire"
        verbose_name_plural = "Installations Solaires"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.nom} ({self.puissance_crete_kwc:.2f} kWc)"
    
    @property
    def puissance_crete_kwc(self):
        """Puissance crÃªte totale en kWc."""
        return (self.nombre_panneaux * self.puissance_panneau_wc) / 1000


class ConsumptionProfileModel(models.Model):
    """
    Profil de consommation Ã©lectrique d'un logement.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='consumption_profiles')
    nom = models.CharField(max_length=200, verbose_name="Nom du profil")
    
    # Logement
    annee_construction = models.IntegerField(
        validators=[MinValueValidator(1800), MaxValueValidator(2030)],
        verbose_name="AnnÃ©e de construction"
    )
    surface_habitable = models.FloatField(
        validators=[MinValueValidator(10)],
        verbose_name="Surface habitable (mÂ²)"
    )
    nb_personnes = models.IntegerField(
        validators=[MinValueValidator(1)],
        verbose_name="Nombre de personnes"
    )
    dpe = models.CharField(
        max_length=1,
        choices=[('A', 'A'), ('B', 'B'), ('C', 'C'), ('D', 'D'), 
                 ('E', 'E'), ('F', 'F'), ('G', 'G')],
        default='C',
        verbose_name="DPE"
    )
    
    # SystÃ¨mes Ã©nergÃ©tiques
    type_chauffage = models.CharField(
        max_length=50,
        choices=[
            ('non_electrique', 'Non Ã©lectrique'),
            ('electrique', 'Ã‰lectrique'),
            ('pompe_a_chaleur', 'Pompe Ã  chaleur'),
        ],
        default='non_electrique',
        verbose_name="Type de chauffage"
    )
    type_ecs = models.CharField(
        max_length=50,
        choices=[
            ('non_electrique', 'Non Ã©lectrique'),
            ('electrique', 'Ã‰lectrique'),
            ('thermodynamique', 'Thermodynamique'),
        ],
        default='non_electrique',
        verbose_name="Type ECS"
    )
    
    # Profil d'occupation
    profile_type = models.CharField(
        max_length=20,
        choices=[
            ('actif_absent', 'Actif absent en journÃ©e (travail externe)'),
            ('teletravail', 'TÃ©lÃ©travail / PrÃ©sence en journÃ©e'),
            ('retraite', 'RetraitÃ© (prÃ©sent toute la journÃ©e)'),
            ('famille', 'Famille avec enfants'),
        ],
        default='actif_absent',
        verbose_name="Type de profil d'occupation",
        help_text="DÃ©finit le pattern de consommation selon le mode de vie"
    )
    
    # Appareils (stockage JSON simple)
    appareils_json = models.TextField(
        blank=True,
        null=True,
        verbose_name="Configuration des appareils (JSON)"
    )
    
    # Consommation calculÃ©e
    consommation_annuelle_kwh = models.FloatField(
        null=True,
        blank=True,
        verbose_name="Consommation annuelle (kWh)"
    )
    
    # MÃ©tadonnÃ©es
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Profil de Consommation"
        verbose_name_plural = "Profils de Consommation"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.nom} ({self.consommation_annuelle_kwh or 0:.0f} kWh/an)"


class SimulationModel(models.Model):
    """
    RÃ©sultat d'une simulation complÃ¨te (production + consommation).
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='simulations')
    installation = models.ForeignKey(
        SolarInstallationModel,
        on_delete=models.CASCADE,
        related_name='simulations'
    )
    profil_consommation = models.ForeignKey(
        ConsumptionProfileModel,
        on_delete=models.CASCADE,
        related_name='simulations'
    )
    
    # RÃ©sultats de production
