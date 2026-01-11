# 🔄 Guide de Migration vers PVGIS 5.3

## Changements Principaux

### ✅ Ce qui a changé dans PVGIS 5.3

1. **URL de l'API** : `v5_2` → `v5_3`
2. **Endpoint TMY** : Ne supporte **PAS** le paramètre `raddatabase`
3. **Base de données** : SARAH3 disponible (plus récent que SARAH2)
4. **Format de réponse** : Structure JSON légèrement modifiée
5. **Timeout recommandé** : 60s (au lieu de 30s)

### ❌ Paramètres NON supportés par TMY

| Paramètre | TMY | MRcalc | seriescalc |
|-----------|-----|--------|------------|
| `raddatabase` | ❌ | ✅ | ✅ |
| `startyear` | ❌ | ✅ | ✅ |
| `endyear` | ❌ | ✅ | ✅ |
| `usehorizon` | ✅ | ✅ | ✅ |

### ✅ Paramètres SUPPORTÉS par TMY

- `lat` : Latitude ✅
- `lon` : Longitude ✅
- `usehorizon` : Utiliser l'horizon (0 ou 1) ✅
- `userhorizon` : Horizon personnalisé ✅
- `outputformat` : Format de sortie (json, csv) ✅

---

## 📋 Étapes de Migration

### Étape 1 : Remplacer pvgis.py

Le nouveau fichier `weather/services/pvgis.py` a été mis à jour avec :

- ✅ URL : `https://re.jrc.ec.europa.eu/api/v5_3`
- ✅ Suppression de `raddatabase` pour TMY
- ✅ Ajout de `usehorizon=1` (recommandé)
- ✅ Parsing amélioré compatible 5.3
- ✅ Meilleure gestion d'erreurs
- ✅ Timeout de 60s
- ✅ User-Agent personnalisé

**Action :** Copier le contenu de l'artifact `weather/services/pvgis.py` dans ton fichier.

---

### Étape 2 : Tester la découverte

```cmd
python test_pvgis_v53_discovery.py
```

Ce script va :
1. Tester différentes URLs (v5_3, v5_2, sans version)
2. Afficher la structure de la réponse
3. Sauvegarder la réponse JSON dans `pvgis_response_*.json`
4. Identifier quelle URL fonctionne

**✅ Résultat attendu :**
```
✅ L'URL qui fonctionne : https://re.jrc.ec.europa.eu/api/v5_3/tmy
```

---

### Étape 3 : Tester le client mis à jour

```cmd
python test_pvgis_simple.py
```

**✅ Résultat attendu avec PVGIS 5.3 :**
```
================================================================================
TEST DIRECT API PVGIS
================================================================================

Localisation : Lyon (45.75°N, 4.85°E)

🌐 URL: https://re.jrc.ec.europa.eu/api/v5_3/tmy
📋 Paramètres: {'lat': 45.75, 'lon': 4.85, 'outputformat': 'json'}

🚀 Envoi de la requête...
✅ Status code: 200

✅ Nombre d'heures: 8760

🎉 API PVGIS 5.3 FONCTIONNE !
```

---

### Étape 4 : Tester l'intégration Django

```cmd
python test_pvgis.py
```

**✅ Tous les tests doivent passer maintenant !**

---

## 🔍 Différences PVGIS 5.2 vs 5.3

### Format de Réponse

#### PVGIS 5.2 (ancien)
```json
{
  "outputs": {
    "tmy_hourly": [
      {
        "time(UTC)": "20050101:0010",
        "T2m": 2.1,
        "G(h)": 0,
        ...
      }
    ]
  }
}
```

#### PVGIS 5.3 (nouveau)
```json
{
  "inputs": {
    "location": {...}
  },
  "outputs": {
    "tmy_hourly": [
      {
        "time(UTC)": "20050101:0010",
        "T2m": 2.1,
        "G(h)": 0,
        ...
      }
    ]
  },
  "meta": {...}
}
```

**Note :** Structure similaire mais avec section `inputs` et `meta` en plus.

---

### Bases de Données Disponibles

| Base | PVGIS 5.2 | PVGIS 5.3 | Couverture | Période |
|------|-----------|-----------|------------|---------|
| SARAH2 | ✅ | ✅ | Europe, Afrique, Asie | 2005-2020 |
| SARAH3 | ❌ | ✅ | Europe, Afrique, Asie | 2005-2022 |
| NSRDB | ✅ | ✅ | Amériques | 1998-2020 |
| ERA5 | ✅ | ✅ | Mondial | 2005-2020 |

