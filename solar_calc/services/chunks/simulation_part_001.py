"""
Service de Simulation Solaire

Ce module gÃ¨re la simulation complÃ¨te d'une installation solaire photovoltaÃ¯que,
incluant le calcul de production, de consommation et d'autoconsommation.

App Django: solar_calc
Auteur: Solar Simulator Team
"""

import pandas as pd
import numpy as np
from datetime import datetime
import logging
from ..dataclasses.consumption import ConsumptionProfile, SystemeChauffage, SystemeECS
from ..dataclasses.production import SolarInstallation, CaracteristiquesPanneau, ConfigurationOnduleur, DonneesGeographiques, TechnologiePanneau, TypeOnduleur

logger = logging.getLogger(__name__)


class SimulationService:
    """
    Service principal de simulation d'installation solaire.
    
    Ce service orchestre :
    - La crÃ©ation des profils de consommation et d'installation
    - La gÃ©nÃ©ration ou rÃ©cupÃ©ration des donnÃ©es mÃ©tÃ©o
    - Le calcul de production solaire
    - Le calcul d'autoconsommation
    - Les simulations avec batterie (optionnel)
    """
    
    def __init__(self):
        """Initialise le service de simulation."""
        self.results = {}

    def creer_profil_consommation_depuis_django(self, django_profile) -> ConsumptionProfile:
        """
        CrÃ©e un profil de consommation Ã  partir d'un modÃ¨le Django.
        
        Args:
            django_profile: Instance de ConsumptionProfileModel
            
        Returns:
            ConsumptionProfile: Profil de consommation dataclass
        """
        chauffage = SystemeChauffage(type_chauffage=django_profile.type_chauffage)
        ecs = SystemeECS(type_ecs=django_profile.type_ecs)

        # Ajouter un champ dans votre modÃ¨le Django ou utiliser une logique
        profile_type = getattr(django_profile, 'profile_type', 'actif_absent')

        profil = ConsumptionProfile(
            annee_construction=django_profile.annee_construction,
            surface_habitable=django_profile.surface_habitable,
            nb_personnes=django_profile.nb_personnes,
            dpe=django_profile.dpe,
            chauffage=chauffage,
            ecs=ecs,
            profile_type=profile_type
        )
        
        return profil

    def creer_installation_depuis_django(self, django_installation) -> SolarInstallation:
        """
        CrÃ©e une installation solaire Ã  partir d'un modÃ¨le Django.
        
        Args:
            django_installation: Instance de SolarInstallationModel
            
        Returns:
            SolarInstallation: Installation solaire dataclass
        """
        # CrÃ©er les caractÃ©ristiques des panneaux
        panneaux = CaracteristiquesPanneau(
            modele=f"Panneau {django_installation.puissance_panneau_wc}Wc",
            fabricant="Standard",
            puissance_crete_wc=django_installation.puissance_panneau_wc,
            technologie=TechnologiePanneau.PERC,
            rendement_stc=22.0
        )
        
        # Mapper le type d'onduleur
        type_onduleur_map = {
            'central': TypeOnduleur.CENTRAL,
            'micro_onduleur': TypeOnduleur.MICRO_ONDULEUR,
            'optimiseurs': TypeOnduleur.OPTIMISEURS
        }
        
        onduleur = ConfigurationOnduleur(
            type_onduleur=type_onduleur_map.get(
                django_installation.type_onduleur, 
                TypeOnduleur.CENTRAL
            ),
            puissance_nominale_kw=django_installation.puissance_onduleur_kw
        )
        
        # CrÃ©er les donnÃ©es gÃ©ographiques
        geographie = DonneesGeographiques(
            latitude=django_installation.latitude,
            longitude=django_installation.longitude,
            altitude=django_installation.altitude,
            orientation_azimut=django_installation.orientation_azimut,
            inclinaison_degres=django_installation.inclinaison_degres,
            facteur_ombrage=django_installation.facteur_ombrage
        )
        
        return SolarInstallation(
            nom_installation=django_installation.nom,
            panneaux=panneaux,
            nombre_panneaux=django_installation.nombre_panneaux,
            onduleur=onduleur,
            geographie=geographie
        )

    def generer_donnees_meteo_simplifiees(
        self, 
        latitude: float, 
        irradiation_annuelle: float = None
    ) -> pd.DataFrame:
        """
        GÃ©nÃ¨re des donnÃ©es mÃ©tÃ©o simplifiÃ©es si PVGIS n'est pas disponible.
        
        Utilise un modÃ¨le sinusoÃ¯dal pour simuler :
        - L'irradiance solaire horaire avec variation jour/nuit
        - La variation saisonniÃ¨re
        - La tempÃ©rature ambiante
        
        Args:
            latitude: Latitude du site (Â°)
            irradiation_annuelle: Irradiation annuelle cible (kWh/mÂ²/an)
                                 Si None, estimÃ©e selon la latitude
            
        Returns:
            pd.DataFrame: DonnÃ©es mÃ©tÃ©o horaires [timestamp, ghi, temperature, vitesse_vent]
        """
        # Estimer l'irradiation selon la latitude si non fournie
        if irradiation_annuelle is None:
            irradiation_annuelle = max(1000, min(1800, 2000 - abs(latitude) * 10))
            logger.info(
                f"ðŸ“¡ Irradiation annuelle estimÃ©e selon latitude: "
                f"{irradiation_annuelle:.0f} kWh/mÂ²/an"
            )

        # CrÃ©er l'index temporel pour une annÃ©e (8760 heures)
        dates = pd.date_range(
            start=f'{datetime.now().year}-01-01',
            periods=8760,
            freq='h'
        )
        
        # GÃ©nÃ©rer le pattern journalier (courbe sinusoÃ¯dale de 6h Ã  18h)
        heures = np.arange(24)
        pattern_jour = np.maximum(0, 800 * np.sin((heures - 6) * np.pi / 12))
        
        # RÃ©pÃ©ter sur toute l'annÃ©e
        irradiance_ghi = np.tile(pattern_jour, 365)
        
        # Ajouter la variation saisonniÃ¨re (maximum en Ã©tÃ©, minimum en hiver)
        jours = np.arange(8760) // 24
        variation_saison = 1 + 0.3 * np.sin((jours - 80) * 2 * np.pi / 365)
        irradiance_ghi *= variation_saison
        
        # Normaliser pour atteindre l'irradiation annuelle cible
        facteur_ajustement = irradiation_annuelle * 1000 / irradiance_ghi.sum()
        irradiance_ghi *= facteur_ajustement
        
        # GÃ©nÃ©rer la tempÃ©rature (variation saisonniÃ¨re)
        temperature = 12 + 10 * np.sin((jours - 80) * 2 * np.pi / 365)
        temperature = np.repeat(temperature, 1)[:8760]

        # CrÃ©er le DataFrame
        df = pd.DataFrame({
            'timestamp': dates,
            'ghi': irradiance_ghi,
            'temperature': temperature,
            'vitesse_vent': 2.0
        })
        
        return df

    def calculer_autoconsommation(
        self, 
        production_horaire: pd.DataFrame, 
        consommation_horaire: pd.DataFrame
    ) -> dict:
        """
        Calcule l'autoconsommation en croisant production et consommation.
        
        Pour chaque heure de l'annÃ©e, dÃ©termine :
        - L'Ã©nergie autoconsommÃ©e (min(production, consommation))
        - L'Ã©nergie injectÃ©e au rÃ©seau (surplus de production)
        - L'Ã©nergie achetÃ©e au rÃ©seau (dÃ©ficit de production)
        
        Args:
            production_horaire: DataFrame avec [timestamp, puissance_ac_kw]
            consommation_horaire: DataFrame avec [timestamp, consommation_kw]
            
        Returns:
