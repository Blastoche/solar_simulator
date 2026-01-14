# frontend/forms.py
"""
Formulaires pour l'application frontend.
"""

from django import forms
from django.core.validators import MinValueValidator, MaxValueValidator
from .models import Installation


class InstallationForm(forms.ModelForm):
    """
    Formulaire de simulation d'installation solaire.
    Version complète avec tous les champs nécessaires.
    """
    
    # Champs supplémentaires pour la consommation (pas dans le modèle Installation)
    consommation_annuelle = forms.IntegerField(
        required=False,
        initial=5000,
        validators=[MinValueValidator(1000), MaxValueValidator(50000)],
        widget=forms.NumberInput(attrs={
            'class': 'w-full px-4 py-3 rounded-lg border border-gray-300 focus:ring-2 focus:ring-blue-500 focus:border-transparent',
            'placeholder': '5000',
            'min': '1000',
            'max': '50000',
        }),
        help_text='Consommation électrique annuelle en kWh'
    )
    
    nb_personnes = forms.IntegerField(
        required=False,
        initial=2,
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        widget=forms.NumberInput(attrs={
            'class': 'w-full px-4 py-3 rounded-lg border border-gray-300 focus:ring-2 focus:ring-blue-500 focus:border-transparent',
            'placeholder': '2',
            'min': '1',
            'max': '10',
        }),
        help_text='Nombre de personnes dans le foyer'
    )
    
    surface_habitable = forms.IntegerField(
        required=False,
        initial=100,
        validators=[MinValueValidator(20), MaxValueValidator(500)],
        widget=forms.NumberInput(attrs={
            'class': 'w-full px-4 py-3 rounded-lg border border-gray-300 focus:ring-2 focus:ring-blue-500 focus:border-transparent',
            'placeholder': '100',
            'min': '20',
            'max': '500',
        }),
        help_text='Surface habitable en m²'
    )
    
    class Meta:
        model = Installation
        fields = [
            'adresse',
            'latitude',
            'longitude',
            'puissance_kw',
            'orientation',
            'inclinaison',
            'type_toiture',
        ]
        
        widgets = {
            'adresse': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 rounded-lg border border-gray-300 focus:ring-2 focus:ring-blue-500 focus:border-transparent',
                'placeholder': 'Ex: 1 rue de la République, 75001 Paris',
                'id': 'adresse-input',
                'required': False,
            }),
            'latitude': forms.HiddenInput(attrs={
                'id': 'latitude-input',
            }),
            'longitude': forms.HiddenInput(attrs={
                'id': 'longitude-input',
            }),
            'puissance_kw': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-3 rounded-lg border border-gray-300 focus:ring-2 focus:ring-blue-500 focus:border-transparent',
                'placeholder': '3',
                'min': '1',
                'max': '100',
                'step': '0.1',
            }),
            'orientation': forms.Select(attrs={
                'class': 'w-full px-4 py-3 rounded-lg border border-gray-300 focus:ring-2 focus:ring-blue-500 focus:border-transparent',
            }),
            'inclinaison': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-3 rounded-lg border border-gray-300 focus:ring-2 focus:ring-blue-500 focus:border-transparent',
                'placeholder': '30',
                'min': '0',
                'max': '90',
            }),
            'type_toiture': forms.Select(attrs={
                'class': 'w-full px-4 py-3 rounded-lg border border-gray-300 focus:ring-2 focus:ring-blue-500 focus:border-transparent',
            }),
        }
        
        labels = {
            'adresse': '📍 Adresse de l\'installation',
            'puissance_kw': '⚡ Puissance installée (kWc)',
            'orientation': '🧭 Orientation du toit',
            'inclinaison': '📐 Inclinaison (degrés)',
            'type_toiture': '🏠 Type de toiture',
        }
        
        help_texts = {
            'puissance_kw': 'Puissance totale des panneaux (ex: 3 kWc)',
            'orientation': 'Direction vers laquelle le toit est orienté',
            'inclinaison': 'Angle d\'inclinaison du toit (0° = plat, 90° = vertical)',
            'type_toiture': 'Matériau du toit',
        }
    
    def clean(self):
        """
        Validation personnalisée du formulaire.
        """
        cleaned_data = super().clean()
        
        # Vérifier que latitude et longitude sont présentes
        latitude = cleaned_data.get('latitude')
        longitude = cleaned_data.get('longitude')
        
        if not latitude or not longitude:
            raise forms.ValidationError(
                "Veuillez sélectionner une adresse valide sur la carte."
            )
        
        # Vérifier que la latitude/longitude sont dans les limites PVGIS
        if latitude < -60 or latitude > 75:
            raise forms.ValidationError(
                f"Latitude invalide ({latitude}°). PVGIS couvre de -60° à 75°."
            )
        
        if longitude < -180 or longitude > 180:
            raise forms.ValidationError(
                f"Longitude invalide ({longitude}°)."
            )
        
        return cleaned_data
    
    def clean_puissance_kw(self):
        """Validation de la puissance."""
        puissance = self.cleaned_data.get('puissance_kw')
        
        if puissance and (puissance < 1 or puissance > 100):
            raise forms.ValidationError(
                "La puissance doit être entre 1 et 100 kWc."
            )
        
        return puissance
    
    def clean_inclinaison(self):
        """Validation de l'inclinaison."""
        inclinaison = self.cleaned_data.get('inclinaison')
        
        if inclinaison is not None and (inclinaison < 0 or inclinaison > 90):
            raise forms.ValidationError(
                "L'inclinaison doit être entre 0° et 90°."
            )
        
        return inclinaison


