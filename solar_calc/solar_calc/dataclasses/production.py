"""
Modèle de Production Solaire Photovoltaïque

Ce module gère les calculs de production solaire basés sur les standards IEA
et les données météorologiques (PVGIS, OpenWeather, Solcast).

App Django: solar_calc
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Tuple
from datetime import datetime
from enum import Enum


class TypeOnduleur(Enum):
    """Types d'onduleurs disponibles."""
    CENTRAL = "central"
    MICRO_ONDULEUR = "micro_onduleur"
    OPTIMISEURS = "optimiseurs"


class TechnologiePanneau(Enum):
    """Technologies de panneaux disponibles."""
    MONOCRISTALLIN = "monocristallin"
    POLYCRISTALLIN = "polycristallin"
    PERC = "perc"
    HJT = "hjt"  # Heterojunction
    TANDEM = "tandem"


@dataclass
class CaracteristiquesPanneau:
    """
    Caractéristiques techniques d'un panneau photovoltaïque.
    """
    modele: str
    fabricant: str
    puissance_crete_wc: float  # Puissance crête en Wc (Watts crête)
    technologie: TechnologiePanneau
    rendement_stc: float  # Rendement en conditions STC (%)
    coefficient_temperature: float = -0.35  # %/°C (typique pour monocristallin)
    dimensions_m: Tuple[float, float] = (1.7, 1.0)  # (largeur, hauteur) en m
    garantie_performance_ans: int = 25
    degradation_annuelle: float = 0.5  # % par an
    
    @property
    def surface_m2(self) -> float:
        """Surface du panneau en m²."""
        return self.dimensions_m[0] * self.dimensions_m[1]
    
    @property
    def rendement_decimal(self) -> float:
        """Rendement en décimal (ex: 0.22 pour 22%)."""
        return self.rendement_stc / 100
    
    def puissance_avec_degradation(self, annees: int) -> float:
        """
        Calcule la puissance du panneau après dégradation.
        
        Args:
            annees: Nombre d'années d'utilisation
            
        Returns:
            float: Puissance en Wc après dégradation
        """
        facteur_degradation = (1 - self.degradation_annuelle / 100) ** annees
        return self.puissance_crete_wc * facteur_degradation


@dataclass
class ConfigurationOnduleur:
    """
    Configuration de l'onduleur ou des micro-onduleurs.
    """
    type_onduleur: TypeOnduleur
    puissance_nominale_kw: float
    rendement_europeen: float = 0.97  # Rendement européen typique
    rendement_max: float = 0.98
    facteur_dimensionnement: float = 1.0  # Ratio DC/AC
    
    def rendement_effectif(self, charge_pct: float) -> float:
        """
        Calcule le rendement effectif de l'onduleur selon la charge.
        
        Args:
            charge_pct: Charge en % de la puissance nominale
            
        Returns:
            float: Rendement effectif (0-1)
        """
        # Courbe de rendement simplifiée
        if charge_pct < 5:
            return 0.85
        elif charge_pct < 10:
            return 0.92
        elif 10 <= charge_pct <= 50:
            return self.rendement_max
        elif 50 < charge_pct <= 100:
            return self.rendement_europeen
        else:  # Surcharge
            return max(0.90, self.rendement_europeen * 0.95)


@dataclass
class DonneesGeographiques:
    """
    Données géographiques et d'orientation de l'installation.
    """
    latitude: float  # Degrés décimaux
    longitude: float  # Degrés décimaux
    altitude: float = 0.0  # Mètres
    orientation_azimut: float = 180.0  # 0=Nord, 90=Est, 180=Sud, 270=Ouest
    inclinaison_degres: float = 30.0  # Angle d'inclinaison des panneaux
    facteur_ombrage: float = 1.0  # 1.0 = pas d'ombrage, 0.0 = ombrage total
    albedo: float = 0.2  # Réflectivité du sol (0.2 typique)
    
    def orientation_optimale(self) -> Tuple[float, float]:
        """
        Retourne l'orientation optimale pour la latitude.
        
        Returns:
            Tuple[float, float]: (azimut, inclinaison) optimaux
        """
        # Azimut optimal : 180° (plein sud dans hémisphère nord)
        azimut_optimal = 180.0 if self.latitude >= 0 else 0.0
        
        # Inclinaison optimale ≈ latitude (simplifié)
        inclinaison_optimale = abs(self.latitude)
        
        return (azimut_optimal, inclinaison_optimale)
    
    def perte_orientation(self) -> float:
        """
        Calcule les pertes dues à l'orientation non optimale.
        
        Returns:
            float: Facteur de perte (1.0 = optimal, <1.0 = pertes)
        """
        azimut_opt, inclinaison_opt = self.orientation_optimale()
        
        # Calcul simplifié des pertes
        # Pertes d'azimut : max 30% si complètement à l'opposé
        diff_azimut = abs(self.orientation_azimut - azimut_opt)
        if diff_azimut > 180:
            diff_azimut = 360 - diff_azimut
        perte_azimut = 1 - (diff_azimut / 180) * 0.3
        
        # Pertes d'inclinaison : max 20% si à plat ou vertical
        diff_inclinaison = abs(self.inclinaison_degres - inclinaison_opt)
        perte_inclinaison = 1 - (diff_inclinaison / 90) * 0.2
        
        return perte_azimut * perte_inclinaison


