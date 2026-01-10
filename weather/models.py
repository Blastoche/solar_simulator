"""
Modèles Django pour l'app weather.

Stockage des données météorologiques et cache des appels API.
"""

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
import json


class Location(models.Model):
    """
    Localisation pour les données météo.
    """
    latitude = models.FloatField(
        validators=[MinValueValidator(-90), MaxValueValidator(90)],
        verbose_name="Latitude"
    )
    longitude = models.FloatField(
        validators=[MinValueValidator(-180), MaxValueValidator(180)],
        verbose_name="Longitude"
    )
    altitude = models.FloatField(
        default=0,
        verbose_name="Altitude (m)"
    )
    nom = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        verbose_name="Nom du lieu"
    )
    
    # Métadonnées
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Localisation"
        verbose_name_plural = "Localisations"
        unique_together = ['latitude', 'longitude']
    
    def __str__(self):
        if self.nom:
            return f"{self.nom} ({self.latitude:.2f}, {self.longitude:.2f})"
        return f"({self.latitude:.2f}, {self.longitude:.2f})"
    
    def coordinates_str(self):
        """Retourne les coordonnées au format string pour PVGIS."""
        return f"{self.latitude:.4f},{self.longitude:.4f}"


class PVGISData(models.Model):
    """
    Données TMY (Typical Meteorological Year) depuis PVGIS.
    Cache des données pour éviter les appels répétés.
    """
    location = models.ForeignKey(
        Location,
        on_delete=models.CASCADE,
        related_name='pvgis_data'
    )
    
    # Paramètres de la requête
    database = models.CharField(
        max_length=50,
        default='PVGIS-SARAH2',
        verbose_name="Base de données PVGIS"
    )
    year_min = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="Année min"
    )
    year_max = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="Année max"
    )
    
    # Données brutes (JSON)
    raw_data = models.TextField(
        verbose_name="Données JSON brutes"
    )
    
    # Statistiques
    irradiation_annuelle_kwh_m2 = models.FloatField(
        null=True,
        blank=True,
        verbose_name="Irradiation annuelle (kWh/m²)"
    )
    temperature_moyenne_annuelle = models.FloatField(
        null=True,
        blank=True,
        verbose_name="Température moyenne (°C)"
    )
    
    # Cache
    is_valid = models.BooleanField(
        default=True,
        verbose_name="Cache valide"
    )
    
    # Métadonnées
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Date d'expiration du cache"
    )
    
    class Meta:
        verbose_name = "Données PVGIS"
        verbose_name_plural = "Données PVGIS"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"PVGIS - {self.location} ({self.created_at.strftime('%Y-%m-%d')})"
    
    def get_data_dict(self):
        """Retourne les données parsées en dict."""
        try:
            return json.loads(self.raw_data)
        except json.JSONDecodeError:
            return None


class WeatherData(models.Model):
    """
    Données météorologiques horaires.
    """
    location = models.ForeignKey(
        Location,
        on_delete=models.CASCADE,
        related_name='weather_data'
    )
    
    # Timestamp
    timestamp = models.DateTimeField(
        verbose_name="Date et heure",
        db_index=True
    )
    
    # Source des données
    source = models.CharField(
        max_length=50,
        choices=[
            ('pvgis', 'PVGIS'),
            ('openweather', 'OpenWeatherMap'),
            ('solcast', 'Solcast'),
            ('manual', 'Manuel'),
        ],
        default='pvgis',
        verbose_name="Source"
    )
    
    # Données d'irradiation (W/m²)
    ghi = models.FloatField(
        null=True,
        blank=True,
        verbose_name="GHI - Global Horizontal Irradiance (W/m²)"
    )
    dni = models.FloatField(
        null=True,
        blank=True,
        verbose_name="DNI - Direct Normal Irradiance (W/m²)"
    )
    dhi = models.FloatField(
        null=True,
        blank=True,
        verbose_name="DHI - Diffuse Horizontal Irradiance (W/m²)"
    )
    
    # Données météorologiques
    temperature = models.FloatField(
        null=True,
        blank=True,
        verbose_name="Température (°C)"
    )
    vitesse_vent = models.FloatField(
        null=True,
        blank=True,
        verbose_name="Vitesse du vent (m/s)"
    )
    humidite = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name="Humidité (%)"
    )
    pression = models.FloatField(
        null=True,
        blank=True,
        verbose_name="Pression (hPa)"
    )
    couverture_nuageuse = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name="Couverture nuageuse (%)"
    )
    
    # Métadonnées
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Donnée Météo"
        verbose_name_plural = "Données Météo"
        ordering = ['timestamp']
        unique_together = ['location', 'timestamp', 'source']
        indexes = [
            models.Index(fields=['location', 'timestamp']),
            models.Index(fields=['timestamp']),
        ]
    
    def __str__(self):
        return f"{self.location} - {self.timestamp.strftime('%Y-%m-%d %H:%M')} ({self.source})"


class APICache(models.Model):
    """
    Cache générique pour les appels API externes.
    """
    # Clé de cache
    cache_key = models.CharField(
        max_length=500,
        unique=True,
        verbose_name="Clé de cache",
        db_index=True
    )
    
    # Données
    data = models.TextField(
        verbose_name="Données JSON"
    )
    
    # Source
    api_source = models.CharField(
        max_length=50,
        choices=[
            ('pvgis', 'PVGIS'),
            ('openweather', 'OpenWeatherMap'),
            ('solcast', 'Solcast'),
        ],
        verbose_name="Source API"
    )
    
    # Cache management
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(
        verbose_name="Date d'expiration"
    )
    hit_count = models.IntegerField(
        default=0,
        verbose_name="Nombre d'accès"
    )
    
    class Meta:
        verbose_name = "Cache API"
        verbose_name_plural = "Caches API"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.api_source} - {self.cache_key[:50]}"
    
    def is_expired(self):
        """Vérifie si le cache est expiré."""
        from django.utils import timezone
        return timezone.now() > self.expires_at
    
    def get_data(self):
        """Retourne les données parsées."""
        try:
            return json.loads(self.data)
        except json.JSONDecodeError:
            return None
    
    def increment_hit(self):
        """Incrémente le compteur d'accès."""
        self.hit_count += 1
        self.save(update_fields=['hit_count'])