# config/celery.py
"""
Configuration Celery pour Solar Simulator.

Ce fichier configure l'application Celery pour exécuter des tâches asynchrones.
"""

import os
from celery import Celery

# Définir le module de settings Django par défaut
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Créer l'application Celery
app = Celery('solar_simulator')

# Charger la configuration depuis Django settings
# Le namespace 'CELERY' signifie que tous les paramètres Celery
# dans settings.py doivent être préfixés par 'CELERY_'
app.config_from_object('django.conf:settings', namespace='CELERY')

# Découvrir automatiquement les tâches dans tous les fichiers tasks.py
# de toutes les apps Django installées
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Tâche de debug pour tester Celery."""
    print(f'Request: {self.request!r}')