@dataclass
class DonneesMeteo:
    """
    Données météorologiques pour le calcul de production.
    """
    timestamp: datetime
    irradiance_ghi: float  # Global Horizontal Irradiance (W/m²)
    irradiance_dni: Optional[float] = None  # Direct Normal Irradiance (W/m²)
    irradiance_dhi: Optional[float] = None  # Diffuse Horizontal Irradiance (W/m²)
    temperature_ambiante: float = 25.0  # °C
    vitesse_vent: float = 0.0  # m/s
    couverture_nuageuse: float = 0.0  # 0-100%
    
    def irradiance_poa(
        self,
        orientation_azimut: float,
        inclinaison: float,
        latitude: float,
        albedo: float = 0.2
    ) -> float:
        """
        Calcule l'irradiance sur le plan incliné (POA - Plane of Array).
        
        Utilise un modèle de transposition simplifié.
        
        Args:
            orientation_azimut: Azimut des panneaux (degrés)
            inclinaison: Inclinaison des panneaux (degrés)
            latitude: Latitude du site (degrés)
            albedo: Albédo du sol
            
        Returns:
            float: Irradiance POA en W/m²
        """
        # Modèle simplifié - À améliorer avec pvlib pour plus de précision
        # Pour l'instant, utilisation d'une approximation basée sur GHI
        
        # Facteur d'inclinaison simplifié
        # Plus l'inclinaison est proche de la latitude, meilleur c'est
        facteur_inclinaison = 1 + (abs(latitude) - inclinaison) / 90 * 0.1
        facteur_inclinaison = max(0.8, min(1.2, facteur_inclinaison))
        
        # Irradiance sur plan incliné (approximation)
        poa = self.irradiance_ghi * facteur_inclinaison
        
        # Ajout de la composante réfléchie (albédo)
        irradiance_reflechie = self.irradiance_ghi * albedo * (1 - np.cos(np.radians(inclinaison))) / 2
        poa += irradiance_reflechie
        
        return max(0, poa)


