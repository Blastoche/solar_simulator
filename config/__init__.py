# config/__init__.py
"""
Ce fichier fait de config un package Python et
importe l'application Celery pour la rendre disponible partout.
"""

# Importer l'application Celery pour que Django la charge au démarrage
from .celery import app as celery_app

__all__ = ('celery_app',)