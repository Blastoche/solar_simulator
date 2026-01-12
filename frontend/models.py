# frontend/models.py
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import uuid

class Installation(models.Model):
    """Représente une installation solaire"""
    
    ORIENTATION_CHOICES = [
        ('N', 'Nord'),
        ('NE', 'Nord-Est'),
        ('E', 'Est'),
        ('SE', 'Sud-Est'),
        ('S', 'Sud'),
        ('SW', 'Sud-Ouest'),
        ('W', 'Ouest'),
        ('NW', 'Nord-Ouest'),
    ]
    
    ROOF_TYPE_CHOICES = [
        ('tuiles', 'Tuiles'),
        ('ardoise', 'Ardoise'),
        ('zinc', 'Zinc'),
        ('beton', 'Béton'),
        ('tole', 'Tôle'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='installations')
    
    # Localisation
    adresse = models.CharField(max_length=255)
    latitude = models.FloatField()
    longitude = models.FloatField()
    
    # Configuration technique
    puissance_kw = models.FloatField(help_text="Puissance en kWc")
    orientation = models.CharField(max_length=2, choices=ORIENTATION_CHOICES)
    inclinaison = models.IntegerField(help_text="Angle en degrés")
    type_toiture = models.CharField(max_length=50, choices=ROOF_TYPE_CHOICES)
    
    # Métadonnées
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.puissance_kw}kWc - {self.adresse}"
    
    class Meta:
        ordering = ['-created_at']


class Simulation(models.Model):
    """Représente une simulation de production solaire"""
    
    STATUS_CHOICES = [
        ('pending', '⏳ En attente'),
        ('running', '🔄 En cours'),
        ('success', '✅ Terminée'),
        ('failed', '❌ Erreur'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    installation = models.ForeignKey(Installation, on_delete=models.CASCADE, related_name='simulations')
    
    # Statut
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    task_id = models.CharField(max_length=255, blank=True, help_text="ID de la tâche Celery")
    error_message = models.TextField(blank=True)
    
    # Résultat (clé étrangère - created après simulation)
    resultat = models.OneToOneField('Resultat', on_delete=models.SET_NULL, null=True, blank=True, related_name='simulation')
    
    # Timing
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"Sim #{self.id} - {self.status}"
    
    @property
    def duration(self):
        """Durée d'exécution en secondes"""
        if self.completed_at and self.started_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None
    
    class Meta:
        ordering = ['-created_at']


class Resultat(models.Model):
    """Résultats d'une simulation"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Production
    production_annuelle_kwh = models.FloatField(help_text="kWh/an")
    production_mensuelle_kwh = models.JSONField(help_text="Données mensuelles")
    production_horaire_kwh = models.JSONField(help_text="Profil horaire moyen")
    
    # Consommation
    consommation_annuelle_kwh = models.FloatField(help_text="kWh/an")
    consommation_mensuelle_kwh = models.JSONField()
    consommation_horaire_kwh = models.JSONField()
    
    # Autoconsommation
    autoconsommation_ratio = models.FloatField(help_text="En %")
    injection_reseau_kwh = models.FloatField(help_text="kWh injectés annuellement")
    
    # Financier
    economie_annuelle_euros = models.FloatField(default=0)
    roi_25ans_euros = models.FloatField(default=0)
    taux_rentabilite_pct = models.FloatField(default=0)
    
    # Métadonnées
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Résultat {self.id}"
    
    class Meta:
        ordering = ['-created_at']
