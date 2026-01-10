@echo off
REM ============================================================================
REM SOLAR SIMULATOR - SCRIPT DE CONFIGURATION (WINDOWS)
REM ============================================================================
REM Exécuter ce script dans le dossier parent où vous voulez créer le projet
REM Exemple : C:\Users\Bastien LAFFARGUE\Projects\

echo.
echo ========================================
echo   SOLAR SIMULATOR - SETUP
echo ========================================
echo.

REM Vérifier si on est déjà dans solar_simulator
if exist manage.py (
    echo [ATTENTION] Vous etes deja dans le dossier solar_simulator
    echo Ce script va creer la structure des dossiers et fichiers manquants
    echo.
    set IN_PROJECT=1
) else (
    echo Creation du projet Solar Simulator...
    echo.
    set IN_PROJECT=0
)

REM ============================================================================
REM CREATION DES DOSSIERS
REM ============================================================================

echo [1/5] Creation des dossiers...
echo.

REM Dossiers principaux
if not exist docs mkdir docs
if not exist static mkdir static
if not exist static\css mkdir static\css
if not exist static\js mkdir static\js
if not exist static\images mkdir static\images
if not exist media mkdir media
if not exist logs mkdir logs
if not exist reports_output mkdir reports_output

echo   - Dossiers principaux crees

REM Dossiers solar_calc
if not exist solar_calc\models mkdir solar_calc\models
if not exist solar_calc\services mkdir solar_calc\services
if not exist solar_calc\tests mkdir solar_calc\tests
if not exist solar_calc\templates mkdir solar_calc\templates
if not exist solar_calc\templates\solar_calc mkdir solar_calc\templates\solar_calc

echo   - Dossiers solar_calc crees

REM Dossiers weather
if not exist weather\services mkdir weather\services
if not exist weather\tests mkdir weather\tests
if not exist weather\templates mkdir weather\templates
if not exist weather\templates\weather mkdir weather\templates\weather

echo   - Dossiers weather crees

REM Dossiers financial
if not exist financial\services mkdir financial\services
if not exist financial\tests mkdir financial\tests
if not exist financial\templates mkdir financial\templates
if not exist financial\templates\financial mkdir financial\templates\financial

echo   - Dossiers financial crees

REM Dossiers reporting
if not exist reporting\services mkdir reporting\services
if not exist reporting\tests mkdir reporting\tests
if not exist reporting\templates mkdir reporting\templates
if not exist reporting\templates\reporting mkdir reporting\templates\reporting

echo   - Dossiers reporting crees

REM Dossiers frontend
if not exist frontend\templates mkdir frontend\templates
if not exist frontend\templates\frontend mkdir frontend\templates\frontend
if not exist frontend\static mkdir frontend\static
if not exist frontend\static\frontend mkdir frontend\static\frontend
if not exist frontend\static\frontend\css mkdir frontend\static\frontend\css
if not exist frontend\static\frontend\js mkdir frontend\static\frontend\js
if not exist frontend\tests mkdir frontend\tests

echo   - Dossiers frontend crees

REM Dossiers battery (futur)
if not exist battery\services mkdir battery\services
if not exist battery\tests mkdir battery\tests

echo   - Dossiers battery crees

REM Dossiers core
if not exist core\management mkdir core\management
if not exist core\management\commands mkdir core\management\commands
if not exist core\tests mkdir core\tests

echo   - Dossiers core crees

echo.
echo [OK] Tous les dossiers ont ete crees !
echo.

REM ============================================================================
REM CREATION DES FICHIERS __init__.py
REM ============================================================================

echo [2/5] Creation des fichiers __init__.py...
echo.

REM solar_calc
type nul > solar_calc\models\__init__.py
type nul > solar_calc\services\__init__.py
type nul > solar_calc\tests\__init__.py

REM weather
type nul > weather\services\__init__.py
type nul > weather\tests\__init__.py

REM financial
type nul > financial\services\__init__.py
type nul > financial\tests\__init__.py

REM reporting
type nul > reporting\services\__init__.py
type nul > reporting\tests\__init__.py

REM battery
type nul > battery\services\__init__.py
type nul > battery\tests\__init__.py

REM frontend
type nul > frontend\tests\__init__.py

REM core
type nul > core\management\__init__.py
type nul > core\management\commands\__init__.py
type nul > core\tests\__init__.py

echo   - Fichiers __init__.py crees
echo.
echo [OK] Fichiers __init__.py crees !
echo.

