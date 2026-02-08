"""
Générateur de graphiques pour les rapports PDF.
Utilise matplotlib pour créer des graphiques propres.
"""

import matplotlib
matplotlib.use('Agg')  # Backend sans interface graphique
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
import io
import base64
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

# Configuration style matplotlib
plt.style.use('seaborn-v0_8-darkgrid')
COLORS = {
    'primary': '#667eea',
    'secondary': '#764ba2',
    'success': '#10b981',
    'warning': '#f59e0b',
    'danger': '#ef4444',
    'info': '#3b82f6'
}


class ChartGenerator:
    """
    Générateur de graphiques pour les rapports PDF.
    """
    
    @staticmethod
    def _fig_to_base64(fig) -> str:
        """
        Convertit une figure matplotlib en base64.
        
        Args:
            fig: Figure matplotlib
        
        Returns:
            String base64 de l'image
        """
        buffer = io.BytesIO()
        fig.savefig(buffer, format='png', dpi=150, bbox_inches='tight', facecolor='white')
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.read()).decode()
        plt.close(fig)
        return f"data:image/png;base64,{image_base64}"
    
    @staticmethod
    def generate_monthly_production_chart(monthly_data: List[float]) -> str:
        """
        Génère le graphique de production mensuelle.
        
        Args:
            monthly_data: Liste de 12 valeurs (kWh par mois)
        
        Returns:
            Image en base64
        """
        fig, ax = plt.subplots(figsize=(10, 5))
        
        months = ['Jan', 'Fév', 'Mar', 'Avr', 'Mai', 'Jun',
                  'Jul', 'Aoû', 'Sep', 'Oct', 'Nov', 'Déc']
        
        ax.plot(months, monthly_data, marker='o', linewidth=2.5,
                markersize=8, color=COLORS['primary'], label='Production')
        ax.fill_between(range(12), monthly_data, alpha=0.3, color=COLORS['primary'])
        
        ax.set_xlabel('Mois', fontsize=12, fontweight='bold')
        ax.set_ylabel('Production (kWh)', fontsize=12, fontweight='bold')
        ax.set_title('Production Solaire Mensuelle', fontsize=14, fontweight='bold', pad=20)
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=10)
        
        # Annotations min/max
        max_idx = monthly_data.index(max(monthly_data))
        min_idx = monthly_data.index(min(monthly_data))
        ax.annotate(f'Max: {monthly_data[max_idx]:.0f} kWh',
                   xy=(max_idx, monthly_data[max_idx]),
                   xytext=(10, 10), textcoords='offset points',
                   fontsize=9, color=COLORS['success'],
                   bbox=dict(boxstyle='round,pad=0.5', facecolor='white', edgecolor=COLORS['success']))
        
        return ChartGenerator._fig_to_base64(fig)
    
    @staticmethod
    def generate_production_vs_consumption_chart(
        monthly_production: List[float],
        monthly_consumption: List[float]
    ) -> str:
        """
        Génère le graphique de comparaison production/consommation.
        
        Args:
            monthly_production: Production mensuelle (12 valeurs)
            monthly_consumption: Consommation mensuelle (12 valeurs)
        
        Returns:
            Image en base64
        """
        fig, ax = plt.subplots(figsize=(10, 5))
        
        months = ['Jan', 'Fév', 'Mar', 'Avr', 'Mai', 'Jun',
                  'Jul', 'Aoû', 'Sep', 'Oct', 'Nov', 'Déc']
        x = range(12)
        width = 0.35
        
        bars1 = ax.bar([i - width/2 for i in x], monthly_production,
                       width, label='Production', color=COLORS['warning'], alpha=0.8)
        bars2 = ax.bar([i + width/2 for i in x], monthly_consumption,
                       width, label='Consommation', color=COLORS['info'], alpha=0.8)
        
        ax.set_xlabel('Mois', fontsize=12, fontweight='bold')
        ax.set_ylabel('Énergie (kWh)', fontsize=12, fontweight='bold')
        ax.set_title('Production vs Consommation', fontsize=14, fontweight='bold', pad=20)
        ax.set_xticks(x)
        ax.set_xticklabels(months)
        ax.legend(fontsize=10)
        ax.grid(True, alpha=0.3, axis='y')
        
        return ChartGenerator._fig_to_base64(fig)
    
    @staticmethod
    def generate_roi_evolution_chart(projections: List[Dict]) -> str:
        """
        Génère le graphique d'évolution du ROI sur 25 ans.
        
        Args:
            projections: Liste des projections financières
        
        Returns:
            Image en base64
        """
        fig, ax = plt.subplots(figsize=(10, 5))
        
        annees = [p['annee'] for p in projections]
        cumul = [p['cumul'] for p in projections]
        
        ax.plot(annees, cumul, linewidth=2.5, color=COLORS['success'], label='Économies cumulées')
        ax.fill_between(annees, 0, cumul, alpha=0.3, color=COLORS['success'])
        ax.axhline(y=0, color='red', linestyle='--', linewidth=1, alpha=0.5)
        
        # Marquer le point de retour sur investissement
        for i, c in enumerate(cumul):
            if c > 0:
                ax.plot(annees[i], c, 'ro', markersize=10)
                ax.annotate(f'Payback: Année {annees[i]}',
                           xy=(annees[i], c),
                           xytext=(20, -20), textcoords='offset points',
                           fontsize=10, color='red', fontweight='bold',
                           bbox=dict(boxstyle='round,pad=0.5', facecolor='white', edgecolor='red'),
                           arrowprops=dict(arrowstyle='->', color='red'))
                break
        
        ax.set_xlabel('Année', fontsize=12, fontweight='bold')
        ax.set_ylabel('Économies cumulées (€)', fontsize=12, fontweight='bold')
        ax.set_title('Retour sur Investissement (25 ans)', fontsize=14, fontweight='bold', pad=20)
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=10)
        
        return ChartGenerator._fig_to_base64(fig)
    
    @staticmethod
    def generate_bill_evolution_chart(projections: List[Dict]) -> str:
        """
        Génère le graphique d'évolution des factures (avec/sans solaire).
        
        Args:
            projections: Liste des projections financières (toutes les 25 années)
        
        Returns:
            Image en base64
        """
        fig, ax = plt.subplots(figsize=(10, 5))
        
        # Prendre toutes les années pour une courbe lisse
        annees = [p['annee'] for p in projections]
        facture_sans = [p['facture_sans'] for p in projections]
        facture_avec = [p['facture_avec'] for p in projections]
        
        ax.plot(annees, facture_sans, linewidth=2.5, color=COLORS['danger'],
                label='Sans solaire', linestyle='--')
        ax.plot(annees, facture_avec, linewidth=2.5, color=COLORS['success'],
                label='Avec solaire')
        
        # Zone d'économies
        ax.fill_between(annees, facture_avec, facture_sans,
                       alpha=0.2, color=COLORS['success'], label='Économies')
        
        ax.set_xlabel('Année', fontsize=12, fontweight='bold')
        ax.set_ylabel('Facture annuelle (€)', fontsize=12, fontweight='bold')
        ax.set_title('Évolution de la Facture Électrique', fontsize=14, fontweight='bold', pad=20)
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=10)
        
        return ChartGenerator._fig_to_base64(fig)