@dataclass
class SolarInstallation:
    """
    Configuration complète d'une installation solaire.
    """
    nom_installation: str
    panneaux: CaracteristiquesPanneau
    nombre_panneaux: int
    onduleur: ConfigurationOnduleur
    geographie: DonneesGeographiques
    pertes_systeme: Dict[str, float] = field(default_factory=lambda: {
        'cablage': 0.02,  # 2%
        'salissure': 0.03,  # 3%
        'mismatch': 0.02,  # 2%
        'connexions': 0.005,  # 0.5%
        'disponibilite': 0.01  # 1%
    })
    
    @property
    def puissance_crete_totale_kwc(self) -> float:
        """Puissance crête totale de l'installation en kWc."""
        return (self.panneaux.puissance_crete_wc * self.nombre_panneaux) / 1000
    
    @property
    def surface_totale_m2(self) -> float:
        """Surface totale des panneaux en m²."""
        return self.panneaux.surface_m2 * self.nombre_panneaux
    
    @property
    def facteur_pertes_total(self) -> float:
        """Facteur de pertes système total."""
        facteur = 1.0
        for perte in self.pertes_systeme.values():
            facteur *= (1 - perte)
        return facteur
    
    def calculer_production_instantanee(
        self,
        donnees_meteo: DonneesMeteo,
        annee_exploitation: int = 0
    ) -> Dict[str, float]:
        """
        Calcule la production instantanée à partir des données météo.
        
        Args:
            donnees_meteo: Données météorologiques du moment
            annee_exploitation: Année d'exploitation (pour dégradation)
            
        Returns:
            dict: Résultats de production
        """
        # 1. Irradiance sur plan incliné
        poa = donnees_meteo.irradiance_poa(
            self.geographie.orientation_azimut,
            self.geographie.inclinaison_degres,
            self.geographie.latitude,
            self.geographie.albedo
        )
        
        # 2. Température des cellules (modèle Ross)
        # T_cell = T_ambient + (NOCT - 20) * (Irradiance / 800)
        # NOCT typique ≈ 45°C
        noct = 45
        temp_cellules = donnees_meteo.temperature_ambiante + (noct - 20) * (poa / 800)
        
        # Ajustement par le vent (refroidissement)
        if donnees_meteo.vitesse_vent > 0:
            temp_cellules -= donnees_meteo.vitesse_vent * 0.5  # Approximation simple
        
        # 3. Puissance DC avec dégradation
        puissance_panneau = self.panneaux.puissance_avec_degradation(annee_exploitation)
        puissance_dc_stc = puissance_panneau * self.nombre_panneaux / 1000  # kW
        
        # 4. Ajustement pour irradiance et température
        # P = P_stc * (G/G_stc) * [1 + γ * (T_cell - T_stc)]
        # G_stc = 1000 W/m², T_stc = 25°C
        facteur_irradiance = poa / 1000
        facteur_temperature = 1 + (self.panneaux.coefficient_temperature / 100) * (temp_cellules - 25)
        
        puissance_dc = puissance_dc_stc * facteur_irradiance * facteur_temperature
        
        # 5. Application du facteur d'ombrage
        puissance_dc *= self.geographie.facteur_ombrage
        
        # 6. Application des pertes système
        puissance_dc *= self.facteur_pertes_total
        
        # 7. Conversion DC → AC par l'onduleur
        charge_onduleur_pct = (puissance_dc / self.onduleur.puissance_nominale_kw) * 100
        rendement_onduleur = self.onduleur.rendement_effectif(charge_onduleur_pct)
        puissance_ac = puissance_dc * rendement_onduleur
        
        # 8. Écrêtage si dépassement de la puissance onduleur
        puissance_ac = min(puissance_ac, self.onduleur.puissance_nominale_kw)
        
        return {
            'puissance_dc_kw': round(puissance_dc, 3),
            'puissance_ac_kw': round(puissance_ac, 3),
            'irradiance_poa_wm2': round(poa, 2),
            'temperature_cellules_c': round(temp_cellules, 2),
            'rendement_onduleur': round(rendement_onduleur, 4),
            'pertes_totales_pct': round((1 - self.facteur_pertes_total) * 100, 2)
        }
    
    def simuler_annee(self, meteo: pd.DataFrame) -> pd.DataFrame:
        """
        Simule la production AC horaire.
        """
        df = meteo.copy()

        # Puissance crête totale
        puissance_kwc = (
            self.nombre_panneaux *
            self.panneaux.puissance_crete_wc / 1000
        )

        # Rendement global
        performance_ratio = 0.80

        # Conversion irradiance → puissance DC
        df['irradiance_poa_wm2'] = df['ghi']
        df['puissance_dc_kw'] = (
            df['irradiance_poa_wm2'] / 1000
            * puissance_kwc
        )

        # Température (pertes thermiques simples)
        perte_temp = 1 - 0.004 * (df['temperature'] - 25)
        perte_temp = perte_temp.clip(lower=0.85, upper=1.05)

        df['puissance_dc_kw'] *= perte_temp

        # Conversion DC → AC
        df['puissance_ac_kw'] = (
            df['puissance_dc_kw']
            * performance_ratio
        )

        df['puissance_ac_kw'] = df['puissance_ac_kw'].clip(lower=0)

        return df[['timestamp', 'puissance_ac_kw']]

    
    def production_annuelle_estimee(
        self,
        irradiation_annuelle_kwh_m2: float,
        annee_exploitation: int = 0
    ) -> float:
        """
        Estimation rapide de la production annuelle basée sur l'irradiation.
        
        Args:
            irradiation_annuelle_kwh_m2: Irradiation annuelle en kWh/m²/an
            annee_exploitation: Année d'exploitation
            
        Returns:
            float: Production annuelle estimée en kWh
        """
        # Formule simplifiée : E = A * r * H * PR
        # A = surface totale, r = rendement, H = irradiation, PR = performance ratio
        
        puissance_avec_degradation = self.panneaux.puissance_avec_degradation(annee_exploitation)
        puissance_totale_kw = (puissance_avec_degradation * self.nombre_panneaux) / 1000
        
        # Performance Ratio (PR) - ratio entre production réelle et théorique
        # Typiquement entre 0.75 et 0.85 pour une installation bien conçue
        pr = (
            self.facteur_pertes_total
            * self.onduleur.rendement_europeen
            * self.geographie.perte_orientation()
            * self.geographie.facteur_ombrage
        )
        
        # Production annuelle = Puissance * Heures équivalentes plein soleil
        # Heures équivalentes = Irradiation / 1 kW/m²
        heures_equivalent = irradiation_annuelle_kwh_m2
        
        production_annuelle = puissance_totale_kw * heures_equivalent * pr
        
        return round(production_annuelle, 2)


