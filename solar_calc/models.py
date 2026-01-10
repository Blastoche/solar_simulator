"""
Modèles Django pour l'app solar_calc

Ces modèles Django (ORM) stockent les données en base de données.
Les modèles de calcul (dataclasses) sont dans solar_calc/models/
"""

from django.db import models
from django.contrib.auth import get_user_model
User = get_user_model()
from django.core.validators import MinValueValidator, MaxValueValidator
import json


class SolarInstallationModel(models.Model):
    """
    Configuration d'une installation solaire (stockage en base de données).
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='installations')
    nom = models.CharField(max_length=200, verbose_name="Nom de l'installation")
    
    # Géolocalisation
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
        verbose_name="Orientation (azimut en degrés)"
    )
    inclinaison_degres = models.FloatField(
        validators=[MinValueValidator(0), MaxValueValidator(90)],
        default=30,
        verbose_name="Inclinaison (degrés)"
    )
    facteur_ombrage = models.FloatField(
        validators=[MinValueValidator(0), MaxValueValidator(1)],
        default=1.0,
        verbose_name="Facteur d'ombrage (0-1)"
    )
    class Meta:
        verbose_name = "Installation solaire"
        verbose_name_plural = "Installations solaires"

    @property
    def puissance_crete_kwc(self):
        return self.nombre_panneaux * self.puissance_panneau_wc / 1000
    
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
    
    # Métadonnées
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
        """Puissance crête totale en kWc."""
        return (self.nombre_panneaux * self.puissance_panneau_wc) / 1000


class ConsumptionProfileModel(models.Model):
    """
    Profil de consommation électrique d'un logement.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='consumption_profiles')
    nom = models.CharField(max_length=200, verbose_name="Nom du profil")
    
    # Logement
    annee_construction = models.IntegerField(
        validators=[MinValueValidator(1800), MaxValueValidator(2030)],
        verbose_name="Année de construction"
    )
    surface_habitable = models.FloatField(
        validators=[MinValueValidator(10)],
        verbose_name="Surface habitable (m²)"
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
    class Meta:
        verbose_name = "Profil de consommation"
        verbose_name_plural = "Profils de consommation"

    # Systèmes énergétiques
    type_chauffage = models.CharField(
        max_length=50,
        choices=[
            ('non_electrique', 'Non électrique'),
            ('electrique', 'Électrique'),
            ('pompe_a_chaleur', 'Pompe à chaleur'),
        ],
        default='non_electrique',
        verbose_name="Type de chauffage"
    )
    type_ecs = models.CharField(
        max_length=50,
        choices=[
            ('non_electrique', 'Non électrique'),
            ('electrique', 'Électrique'),
            ('thermodynamique', 'Thermodynamique'),
        ],
        default='non_electrique',
        verbose_name="Type ECS"
    )
    
    # Appareils (stockage JSON simple)
    appareils_json = models.TextField(
        blank=True,
        null=True,
        verbose_name="Configuration des appareils (JSON)"
    )
    
    # Consommation calculée
    consommation_annuelle_kwh = models.FloatField(
        null=True,
        blank=True,
        verbose_name="Consommation annuelle (kWh)"
    )
    
    # Métadonnées
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
    Résultat d'une simulation complète (production + consommation).
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
    
    # Résultats de production
    production_annuelle_kwh = models.FloatField(
        verbose_name="Production annuelle (kWh)"
    )
    production_specifique_kwh_kwc = models.FloatField(
        verbose_name="Production spécifique (kWh/kWc/an)"
    )
    
    # Résultats de consommation
    consommation_annuelle_kwh = models.FloatField(
        verbose_name="Consommation annuelle (kWh)"
    )
    
    # Résultats d'autoconsommation
    autoconsommation_kwh = models.FloatField(
        verbose_name="Autoconsommation (kWh)"
    )
    injection_reseau_kwh = models.FloatField(
        verbose_name="Injection réseau (kWh)"
    )
    achat_reseau_kwh = models.FloatField(
        verbose_name="Achat réseau (kWh)"
    )
    taux_autoconsommation_pct = models.FloatField(
        verbose_name="Taux d'autoconsommation (%)"
    )
    taux_autoproduction_pct = models.FloatField(
        verbose_name="Taux d'autoproduction (%)"
    )
    
    # Données horaires (stockage JSON compressé ou fichier)
    donnees_horaires_url = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name="URL des données horaires"
    )
    
    # Statut
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'En attente'),
            ('running', 'En cours'),
            ('completed', 'Terminée'),
            ('failed', 'Échouée'),
        ],
        default='pending',
        verbose_name="Statut"
    )
    
    # Métadonnées
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Simulation"
        verbose_name_plural = "Simulations"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Simulation {self.id} - {self.installation.nom} ({self.status})"
    
    @property
    def economie_annuelle_estimee(self):
        """
        Économie annuelle estimée (simplifié).
        Tarif moyen : 0.2276 €/kWh
        """
        tarif_moyen = 0.2276
        economie = (
            self.autoconsommation_kwh * tarif_moyen +
            self.injection_reseau_kwh * 0.13  # Tarif vente surplus
        )
        return round(economie, 2)