"""
Service de génération de rapports PDF.
Utilise WeasyPrint pour convertir HTML → PDF.
"""

import logging
from django.template.loader import render_to_string
from django.conf import settings
from weasyprint import HTML, CSS
from weasyprint.text.fonts import FontConfiguration
import os

from financial.services.advanced_calculator import AdvancedFinancialCalculator, calculate_co2_impact
from reporting.services.chart_generator import ChartGenerator

from datetime import datetime

logger = logging.getLogger(__name__)


class PDFGenerator:
    """
    Générateur de rapports PDF pour les simulations solaires.
    """
    
    def __init__(self, resultat):
        """
        Initialise le générateur avec un résultat de simulation.
        
        Args:
            resultat: Objet Resultat Django
        """
        self.resultat = resultat
        self.installation = resultat.simulation.installation if hasattr(resultat, 'simulation') else None
        
    def generate_rapport_complet(self):
        """
        Génère un rapport PDF complet.
        
        Returns:
            bytes: Contenu du PDF
        """
        logger.info(f"🔄 Génération PDF pour résultat {self.resultat.id}")
        
        # Préparer les données pour le template
        context = self._prepare_context()
        
        # Générer HTML depuis template
        html_string = render_to_string('reporting/pdf_rapport.html', context)
        
        # Convertir HTML → PDF
        font_config = FontConfiguration()
        
        # Créer le PDF
        pdf_file = HTML(string=html_string, base_url=settings.STATIC_URL).write_pdf(
            font_config=font_config
        )
        
        logger.info(f"✅ PDF généré : {len(pdf_file)} bytes")
        return pdf_file
    
    def _prepare_context(self):
        """
        Prépare le contexte pour le template PDF.
        
        Returns:
            dict: Contexte avec toutes les données
        """
        # ===== CALCULS FINANCIERS AVANCÉS =====
        advanced_calc = AdvancedFinancialCalculator(
            puissance_kwc=float(self.installation.puissance_kw) if self.installation else 4.0,
            production_annuelle=self.resultat.production_annuelle_kwh,
            consommation_annuelle=self.resultat.consommation_annuelle_kwh,
            autoconso_ratio=self.resultat.autoconsommation_ratio,
            injection_reseau=self.resultat.injection_reseau_kwh
        )
        
        # Projections 25 ans
        projections_25ans = advanced_calc.calculate_25_years_projection()
        
        # Métriques résumées
        summary_metrics = advanced_calc.get_summary_metrics()
        
        # Tableau de projection (années clés)
        projection_table = advanced_calc.get_projection_table_data()
        
        # Données complètes pour graphiques (toutes les 25 années)
        all_projections_for_charts = [
            {
                'annee': p.annee,
                'facture_sans': p.facture_sans_solaire,
                'facture_avec': p.facture_avec_solaire,
                'cumul': p.economie_cumulee
            }
            for p in projections_25ans
        ]
        
        # ===== IMPACT CO2 =====
        co2_impact = calculate_co2_impact(self.resultat.production_annuelle_kwh)
        
        # ===== GÉNÉRATION DES GRAPHIQUES =====
        chart_gen = ChartGenerator()
        
        try:
            chart_monthly_prod = chart_gen.generate_monthly_production_chart(
                self.resultat.production_mensuelle_kwh
            )
        except Exception as e:
            logger.error(f"Erreur génération graphique production: {e}")
            chart_monthly_prod = None
        
        try:
            chart_prod_vs_conso = chart_gen.generate_production_vs_consumption_chart(
                self.resultat.production_mensuelle_kwh,
                self.resultat.consommation_mensuelle_kwh
            )
        except Exception as e:
            logger.error(f"Erreur génération graphique prod vs conso: {e}")
            chart_prod_vs_conso = None
        
        try:
            chart_roi = chart_gen.generate_roi_evolution_chart(all_projections_for_charts)
        except Exception as e:
            logger.error(f"Erreur génération graphique ROI: {e}")
            chart_roi = None
        
        try:
            chart_facture = chart_gen.generate_bill_evolution_chart(all_projections_for_charts)
        except Exception as e:
            logger.error(f"Erreur génération graphique facture: {e}")
            chart_facture = None
        
        # ===== CONTEXTE POUR LE TEMPLATE =====
        context = {
            # Métadonnées
            'date_generation': datetime.now().strftime('%d/%m/%Y'),
            'titre': 'Rapport de Simulation Solaire',
            
            # Installation
            'installation': {
                'adresse': self.installation.adresse if self.installation else 'N/A',
                'puissance_kwc': float(self.installation.puissance_kw) if self.installation else 0,
                'orientation': self._get_orientation_label(),
                'inclinaison': f"{int(float(self.installation.inclinaison))}°" if self.installation else 'N/A',
                'latitude': round(float(self.installation.latitude), 2) if self.installation else 0,
                'longitude': round(float(self.installation.longitude), 2) if self.installation else 0,
            },
            
            # Production
            'production': {
                'annuelle': round(self.resultat.production_annuelle_kwh, 0),
                'specifique': round(self.resultat.production_annuelle_kwh / float(self.installation.puissance_kw), 0) if self.installation else 0,
                'mensuelle': self.resultat.production_mensuelle_kwh,
                'horaire': self.resultat.production_horaire_kwh,
            },
            
            # Consommation
            'consommation': {
                'annuelle': round(self.resultat.consommation_annuelle_kwh, 0),
                'mensuelle': self.resultat.consommation_mensuelle_kwh,
                'horaire': self.resultat.consommation_horaire_kwh,
            },
            
            # Autoconsommation
            'autoconsommation': {
                'ratio': round(self.resultat.autoconsommation_ratio, 1),
                'energie': round(self.resultat.production_annuelle_kwh * self.resultat.autoconsommation_ratio / 100, 0),
                'injection': round(self.resultat.injection_reseau_kwh, 0),
            },
            
            # Financier (ancien - pour compatibilité)
            'financier': {
                'economie_annuelle': round(self.resultat.economie_annuelle_euros, 0),
                'roi_25ans': round(self.resultat.roi_25ans_euros, 0),
                'taux_rentabilite': round(self.resultat.taux_rentabilite_pct, 1),
                'cout_installation': round(summary_metrics['cout_installation'], 0),
                'payback': round(summary_metrics['payback_years'], 1),
            },
            
            # Financier AVANCÉ (nouveau)
            'financier_avance': {
                'cout_installation': summary_metrics['cout_installation'],
                'prime_autoconso': summary_metrics['prime_autoconso'],
                'investissement_net': summary_metrics['investissement_net'],
                'economie_an1': summary_metrics['economie_annuelle_an1'],
                'economie_an25': summary_metrics['economie_annuelle_an25'],
                'economie_totale': summary_metrics['economie_totale_25ans'],
                'payback_years': summary_metrics['payback_years'],
                'taux_rentabilite': summary_metrics['taux_rentabilite'],
            },
            
            # Tableau de projection
            'projection_table': projection_table,
            
            # Impact environnemental
            'co2': {
                'annuel_kg': co2_impact['co2_evite_annuel_kg'],
                'total_tonnes': co2_impact['co2_evite_25ans_tonnes'],
                'km_voiture': co2_impact['equivalent_km_voiture'],
                'arbres': co2_impact['equivalent_arbres'],
            },
            
            # Graphiques (base64)
            'charts': {
                'monthly_production': chart_monthly_prod,
                'prod_vs_conso': chart_prod_vs_conso,
                'roi_evolution': chart_roi,
                'bill_evolution': chart_facture,
            },
            
            # Batterie (si présente)
            'batterie': self._get_batterie_info(),
        }
        
        return context
    
    def _get_orientation_label(self):
        """Convertit l'angle d'orientation en label."""
        if not self.installation:
            return 'N/A'
        
        # Convertir en float pour gérer les strings
        try:
            angle = float(self.installation.orientation)
        except (ValueError, TypeError):
            return 'Non renseignée'
        
        # Convertir angle en direction cardinale
        if 337.5 <= angle or angle < 22.5:
            return 'Nord (0°)'
        elif 22.5 <= angle < 67.5:
            return f'Nord-Est ({int(angle)}°)'
        elif 67.5 <= angle < 112.5:
            return f'Est ({int(angle)}°)'
        elif 112.5 <= angle < 157.5:
            return f'Sud-Est ({int(angle)}°)'
        elif 157.5 <= angle < 202.5:
            return f'Sud ({int(angle)}°)'
        elif 202.5 <= angle < 247.5:
            return f'Sud-Ouest ({int(angle)}°)'
        elif 247.5 <= angle < 292.5:
            return f'Ouest ({int(angle)}°)'
        else:
            return f'Nord-Ouest ({int(angle)}°)'
    
    def _get_batterie_info(self):
        """Récupère les infos batterie si disponibles."""
        if not self.installation or not hasattr(self.installation, 'avec_batterie'):
            return None
        
        if not self.installation.avec_batterie:
            return None
        
        # TODO: Récupérer vraies données batterie depuis le module battery
        return {
            'presente': True,
            'capacite': 10,  # kWh - placeholder
            'autonomie': 1.5,  # jours - placeholder
        }


def generate_pdf_for_resultat(resultat_id):
    """
    Fonction helper pour générer un PDF depuis un ID de résultat.
    
    Args:
        resultat_id: UUID du résultat
    
    Returns:
        bytes: Contenu du PDF
    """
    from frontend.models import Resultat
    
    resultat = Resultat.objects.get(id=resultat_id)
    generator = PDFGenerator(resultat)
    return generator.generate_rapport_complet()