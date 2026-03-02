# ☀️ Solar Simulator — Simulateur Photovoltaïque Résidentiel

Simulateur complet de production solaire photovoltaïque avec analyse personnalisée de consommation, calcul d'autoconsommation, comparaison de scénarios (actuel vs optimisé), simulation de batterie et analyse financière.

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![Django Version](https://img.shields.io/badge/django-4.2_LTS-green)](https://www.djangoproject.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 📋 Table des Matières

- [Fonctionnalités](#-fonctionnalités)
- [Parcours Utilisateur](#-parcours-utilisateur)
- [Technologies](#-technologies)
- [Installation](#-installation)
- [Configuration](#️-configuration)
- [Architecture](#-architecture)
- [APIs Externes](#-apis-externes)
- [État d'avancement](#-état-davancement)
- [Roadmap](#-roadmap)
- [Licence](#-licence)

---

## ✨ Fonctionnalités

### 🔌 Analyse de Consommation Électrique
- **Calculateur rapide** : estimation en 2 min basée sur le logement (surface, DPE, nombre de personnes)
- **Calculateur expert** : analyse détaillée appareil par appareil
- **Profil de consommation** : configuration du logement (chauffage, ECS, appareils programmables, profil d'occupation)
- **Décomposition par poste** : chauffage, ECS, électroménager, éclairage, etc.
- **Génération de profils horaires** : 8760 points/an (1 par heure) personnalisés selon le profil d'occupation

### ☀️ Simulation de Production Solaire
- Données d'irradiation réelles via **PVGIS 5.3** (European Commission — JRC)
- Modèle de production : GHI × Performance Ratio (0.85) × correction température
- Prise en compte de l'orientation (N/NE/E/SE/S/SW/W/NW + **Est/Ouest réparti**) et inclinaison
- Simulation annuelle complète sur 8760 heures
- Calcul de puissance recommandée selon la consommation

### ⚡ Autoconsommation & Scénarios
- **Scénario actuel** : autoconsommation avec les horaires habituels de l'utilisateur
- **Scénario optimisé** : appareils programmés aux heures de production solaire (11h-16h)
- Calcul des gains potentiels entre les deux scénarios (kWh, %, €)
- Taux d'autoconsommation (part de production consommée sur place)
- Taux d'autonomie/autoproduction (part de consommation couverte par le solaire)

### 🔋 Simulation Batterie
- Comparaison de capacités (2.5 / 5 / 10 / 15 kWh)
- Impact sur le taux d'autoconsommation
- Estimation prix TTC installé (marché français 2025)
- Calcul du ROI par capacité
- Recommandation de capacité optimale

### 💰 Analyse Financière
- Tarifs EDF OA actualisés (février 2026) selon la puissance (≤9 / 9-36 / 36-100 kWc)
- Tarif achat réseau : 0.194 €/kWh (tarif réglementé base)
- Économies annuelles (autoconsommation + revente surplus)
- Projection sur 25 ans
- Taux de rentabilité

### 📊 Rapports & Exports
- Génération de rapports PDF (WeasyPrint)
- Export Excel (openpyxl)
- Graphiques interactifs Plotly (mensuel + profil horaire moyen 24h)
- Comparaison visuelle des scénarios

---

## 🚶 Parcours Utilisateur

Le simulateur fonctionne en **4 étapes** via un formulaire multi-step :

1. **📍 Localisation** — Sélection sur carte interactive (Leaflet) → coordonnées GPS
2. **⚡ Consommation** — 3 options :
   - "J'ai déjà analysé" (retour calculateur)
   - "Je connais ma conso" → saisie kWh + **création obligatoire d'un profil de consommation**
   - "Je ne connais pas" → calculateur rapide ou expert
3. **🎯 Objectif** — Choix entre rentabilité maximale, autoconsommation maximale, ou équilibre
4. **⚙️ Configuration** — Puissance recommandée + ajustement (orientation, inclinaison, toiture)

→ **Lancement de la simulation** via Celery (tâche asynchrone avec barre de progression)

→ **Page de résultats** : 5 KPIs, détails installation, bilan solaire, graphiques mensuel et horaire, comparaison scénarios, section batterie, exports PDF/Excel

---

## 🛠 Technologies

### Backend
| Composant | Technologie | Usage |
|-----------|-------------|-------|
| Framework | Django 4.2 LTS | Application web |
| Base de données | SQLite3 (dev) / PostgreSQL (prod) | Persistance |
| Cache & Broker | Redis | Cache PVGIS + broker Celery |
| Tâches async | Celery | Simulation en arrière-plan |
| API REST | Django REST Framework | APIs futures |

### Calculs Scientifiques
| Composant | Usage |
|-----------|-------|
| NumPy | Calculs vectoriels (8760 points horaires) |
| Pandas | Manipulation des DataFrames météo PVGIS |

### Frontend
| Composant | Usage |
|-----------|-------|
| Tailwind CSS | Styling (via CDN) |
| Plotly.js | Graphiques interactifs (mensuel, horaire) |
| Leaflet.js | Carte interactive (sélection localisation) |
| HTMX | Polling progression simulation |
| Font Awesome | Icônes |

### Génération de Documents
| Composant | Usage |
|-----------|-------|
| WeasyPrint | Rapports PDF |
| ReportLab | PDF (alternative) |
| openpyxl | Export Excel |

---

## 📦 Installation

### Prérequis
- Python 3.10+
- Redis 6+ (pour Celery)
- Git

### Installation rapide (Windows)

```bash
# 1. Cloner et configurer
git clone <repo-url>
cd solar_simulator

# 2. Environnement virtuel
python -m venv venv
venv\Scripts\activate

# 3. Dépendances
pip install -r requirements.txt

# 4. Base de données
python manage.py migrate
python manage.py createsuperuser

# 5. Lancer (3 terminaux)
python manage.py runserver          # Terminal 1 : Django
redis-server                        # Terminal 2 : Redis
celery -A config worker -l info --pool=solo   # Terminal 3 : Celery (--pool=solo sur Windows)
```

Accéder à : **http://localhost:8000**

### Installation détaillée

Voir `docs/Guide_windows.md` pour un guide pas à pas sur Windows.

---

## ⚙️ Configuration

### Variables d'environnement

```bash
# Django
SECRET_KEY=votre-clé-secrète
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Redis (requis pour Celery)
REDIS_URL=redis://localhost:6379/0
```

### APIs externes

PVGIS ne nécessite **aucune clé API**. Les données sont mises en cache automatiquement.

---

## 🏗 Architecture

Voir `docs/Architecture actuelle du projet.txt` pour l'arbre complet.

### 7 Apps Django

| App | Rôle | État |
|-----|------|------|
| **config** | Configuration Django, Celery, URLs racine | ✅ Complet |
| **core** | Validators, commandes management, utilitaires | ✅ Complet |
| **weather** | Intégration PVGIS 5.3, cache Redis, modèles météo | ✅ Complet |
| **solar_calc** | Calculs production, consommation, profils horaires, tâche Celery | ✅ Complet |
| **battery** | Simulation batterie, sizing, pricing | ✅ Complet |
| **financial** | Calculs financiers avancés (ROI, VAN, TRI) | 🔶 Partiel |
| **reporting** | Génération PDF, graphiques | ✅ Complet |
| **frontend** | Vues, formulaires, templates, modèles Installation/Simulation/Resultat | ✅ Complet |

### Flux de données principal

```
Utilisateur → Formulaire multi-step (form.html)
    → SimulationFormView (views.py)
        → Création Installation + ConsumptionProfile + Simulation
        → Lancement run_simulation_task (Celery)
            → get_pvgis_weather_data() → 8760h GHI + température
            → decompose_consumption() → répartition par poste
            → generate_personalized_hourly_profile() → 8760h conso (actuel + optimisé)
            → Calcul production horaire = GHI × PR × kWc × correction temp
            → Calcul autoconsommation = min(production, consommation) par heure
            → Agrégation mensuelle (12 mois) + profil horaire moyen (24h)
            → Sauvegarde Resultat en base
    → Page progression (polling HTMX)
    → Page résultats (results.html + Plotly)
```

---

## 🌐 APIs Externes

### PVGIS 5.3 (European Commission — JRC)
- **Usage** : Données d'irradiation solaire TMY (Typical Meteorological Year)
- **Endpoint** : `https://re.jrc.ec.europa.eu/api/v5_3/tmy`
- **Données** : GHI, température, vent — 8760 valeurs horaires
- **Clé API** : Non requise
- **Cache** : Redis (évite les appels répétés pour les mêmes coordonnées)
- **Documentation** : https://joint-research-centre.ec.europa.eu/pvgis-online-tool_en

---

## 📈 État d'avancement

**Dernière mise à jour : Février 2026**

| Module | Avancement | Détails |
|--------|:----------:|---------|
| Architecture & Config | ✅ 100% | Django, Celery, Redis, structure 7 apps |
| Weather / PVGIS | ✅ 100% | API v5.3, cache Redis, normalisation timestamps |
| Consommation | ✅ 100% | Calculateur rapide + expert, profils horaires, décomposition par poste |
| Production solaire | ✅ 100% | Modèle GHI×PR, correction température, 8760h |
| Formulaire simulation | ✅ 100% | 4 étapes, profil obligatoire, restauration état |
| Tâche Celery | ✅ 100% | Progression temps réel, 2 scénarios, agrégation mensuelle + horaire |
| Page résultats | ✅ 100% | 5 KPIs, bilan solaire, graphiques Plotly, scénarios |
| Batterie | ✅ 100% | Simulation, sizing, pricing, comparaison capacités |
| Reporting PDF | ✅ 95% | Génération PDF WeasyPrint, export Excel |
| Financier avancé | 🔶 40% | Tarifs actualisés intégrés, ROI 25 ans basique. VAN/TRI à implémenter |
| Tests | 🔶 30% | Tests PVGIS, simulation basique. Couverture à améliorer |
| Authentification | ⬜ 10% | Modèle User lié mais pas de login/register UI |
| Déploiement | ⬜ 0% | Local uniquement |

**Score global : ~80%** — MVP fonctionnel, simulation end-to-end opérationnelle.

---

## 🗓 Roadmap

### ✅ Phase 1 — MVP (terminé)
- [x] Architecture Django 7 apps
- [x] Intégration PVGIS 5.3
- [x] Calculateurs de consommation (rapide + expert)
- [x] Profils de consommation personnalisés
- [x] Simulation production solaire 8760h
- [x] Formulaire multi-step avec carte interactive
- [x] Tâche Celery avec progression
- [x] Page résultats avec graphiques Plotly
- [x] Comparaison scénarios actuel/optimisé
- [x] Simulation batterie

### ✅ Phase 2 — Enrichissement (terminé)
- [x] Rapports PDF (WeasyPrint)
- [x] Export Excel
- [x] Profil obligatoire avant simulation
- [x] Orientation Est/Ouest (réparti)
- [x] Tarifs EDF OA actualisés (T1 2026)
- [x] 5 KPIs résultats + bilan solaire détaillé

### 🔜 Phase 3 — Prochaines étapes
- [ ] Authentification complète (login, register, historique simulations)
- [ ] Module financier avancé (VAN, TRI, LCOE, projection détaillée)
- [ ] Prise en compte de l'ombrage (masques solaires)
- [ ] Intégration OpenWeather (prévisions court terme)
- [ ] Comparaison de scénarios (puissances, orientations)
- [ ] Tableau de bord utilisateur (historique projets)

### 🔮 Phase 4 — Production & Monétisation
- [ ] Déploiement (VPS / PaaS)
- [ ] Modèle freemium (simulation gratuite / PDF premium)
- [ ] Optimisation performances (PostgreSQL, cache avancé)
- [ ] Tests automatisés (couverture > 80%)
- [ ] Documentation utilisateur
- [ ] API REST publique

---

## 📝 Licence

Ce projet est sous licence MIT.

---

**Made with ☀️ and ❤️ in France**
