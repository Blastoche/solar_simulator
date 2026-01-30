"""
Simulation de batterie heure par heure.
S'intègre avec le DataFrame existant de SimulationService.

VERSION CORRIGÉE : Calcul correct de l'autoconsommation
"""

import logging
import pandas as pd
from typing import Dict
from ..models import BatterySystem

logger = logging.getLogger(__name__)


class BatterySimulationService:
    """
    Simule batterie avec votre DataFrame existant.
    """
    
    @classmethod
    def simulate(
        cls,
        battery: BatterySystem,
        donnees_horaires: pd.DataFrame,
        save_logs: bool = False
    ) -> Dict:
        """
        Simule batterie sur 8760h avec calcul correct de l'autoconsommation.
        
        LOGIQUE CORRIGÉE :
        - Autoconsommation = Énergie produite ET consommée (directe ou via batterie)
        - Charge batterie = Stockage (pas encore autoconsommé)
        - Décharge batterie = Devient autoconsommation quand consommée
        
        Args:
            battery: BatterySystem (config)
            donnees_horaires: DataFrame avec colonnes :
                - puissance_ac_kw (production)
                - consommation_kw (consommation)
                - autoconso_kw (autoconso sans batterie)
                - injection_kw (surplus sans batterie)
                - achat_kw (import sans batterie)
            save_logs: Sauver logs horaires dans DB
        
        Returns:
            {
                'autoconso_total_kwh': float,
                'taux_autoconso_pct': float,
                'surplus_total_kwh': float,
                'import_total_kwh': float,
                'cycles_annuels': int,
                'duree_vie_ans': int,
                'gain_autoconso_pct': float
            }
        """
        
        # Paramètres batterie
        soc = float(battery.capacite_utilisable_kwh) * 0.5  # État initial 50%
        soc_min = float(battery.capacite_utilisable_kwh) * (1 - float(battery.dod_max))
        soc_max = float(battery.capacite_utilisable_kwh)
        efficiency = float(battery.efficacite)
        power_max = float(battery.puissance_max_kw)
        
        # Métriques
        autoconso_total = 0
        surplus_total = 0
        import_total = 0
        energy_cycled = 0
        
        logs = []
        
        # Boucle sur 8760 heures
        for idx, row in donnees_horaires.iterrows():
            prod = row['puissance_ac_kw']
            conso = row['consommation_kw']
            
            # Net = production - consommation
            net = prod - conso
            
            charge_h = 0
            discharge_h = 0
            
            if net > 0:
                # ===== CAS 1 : SURPLUS (Production > Consommation) =====
                # Autoconsommation directe
                autoconso_direct = min(prod, conso)
                surplus = net
                
                # Charger batterie avec le surplus
                charge_possible = min(
                    surplus,
                    soc_max - soc,
                    power_max
                )
                
                if charge_possible > 0:
                    charge_h = charge_possible * efficiency
                    soc += charge_h
                    energy_cycled += charge_h
                    surplus -= charge_possible
                
                # Ce qui reste = surplus vendu au réseau
                surplus_total += surplus
                
                # ✅ CORRECTION : Seule l'autoconso directe compte
                # L'énergie chargée dans la batterie n'est PAS encore autoconsommée
                autoconso_total += autoconso_direct
                
            else:
                # ===== CAS 2 : DÉFICIT (Production < Consommation) =====
                # Autoconsommation directe
                autoconso_direct = min(prod, conso)
                deficit = abs(net)
                
                # Décharger batterie pour combler le déficit
                discharge_possible = min(
                    deficit,
                    soc - soc_min,
                    power_max
                )
                
                if discharge_possible > 0:
                    discharge_h = discharge_possible
                    soc -= discharge_h / efficiency
                    deficit -= discharge_h
                
                # Ce qui reste = acheté au réseau
                import_total += deficit
                
                # ✅ Autoconsommation = directe + énergie de la batterie consommée
                autoconso_total += autoconso_direct + discharge_h
            
            # Logs (optionnel)
            if save_logs:
                logs.append({
                    'hour': idx,
                    'soc_kwh': round(soc, 3),
                    'soc_pct': round((soc / float(battery.capacite_utilisable_kwh)) * 100, 2),
                    'charge_kwh': round(charge_h, 3),
                    'discharge_kwh': round(discharge_h, 3),
                })
        
        # Calculs finaux
        production_total = donnees_horaires['puissance_ac_kw'].sum()
        consommation_total = donnees_horaires['consommation_kw'].sum()
        
        cycles_annuels = energy_cycled / float(battery.capacite_utilisable_kwh)
        duree_vie = battery.cycles_garantis / cycles_annuels if cycles_annuels > 0 else 99
        
        taux_autoconso = (autoconso_total / production_total * 100) if production_total > 0 else 0
        
        # Gain par rapport à sans batterie
        autoconso_sans_batterie = donnees_horaires['autoconso_kw'].sum()
        taux_sans_batterie = (autoconso_sans_batterie / production_total * 100) if production_total > 0 else 0
        gain_autoconso = taux_autoconso - taux_sans_batterie
        
        logger.info(
            f"🔋 Simulation batterie {battery.capacite_kwh}kWh : "
            f"Autoconso {taux_autoconso:.1f}% (+{gain_autoconso:.1f}%), "
            f"Cycles {cycles_annuels:.0f}/an, Durée vie {duree_vie:.0f} ans"
        )
        
        result = {
            'autoconso_total_kwh': round(autoconso_total, 0),
            'taux_autoconso_pct': round(taux_autoconso, 1),
            'surplus_total_kwh': round(surplus_total, 0),
            'import_total_kwh': round(import_total, 0),
            'cycles_annuels': round(cycles_annuels, 0),
            'duree_vie_ans': round(duree_vie, 0),
            'gain_autoconso_pct': round(gain_autoconso, 1),
            'logs': logs if save_logs else []
        }
        
        return result
    
    @classmethod
    def calculate_financial(
        cls,
        battery_result: Dict,
        donnees_sans_batterie: Dict,
        prix_achat_kwh: float = 0.2276,
        prix_vente_kwh: float = 0.13,
        cout_batterie: float = 8000
    ) -> Dict:
        """
        Calcule ROI et économies avec batterie.
        
        Args:
            battery_result: Résultat de simulate()
            donnees_sans_batterie: Résultat sans batterie
            prix_achat_kwh: Prix achat (€/kWh)
            prix_vente_kwh: Prix vente surplus (€/kWh)
            cout_batterie: Coût installation batterie (€)
        
        Returns:
            {
                'economie_annuelle': float,
                'roi_annees': float,
                'gain_vs_sans_batterie': float
            }
        """
        
        # Sans batterie
        achat_sans = donnees_sans_batterie['achat_reseau_kwh']
        surplus_sans = donnees_sans_batterie['injection_reseau_kwh']
        
        cout_sans = achat_sans * prix_achat_kwh
        revenu_sans = surplus_sans * prix_vente_kwh
        balance_sans = cout_sans - revenu_sans
        
        # Avec batterie
        achat_avec = battery_result['import_total_kwh']
        surplus_avec = battery_result['surplus_total_kwh']
        
        cout_avec = achat_avec * prix_achat_kwh
        revenu_avec = surplus_avec * prix_vente_kwh
        balance_avec = cout_avec - revenu_avec
        
        # Économies
        economie_annuelle = balance_sans - balance_avec
        
        # ROI
        roi = cout_batterie / economie_annuelle if economie_annuelle > 0 else 99
        
        return {
            'economie_annuelle': round(economie_annuelle, 2),
            'roi_annees': round(roi, 1),
            'cout_sans_batterie': round(balance_sans, 2),
            'cout_avec_batterie': round(balance_avec + (cout_batterie / 20), 2),  # Amortissement 20 ans
        }