**SARAH3 est recommandé** car plus récent (jusqu'en 2022).

---

## ⚠️ Points d'Attention

### 1. Timeout augmenté

PVGIS 5.3 peut être plus lent. Le timeout a été augmenté :
- Ancien : 30 secondes
- Nouveau : **60 secondes**

### 2. Cache Django

Les données en cache de PVGIS 5.2 sont **incompatibles** avec 5.3.

**Solution :** Vider le cache :

```python
# Dans Django shell
python manage.py shell

from weather.models import PVGISData
PVGISData.objects.all().delete()
```

Ou via l'admin Django :
- Aller dans WEATHER → Données PVGIS
- Sélectionner tout → Supprimer

### 3. Format des Colonnes

PVGIS 5.3 utilise les mêmes noms de colonnes :
- `G(h)` → GHI
- `Gb(n)` → DNI
- `Gd(h)` → DHI
- `T2m` → Température

Le parsing a été amélioré pour gérer les variations.

---

## 🔧 Dépannage

### Erreur : 400 BAD REQUEST

**Cause :** Paramètres invalides

**Solutions :**
1. ✅ Vérifier que `raddatabase` n'est PAS dans les paramètres TMY
2. ✅ Vérifier l'URL : doit être `/api/v5_3/tmy`
3. ✅ Vérifier les coordonnées : -90≤lat≤90, -180≤lon≤180

### Erreur : 404 NOT FOUND

**Cause :** URL incorrecte

**Solution :** Utiliser exactement `https://re.jrc.ec.europa.eu/api/v5_3/tmy`

### Erreur : Timeout

**Cause :** PVGIS lent ou problème réseau

**Solutions :**
1. Augmenter le timeout (déjà fait : 60s)
2. Vérifier la connexion Internet
3. Réessayer plus tard (PVGIS peut être surchargé)

### Erreur : Parsing JSON

**Cause :** Structure de réponse inattendue

**Solution :** 
1. Lancer `test_pvgis_v53_discovery.py`
2. Examiner le fichier `pvgis_response_*.json`
3. Vérifier la structure dans les logs

---

## 📊 Tests de Validation

### Checklist Complète

- [ ] Script de découverte exécuté
- [ ] URL v5_3 confirmée fonctionnelle
- [ ] Fichier `pvgis.py` mis à jour
- [ ] Cache Django vidé
- [ ] Test simple passé (`test_pvgis_simple.py`)
- [ ] Test complet passé (`test_pvgis.py`)
- [ ] Simulation avec PVGIS fonctionne (`test_simulation.py`)
- [ ] Admin Django affiche les données

### Commandes de Test

```cmd
REM 1. Découverte de l'API
python test_pvgis_v53_discovery.py

REM 2. Test simple
python test_pvgis_simple.py

REM 3. Test complet
python test_pvgis.py

REM 4. Test avec simulation
python test_simulation.py
```

---

## 📚 Documentation Officielle

- **Manuel Utilisateur :** https://joint-research-centre.ec.europa.eu/photovoltaic-geographical-information-system-pvgis/getting-started-pvgis/pvgis-user-manual_en
- **API Documentation :** https://joint-research-centre.ec.europa.eu/pvgis-tools/api_en
- **TMY Endpoint :** https://re.jrc.ec.europa.eu/api/v5_3/tmy
- **Changelog :** https://joint-research-centre.ec.europa.eu/pvgis-online-tool/pvgis-releases_en

---

## ✅ Résumé des Modifications

| Fichier | Modification | Raison |
|---------|--------------|--------|
| `pvgis.py` ligne 24 | `v5_2` → `v5_3` | Version actuelle |
| `pvgis.py` ligne 68 | Supprimé `raddatabase` | Non supporté par TMY |
| `pvgis.py` ligne 73 | Ajouté `usehorizon` | Recommandé pour précision |
| `pvgis.py` ligne 19 | Timeout 30s → 60s | API plus lente |
| `pvgis.py` ligne 155 | Parsing amélioré | Compatibilité 5.3 |

---

**Une fois ces modifications appliquées, PVGIS 5.3 devrait fonctionner parfaitement !** ✅