class SimulationAvanceeForm(InstallationForm):
    """
    Formulaire de simulation avancée avec options premium.
    Hérite de InstallationForm et ajoute des champs supplémentaires.
    """
    
    # Options avancées
    type_panneaux = forms.ChoiceField(
        choices=[
            ('monocristallin', 'Monocristallin (haute performance)'),
            ('polycristallin', 'Polycristallin (bon rapport qualité/prix)'),
            ('amorphe', 'Amorphe (adapté aux zones peu ensoleillées)'),
        ],
        initial='monocristallin',
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-3 rounded-lg border border-gray-300 focus:ring-2 focus:ring-blue-500',
        }),
        help_text='Type de cellules photovoltaïques'
    )
    
    avec_batterie = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'w-5 h-5 text-blue-600 rounded focus:ring-2 focus:ring-blue-500',
        }),
        help_text='Ajouter un système de stockage par batterie'
    )
    
    capacite_batterie = forms.FloatField(
        required=False,
        validators=[MinValueValidator(0), MaxValueValidator(50)],
        widget=forms.NumberInput(attrs={
            'class': 'w-full px-4 py-3 rounded-lg border border-gray-300 focus:ring-2 focus:ring-blue-500',
            'placeholder': '10',
            'min': '0',
            'max': '50',
            'step': '0.5',
        }),
        help_text='Capacité de la batterie en kWh (si applicable)'
    )
    
    prix_achat_kwh = forms.FloatField(
        required=False,
        initial=0.2276,
        validators=[MinValueValidator(0), MaxValueValidator(1)],
        widget=forms.NumberInput(attrs={
            'class': 'w-full px-4 py-3 rounded-lg border border-gray-300 focus:ring-2 focus:ring-blue-500',
            'placeholder': '0.2276',
            'step': '0.0001',
        }),
        help_text='Prix d\'achat de l\'électricité (€/kWh)'
    )
    
    prix_vente_kwh = forms.FloatField(
        required=False,
        initial=0.13,
        validators=[MinValueValidator(0), MaxValueValidator(1)],
        widget=forms.NumberInput(attrs={
            'class': 'w-full px-4 py-3 rounded-lg border border-gray-300 focus:ring-2 focus:ring-blue-500',
            'placeholder': '0.13',
            'step': '0.0001',
        }),
        help_text='Prix de revente du surplus (€/kWh)'
    )
    
    cout_installation = forms.FloatField(
        required=False,
        validators=[MinValueValidator(0), MaxValueValidator(100000)],
        widget=forms.NumberInput(attrs={
            'class': 'w-full px-4 py-3 rounded-lg border border-gray-300 focus:ring-2 focus:ring-blue-500',
            'placeholder': '8000',
            'step': '100',
        }),
        help_text='Coût total de l\'installation (€)'
    )
    
    def clean(self):
        """Validation pour la version avancée."""
        cleaned_data = super().clean()
        
        # Si batterie activée, capacité obligatoire
        avec_batterie = cleaned_data.get('avec_batterie')
        capacite_batterie = cleaned_data.get('capacite_batterie')
        
        if avec_batterie and not capacite_batterie:
            raise forms.ValidationError({
                'capacite_batterie': 'Veuillez indiquer la capacité de la batterie.'
            })
        
        return cleaned_data
