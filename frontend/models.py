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
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='frontend_installations')
    
    # Localisation
    adresse = models.CharField(max_length=255)
    latitude = models.FloatField()
    longitude = models.FloatField()
    
    # Configuration technique
    puissance_kw = models.FloatField(help_text="Puissance en kWc")
    orientation = models.CharField(max_length=2, choices=ORIENTATION_CHOICES)
    inclinaison = models.IntegerField(help_text="Angle en degrés")
    type_toiture = models.CharField(max_length=50, choices=ROOF_TYPE_CHOICES)
    
    # Lien avec l'analyse de consommation (optionnel)
    consommation_source = models.ForeignKey(
        'ConsommationCalculee',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='installations_generees',
        verbose_name="Analyse de consommation source"
    )

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

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
import json


class AppareillectriqueCategory(models.Model):
    """Catégories d'appareils électriques"""
    
    nom = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    ordre = models.IntegerField(default=0, help_text="Ordre d'affichage")
    icon = models.CharField(max_length=50, default='⚡', help_text="Emoji ou icône")
    description = models.TextField(blank=True)
    
    # Pourcentage typique de la consommation totale
    pourcentage_moyen = models.FloatField(
        default=10.0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="% moyen de la consommation totale"
    )
    
    class Meta:
        verbose_name = "Catégorie d'appareil"
        verbose_name_plural = "Catégories d'appareils"
        ordering = ['ordre', 'nom']
    
    def __str__(self):
        return f"{self.icon} {self.nom}"


class AppareilElectrique(models.Model):
    """Base de données des appareils électriques avec leurs caractéristiques de consommation"""
    
    category = models.ForeignKey(
        AppareillectriqueCategory,
        on_delete=models.CASCADE,
        related_name='appareils'
    )
    
    nom = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200)
    description = models.TextField(blank=True)
    
    # Caractéristiques électriques
    puissance_nominale_w = models.IntegerField(
        help_text="Puissance nominale en Watts"
    )
    puissance_veille_w = models.IntegerField(
        default=0,
        help_text="Puissance en veille (W)"
    )
    
    # Usage typique
    heures_jour_defaut = models.FloatField(
        default=1.0,
        validators=[MinValueValidator(0), MaxValueValidator(24)],
        help_text="Heures d'utilisation par jour (moyenne)"
    )
    jours_semaine_defaut = models.IntegerField(
        default=7,
        validators=[MinValueValidator(1), MaxValueValidator(7)],
        help_text="Jours d'utilisation par semaine"
    )
    
    # Saisonnalité (JSON : {1: 1.0, 2: 1.0, ..., 12: 1.0})
    # 1.0 = normal, 1.5 = +50%, 0.5 = -50%, 0.0 = pas utilisé
    variations_mensuelles = models.JSONField(
        default=dict,
        blank=True,
        help_text="Facteurs multiplicateurs par mois (1-12)"
    )
    
    # Consommation annuelle calculée (kWh/an)
    consommation_annuelle_kwh = models.FloatField(
        editable=False,
        help_text="Consommation annuelle calculée automatiquement"
    )
    
    # Questions personnalisées (JSON)
    # [
    #   {
    #     "field": "capacite",
    #     "label": "Capacité (litres)",
    #     "type": "number",
    #     "default": 200,
    #     "min": 50,
    #     "max": 500
    #   }
    # ]
    questions_personnalisees = models.JSONField(
        default=list,
        blank=True,
        help_text="Questions spécifiques pour cet appareil"
    )
    
    # Formule de calcul personnalisée (optionnel)
    # Ex: "puissance * heures * (capacite / 100) * 365"
    formule_calcul = models.TextField(
        blank=True,
        help_text="Formule Python pour calcul personnalisé (optionnel)"
    )
    
    # Modes d'affichage
    mode_rapide = models.BooleanField(
        default=True,
        help_text="Apparaît dans le mode rapide"
    )
    mode_expert = models.BooleanField(
        default=True,
        help_text="Apparaît dans le mode expert"
    )
    
    # Métadonnées
    ordre = models.IntegerField(default=0)
    actif = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Appareil électrique"
        verbose_name_plural = "Appareils électriques"
        ordering = ['category__ordre', 'ordre', 'nom']
        unique_together = [['category', 'slug']]
    
    def __str__(self):
        return f"{self.nom} ({self.category.nom})"
    
    def save(self, *args, **kwargs):
        """Calcule la consommation annuelle avant sauvegarde"""
        if not self.variations_mensuelles:
            # Par défaut : uniforme toute l'année
            self.variations_mensuelles = {str(i): 1.0 for i in range(1, 13)}
        
        # Calcul simple si pas de formule personnalisée
        if not self.formule_calcul:
            heures_annuelles = (
                self.heures_jour_defaut *
                (self.jours_semaine_defaut / 7) *
                365
            )
            
            # Moyenne des variations mensuelles
            avg_variation = sum(self.variations_mensuelles.values()) / 12
            
            # Consommation annuelle (kWh)
            self.consommation_annuelle_kwh = (
                self.puissance_nominale_w / 1000 *  # W → kW
                heures_annuelles *
                avg_variation
            )
        
        super().save(*args, **kwargs)
    
    def get_consommation_mensuelle(self):
        """Retourne la consommation pour chaque mois (liste de 12 valeurs)"""
        heures_mensuelles = (
            self.heures_jour_defaut *
            (self.jours_semaine_defaut / 7) *
            30.42  # Moyenne jours/mois
        )
        
        consommation_base_mensuelle = (
            self.puissance_nominale_w / 1000 * heures_mensuelles
        )
        
        monthly = []
        for mois in range(1, 13):
            facteur = self.variations_mensuelles.get(str(mois), 1.0)
            monthly.append(round(consommation_base_mensuelle * facteur, 2))
        
        return monthly


