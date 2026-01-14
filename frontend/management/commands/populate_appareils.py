# frontend/management/commands/populate_appareils.py
"""
Commande Django pour peupler la base de données avec les appareils électriques.

Usage:
    python manage.py populate_appareils
    python manage.py populate_appareils --reset  # Supprime et recrée tout
"""

from django.core.management.base import BaseCommand
from django.utils.text import slugify
from frontend.models import AppareillectriqueCategory, AppareilElectrique


class Command(BaseCommand):
    help = 'Peuple la base de données avec les appareils électriques de base'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Supprime toutes les données existantes avant de recréer',
        )

    def handle(self, *args, **options):
        if options['reset']:
            self.stdout.write(self.style.WARNING('🗑️  Suppression des données existantes...'))
            AppareilUtilisateur.objects.all().delete()
            AppareilElectrique.objects.all().delete()
            AppareillectriqueCategory.objects.all().delete()
        
        self.stdout.write(self.style.SUCCESS('📊 Création des catégories...'))
        categories = self.create_categories()
        
        self.stdout.write(self.style.SUCCESS('🔌 Création des appareils...'))
        self.create_appareils(categories)
        
        self.stdout.write(self.style.SUCCESS('✅ Base de données peuplée avec succès !'))
        
        # Stats
        nb_categories = AppareillectriqueCategory.objects.count()
        nb_appareils = AppareilElectrique.objects.count()
        self.stdout.write(
            self.style.SUCCESS(
                f'📈 {nb_categories} catégories et {nb_appareils} appareils créés'
            )
        )

    def create_categories(self):
        """Crée les catégories d'appareils"""
        categories_data = [
            {'nom': 'Chauffage', 'icon': '🔥', 'ordre': 1, 'pourcentage': 45},
            {'nom': 'Eau Chaude Sanitaire', 'icon': '🚿', 'ordre': 2, 'pourcentage': 15},
            {'nom': 'Cuisson', 'icon': '🍳', 'ordre': 3, 'pourcentage': 8},
            {'nom': 'Électroménager', 'icon': '🧺', 'ordre': 4, 'pourcentage': 20},
            {'nom': 'Audiovisuel & Informatique', 'icon': '📺', 'ordre': 5, 'pourcentage': 7},
            {'nom': 'Éclairage', 'icon': '💡', 'ordre': 6, 'pourcentage': 3},
            {'nom': 'Climatisation', 'icon': '❄️', 'ordre': 7, 'pourcentage': 5},
            {'nom': 'Extérieur & Mobilité', 'icon': '🏊', 'ordre': 8, 'pourcentage': 10},
            {'nom': 'Divers', 'icon': '📦', 'ordre': 9, 'pourcentage': 2},
        ]
        
        categories = {}
        for cat_data in categories_data:
            cat, created = AppareillectriqueCategory.objects.get_or_create(
                slug=slugify(cat_data['nom']),
                defaults={
                    'nom': cat_data['nom'],
                    'icon': cat_data['icon'],
                    'ordre': cat_data['ordre'],
                    'pourcentage_moyen': cat_data['pourcentage'],
                }
            )
            categories[cat_data['nom']] = cat
            status = '✓ Créé' if created else '↻ Existe'
            self.stdout.write(f"  {status}: {cat}")
        
        return categories

    def create_appareils(self, categories):
        """Crée les appareils électriques"""
        
        # Variations saisonnières prédéfinies
        hiver = {str(i): 1.5 if i in [1,2,3,10,11,12] else 0.3 for i in range(1, 13)}
        ete = {str(i): 1.5 if i in [6,7,8] else 0.3 for i in range(1, 13)}
        uniforme = {str(i): 1.0 for i in range(1, 13)}
        
        appareils_data = [
            # ==================== CHAUFFAGE ====================
            {
                'category': 'Chauffage',
                'nom': 'Chauffage électrique (convecteurs)',
                'puissance': 1500,  # Par pièce
                'heures_jour': 10,  # Hiver
                'variations': hiver,
                'mode_rapide': True,
                'questions': [
                    {'field': 'nb_pieces', 'label': 'Nombre de pièces chauffées', 'type': 'number', 'default': 4},
                ]
            },
            {
                'category': 'Chauffage',
                'nom': 'Pompe à chaleur (PAC)',
                'puissance': 2500,
                'heures_jour': 8,
                'variations': hiver,
                'mode_rapide': True,
                'description': 'COP moyen de 3.0 déjà appliqué sur la puissance'
            },
            {
                'category': 'Chauffage',
                'nom': 'Radiateurs à inertie',
                'puissance': 1200,
                'heures_jour': 12,
                'variations': hiver,
                'mode_rapide': False,
            },
            {
                'category': 'Chauffage',
                'nom': 'Chauffage d\'appoint',
                'puissance': 2000,
                'heures_jour': 2,
                'variations': hiver,
                'mode_rapide': False,
            },
            
            # ==================== EAU CHAUDE ====================
            {
                'category': 'Eau Chaude Sanitaire',
                'nom': 'Ballon d\'eau chaude électrique 200L',
                'puissance': 2500,
                'heures_jour': 3,
                'variations': uniforme,
                'mode_rapide': True,
                'questions': [
                    {'field': 'capacite', 'label': 'Capacité (litres)', 'type': 'select', 'options': [50, 100, 150, 200, 250, 300], 'default': 200},
                    {'field': 'nb_personnes', 'label': 'Nombre de personnes', 'type': 'number', 'default': 4},
                ]
            },
            {
                'category': 'Eau Chaude Sanitaire',
                'nom': 'Chauffe-eau thermodynamique',
                'puissance': 500,  # COP déjà appliqué
                'heures_jour': 3,
                'variations': uniforme,
                'mode_rapide': True,
            },
            
            # ==================== CUISSON ====================
            {
                'category': 'Cuisson',
                'nom': 'Plaques induction (4 feux)',
                'puissance': 3000,
                'heures_jour': 1.5,
                'variations': uniforme,
                'mode_rapide': True,
            },
            {
                'category': 'Cuisson',
                'nom': 'Four électrique',
                'puissance': 2500,
                'heures_jour': 0.5,
                'jours_semaine': 5,
                'variations': uniforme,
                'mode_rapide': True,
            },
            {
                'category': 'Cuisson',
                'nom': 'Micro-ondes',
                'puissance': 1000,
                'veille': 3,
                'heures_jour': 0.3,
                'variations': uniforme,
                'mode_rapide': False,
            },
            {
                'category': 'Cuisson',
                'nom': 'Bouilloire électrique',
                'puissance': 2000,
                'heures_jour': 0.2,
                'variations': uniforme,
                'mode_rapide': False,
            },
            {
                'category': 'Cuisson',
                'nom': 'Machine à café',
                'puissance': 1000,
                'veille': 2,
                'heures_jour': 0.5,
                'variations': uniforme,
                'mode_rapide': False,
            },
            
            # ==================== ÉLECTROMÉNAGER ====================
            {
                'category': 'Électroménager',
                'nom': 'Réfrigérateur combiné',
                'puissance': 150,
                'heures_jour': 24,
                'variations': uniforme,
                'mode_rapide': True,
                'questions': [
                    {'field': 'type', 'label': 'Type', 'type': 'select', 'options': ['Simple', 'Combiné', 'Américain'], 'default': 'Combiné'},
                    {'field': 'classe', 'label': 'Classe énergétique', 'type': 'select', 'options': ['A+++', 'A++', 'A+', 'A', 'B ou moins'], 'default': 'A++'},
                ]
            },
            {
                'category': 'Électroménager',
                'nom': 'Congélateur',
                'puissance': 150,
                'heures_jour': 24,
                'variations': uniforme,
                'mode_rapide': True,
            },
            {
                'category': 'Électroménager',
                'nom': 'Lave-linge',
                'puissance': 2000,
                'heures_jour': 2,
                'jours_semaine': 3,
                'variations': uniforme,
                'mode_rapide': True,
                'questions': [
                    {'field': 'cycles_semaine', 'label': 'Cycles par semaine', 'type': 'number', 'default': 3},
                    {'field': 'temperature', 'label': 'Température moyenne (°C)', 'type': 'select', 'options': [30, 40, 60, 90], 'default': 40},
                ]
            },
            {
                'category': 'Électroménager',
                'nom': 'Sèche-linge',
                'puissance': 2500,
                'heures_jour': 1.5,
                'jours_semaine': 2,
                'variations': uniforme,
                'mode_rapide': True,
            },
            {
                'category': 'Électroménager',
                'nom': 'Lave-vaisselle',
                'puissance': 1500,
                'heures_jour': 1.5,
                'jours_semaine': 4,
                'variations': uniforme,
                'mode_rapide': True,
            },
            {
                'category': 'Électroménager',
                'nom': 'Aspirateur',
                'puissance': 1500,
                'heures_jour': 0.5,
                'jours_semaine': 2,
                'variations': uniforme,
                'mode_rapide': False,
            },
            {
                'category': 'Électroménager',
                'nom': 'Fer à repasser',
                'puissance': 2000,
                'heures_jour': 1,
                'jours_semaine': 2,
                'variations': uniforme,
                'mode_rapide': False,
            },
            
            # ==================== AUDIOVISUEL ====================
            {
                'category': 'Audiovisuel & Informatique',
                'nom': 'TV LED 50 pouces',
                'puissance': 80,
                'veille': 1,
                'heures_jour': 4,
                'variations': uniforme,
                'mode_rapide': True,
                'questions': [
                    {'field': 'taille', 'label': 'Taille (pouces)', 'type': 'select', 'options': [32, 43, 50, 55, 65, 75], 'default': 50},
                    {'field': 'heures', 'label': 'Heures/jour', 'type': 'number', 'default': 4},
                ]
            },
            {
                'category': 'Audiovisuel & Informatique',
                'nom': 'Box Internet',
                'puissance': 15,
                'heures_jour': 24,
                'variations': uniforme,
                'mode_rapide': True,
            },
            {
                'category': 'Audiovisuel & Informatique',
                'nom': 'Ordinateur portable',
                'puissance': 60,
                'veille': 2,
                'heures_jour': 4,
                'variations': uniforme,
                'mode_rapide': False,
            },
            {
                'category': 'Audiovisuel & Informatique',
                'nom': 'Ordinateur fixe',
                'puissance': 200,
                'veille': 5,
                'heures_jour': 4,
                'variations': uniforme,
                'mode_rapide': False,
            },
            {
                'category': 'Audiovisuel & Informatique',
                'nom': 'Console de jeux',
                'puissance': 150,
                'veille': 10,
                'heures_jour': 2,
                'variations': uniforme,
                'mode_rapide': False,
            },
            
            # ==================== ÉCLAIRAGE ====================
            {
                'category': 'Éclairage',
                'nom': 'Ampoule LED 10W',
                'puissance': 10,
                'heures_jour': 4,
                'variations': hiver,  # Plus en hiver
                'mode_rapide': True,
                'questions': [
                    {'field': 'nb_ampoules', 'label': 'Nombre d\'ampoules', 'type': 'number', 'default': 15},
                ]
            },
            {
                'category': 'Éclairage',
                'nom': 'Ampoule halogène 50W',
                'puissance': 50,
                'heures_jour': 4,
                'variations': hiver,
                'mode_rapide': False,
            },
            
            # ==================== CLIMATISATION ====================
            {
                'category': 'Climatisation',
                'nom': 'Climatisation fixe',
                'puissance': 1500,
                'heures_jour': 6,
                'variations': ete,
                'mode_rapide': True,
            },
            {
                'category': 'Climatisation',
                'nom': 'Ventilateur',
                'puissance': 50,
                'heures_jour': 8,
                'variations': ete,
                'mode_rapide': False,
            },
            {
                'category': 'Climatisation',
                'nom': 'VMC double flux',
                'puissance': 50,
                'heures_jour': 24,
                'variations': uniforme,
                'mode_rapide': False,
            },
            
            # ==================== EXTÉRIEUR ====================
            {
                'category': 'Extérieur & Mobilité',
                'nom': 'Piscine - Filtration',
                'puissance': 750,
                'heures_jour': 8,
                'variations': ete,
                'mode_rapide': True,
                'questions': [
                    {'field': 'volume', 'label': 'Volume de la piscine (m³)', 'type': 'number', 'default': 40},
                ]
            },
            {
                'category': 'Extérieur & Mobilité',
                'nom': 'Piscine - Chauffage électrique',
                'puissance': 3000,
                'heures_jour': 6,
                'variations': ete,
                'mode_rapide': False,
            },
            {
                'category': 'Extérieur & Mobilité',
                'nom': 'Borne recharge véhicule électrique',
                'puissance': 3700,  # 16A monophasé
                'heures_jour': 4,
                'jours_semaine': 5,
                'variations': uniforme,
                'mode_rapide': True,
                'questions': [
                    {'field': 'puissance', 'label': 'Puissance de la borne (kW)', 'type': 'select', 'options': [3.7, 7.4, 11, 22], 'default': 7.4},
                    {'field': 'km_semaine', 'label': 'Kilomètres par semaine', 'type': 'number', 'default': 200},
                ]
            },
            {
                'category': 'Extérieur & Mobilité',
                'nom': 'Spa / Jacuzzi',
                'puissance': 2500,
                'heures_jour': 3,
                'jours_semaine': 3,
                'variations': uniforme,
                'mode_rapide': False,
            },
            
            # ==================== DIVERS ====================
            {
                'category': 'Divers',
                'nom': 'Cave à vin',
                'puissance': 100,
                'heures_jour': 24,
                'variations': uniforme,
                'mode_rapide': False,
            },
            {
                'category': 'Divers',
                'nom': 'Aquarium 200L',
                'puissance': 150,
                'heures_jour': 24,
                'variations': uniforme,
                'mode_rapide': False,
            },
            {
                'category': 'Divers',
                'nom': 'Sèche-serviettes électrique',
                'puissance': 500,
                'heures_jour': 4,
                'variations': hiver,
                'mode_rapide': False,
            },
        ]
        
        for app_data in appareils_data:
            category = categories[app_data['category']]
            
            appareil, created = AppareilElectrique.objects.get_or_create(
                category=category,
                slug=slugify(app_data['nom']),
                defaults={
                    'nom': app_data['nom'],
                    'puissance_nominale_w': app_data['puissance'],
                    'puissance_veille_w': app_data.get('veille', 0),
                    'heures_jour_defaut': app_data.get('heures_jour', 1.0),
                    'jours_semaine_defaut': app_data.get('jours_semaine', 7),
                    'variations_mensuelles': app_data.get('variations', uniforme),
                    'mode_rapide': app_data.get('mode_rapide', True),
                    'mode_expert': True,
                    'questions_personnalisees': app_data.get('questions', []),
                    'description': app_data.get('description', ''),
                }
            )
            
            status = '✓' if created else '↻'
            conso = appareil.consommation_annuelle_kwh
            self.stdout.write(f"  {status} {appareil.nom}: {conso:.0f} kWh/an")
