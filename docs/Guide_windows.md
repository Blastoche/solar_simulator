# 🪟 Guide des Commandes Windows - Solar Simulator

Guide spécifique pour Windows (PowerShell et CMD)

---

## 📋 Commandes de Base

### Différences Unix vs Windows

| Unix/Linux/Mac | Windows CMD | Windows PowerShell |
|----------------|-------------|-------------------|
| `ls` | `dir` | `ls` ou `dir` |
| `touch file.txt` | `type nul > file.txt` | `New-Item file.txt` |
| `cat file.txt` | `type file.txt` | `Get-Content file.txt` |
| `rm file.txt` | `del file.txt` | `Remove-Item file.txt` |
| `mkdir folder` | `mkdir folder` | `New-Item -Type Directory folder` |
| `cd folder` | `cd folder` | `cd folder` |
| `pwd` | `cd` | `pwd` ou `Get-Location` |
| `clear` | `cls` | `Clear-Host` ou `cls` |

---

## 🚀 Installation du Projet

### Étape 1 : Créer le dossier et naviguer

**CMD / PowerShell :**
```cmd
mkdir solar_simulator
cd solar_simulator
```

### Étape 2 : Créer l'environnement virtuel

**CMD :**
```cmd
python -m venv venv
venv\Scripts\activate.bat
```

**PowerShell :**
```powershell
python -m venv venv
venv\Scripts\Activate.ps1
```

**⚠️ Erreur PowerShell courante :**
Si vous obtenez une erreur de sécurité dans PowerShell :
```powershell
# Exécuter en tant qu'administrateur
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Étape 3 : Installer Django

```cmd
pip install django
```

### Étape 4 : Créer le projet Django

```cmd
django-admin startproject config .
```
**⚠️ Attention au `.` à la fin !** Il place manage.py à la racine.

### Étape 5 : Créer les apps

```cmd
python manage.py startapp core
python manage.py startapp weather
python manage.py startapp solar_calc
python manage.py startapp battery
python manage.py startapp financial
python manage.py startapp reporting
python manage.py startapp frontend
```

---

## 📂 Création de la Structure

### Créer les dossiers

**CMD / PowerShell :**
```cmd
REM Dossiers principaux
mkdir docs
mkdir static\css static\js static\images
mkdir media
mkdir logs
mkdir reports_output

REM solar_calc
mkdir solar_calc\models
mkdir solar_calc\services
mkdir solar_calc\tests

REM weather
mkdir weather\services
mkdir weather\tests

REM financial
mkdir financial\services
mkdir financial\tests

REM reporting
mkdir reporting\services
mkdir reporting\tests

REM frontend
mkdir frontend\templates\frontend
mkdir frontend\static\frontend\css
mkdir frontend\static\frontend\js
mkdir frontend\tests

REM battery
mkdir battery\services
mkdir battery\tests

REM core
mkdir core\management\commands
mkdir core\tests
```

### Créer les fichiers __init__.py

**CMD :**
```cmd
type nul > solar_calc\models\__init__.py
type nul > solar_calc\services\__init__.py
type nul > solar_calc\tests\__init__.py
type nul > weather\services\__init__.py
type nul > weather\tests\__init__.py
type nul > financial\services\__init__.py
type nul > financial\tests\__init__.py
type nul > reporting\services\__init__.py
type nul > reporting\tests\__init__.py
type nul > battery\services\__init__.py
type nul > battery\tests\__init__.py
type nul > frontend\tests\__init__.py
type nul > core\management\__init__.py
type nul > core\management\commands\__init__.py
type nul > core\tests\__init__.py
```

**PowerShell :**
```powershell
New-Item solar_calc\models\__init__.py -ItemType File
New-Item solar_calc\services\__init__.py -ItemType File
New-Item solar_calc\tests\__init__.py -ItemType File
# ... etc
```

---

## 🛠 Script Automatisé

### Utiliser le script setup_project.bat

1. **Télécharger/créer** le fichier `setup_project.bat`
2. **Placer** le fichier dans le dossier où vous voulez créer le projet
3. **Double-cliquer** sur `setup_project.bat`
   
   OU

4. **Exécuter** depuis CMD :
   ```cmd
   setup_project.bat
   ```

Le script va :
- ✅ Créer tous les dossiers
- ✅ Créer tous les fichiers `__init__.py`
- ✅ Créer l'environnement virtuel
- ✅ Créer les fichiers de base (README, .gitignore, .env.example)

---

## 📥 Copier les Fichiers

### Depuis l'explorateur Windows

1. **Ouvrir l'explorateur** : `Win + E`
2. **Naviguer** vers `C:\Users\Bastien LAFFARGUE\solar_simulator`
3. **Créer les dossiers** (si pas déjà fait) :
   - `solar_calc\models\`
4. **Copier** les fichiers :
   - `consumption.py` → `solar_calc\models\consumption.py`
   - `production.py` → `solar_calc\models\production.py`

### Depuis la ligne de commande

**CMD :**
```cmd
REM Si les fichiers sont dans Downloads
copy "%USERPROFILE%\Downloads\consumption.py" solar_calc\models\consumption.py
copy "%USERPROFILE%\Downloads\production.py" solar_calc\models\production.py