class ConsommationCalculee(models.Model):
    """Résultat du calcul de consommation électrique d'un foyer"""
    
    # Lien avec la simulation (optionnel)
    simulation = models.OneToOneField(
        'Simulation',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='consommation_calculee'
    )
    
    # Paramètres du logement
    surface_habitable = models.FloatField(
        validators=[MinValueValidator(10), MaxValueValidator(1000)],
        help_text="Surface habitable en m²"
    )
    nb_personnes = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(15)],
        help_text="Nombre de personnes dans le foyer"
    )
    
    DPE_CHOICES = [
        ('A', 'A - Très performant (< 50 kWh/m²/an)'),
        ('B', 'B - Performant (50-90 kWh/m²/an)'),
        ('C', 'C - Assez performant (91-150 kWh/m²/an)'),
        ('D', 'D - Moyen (151-230 kWh/m²/an)'),
        ('E', 'E - Médiocre (231-330 kWh/m²/an)'),
        ('F', 'F - Énergivore (331-450 kWh/m²/an)'),
        ('G', 'G - Très énergivore (> 450 kWh/m²/an)'),
    ]
    dpe = models.CharField(
        max_length=1,
        choices=DPE_CHOICES,
        help_text="Étiquette DPE du logement"
    )
    
    annee_construction = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1800), MaxValueValidator(2030)],
        help_text="Année de construction du logement"
    )
    
    # Chauffage
    TYPE_CHAUFFAGE_CHOICES = [
        ('electrique', 'Électrique (convecteurs, radiateurs)'),
        ('pac', 'Pompe à chaleur (PAC)'),
        ('gaz', 'Gaz'),
        ('fioul', 'Fioul'),
        ('bois', 'Bois / Granulés'),
        ('autre', 'Autre'),
    ]
    type_chauffage = models.CharField(
        max_length=50,
        choices=TYPE_CHAUFFAGE_CHOICES,
        default='electrique'
    )
    
    temperature_consigne = models.FloatField(
        default=19.0,
        validators=[MinValueValidator(15), MaxValueValidator(25)],
        help_text="Température de chauffage souhaitée (°C)"
    )
    
    TYPE_VMC_CHOICES = [
        ('simple_flux', 'VMC Simple flux'),
        ('double_flux', 'VMC Double flux'),
        ('naturelle', 'Ventilation naturelle'),
        ('aucune', 'Aucune / Je ne sais pas'),
    ]
    type_vmc = models.CharField(
        max_length=50,
        choices=TYPE_VMC_CHOICES,
        default='aucune',
        blank=True
    )
    
    # ECS (Eau Chaude Sanitaire)
    TYPE_ECS_CHOICES = [
        ('ballon_electrique', 'Ballon électrique (cumulus)'),
        ('thermodynamique', 'Chauffe-eau thermodynamique'),
        ('gaz', 'Chauffe-eau gaz'),
        ('solaire', 'Chauffe-eau solaire'),
        ('autre', 'Autre'),
    ]
    type_ecs = models.CharField(
        max_length=50,
        choices=TYPE_ECS_CHOICES,
        default='ballon_electrique'
    )
    
    capacite_ecs_litres = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(30), MaxValueValidator(500)],
        help_text="Capacité du ballon d'eau chaude (litres)"
    )

    # Cuisson
    TYPE_CUISSON_CHOICES = [
        ('induction', 'Induction'),
        ('vitroceramique', 'Vitrocéramique'),
        ('gaz', 'Gaz'),
        ('mixte', 'Mixte'),
    ]
    type_cuisson = models.CharField(
        max_length=50,
        choices=TYPE_CUISSON_CHOICES,
        blank=True,
        default='',
        help_text="Type de plaque de cuisson"
    )
    
    # Contrat électrique
    PUISSANCE_CHOICES = [
        ('3kVA', '3 kVA'),
        ('6kVA', '6 kVA'),
        ('9kVA', '9 kVA'),
        ('12kVA', '12 kVA'),
        ('15kVA', '15 kVA'),
        ('18kVA', '18 kVA'),
        ('24kVA', '24 kVA'),
        ('30kVA', '30 kVA'),
        ('36kVA', '36 kVA'),
    ]
    puissance_compteur = models.CharField(
        max_length=10,
        choices=PUISSANCE_CHOICES,
        blank=True,
        default='',
        help_text="Puissance souscrite du compteur"
    )
    
    TYPE_CONTRAT_CHOICES = [
        ('base', 'Base'),
        ('hphc', 'Heures Pleines / Heures Creuses'),
        ('tempo', 'Tempo'),
    ]
    type_contrat = models.CharField(
        max_length=20,
        choices=TYPE_CONTRAT_CHOICES,
        blank=True,
        default='base',
        help_text="Type de contrat électrique"
    )

    
    # Localisation (pour zone climatique)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    zone_climatique = models.CharField(
        max_length=2,
        choices=[('H1', 'H1 - Nord'), ('H2', 'H2 - Centre'), ('H3', 'H3 - Sud')],
        default='H2'
    )
    
    # Mode de calcul
    MODE_CHOICES = [
        ('rapide', 'Mode Rapide'),
        ('expert', 'Mode Expert'),
    ]
    mode_calcul = models.CharField(
        max_length=20,
        choices=MODE_CHOICES,
        default='rapide'
    )
    
    # Résultats globaux
    consommation_annuelle_totale = models.FloatField(
        help_text="Consommation totale calculée (kWh/an)"
    )
    consommation_moyenne_attendue = models.FloatField(
        help_text="Consommation moyenne pour ce profil (kWh/an)"
    )
    ecart_pourcentage = models.FloatField(
        help_text="Écart par rapport à la moyenne (%)"
    )
    
    # Répartition par poste (JSON)
    # {
    #   "chauffage": {"kwh": 8500, "pourcentage": 45.2},
    #   "ecs": {"kwh": 2500, "pourcentage": 13.3},
    #   "cuisson": {"kwh": 800, "pourcentage": 4.2},
    #   ...
    # }
    repartition_postes = models.JSONField(
        default=dict,
        help_text="Répartition de la consommation par poste"
    )
    
    # Consommation mensuelle (JSON - 12 valeurs en kWh)
    # [450, 520, 380, 320, 280, 250, 240, 250, 290, 350, 410, 480]
    consommation_mensuelle = models.JSONField(
        default=list,
        help_text="Consommation mensuelle (12 valeurs)"
    )
    
    # Métadonnées
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Consommation calculée"
        verbose_name_plural = "Consommations calculées"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Consommation : {self.consommation_annuelle_totale:.0f} kWh/an ({self.nb_personnes} pers, {self.surface_habitable}m²)"
    
    def get_message_comparaison(self):
        """Retourne un message de comparaison à la moyenne"""
        ecart = self.ecart_pourcentage
        
        if ecart > 20:
            emoji = "⚠️"
            niveau = "très supérieure"
            conseil = "Des économies importantes sont possibles !"
        elif ecart > 10:
            emoji = "ℹ️"
            niveau = "supérieure"
            conseil = "Quelques optimisations sont envisageables."
        elif ecart > -10:
            emoji = "✅"
            niveau = "dans la moyenne"
            conseil = "Votre consommation est conforme aux attentes."
        elif ecart > -20:
            emoji = "🌟"
            niveau = "inférieure"
            conseil = "Bonne maîtrise de votre consommation !"
        else:
            emoji = "🏆"
            niveau = "très inférieure"
            conseil = "Consommation exemplaire !"
        
        return {
            'emoji': emoji,
            'niveau': niveau,
            'conseil': conseil,
            'ecart': abs(ecart)
        }
    
    # === NOUVEAUX CHAMPS MODE EXPERT ===
    
    # Profil d'usage
    profil_usage = models.CharField(
        max_length=30,
        blank=True,
        choices=[
            ('actif_absent', 'Actif absent (travail)'),
            ('teletravail_partiel', 'Télétravail partiel'),
            ('teletravail_complet', 'Télétravail complet'),
            ('retraite', 'Retraité / Présent journée'),
        ],
        help_text="Profil d'occupation du logement"
    )
    heure_lever = models.IntegerField(
        null=True,
        blank=True,
        help_text="Heure de lever (0-23)"
    )
    heure_coucher = models.IntegerField(
        null=True,
        blank=True,
        help_text="Heure de coucher (0-23)"
    )
    
    # Optimisation HP/HC
    pct_hc_actuel = models.FloatField(
        null=True,
        blank=True,
        help_text="% actuel de consommation en heures creuses"
    )
    pct_hc_optimal = models.FloatField(
        null=True,
        blank=True,
        help_text="% optimal possible avec programmation"
    )
    economie_optimisation_hphc = models.FloatField(
        null=True,
        blank=True,
        help_text="Économie annuelle possible en € avec optimisation HP/HC"
    )
    
    # Projection long terme
    projection_10ans = models.JSONField(
        default=dict,
        blank=True,
        help_text="Projection consommation et coûts sur 10 ans"
    )
    
    # Recommandations
    recommandations = models.JSONField(
        default=list,
        blank=True,
        help_text="Liste des recommandations d'optimisation"
    )

