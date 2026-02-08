"""
Vues pour le module reporting.
"""

from django.http import HttpResponse, Http404
from django.shortcuts import get_object_or_404
from django.views import View
from frontend.models import Resultat
from .services.pdf_generator import PDFGenerator
import logging

logger = logging.getLogger(__name__)


class DownloadPDFView(View):
    """
    Vue pour télécharger le rapport PDF d'une simulation.
    """
    
    def get(self, request, resultat_id):
        """
        Génère et renvoie le PDF.
        
        Args:
            resultat_id: UUID du résultat
        """
        try:
            # Récupérer le résultat
            resultat = get_object_or_404(Resultat, id=resultat_id)
            
            # Générer le PDF
            generator = PDFGenerator(resultat)
            pdf_content = generator.generate_rapport_complet()
            
            # Nom du fichier
            installation = resultat.simulation.installation
            filename = f"rapport_solaire_{installation.adresse.replace(' ', '_')[:30]}.pdf"
            
            # Retourner le PDF
            response = HttpResponse(pdf_content, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            
            logger.info(f"✅ PDF téléchargé pour résultat {resultat_id}")
            return response
            
        except Exception as e:
            logger.error(f"❌ Erreur génération PDF: {str(e)}", exc_info=True)
            raise Http404("Impossible de générer le rapport PDF")