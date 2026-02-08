"""
ModÃ¨les de Consommation Ã‰lectrique RÃ©sidentielle

Ce module gÃ¨re les profils de consommation des utilisateurs
et calcule la consommation Ã©lectrique estimÃ©e.

App Django: solar_calc
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import List, Optional, Dict
from datetime import datetime
from solar_calc.services.consumption_profiles import ConsumptionProfiles


@dataclass
class Appareil:
    """
    ReprÃ©sente un appareil Ã©lectrique avec ses caractÃ©ristiques.
    """
    nom: str
    puissance_moyenne: float  # en watts
    frequence_journaliere: float = 1.0  # heures d'utilisation par jour
    coefficient_usage: float = 1.0  # coefficient d'ajustement
    classe_energetique: Optional[str] = None  # A+++, A++, A+, A, B, C, D, E, F, G
    age_appareil: Optional[int] = None  # en annÃ©es
    
    def consommation_annuelle_kwh(self) -> float:
        """
        Calcule la consommation annuelle de l'appareil en kWh.
        
        Returns:
            float: Consommation annuelle en kWh
        """
        consommation = (
            self.puissance_moyenne / 1000  # conversion W â†’ kW
            * self.frequence_journaliere
            * 365
            * self.coefficient_usage
        )
        
        # Ajustement selon la classe Ã©nergÃ©tique
        if self.classe_energetique:
            facteurs_classe = {
                'A+++': 0.7, 'A++': 0.8, 'A+': 0.9, 'A': 1.0,
                'B': 1.1, 'C': 1.2, 'D': 1.3, 'E': 1.5, 'F': 1.7, 'G': 2.0
            }
            consommation *= facteurs_classe.get(self.classe_energetique, 1.0)
        
        # Ajustement selon l'Ã¢ge (dÃ©gradation)
        if self.age_appareil and self.age_appareil > 5:
            degradation = 1 + (self.age_appareil - 5) * 0.02  # +2% par an aprÃ¨s 5 ans
            consommation *= degradation
        
        return round(consommation, 2)


@dataclass
class SystemeChauffage:
    """
    ReprÃ©sente le systÃ¨me de chauffage du logement.
    """
    type_chauffage: str  # "non_electrique", "electrique", "pompe_a_chaleur"
    puissance_nominale: Optional[float] = None  # en kW
    rendement: float = 1.0  # COP pour PAC, rendement sinon
    surface_chauffee: Optional[float] = None  # mÂ²
    
    def consommation_annuelle_kwh(
        self, 
        surface: float, 
        dpe: str, 
        temperature_moyenne: float = 12.0
    ) -> float:
        """
        Calcule la consommation annuelle de chauffage.
        
        Args:
            surface: Surface habitable en mÂ²
            dpe: Diagnostic de Performance Ã‰nergÃ©tique (A Ã  G)
            temperature_moyenne: TempÃ©rature moyenne annuelle en Â°C
            
        Returns:
            float: Consommation annuelle en kWh
        """
        if self.type_chauffage == "non_electrique":
            return 0.0
        
        # Consommation de base selon DPE (kWh/mÂ²/an)
        dpe_consommation = {
            'A': 30, 'B': 40, 'C': 50, 'D': 70, 
            'E': 100, 'F': 130, 'G': 180
        }
        
        conso_base = dpe_consommation.get(dpe, 50) * surface
        
        # Ajustement selon la tempÃ©rature moyenne
        # RÃ©fÃ©rence : 12Â°C (moyenne France)
        ajustement_temp = 1 + (12 - temperature_moyenne) * 0.05
        conso_base *= ajustement_temp
        
        # Si pompe Ã  chaleur, diviser par le COP
        if self.type_chauffage == "pompe_a_chaleur":
            conso_base /= self.rendement if self.rendement > 1 else 3.0  # COP moyen
        
        return round(conso_base, 2)


@dataclass
class SystemeECS:
    """
    ReprÃ©sente le systÃ¨me d'Eau Chaude Sanitaire.
    """
    type_ecs: str  # "non_electrique", "electrique", "thermodynamique"
    volume_stockage: Optional[float] = None  # en litres
    puissance: Optional[float] = None  # en kW
    rendement: float = 1.0  # COP pour thermodynamique
    
    def consommation_annuelle_kwh(self, nb_personnes: int) -> float:
        """
        Calcule la consommation annuelle d'ECS.
        
        Args:
            nb_personnes: Nombre de personnes dans le logement
            
        Returns:
            float: Consommation annuelle en kWh
        """
        if self.type_ecs == "non_electrique":
            return 0.0
        
        # Consommation moyenne : 800 kWh/personne/an pour chauffe-eau Ã©lectrique
        conso_base = 800 * nb_personnes
        
        # Ajustement selon le volume de stockage
        if self.volume_stockage:
            # Pertes thermiques proportionnelles au volume
            pertes = self.volume_stockage * 0.5  # kWh/an/litre
            conso_base += pertes
        
        # Si thermodynamique, diviser par le COP
        if self.type_ecs == "thermodynamique":
            conso_base /= self.rendement if self.rendement > 1 else 2.5  # COP moyen
        
        return round(conso_base, 2)


@dataclass
class Piscine:
    """
    ReprÃ©sente une piscine avec ses Ã©quipements.
    """
    a_piscine: bool = False
    volume: Optional[float] = None  # en mÂ³
    type_filtration: str = "standard"  # "standard", "variable_speed"
    pompe_chaleur: bool = False
    puissance_pac: Optional[float] = None  # en kW
    mois_utilisation: int = 6  # mois d'utilisation par an
    
    def consommation_annuelle_kwh(self) -> float:
        """
        Calcule la consommation annuelle de la piscine.
        
        Returns:
            float: Consommation annuelle en kWh
        """
        if not self.a_piscine or not self.volume:
            return 0.0
        
        # Filtration : environ 8h/jour pendant la saison
        if self.type_filtration == "standard":
            conso_filtration = 1.0  # kW
        else:  # variable_speed
            conso_filtration = 0.5  # kW (Ã©conomie 50%)
        
        jours_utilisation = self.mois_utilisation * 30
        conso_totale = conso_filtration * 8 * jours_utilisation
        
        # Pompe Ã  chaleur piscine
        if self.pompe_chaleur and self.puissance_pac:
            # Utilisation moyenne 4h/jour pendant la saison
            conso_pac = self.puissance_pac * 4 * jours_utilisation
            conso_totale += conso_pac
        
        return round(conso_totale, 2)


@dataclass
class ConsumptionProfile:
    """
    Profil complet de consommation Ã©lectrique d'un logement.
    """
    # Informations du logement
    annee_construction: int
    surface_habitable: float  # mÂ²
    nb_personnes: int
    dpe: str  # Diagnostic Performance Ã‰nergÃ©tique (A Ã  G)
    adresse: Optional[str] = None
    latitude: Optional[float] = None