class AppareilConsommation(models.Model):
    """
    Modèle pour stocker les appareils électriques détaillés (mode expert).
    Chaque appareil est lié à une ConsommationCalculee.
    """
    
    CATEGORIES = [
        ('refrigeration', 'Réfrigération'),
        ('lavage', 'Lavage'),
        ('cuisson', 'Cuisson'),
        ('audiovisuel', 'Audiovisuel'),
        ('eclairage', 'Éclairage'),
        ('piscine', 'Piscine'),
        ('spa', 'Spa/Jacuzzi'),
        ('vehicule', 'Véhicule électrique'),
        ('autre', 'Autre'),
    ]
    
    # Relations
    consommation = models.ForeignKey(
        ConsommationCalculee,
        on_delete=models.CASCADE,
        related_name='appareils'
    )
    
    # Identification
    categorie = models.CharField(
        max_length=30,
        choices=CATEGORIES,
        help_text="Catégorie de l'appareil"
    )
    type_appareil = models.CharField(
        max_length=50,
        help_text="Type précis (ex: frigo_combine, lave_linge, tv_55)"
    )
    nom_affichage = models.CharField(
        max_length=100,
        blank=True,
        help_text="Nom pour affichage utilisateur (ex: 'Réfrigérateur combiné A+++')"
    )
    
    # Caractéristiques techniques
    nombre = models.IntegerField(
        default=1,
        help_text="Nombre d'appareils identiques"
    )
    classe_energetique = models.CharField(
        max_length=10,
        blank=True,
        help_text="Classe énergie (A+++, A++, A+, A, B, C)"
    )
    puissance_w = models.IntegerField(
        null=True,
        blank=True,
        help_text="Puissance en Watts"
    )
    
    # Usage
    cycles_semaine = models.IntegerField(
        null=True,
        blank=True,
        help_text="Nombre de cycles par semaine (lave-linge, lave-vaisselle, sèche-linge)"
    )
    heures_jour = models.FloatField(
        null=True,
        blank=True,
        help_text="Heures d'utilisation par jour (TV, ordinateur, pompe piscine)"
    )
    mois_debut = models.IntegerField(
        null=True,
        blank=True,
        help_text="Mois de début d'utilisation (1-12) pour équipements saisonniers"
    )
    mois_fin = models.IntegerField(
        null=True,
        blank=True,
        help_text="Mois de fin d'utilisation (1-12)"
    )
    
    # Caractéristiques spécifiques
    km_an = models.IntegerField(
        null=True,
        blank=True,
        help_text="Kilomètres par an (véhicule électrique)"
    )
    conso_100km = models.FloatField(
        null=True,
        blank=True,
        help_text="Consommation kWh/100km (véhicule électrique)"
    )
    rendement_charge = models.FloatField(
        null=True,
        blank=True,
        help_text="Rendement de charge 0-1 (véhicule électrique)"
    )
    pct_recharge_domicile = models.IntegerField(
        null=True,
        blank=True,
        help_text="% de recharge à domicile (véhicule électrique)"
    )
    
    # Consommation calculée
    consommation_annuelle = models.FloatField(
        help_text="Consommation annuelle en kWh"
    )
    consommation_mensuelle = models.JSONField(
        default=list,
        help_text="Liste de 12 valeurs (consommation mensuelle en kWh)"
    )
    cout_annuel = models.FloatField(
        null=True,
        blank=True,
        help_text="Coût annuel estimé en €"
    )
    
    # Métadonnées
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Appareil consommation (mode expert)"
        verbose_name_plural = "Appareils consommation (mode expert)"
        ordering = ['categorie', 'type_appareil']
    
    def __str__(self):
        if self.nom_affichage:
            return f"{self.nom_affichage} ({self.consommation_annuelle:.0f} kWh/an)"
        return f"{self.get_categorie_display()} - {self.type_appareil}"
    
    def save(self, *args, **kwargs):
        # Générer nom_affichage si vide
        if not self.nom_affichage:
            self.nom_affichage = self._generer_nom_affichage()
        super().save(*args, **kwargs)
    
    def _generer_nom_affichage(self):
        """Génère un nom d'affichage automatique."""
        nom = self.get_categorie_display()
        
        # Ajouter type spécifique
        if self.type_appareil:
            type_readable = self.type_appareil.replace('_', ' ').title()
            nom = type_readable
        
        # Ajouter classe énergétique
        if self.classe_energetique:
            nom += f" {self.classe_energetique}"
        
        # Ajouter nombre si > 1
        if self.nombre > 1:
            nom += f" (×{self.nombre})"
        
        return nom