REM Si les fichiers sont ailleurs
copy "C:\chemin\vers\consumption.py" solar_calc\models\consumption.py
```

**PowerShell :**
```powershell
Copy-Item "$env:USERPROFILE\Downloads\consumption.py" -Destination "solar_calc\models\consumption.py"
Copy-Item "$env:USERPROFILE\Downloads\production.py" -Destination "solar_calc\models\production.py"
```

---

## 🔧 Installation des Dépendances

### requirements.txt

1. **Créer** le fichier `requirements.txt` à la racine
2. **Copier** le contenu fourni précédemment
3. **Installer** :

```cmd
pip install -r requirements.txt
```

### Mise à jour pip (recommandé)

```cmd
python -m pip install --upgrade pip
```

---

## 🐘 Configuration PostgreSQL (Optionnel)

### Installer PostgreSQL sur Windows

1. **Télécharger** : https://www.postgresql.org/download/windows/
2. **Installer** PostgreSQL (inclut pgAdmin)
3. **Créer la base de données** :

**Via pgAdmin :**
- Ouvrir pgAdmin
- Créer une nouvelle base : `solar_simulator`
- Créer un utilisateur : `solar_user`

**Via psql (CMD) :**
```cmd
psql -U postgres
CREATE DATABASE solar_simulator;
CREATE USER solar_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE solar_simulator TO solar_user;
\q
```

### Alternative : Utiliser SQLite (plus simple)

Dans `.env` :
```env
# Utiliser SQLite au lieu de PostgreSQL
DATABASE_URL=sqlite:///db.sqlite3
```

---

## 🔴 Configuration Redis (Optionnel)

### Installer Redis sur Windows

**Option 1 : WSL2 (Recommandé)**
```powershell
# Installer WSL2
wsl --install

# Dans WSL2 (Ubuntu)
sudo apt update
sudo apt install redis-server
redis-server
```

**Option 2 : Redis Windows (Unofficial)**
- Télécharger : https://github.com/tporadowski/redis/releases
- Installer et lancer `redis-server.exe`

**Option 3 : Sans Redis (Développement)**
Commenter Redis dans `requirements.txt` et utiliser la DB pour le cache.

---

## ⚙️ Configuration Django

### Créer le fichier .env

```cmd
copy .env.example .env
notepad .env
```

Remplir :
```env
DEBUG=True
SECRET_KEY=votre-clé-secrète-générer-en-avec-python
DATABASE_URL=sqlite:///db.sqlite3
ALLOWED_HOSTS=localhost,127.0.0.1
```

### Générer une SECRET_KEY

**Python :**
```cmd
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

**PowerShell :**
```powershell
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

---

## 🚀 Lancer le Projet

### Migrations

```cmd
python manage.py migrate
```

### Créer un superuser

```cmd
python manage.py createsuperuser
```

### Lancer le serveur

```cmd
python manage.py runserver
```

Accéder à : http://localhost:8000

### Lancer Celery (si configuré)

**Terminal 1 - Redis :**
```cmd
redis-server
```

**Terminal 2 - Celery Worker :**
```cmd
celery -A config worker -l info
```

**Terminal 3 - Django :**
```cmd
python manage.py runserver
```

---

## 🐛 Dépannage Windows

### Erreur : "python n'est pas reconnu"

**Solution :**
1. Vérifier que Python est installé : https://www.python.org/downloads/
2. Ajouter Python au PATH :
   - `Win + R` → `sysdm.cpl` → Variables d'environnement
   - Ajouter : `C:\Users\VotreNom\AppData\Local\Programs\Python\Python310`

### Erreur : "pip n'est pas reconnu"

```cmd
python -m ensurepip --upgrade
```

### Erreur PowerShell : "Execution de scripts désactivée"

**En tant qu'administrateur :**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Erreur : "Port 8000 déjà utilisé"

**Tuer le processus :**
```cmd
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

**Ou utiliser un autre port :**
```cmd
python manage.py runserver 8080
```

### Encodage de caractères (accents français)

**Dans les fichiers Python :**
```python
# -*- coding: utf-8 -*-
```

**Dans CMD :**
```cmd
chcp 65001
```

---

## 📝 Éditeurs Recommandés

### Visual Studio Code (Gratuit)
- **Télécharger** : https://code.visualstudio.com/
- **Extensions** :
  - Python (Microsoft)
  - Django (Baptiste Darthenay)
  - GitLens
  - Pylance

### PyCharm Community (Gratuit)
- **Télécharger** : https://www.jetbrains.com/pycharm/download/

---

## 🎯 Commandes Utiles

### Lister les packages installés
```cmd
pip list
```

### Mettre à jour un package
```cmd
pip install --upgrade django
```

### Créer requirements.txt depuis l'environnement
```cmd
pip freeze > requirements.txt
```

### Désactiver l'environnement virtuel
```cmd
deactivate
```

### Nettoyer les fichiers .pyc
```cmd
for /r %i in (*.pyc) do del "%i"
for /r %i in (__pycache__) do rmdir /s /q "%i"
```

**PowerShell :**
```powershell
Get-ChildItem -Recurse -Filter "*.pyc" | Remove-Item
Get-ChildItem -Recurse -Filter "__pycache__" | Remove-Item -Recurse -Force
```

---

## ✅ Checklist Finale

- [ ] Python installé (3.10+)
- [ ] Git installé
- [ ] Environnement virtuel créé
- [ ] Dépendances installées
- [ ] Structure de dossiers créée
- [ ] Fichiers de configuration (.env)
- [ ] Apps Django créées
- [ ] Fichiers de calcul copiés
- [ ] Migrations effectuées
- [ ] Superuser créé
- [ ] Serveur de développement fonctionne

---

**Besoin d'aide ? Consulte le README.md ou ouvre une issue !** 🚀