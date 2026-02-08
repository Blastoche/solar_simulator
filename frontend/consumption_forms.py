"""
Formulaire de configuration du profil de consommation - VERSION COMPLÈTE

Fichier: solar_calc/forms/consumption_form.py
"""

from django import forms
from solar_calc.models import ConsumptionProfileModel


class ConsumptionConfigurationForm(forms.ModelForm):
    """
    Formulaire complet pour configurer le profil de consommation.
    """
    
    # Champs supplémentaires (checkboxes pour appareils)
    appareil_lave_linge = forms.BooleanField(
        required=False,
        label="Lave-linge",
        widget=forms.CheckboxInput(attrs={'class': 'mr-2'})
    )
    
    appareil_lave_vaisselle = forms.BooleanField(
        required=False,
        label="Lave-vaisselle",
        widget=forms.CheckboxInput(attrs={'class': 'mr-2'})
    )
    
    appareil_seche_linge = forms.BooleanField(
        required=False,
        label="Sèche-linge",
        widget=forms.CheckboxInput(attrs={'class': 'mr-2'})
    )
    
    appareil_vehicule_electrique = forms.BooleanField(
        required=False,
        label="Véhicule électrique",
        widget=forms.CheckboxInput(attrs={'class': 'mr-2'})
    )
    
    appareil_piscine = forms.BooleanField(
        required=False,
        label="Piscine / Spa",
        widget=forms.CheckboxInput(attrs={'class': 'mr-2'})
    )
    
    class Meta:
        model = ConsumptionProfileModel
        fields = [
            'nom',
            'consommation_annuelle_kwh',
            'nb_personnes',
            'periode_construction',
            'surface_habitable',
            'dpe',
            'type_chauffage',
            'type_ecs',
            'profile_type',
        ]
        
        widgets = {
            'nom': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border rounded-lg',
                'placeholder': 'Mon profil'
            }),
            'consommation_annuelle_kwh': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2 border rounded-lg',
                'placeholder': '5000',
                'min': '500',
                'max': '50000',
                'step': '100'
            }),
            'nb_personnes': forms.Select(attrs={
                'class': 'w-full px-4 py-2 border rounded-lg'
            }),
            'annee_construction': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2 border rounded-lg',
                'placeholder': '2010',
                'min': '1900',
                'max': '2030'
            }),
            'surface_habitable': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2 border rounded-lg',
                'placeholder': '100',
                'min': '20',
                'max': '500',
                'step': '0.1'
            }),
            'dpe': forms.Select(attrs={
                'class': 'w-full px-4 py-2 border rounded-lg'
            }),
            'type_chauffage': forms.Select(attrs={
                'class': 'w-full px-4 py-2 border rounded-lg'
            }),
            'type_ecs': forms.Select(attrs={
                'class': 'w-full px-4 py-2 border rounded-lg'
            }),
            'profile_type': forms.RadioSelect(attrs={
                'class': 'mr-2'
            }),
        }
        
        labels = {
            'nom': 'Nom du profil',
            'consommation_annuelle_kwh': 'Consommation annuelle (kWh/an)',
            'nb_personnes': 'Nombre de personnes',
            'periode_construction': 'Période de construction',
            'surface_habitable': 'Surface habitable (m²)',
            'dpe': 'Classe énergétique (DPE)',
            'type_chauffage': 'Type de chauffage',
            'type_ecs': 'Eau chaude sanitaire (ECS)',
            'profile_type': 'Profil d\'occupation',
        }
    
    def __init__(self, *args, **kwargs):
        """Personnalisation du formulaire."""
        super().__init__(*args, **kwargs)
        
        # ===== AJOUTER MANUELLEMENT LES CHOICES POUR nb_personnes =====
        self.fields['nb_personnes'] = forms.ChoiceField(
            choices=[
                (1, '1 personne'),
                (2, '2 personnes'),
                (3, '3-4 personnes'),
                (5, '5+ personnes'),
            ],
            widget=forms.Select(attrs={
                'class': 'w-full px-4 py-2 border rounded-lg'
            }),
            label='Nombre de personnes',
            initial=2
        )
        
        # ===== CHAMPS OPTIONNELS =====
        # Période de construction
        self.fields['periode_construction'] = forms.ChoiceField(
            choices=[
                ('', '-- Sélectionnez --'),
                ('avant_1975', 'Avant 1975 (pas d\'isolation)'),
                ('1975_2000', '1975-2000 (isolation basique)'),
                ('2000_2012', '2000-2012 (bonne isolation)'),
                ('2013_2020', '2013-2020 (RT 2012)'),
                ('apres_2021', 'Après 2021 (RE 2020)'),
            ],
            required=False,
            widget=forms.Select(attrs={
                'class': 'w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500'
            }),
            label="Période de construction"
        )
        self.fields['surface_habitable'].required = False
        self.fields['dpe'].required = False
        self.fields['nom'].required = False
        
        # ===== VALEURS PAR DÉFAUT =====
        if not self.instance.pk:
            self.fields['consommation_annuelle_kwh'].initial = 5000
            self.fields['nb_personnes'].initial = 2
            self.fields['dpe'].initial = 'D'
    
    def clean_consommation_annuelle_kwh(self):
        """Valide la consommation."""
        consommation = self.cleaned_data.get('consommation_annuelle_kwh')
        
        if consommation:
            if consommation < 500:
                raise forms.ValidationError(
                    "⚠️ Consommation très faible. Vérifiez votre saisie."
                )
            if consommation > 50000:
                raise forms.ValidationError(
                    "⚠️ Consommation très élevée. Vérifiez votre saisie."
                )
        
        return consommation
    
    def save(self, commit=True, user=None):
        """
        Sauvegarde le profil avec les données d'appareils en JSON.
        """
        import json
        
        instance = super().save(commit=False)
        
        # Assigner l'utilisateur
        if user:
            instance.user = user
        
        # Générer nom par défaut si vide
        if not instance.nom:
            instance.nom = f"Profil {instance.nb_personnes} personnes"
        
        # Construire le JSON des appareils
        appareils_data = {
            "meta": {
                "nb_personnes": int(self.cleaned_data.get('nb_personnes', 2)),
                "type_logement": "maison" if self.cleaned_data.get('surface_habitable', 0) > 80 else "appartement"
            },
            "chauffage": {
                "type": instance.type_chauffage,
                "programmable": False
            },
            "ecs": {
                "type": instance.type_ecs,
                "programmable": instance.type_ecs in ['electrique', 'thermodynamique'],
                "heure_habituelle": 2,
                "heure_optimale": 12
            },
            "appareils": {}
        }
        
        # Ajouter les appareils cochés
        if self.cleaned_data.get('appareil_lave_linge'):
            appareils_data["appareils"]["lave_linge"] = {
                "present": True,
                "programmable": True,
                "heure_habituelle": 20,
                "heure_optimale": 12,
                "cycles_par_semaine": 4
            }
        
        if self.cleaned_data.get('appareil_lave_vaisselle'):
            appareils_data["appareils"]["lave_vaisselle"] = {
                "present": True,
                "programmable": True,
                "heure_habituelle": 21,
                "heure_optimale": 13,
                "cycles_par_semaine": 5
            }
        
        if self.cleaned_data.get('appareil_seche_linge'):
            appareils_data["appareils"]["seche_linge"] = {
                "present": True,
                "programmable": True,
                "heure_habituelle": 22,
                "heure_optimale": 14,
                "cycles_par_semaine": 3
            }
        
        if self.cleaned_data.get('appareil_vehicule_electrique'):
            appareils_data["appareils"]["vehicule_electrique"] = {
                "present": True,
                "programmable": True,
                "heure_habituelle": 19,
                "heure_optimale": 11,
                "jours_par_semaine": 5
            }
        
        if self.cleaned_data.get('appareil_piscine'):
            appareils_data["appareils"]["piscine"] = {
                "present": True,
                "programmable": True,
                "heure_habituelle": 6,
                "heure_optimale": 11,
                "mois_utilisation": 6
            }
        
        # Sauvegarder en JSON
        instance.appareils_json = json.dumps(appareils_data, ensure_ascii=False)
        
        if commit:
            instance.save()
        
        return instance
    
    def clean(self):
        cleaned_data = super().clean()
        dpe = cleaned_data.get('dpe')
        periode = cleaned_data.get('periode_construction')
        
        # Au moins un des deux obligatoire
        if not dpe and not periode:
            raise forms.ValidationError(
                "⚠️ Vous devez renseigner soit la période de construction, soit le DPE de votre logement."
            )
        
        return cleaned_data