class AppareilUtilisateur(models.Model):
    """Appareils sélectionnés et configurés par l'utilisateur"""
    
    consommation = models.ForeignKey(
        ConsommationCalculee,
        on_delete=models.CASCADE,
        related_name='appareils_utilisateur'
    )
    appareil = models.ForeignKey(
        AppareilElectrique,
        on_delete=models.CASCADE,
        related_name='utilisations'
    )
    
    # Paramètres personnalisés
    quantite = models.IntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(50)],
        help_text="Nombre d'appareils de ce type"
    )
    
    heures_jour = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(24)],
        help_text="Heures d'utilisation par jour (override)"
    )
    
    jours_semaine = models.IntegerField(
        default=7,
        validators=[MinValueValidator(1), MaxValueValidator(7)],
        help_text="Jours d'utilisation par semaine"
    )
    
    # Mois d'utilisation (JSON - liste de 1 à 12)
    # Ex: [6, 7, 8] pour été uniquement
    # Ex: [1, 2, 3, 10, 11, 12] pour hiver
    mois_utilisation = models.JSONField(
        default=list,
        blank=True,
        help_text="Mois d'utilisation (1-12). Vide = toute l'année"
    )
    
    # Réponses aux questions personnalisées (JSON)
    # {"capacite": 200, "temperature": 60, "nb_cycles": 5}
    parametres_personnalises = models.JSONField(
        default=dict,
        blank=True,
        help_text="Réponses aux questions spécifiques"
    )
    
    # Consommation calculée pour cet appareil
    consommation_annuelle_kwh = models.FloatField(
        help_text="Consommation annuelle de cet appareil (kWh/an)"
    )
    consommation_mensuelle = models.JSONField(
        default=list,
        help_text="Consommation mensuelle (12 valeurs)"
    )
    
    class Meta:
        verbose_name = "Appareil utilisateur"
        verbose_name_plural = "Appareils utilisateur"
        ordering = ['appareil__category__ordre', 'appareil__ordre']
    
    def __str__(self):
        qty_str = f"{self.quantite}x " if self.quantite > 1 else ""
        return f"{qty_str}{self.appareil.nom}"
    
    def save(self, *args, **kwargs):
        """Calcule la consommation avant sauvegarde"""
        # Utiliser les heures personnalisées ou celles par défaut
        heures = self.heures_jour if self.heures_jour is not None else self.appareil.heures_jour_defaut
        
        # Calcul de base
        heures_annuelles = heures * (self.jours_semaine / 7) * 365
        conso_base = (self.appareil.puissance_nominale_w / 1000) * heures_annuelles * self.quantite
        
        # Appliquer les mois d'utilisation
        if self.mois_utilisation:
            # Seulement certains mois
            facteur_mois = len(self.mois_utilisation) / 12
            conso_base *= facteur_mois
        
        self.consommation_annuelle_kwh = round(conso_base, 2)
        
        # Répartition mensuelle
        monthly = []
        for mois in range(1, 13):
            if not self.mois_utilisation or mois in self.mois_utilisation:
                # Mois actif
                variation = self.appareil.variations_mensuelles.get(str(mois), 1.0)
                conso_mois = (conso_base / 12) * variation
            else:
                # Mois inactif
                conso_mois = 0
            
            monthly.append(round(conso_mois, 2))
        
        self.consommation_mensuelle = monthly
        
        super().save(*args, **kwargs)