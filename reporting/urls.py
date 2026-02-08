"""
URLs pour le module reporting.
"""

from django.urls import path
from .views import DownloadPDFView

app_name = 'reporting'

urlpatterns = [
    path('pdf/<uuid:resultat_id>/', DownloadPDFView.as_view(), name='download_pdf'),
]