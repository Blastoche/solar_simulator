"""
Modèles de Consommation Électrique Résidentielle

Ce module gère les profils de consommation des utilisateurs
et calcule la consommation électrique estimée.

App Django: solar_calc
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import List, Optional, Dict
from datetime import datetime


@dataclass
class Appareil:
    """
    Représente un appareil électrique avec ses caractéristiques.
    """
    nom: str
    puissance_moyenne: float  # en watts
    frequence_journaliere: float = 1.0  # heures d'utilisation par jour
    coefficient_usage: float = 1.0  # coefficient d'ajustement
    classe_energetique: Optional[str] = None  # A+++, A++, A+, A, B, C, D, E, F, G
    age_appareil: Optional[int] = None  # en années
    
    def consommation_annuelle_kwh(self) -> float:
        """
        Calcule la consommation annuelle de l'appareil en kWh.
        
        Returns:
            float: Consommation annuelle en kWh
        """
        consommation = (
            self.puissance_moyenne / 1000  # conversion W → kW
            * self.frequence_journaliere
            * 365
            * self.coefficient_usage
        )
        
        # Ajustement selon la classe énergétique
        if self.classe_energetique:
            facteurs_classe = {
                'A+++': 0.7, 'A++': 0.8, 'A+': 0.9, 'A': 1.0,
                'B': 1.1, 'C': 1.2, 'D': 1.3, 'E': 1.5, 'F': 1.7, 'G': 2.0
            }
            consommation *= facteurs_classe.get(self.classe_energetique, 1.0)
        
        # Ajustement selon l'âge (dégradation)
        if self.age_appareil and self.age_appareil > 5:
            degradation = 1 + (self.age_appareil - 5) * 0.02  # +2% par an après 5 ans
            consommation *= degradation
        
        return round(consommation, 2)


@dataclass
class SystemeChauffage:
    """
    Représente le système de chauffage du logement.
    """
    type_chauffage: str  # "non_electrique", "electrique", "pompe_a_chaleur"
    puissance_nominale: Optional[float] = None  # en kW
    rendement: float = 1.0  # COP pour PAC, rendement sinon
    surface_chauffee: Optional[float] = None  # m²
    
    def consommation_annuelle_kwh(
        self, 
        surface: float, 
        dpe: str, 
        temperature_moyenne: float = 12.0
    ) -> float:
        """
        Calcule la consommation annuelle de chauffage.
        
        Args:
            surface: Surface habitable en m²
            dpe: Diagnostic de Performance Énergétique (A à G)
            temperature_moyenne: Température moyenne annuelle en °C
            
        Returns:
            float: Consommation annuelle en kWh
        """
        if self.type_chauffage == "non_electrique":
            return 0.0
        
        # Consommation de base selon DPE (kWh/m²/an)
        dpe_consommation = {
            'A': 30, 'B': 40, 'C': 50, 'D': 70, 
            'E': 100, 'F': 130, 'G': 180
        }
        
        conso_base = dpe_consommation.get(dpe, 50) * surface
        
        # Ajustement selon la température moyenne
        # Référence : 12°C (moyenne France)
        ajustement_temp = 1 + (12 - temperature_moyenne) * 0.05
        conso_base *= ajustement_temp
        
        # Si pompe à chaleur, diviser par le COP
        if self.type_chauffage == "pompe_a_chaleur":
            conso_base /= self.rendement if self.rendement > 1 else 3.0  # COP moyen
        
        return round(conso_base, 2)


@dataclass
class SystemeECS:
    """
    Représente le système d'Eau Chaude Sanitaire.
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
        
        # Consommation moyenne : 800 kWh/personne/an pour chauffe-eau électrique
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
    Représente une piscine avec ses équipements.
    """
    a_piscine: bool = False
    volume: Optional[float] = None  # en m³
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
            conso_filtration = 0.5  # kW (économie 50%)
        
        jours_utilisation = self.mois_utilisation * 30
        conso_totale = conso_filtration * 8 * jours_utilisation
        
        # Pompe à chaleur piscine
        if self.pompe_chaleur and self.puissance_pac:
            # Utilisation moyenne 4h/jour pendant la saison
            conso_pac = self.puissance_pac * 4 * jours_utilisation
            conso_totale += conso_pac
        
        return round(conso_totale, 2)


@dataclass
class ProfilConsommation:
    """
    Profil complet de consommation électrique d'un logement.
    """
    # Informations du logement
    annee_construction: int
    surface_habitable: float  # m²
    nb_personnes: int
    dpe: str  # Diagnostic Performance Énergétique (A à G)
    adresse: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    altitude: Optional[float] = None
    
    # Équipements électriques de base
    refrigerateur: Optional[Appareil] = None
    congelateur: Optional[Appareil] = None
    plaques_cuisson: Optional[Appareil] = None
    four: Optional[Appareil] = None
    lave_linge: Optional[Appareil] = None
    lave_vaisselle: Optional[Appareil] = None
    seche_linge: Optional[Appareil] = None
    micro_ondes: Optional[Appareil] = None
    
    # Systèmes énergétiques
    chauffage: Optional[SystemeChauffage] = None
    ecs: Optional[SystemeECS] = None
    piscine: Optional[Piscine] = None
    
    # Données météorologiques
    temperature_moyenne_annuelle: float = 12.0
    
    # Autres équipements (à enrichir)
    autres_appareils: List[Appareil] = field(default_factory=list)
    
    def calcul_consommation_base(self) -> float:
        """
        Calcul de la consommation électrique annuelle de base.
        
        Returns:
            float: Consommation annuelle totale en kWh
        """
        consommation_totale = 0.0
        
        # Consommation des appareils électriques
        appareils = [
            self.refrigerateur,
            self.congelateur,
            self.plaques_cuisson,
            self.four,
            self.lave_linge,
            self.lave_vaisselle,
            self.seche_linge,
            self.micro_ondes
        ]
        
        for appareil in appareils:
            if appareil:
                consommation_totale += appareil.consommation_annuelle_kwh()
        
        # Autres appareils
        for appareil in self.autres_appareils:
            consommation_totale += appareil.consommation_annuelle_kwh()
        
        # Chauffage
        if self.chauffage:
            consommation_totale += self.chauffage.consommation_annuelle_kwh(
                self.surface_habitable,
                self.dpe,
                self.temperature_moyenne_annuelle
            )
        
        # ECS
        if self.ecs:
            consommation_totale += self.ecs.consommation_annuelle_kwh(
                self.nb_personnes
            )
        
        # Piscine
        if self.piscine:
            consommation_totale += self.piscine.consommation_annuelle_kwh()
        
        # Consommation de base (éclairage, appareils en veille, etc.)
        # Environ 400 kWh/an/personne
        consommation_base = 400 * self.nb_personnes
        consommation_totale += consommation_base
        
        return round(consommation_totale, 2)
    
    def repartition_consommation(self) -> Dict[str, float]:
        """
        Calcule la répartition de la consommation par poste.
        
        Returns:
            dict: Répartition de la consommation
        """
        repartition = {
            'chauffage': 0.0,
            'ecs': 0.0,
            'electromenager': 0.0,
            'cuisson': 0.0,
            'piscine': 0.0,
            'base': 400 * self.nb_personnes
        }
        
        # Chauffage
        if self.chauffage:
            repartition['chauffage'] = self.chauffage.consommation_annuelle_kwh(
                self.surface_habitable, self.dpe, self.temperature_moyenne_annuelle
            )
        
        # ECS
        if self.ecs:
            repartition['ecs'] = self.ecs.consommation_annuelle_kwh(self.nb_personnes)
        
        # Électroménager
        appareils_electro = [
            self.refrigerateur, self.congelateur, self.lave_linge,
            self.lave_vaisselle, self.seche_linge, self.micro_ondes
        ]
        for app in appareils_electro:
            if app:
                repartition['electromenager'] += app.consommation_annuelle_kwh()
        
        # Cuisson
        if self.plaques_cuisson:
            repartition['cuisson'] += self.plaques_cuisson.consommation_annuelle_kwh()
        if self.four:
            repartition['cuisson'] += self.four.consommation_annuelle_kwh()
        
        # Piscine
        if self.piscine:
            repartition['piscine'] = self.piscine.consommation_annuelle_kwh()
        
        return repartition
    
    def generer_profil_horaire(self) -> pd.DataFrame:
        """
        Génère un profil de consommation horaire simplifié sur une année (8760h).
        
        Returns:
            pd.DataFrame: DataFrame avec colonnes [timestamp, consommation_kw]
        """
        # Créer un index horaire pour une année
        dates = pd.date_range(
            start=f'{datetime.now().year}-01-01',
            periods=8760,
            freq='H'
        )
        
        # Consommation annuelle totale
        conso_totale = self.calcul_consommation_base()
        
        # Répartition de base (simplifié - à améliorer avec profils réels)
        # Pattern journalier simple : creux la nuit, pics matin/soir
        pattern_journalier = np.array([
            0.3, 0.3, 0.3, 0.3, 0.3, 0.4,  # 0h-5h
            0.7, 1.2, 1.0, 0.6, 0.5, 0.6,  # 6h-11h
            0.8, 0.7, 0.5, 0.5, 0.6, 0.9,  # 12h-17h
            1.5, 1.3, 1.1, 0.9, 0.6, 0.4   # 18h-23h
        ])
        
        # Répéter le pattern pour toute l'année
        pattern_annuel = np.tile(pattern_journalier, 365)
        
        # Normaliser pour correspondre à la consommation totale
        pattern_normalise = pattern_annuel / pattern_annuel.sum() * conso_totale
        
        # Créer le DataFrame
        df = pd.DataFrame({
            'timestamp': dates,
            'consommation_kw': pattern_normalise
        })
        
        return df


def creer_profil_standard() -> ProfilConsommation:
    """
    Créer un profil de consommation standard français (maison type).
    
    Returns:
        ProfilConsommation: Profil standard
    """
    return ProfilConsommation(
        annee_construction=2015,
        surface_habitable=100,
        nb_personnes=3,
        dpe='C',
        refrigerateur=Appareil(
            nom="Réfrigérateur Combiné",
            puissance_moyenne=150,
            frequence_journaliere=24,
            classe_energetique='A++'
        ),
        congelateur=Appareil(
            nom="Congélateur Coffre",
            puissance_moyenne=200,
            frequence_journaliere=24,
            classe_energetique='A+'
        ),
        plaques_cuisson=Appareil(
            nom="Plaques à Induction",
            puissance_moyenne=2200,
            frequence_journaliere=1.5
        ),
        four=Appareil(
            nom="Four Électrique",
            puissance_moyenne=2000,
            frequence_journaliere=0.5
        ),
        lave_linge=Appareil(
            nom="Lave-linge",
            puissance_moyenne=2000,
            frequence_journaliere=0.5,
            classe_energetique='A+++'
        ),
        lave_vaisselle=Appareil(
            nom="Lave-vaisselle",
            puissance_moyenne=1800,
            frequence_journaliere=0.4,
            classe_energetique='A++'
        ),
        chauffage=SystemeChauffage(
            type_chauffage="electrique",
            puissance_nominale=9.0
        ),
        ecs=SystemeECS(
            type_ecs="electrique",
            volume_stockage=200
        )
    )


def main():
    """
    Exemple d'utilisation du module.
    """
    print("=" * 80)
    print("PROFIL DE CONSOMMATION - EXEMPLE")
    print("=" * 80)
    
    # Créer un profil standard
    profil = creer_profil_standard()
    
    # Calculer la consommation annuelle
    consommation_annuelle = profil.calcul_consommation_base()
    print(f"\nConsommation électrique annuelle estimée : {consommation_annuelle:,.0f} kWh")
    
    # Répartition par poste
    print("\nRépartition de la consommation :")
    repartition = profil.repartition_consommation()
    for poste, conso in repartition.items():
        if conso > 0:
            pourcentage = (conso / consommation_annuelle) * 100
            print(f"  {poste.capitalize():<20}: {conso:>8,.0f} kWh ({pourcentage:>5.1f}%)")
    
    # Générer profil horaire
    print("\nGénération du profil horaire (8760h)...")
    profil_horaire = profil.generer_profil_horaire()
    print(f"  Premières heures :")
    print(profil_horaire.head(10))
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()