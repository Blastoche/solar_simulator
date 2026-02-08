# 📋 Contrats des Modules - Solar Simulator

Documentation des interfaces garanties entre modules.

**Date de création** : Janvier 2025  
**Version** : 1.0  
**Objectif** : Garantir des contrats clairs entre les modules pour faciliter la maintenance et les tests

---

## 🌤️ Module Weather

### Fonction principale
```python
get_normalized_weather_data(latitude: float, longitude: float, use_cache: bool = True)
```

**Contrat garanti** :

**Input** :
- `latitude` : float (-90 à 90)
- `longitude` : float (-180 à 180)
- `use_cache` : boolean (défaut: True)

**Output** :
- `DataFrame` : pandas DataFrame avec 8760 lignes
  - Colonnes : `['timestamp', 'ghi', 'dni', 'dhi', 'temperature', 'vitesse_vent', 'humidite', 'pression', 'direction_vent']`
  - `timestamp` : datetime (année courante normalisée)
  - `ghi` : W/m² (>= 0)
  - `temperature` : °C
  - Pas de valeurs manquantes sur colonnes obligatoires

- `WeatherMetadata` : dataclass avec :
  - `source` : 'api' | 'cache' | 'fallback'
  - `irradiation_annuelle` : float (kWh/m²/an)
  - `latitude` : float
  - `longitude` : float
  - `api_version` : str ('PVGIS 5.3')
  - `retrieved_at` : str (ISO datetime)
  - `cached_until` : str | None (ISO datetime)

**Exceptions** :
- `ValueError` : Coordonnées invalides
- `Exception` : API et cache échouent tous les deux

**Exemple** :
```python
from weather.services import get_normalized_weather_data

df, metadata = get_normalized_weather_data(43.3, 5.37)
print(f"Lignes: {len(df)}")  # 8760
print(f"Irradiation: {metadata.irradiation_annuelle} kWh/m²/an")
```

---

## ☀️ Module Solar_Calc

### Classe SimulationCalculator

#### Méthode : calculate_production_normalized
```python
calculate_production_normalized(weather_data: pd.DataFrame) -> ProductionResult
```

**Contrat garanti** :

**Input** :
- `weather_data` : DataFrame conforme au contrat Weather (8760 lignes)

**Output** : `ProductionResult` (dataclass)
- `annuelle` : float (kWh, > 0)
- `specifique` : float (kWh/kWc)
- `monthly` : List[float] (12 valeurs en kWh)
- `daily` : List[float] (24 valeurs en kW)
- `autoconso_ratio` : float (0-100, %)
- `injection` : float (kWh injectés au réseau)
- `performance_ratio` : float (0-1, PR appliqué)

**Exemple** :
```python
calculator = SimulationCalculator(installation)
production = calculator.calculate_production_normalized(weather_df)
print(f"Production: {production.annuelle} kWh")
print(f"Spécifique: {production.specifique} kWh/kWc")
```

---

#### Méthode : calculate_consumption_normalized
```python
calculate_consumption_normalized(consommation_annuelle: float = None) -> ConsumptionResult
```

**Contrat garanti** :

**Input** :
- `consommation_annuelle` : float optionnel (kWh/an)
  - Si None : utilise `installation.consommation_annuelle` ou valeur par défaut

**Output** : `ConsumptionResult` (dataclass)
- `annuelle` : float (kWh, > 0)
- `monthly` : List[float] (12 valeurs en kWh)
- `daily` : List[float] (24 valeurs en kW)
- `source` : str ('formulaire' | 'installation' | 'defaut')

**Exemple** :
```python
consumption = calculator.calculate_consumption_normalized(6000)
print(f"Consommation: {consumption.annuelle} kWh")
print(f"Source: {consumption.source}")
```

---

#### Méthode : calculate_financial_normalized
```python
calculate_financial_normalized(
    production: ProductionResult, 
    consumption: ConsumptionResult
) -> FinancialResult
```

**Contrat garanti** :

**Input** :
- `production` : ProductionResult (de calculate_production_normalized)
- `consumption` : ConsumptionResult (de calculate_consumption_normalized)

**Output** : `FinancialResult` (dataclass)
- `economie_annuelle` : float (€/an)
- `roi_25ans` : float (€ sur 25 ans)
- `taux_rentabilite` : float (% par an)
- `cout_installation` : float (€)
- `payback_years` : float (années de retour sur investissement, calculé auto)

**Exemple** :
```python
financial = calculator.calculate_financial_normalized(production, consumption)
print(f"Économies: {financial.economie_annuelle}€/an")
print(f"ROI 25 ans: {financial.roi_25ans}€")
print(f"Payback: {financial.payback_years} ans")
```

---

## 🔄 Flux de données complet
```
Frontend (views.py)
    ↓
    Crée Installation + Simulation
    ↓
solar_calc.tasks.run_simulation_task (Celery)
    ↓
┌─────────────────────────────────────────────┐
│  weather.get_normalized_weather_data()      │ → (DataFrame 8760h, WeatherMetadata)
└─────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────┐
│  calculator.calculate_production_normalized │ → ProductionResult
└─────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────┐
│  calculator.calculate_consumption_normalized│ → ConsumptionResult
└─────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────┐
│  calculator.calculate_financial_normalized  │ → FinancialResult
└─────────────────────────────────────────────┘
    ↓
Sauvegarde Resultat (BDD) + Affichage Frontend
```

---

## ✅ Avantages de cette architecture

### 1. **Contrats explicites**
Chaque module garantit la structure de ses sorties. Plus de surprise sur le format des données.

### 2. **Validation automatique**
Les fonctions `validate_*()` détectent immédiatement les erreurs de structure.

### 3. **Documentation intégrée**
Le code est autodocumenté grâce aux dataclasses et docstrings.

### 4. **Rétrocompatibilité**
Les anciennes fonctions (`calculate_production`, etc.) existent toujours. Migration progressive possible.

### 5. **Testabilité**
Chaque module peut être testé isolément avec des données mockées.

### 6. **Type hints**
Les dataclasses offrent un typage fort, détectable par les IDE.

---

## 🧪 Tests recommandés

### Test Weather
```python
from weather.services import get_normalized_weather_data
from weather.contracts import WeatherMetadata

df, metadata = get_normalized_weather_data(43.3, 5.37)
assert len(df) == 8760
assert isinstance(metadata, WeatherMetadata)
assert metadata.irradiation_annuelle > 0
```

### Test Solar_calc
```python
from solar_calc.services.calculator import SimulationCalculator
from solar_calc.contracts import ProductionResult

calculator = SimulationCalculator(installation)
production = calculator.calculate_production_normalized(weather_df)
assert isinstance(production, ProductionResult)
assert production.annuelle > 0
assert len(production.monthly) == 12
assert len(production.daily) == 24
```

---

## 📅 Évolutions futures

### Phase 2
- [ ] `battery/contracts.py` → Contrats pour module batterie
- [ ] `financial/contracts.py` → Contrats pour analyses économiques avancées
- [ ] `reporting/contracts.py` → Contrats pour génération de rapports

### Phase 3
- [ ] Moteur central `core/simulation_engine.py`
- [ ] Orchestration unifiée des modules
- [ ] API REST avec contrats OpenAPI

---

## 🔗 Références

- **PVGIS 5.3** : https://re.jrc.ec.europa.eu/pvg_tools/en/
- **Django Best Practices** : https://docs.djangoproject.com/
- **Python Dataclasses** : https://docs.python.org/3/library/dataclasses.html

---

**Dernière mise à jour** : 30 janvier 2025  
**Auteur** : Bastien Laffargue  
**Projet** : Solar Simulator MVP