REM ============================================================================
REM CREATION DES FICHIERS DE BASE
REM ============================================================================

echo [3/5] Creation des fichiers de base...
echo.

REM Créer README.md s'il n'existe pas
if not exist README.md (
    echo # Solar Simulator > README.md
    echo. >> README.md
    echo Simulateur de production solaire photovoltaique >> README.md
    echo   - README.md cree
)

REM Créer .gitignore s'il n'existe pas
if not exist .gitignore (
    echo __pycache__/ > .gitignore
    echo *.py[cod] >> .gitignore
    echo *$py.class >> .gitignore
    echo .env >> .gitignore
    echo venv/ >> .gitignore
    echo .venv/ >> .gitignore
    echo *.sqlite3 >> .gitignore
    echo media/ >> .gitignore
    echo staticfiles/ >> .gitignore
    echo   - .gitignore cree
)

REM Créer .env.example s'il n'existe pas
if not exist .env.example (
    echo DEBUG=True > .env.example
    echo SECRET_KEY=your-secret-key-here >> .env.example
    echo DATABASE_URL=postgresql://user:password@localhost:5432/solar_simulator >> .env.example
    echo   - .env.example cree
)

echo.
echo [OK] Fichiers de base crees !
echo.

REM ============================================================================
REM VERIFICATION DE L'ENVIRONNEMENT VIRTUEL
REM ============================================================================

echo [4/5] Verification de l'environnement virtuel...
echo.

if exist venv\Scripts\activate.bat (
    echo   - Environnement virtuel deja present
) else (
    echo   - Creation de l'environnement virtuel...
    python -m venv venv
    if errorlevel 1 (
        echo [ERREUR] Impossible de creer l'environnement virtuel
        echo Verifiez que Python est installe et dans le PATH
        pause
        exit /b 1
    )
    echo   - Environnement virtuel cree !
)

echo.
echo [OK] Environnement virtuel pret !
echo.

REM ============================================================================
REM AFFICHAGE DE LA STRUCTURE
REM ============================================================================

echo [5/5] Structure du projet :
echo.
echo solar_simulator\
echo   ^|-- config\              (Django settings)
echo   ^|-- core\                (Utilitaires communs)
echo   ^|-- weather\             (APIs meteo)
echo   ^|-- solar_calc\          (Calculs production/conso)
echo   ^|   ^|-- models\         
echo   ^|   ^|   ^|-- consumption.py
echo   ^|   ^|   ^+-- production.py
echo   ^|   ^+-- services\
echo   ^|-- financial\           (Analyses financieres)
echo   ^|-- battery\             (Stockage - futur)
echo   ^|-- reporting\           (Rapports PDF)
echo   ^|-- frontend\            (Interface web)
echo   ^|-- static\              (CSS, JS, images)
echo   ^|-- media\               (Uploads)
echo   ^|-- docs\                (Documentation)
echo   ^|-- logs\                (Fichiers de log)
echo   ^|-- reports_output\      (Rapports generes)
echo   ^|-- venv\                (Environnement virtuel)
echo   ^|-- requirements.txt
echo   ^|-- .env.example
echo   ^|-- .gitignore
echo   ^+-- README.md
echo.

REM ============================================================================
REM INSTRUCTIONS FINALES
REM ============================================================================

echo ========================================
echo   SETUP TERMINE !
echo ========================================
echo.
echo Prochaines etapes :
echo.
echo 1. Activer l'environnement virtuel :
echo    venv\Scripts\activate
echo.
echo 2. Installer les dependances :
echo    pip install -r requirements.txt
echo.
echo 3. Si Django n'est pas encore installe :
echo    pip install django
echo.
echo 4. Creer les apps Django (si pas deja fait) :
echo    python manage.py startapp core
echo    python manage.py startapp weather
echo    python manage.py startapp solar_calc
echo    etc.
echo.
echo 5. Copier les fichiers de calcul :
echo    - consumption.py dans solar_calc\models\
echo    - production.py dans solar_calc\models\
echo.
echo 6. Configurer le fichier .env :
echo    - Copier .env.example vers .env
echo    - Remplir les valeurs
echo.
echo 7. Lancer les migrations :
echo    python manage.py migrate
echo.
echo 8. Creer un superuser :
echo    python manage.py createsuperuser
echo.
echo 9. Lancer le serveur :
echo    python manage.py runserver
echo.
echo ========================================
echo.

pause
