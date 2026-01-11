# ☀️ Solar Simulator - Simulateur Photovoltaïque

Simulateur de production solaire photovoltaïque avec analyse de consommation électrique résidentielle et calculs financiers avancés.

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![Django Version](https://img.shields.io/badge/django-4.2-green)](https://www.djangoproject.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 📋 Table des Matières

- [Fonctionnalités](#-fonctionnalités)
- [Technologies](#-technologies)
- [Installation](#-installation)
- [Configuration](#️-configuration)
- [Utilisation](#-utilisation)
- [Architecture](#-architecture)
- [APIs Externes](#-apis-externes)
- [Développement](#-développement)
- [Tests](#-tests)
- [Roadmap](#-roadmap)
- [Licence](#-licence)

---

## ✨ Fonctionnalités

### 🔌 Calcul de Consommation Électrique
- Profil détaillé par appareil (électroménager, chauffage, ECS)
- Prise en compte du DPE (Diagnostic de Performance Énergétique)
- Génération de profils horaires (8760h/an)
- Répartition par poste de consommation

### ☀️ Calcul de Production Solaire
- Modèles physiques de production photovoltaïque
- Prise en compte de :
  - Orientation et inclinaison des panneaux
  - Ombrage et facteurs environnementaux
  - Température des cellules
  - Dégradation annuelle des panneaux
  - Pertes système (câblage, onduleur, salissure)
- Simulation annuelle (8760h)

### 💰 Analyse Financière *(à venir)*
- Calcul ROI (Retour sur Investissement)
- Calcul VAN (Valeur Actualisée Nette)
- Calcul TRI (Taux de Rentabilité Interne)
- Projection sur 25 ans
- Analyse de subventions

### 🔋 Stockage par Batterie *(futur)*
- Simulation de batteries
- Stratégies de charge/décharge
- Optimisation autoconsommation

### 📊 Rapports *(à venir)*
- Génération de rapports PDF
- Export Excel/CSV
- Graphiques interactifs
- Comparaison de scénarios

---

## 🛠 Technologies

### Backend
- **Django 4.2** - Framework web
- **PostgreSQL 14+** - Base de données
- **Redis** - Cache et broker Celery
- **Celery** - Tâches asynchrones

### Calculs Scientifiques
- **NumPy** - Calculs numériques
- **Pandas** - Manipulation de données
- **SciPy** - Algorithmes d'optimisation

### Visualisations
- **Plotly** - Graphiques interactifs
- **Matplotlib** - Graphiques statiques

### Frontend
- **HTMX** - Interactivité sans JS complexe
- **Alpine.js** - Interactions légères
- **Tailwind CSS** - Styling moderne

### APIs Externes
- **PVGIS** - Données d'irradiation solaire
- **OpenWeatherMap** - Prévisions météo
- **Solcast** - Prévisions solaires précises (optionnel)

---

## 📦 Installation

### Prérequis

- Python 3.10+
- PostgreSQL 14+
- Redis 6+
- Git

### 1. Cloner le repository

```bash
git clone https://github.com/yourusername/solar-simulator.git
cd solar-simulator
```

### 2. Créer un environnement virtuel

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows
```

### 3. Installer les dépendances

```bash
# Production
pip install -r requirements.txt

# Développement (inclut les outils de dev)
pip install -r requirements-dev.txt
```

### 4. Configuration de la base de données

```bash
# Créer la base PostgreSQL
createdb solar_simulator

# Ou via psql
psql -U postgres
CREATE DATABASE solar_simulator;
CREATE USER solar_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE solar_simulator TO solar_user;
\q
```

### 5. Configuration de l'environnement

```bash
# Copier le fichier d'exemple
cp .env.example .env

# Éditer .env et remplir vos valeurs
nano .env
```

### 6. Migrations Django

```bash
python manage.py migrate
python manage.py createsuperuser
```

### 7. Lancer le serveur

```bash
# Serveur de développement
python manage.py runserver

# Redis (dans un terminal séparé)
redis-server

# Celery (dans un terminal séparé)
celery -A config worker -l info
```

Accéder à : http://localhost:8000

---

## ⚙️ Configuration

### Variables d'environnement essentielles

```bash
# Django
SECRET_KEY=votre-clé-secrète-très-longue
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Base de données
DATABASE_URL=postgresql://solar_user:password@localhost:5432/solar_simulator

# Redis
REDIS_URL=redis://localhost:6379/0

# APIs
OPENWEATHER_API_KEY=votre_clé_api
```

Voir `.env.example` pour la liste complète.

---

## 🚀 Utilisation

### En ligne de commande Python

#### Calcul de consommation

```python
from solar_calc.models.consumption import creer_profil_standard

profil = creer_profil_standard()
conso_annuelle = profil.calcul_consommation_base()
print(f"Consommation : {conso_annuelle:,.0f} kWh/an")
# Résultat : Consommation : 12,450 kWh/an

# Répartition par poste
repartition = profil.repartition_consommation()
for poste, valeur in repartition.items():
    print(f"{poste}: {valeur:,.0f} kWh")
```

#### Calcul de production

```python
from solar_calc.models.production import creer_installation_standard

installation = creer_installation_standard()
production = installation.production_annuelle_estimee(irradiation=1400)
print(f"Production : {production:,.0f} kWh/an")
# Résultat : Production : 3,850 kWh/an
```

### Via l'interface web *(à venir)*

1. Accéder à http://localhost:8000
2. Créer un nouveau projet de simulation
3. Configurer l'installation (panneaux, orientation, etc.)
4. Définir le profil de consommation
5. Lancer la simulation
6. Consulter les résultats et graphiques
7. Télécharger le rapport PDF

---

## 🏗 Architecture

```
solar_simulator/                    ← RACINE DU PROJET
│
├── 📄 requirements.txt             ← À LA RACINE
├── 📄 requirements-dev.txt         ← À LA RACINE
├── 📄 .env.example                 ← À LA RACINE
├── 📄 .env                         ← À LA RACINE (à créer, pas versionné)
├── 📄 .gitignore                   ← À LA RACINE
├── 📄 README.md                    ← À LA RACINE
├── 📄 manage.py                    ← À LA RACINE (créé par Django)

│
├── 📂 venv/                        ← Environnement virtuel (ignoré par git)
│
├── 📂 docs/                        # DOCUMENTATION (optionnel)
│   ├── structure.py                
│   ├── architecture.py             
│   ├── etat_simulateur.md          
│   └── guide_windows.md
│
├── 📂 static/                      # Fichiers statiques globaux
│   ├── css/
│   ├── js/
│   └── images/
│
├── 📂 media/                       # Uploads utilisateurs (créé auto)
│
├── 📂 reports_output/              # Rapports PDF générés (créé auto)
│
├── 📂 logs/                        # Fichiers de logs (créé auto)
│
├── 📂 config/                      # CONFIGURATION DJANGO
│   ├── __init__.py
│   ├── settings.py                 # Settings principal
│   ├── urls.py                     # URLs racine
│   ├── wsgi.py
│   └── asgi.py
│
├── 📂 core/                        # APP CORE
│   ├── management/
│	 │   ├── __init__.py
│   │   ├── commands/               # Commandes Django custom 
│   └── tests/
│       ├── __init__.py
│
├── 📂 weather/                     # APP WEATHER
│   ├── models.py                   # Modèles Django (WeatherData, etc.)
│   ├── admin.py
│   ├── services/                   # Services API
│   │   ├── __init__.py
│   │   ├── pvgis.py                # Client PVGIS
│   │   ├── __pycache__/             
│   ├── templates/
│   ├── migrations/
│   └── tests/
│       ├── __init__.py
│
├── 📂 solar_calc/                  # APP SOLAR_CALC
│   ├── models.py                   # Modèles Django ORM
│   ├── admin.py
│   ├── dataclasses/                # Modèles de calcul (dataclasses)
│   │   ├── __init__.py
│   │   ├── consumption.py          # ✅ TON FICHIER ENRICHI
│   │   └── production.py           # ✅ TON FICHIER CRÉÉ
│   ├── services/                   # Services métier
│   │   ├── __init__.py
│   │   ├── simulation.py           # Orchestration simulation
│   ├── migrations/                
│   └── tests/
│       ├── __init__.py
│
├── 📂 battery/                     # APP BATTERY (future)
│   ├── __init__.py
│   ├── models.py
│   ├── services/
│   │   └── battery_simulation.py
│   └── tests/
│
├── 📂 financial/                   # APP FINANCIAL
│   ├── services/                   
│   ├── templates/                   
│   └── tests/
│
├── 📂 reporting/                   # APP REPORTING
│   ├── services/                   
│   ├── templates/                   
│   └── tests/
│
├── 📂 frontend/                    # APP FRONTEND
│   ├── views.py                    # Vues principales
│   ├── urls.py
│   ├── templates/                  # Templates HTML
│   │   ├── base.html               # Template de base
│   │   ├── frontend/
│   │   ├── home.html               # Page d'accueil
│   ├── static/                     # Fichiers statiques de l'app
│   │   └── frontend/
│   │       ├── css/
│   │       ├── js/
│   │       └── images/
│   └── tests/
│
└── 📂 tests/                       # TESTS GLOBAUX (optionnel)
    ├── test_pvgis.py
    ├── test_pvgis_simple.py               
    └── test_pvgis_v53_discovery.py
    ├── test_simulation.py


### Modules Principaux

#### 1. Weather (Météo)
Récupération et cache des données météorologiques depuis PVGIS, OpenWeather, et Solcast.

#### 2. Solar_Calc (Calculs)
Calculs de production solaire et consommation électrique.

#### 3. Financial (Financier)
Analyses économiques : ROI, VAN, TRI, projections.

#### 4. Reporting (Rapports)
Génération de rapports PDF, exports Excel/CSV.

#### 5. Frontend (Interface)
Interfaces web utilisateur avec formulaires et dashboards.

---

## 🌐 APIs Externes

### PVGIS (Gratuit)
- **Usage** : Données d'irradiation solaire historiques (TMY)
- **Documentation** : https://joint-research-centre.ec.europa.eu/pvgis-online-tool_en
- **Limite** : Aucune
- **Clé API** : Non requise

### OpenWeatherMap
- **Usage** : Prévisions météo court terme
- **Documentation** : https://openweathermap.org/api
- **Plan gratuit** : 1000 appels/jour
- **Inscription** : https://home.openweathermap.org/users/sign_up

### Solcast (Optionnel)
- **Usage** : Prévisions solaires haute précision
- **Documentation** : https://docs.solcast.com.au/
- **Plan gratuit** : 10 appels/jour
- **Inscription** : https://solcast.com/free-rooftop-solar-forecasting

---

## 👨‍💻 Développement

### Structure du code

```bash
# Formatter le code
black .

# Linter
flake8 .

# Type checking
mypy .

# Trier les imports
isort .
```

### Pre-commit hooks

```bash
# Installer pre-commit
pip install pre-commit

# Installer les hooks
pre-commit install

# Lancer manuellement
pre-commit run --all-files
```

### Créer une nouvelle migration

```bash
python manage.py makemigrations
python manage.py migrate
```

---

## 🧪 Tests

```bash
# Lancer tous les tests
pytest

# Avec couverture
pytest --cov=. --cov-report=html

# Tests spécifiques
pytest solar_calc/tests/

# Tests marqués
pytest -m "not slow"  # Exclure tests lents
```

---

## 🗓 Roadmap

### Phase 1 - MVP (4 semaines) ✅ 60%
- [x] Architecture du projet
- [x] Modèles de consommation
- [x] Modèles de production
- [ ] Intégration API PVGIS
- [ ] Interface web basique
- [ ] Simulation complète (couplage production/consommation)

### Phase 2 - Enrichissement (4 semaines)
- [ ] Module financier (ROI, VAN, TRI)
- [ ] Génération de rapports PDF
- [ ] Graphiques interactifs Plotly
- [ ] Intégration OpenWeather
- [ ] Dashboard avancé

### Phase 3 - Fonctionnalités Avancées (4 semaines)
- [ ] Module batterie
- [ ] Optimisation multi-objectif
- [ ] Comparaison de scénarios
- [ ] API REST publique
- [ ] Amélioration avec pvlib-python

### Phase 4 - Production (ongoing)
- [ ] Tests complets
- [ ] Documentation utilisateur
- [ ] Optimisation performances
- [ ] Déploiement
- [ ] Monitoring

---

## 📈 État d'avancement

**Modules fonctionnels** : 60%
- ✅ Architecture : 100%
- ✅ Consommation : 90%
- ✅ Production : 95%
- ⬜ Weather : 0%
- ⬜ Financial : 0%
- ⬜ Reporting : 0%
- ⬜ Frontend : 0%

---

## 🤝 Contribution

Les contributions sont les bienvenues ! 

1. Fork le projet
2. Créer une branche (`git checkout -b feature/amazing-feature`)
3. Commit les changements (`git commit -m 'Add amazing feature'`)
4. Push vers la branche (`git push origin feature/amazing-feature`)
5. Ouvrir une Pull Request

---

## 📝 Licence

Ce projet est sous licence MIT. Voir le fichier `LICENSE` pour plus de détails.

---

## 👤 Auteur

**Votre Nom**
- Email: votre.email@example.com
- GitHub: [@yourusername](https://github.com/yourusername)

---

## 🙏 Remerciements

- [PVGIS](https://re.jrc.ec.europa.eu/pvg_tools/en/) pour les données d'irradiation
- [OpenWeatherMap](https://openweathermap.org/) pour les données météo
- [Django](https://www.djangoproject.com/) pour le framework web
- [pvlib-python](https://pvlib-python.readthedocs.io/) pour les modèles solaires

---

## 📞 Support

Pour toute question ou problème :
- Ouvrir une [issue](https://github.com/yourusername/solar-simulator/issues)
- Consulter la [documentation](https://solar-simulator.readthedocs.io)
- Email : support@solar-simulator.com

---

**Made with ☀️ and ❤️ in France**# Solar Simulator 
 
Simulateur de production solaire photovoltaique 
