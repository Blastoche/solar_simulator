# frontend/forms.py
from django import forms
from django.core.exceptions import ValidationError
from .models import Installation

class InstallationForm(forms.ModelForm):
    """Formulaire pour créer une installation"""
    
    class Meta:
        model = Installation
        fields = ['adresse', 'latitude', 'longitude', 'puissance_kw', 'orientation', 'inclinaison', 'type_toiture']
        widgets = {
            'adresse': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border rounded-lg',
                'placeholder': '123 Rue de la Paix, 75000 Paris',
                'hx-post': '/api/geocode/',
                'hx-trigger': 'change',
                'hx-swap': 'none',
            }),
            'latitude': forms.HiddenInput(),
            'longitude': forms.HiddenInput(),
            'puissance_kw': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2 border rounded-lg',
                'min': '1',
                'max': '100',
                'step': '0.5',
                'value': '6',
            }),
            'orientation': forms.Select(attrs={
                'class': 'w-full px-4 py-2 border rounded-lg',
            }),
            'inclinaison': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2 border rounded-lg',
                'min': '0',
                'max': '90',
                'value': '30',
            }),
            'type_toiture': forms.Select(attrs={
                'class': 'w-full px-4 py-2 border rounded-lg',
            }),
        }
    
    def clean_puissance_kw(self):
        puissance = self.cleaned_data.get('puissance_kw')
        if puissance and puissance <= 0:
            raise ValidationError("La puissance doit être positive")
        return puissance
    
    def clean_inclinaison(self):
        inclinaison = self.cleaned_data.get('inclinaison')
        if inclinaison and not (0 <= inclinaison <= 90):
            raise ValidationError("L'inclinaison doit être entre 0 et 90°")
        return inclinaison