def creer_installation_standard() -> SolarInstallation:
    """
    Crée une installation solaire standard française (résidentiel).
    
    Returns:
        SolarInstallation: Installation de 3 kWc en toiture
    """
    panneaux = CaracteristiquesPanneau(
        modele="JS-500M",
        fabricant="JinkoSolar",
        puissance_crete_wc=500,
        technologie=TechnologiePanneau.PERC,
        rendement_stc=22.0,
        coefficient_temperature=-0.35,
        dimensions_m=(1.722, 1.134)
    )
    
    # 6 panneaux de 500Wc = 3 kWc
    nombre_panneaux = 6
    
    onduleur = ConfigurationOnduleur(
        type_onduleur=TypeOnduleur.CENTRAL,
        puissance_nominale_kw=3.0,
        rendement_europeen=0.97
    )
    
    geographie = DonneesGeographiques(
        latitude=45.75,  # Lyon
        longitude=4.85,
        altitude=200,
        orientation_azimut=180,  # Plein sud
        inclinaison_degres=35,
        facteur_ombrage=0.95  # Léger ombrage
    )
    
    return SolarInstallation(
        nom_installation="Installation résidentielle standard 3kWc",
        panneaux=panneaux,
        nombre_panneaux=nombre_panneaux,
        onduleur=onduleur,
        geographie=geographie
    )


def main():
    """
    Exemple d'utilisation du module.
    """
    print("=" * 80)
    print("MODÈLE DE PRODUCTION SOLAIRE - EXEMPLE")
    print("=" * 80)
    
    # Créer une installation standard
    installation = creer_installation_standard()
    
    print(f"\nConfiguration de l'installation :")
    print(f"  Nom : {installation.nom_installation}")
    print(f"  Puissance crête : {installation.puissance_crete_totale_kwc:.2f} kWc")
    print(f"  Nombre de panneaux : {installation.nombre_panneaux}")
    print(f"  Surface totale : {installation.surface_totale_m2:.2f} m²")
    print(f"  Localisation : {installation.geographie.latitude}°N, {installation.geographie.longitude}°E")
    print(f"  Orientation : {installation.geographie.orientation_azimut}° (azimut)")
    print(f"  Inclinaison : {installation.geographie.inclinaison_degres}°")
    
    # Simulation d'un instant donné
    print("\n" + "-" * 80)
    print("SIMULATION INSTANTANÉE (conditions optimales)")
    print("-" * 80)
    
    meteo_test = DonneesMeteo(
        timestamp=datetime.now(),
        irradiance_ghi=800,  # Belle journée ensoleillée
        temperature_ambiante=25,
        vitesse_vent=2.0
    )
    
    production = installation.calculer_production_instantanee(meteo_test)
    print(f"\nConditions météo :")
    print(f"  Irradiance GHI : {meteo_test.irradiance_ghi} W/m²")
    print(f"  Température : {meteo_test.temperature_ambiante}°C")
    print(f"  Vent : {meteo_test.vitesse_vent} m/s")
    
    print(f"\nProduction :")
    print(f"  Puissance DC : {production['puissance_dc_kw']:.3f} kW")
    print(f"  Puissance AC : {production['puissance_ac_kw']:.3f} kW")
    print(f"  Irradiance POA : {production['irradiance_poa_wm2']:.2f} W/m²")
    print(f"  Température cellules : {production['temperature_cellules_c']:.2f}°C")
    print(f"  Rendement onduleur : {production['rendement_onduleur']:.2%}")
    print(f"  Pertes système : {production['pertes_totales_pct']:.2f}%")
    
    # Estimation annuelle
    print("\n" + "-" * 80)
    print("ESTIMATION PRODUCTION ANNUELLE")
    print("-" * 80)
    
    # Irradiation typique Lyon : ~1400 kWh/m²/an
    irradiation_lyon = 1400
    prod_annuelle = installation.production_annuelle_estimee(irradiation_lyon)
    
    print(f"\nIrradiation annuelle : {irradiation_lyon} kWh/m²/an")
    print(f"Production annuelle estimée : {prod_annuelle:,.0f} kWh")
    print(f"Production spécifique : {prod_annuelle / installation.puissance_crete_totale_kwc:.0f} kWh/kWc/an")
    
    # Simulation sur 25 ans avec dégradation
    print("\n" + "-" * 80)
    print("PRODUCTION SUR 25 ANS (avec dégradation)")
    print("-" * 80)
    
    for annee in [0, 5, 10, 15, 20, 25]:
        prod = installation.production_annuelle_estimee(irradiation_lyon, annee)
        perte_pct = ((installation.production_annuelle_estimee(irradiation_lyon, 0) - prod) / 
                     installation.production_annuelle_estimee(irradiation_lyon, 0)) * 100
        print(f"  Année {annee:2d} : {prod:>7,.0f} kWh (perte : {perte_pct:>4.1f}%)")
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()