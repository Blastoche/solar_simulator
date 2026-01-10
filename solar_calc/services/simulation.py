"""
Service de simulation complète : production + consommation + autoconsommation.

Ce service orchestre les calculs en utilisant les modèles de calcul
(consumption.py et production.py) et les données météo PVGIS.
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, Tuple
import logging

from ..models.consumption import (
    ProfilConsommation,
    Appareil,
    SystemeChauffage,
    SystemeECS,
)
from ..models.production import (
    InstallationSolaire,
    CaracteristiquesPanneau,
    ConfigurationOnduleur,
    DonneesGeographiques,
    DonneesMeteo,
    TechnologiePanneau,
    TypeOnduleur,
)

logger = logging.getLogger(__name__)


class SimulationService:
    """
    Service principal de simulation.
    
    Orchestre :
    1. Récupération données météo (PVGIS)
    2. Calcul de consommation
    3. Calcul de production
    4. Calcul d'autoconsommation
    5. Agrégation des résultats
    """
    
    def __init__(self):
        self.results = {}
    
    def creer_profil_consommation_depuis_django(
        self,
        django_profile
    ) -> ProfilConsommation:
        """
        Convertit un ConsumptionProfile Django en ProfilConsommation (dataclass).
        
        Args:
            django_profile: Instance du modèle Django ConsumptionProfile
            
        Returns:
            ProfilConsommation: Instance de la dataclass de calcul
        """
        # Créer le système de chauffage
        chauffage = SystemeChauffage(
            type_chauffage=django_profile.type_chauffage
        )
        
        # Créer le système ECS
        ecs = SystemeECS(
            type_ecs=django_profile.type_ecs
        )
        
        # Créer le profil de consommation
        profil = ProfilConsommation(
            annee_construction=django_profile.annee_construction,
            surface_habitable=django_profile.surface_habitable,
            nb_personnes=django_profile.nb_personnes,
            dpe=django_profile.dpe,
            chauffage=chauffage,
            ecs=ecs,
            # TODO: Parser appareils_json pour ajouter les appareils
        )
        
        return profil
    
    def creer_installation_depuis_django(
        self,
        django_installation
    ) -> InstallationSolaire:
        """
        Convertit une SolarInstallation Django en InstallationSolaire (dataclass).
        
        Args:
            django_installation: Instance du modèle Django SolarInstallation
            
        Returns:
            InstallationSolaire: Instance de la dataclass de calcul
        """
        # Créer les caractéristiques des panneaux
        panneaux = CaracteristiquesPanneau(
            modele=f"Panneau {django_installation.puissance_panneau_wc}Wc",
            fabricant="Standard",
            puissance_crete_wc=django_installation.puissance_panneau_wc,
            technologie=TechnologiePanneau.PERC,
            rendement_stc=22.0,
        )
        
        # Créer la configuration de l'onduleur
        type_onduleur_map = {
            'central': TypeOnduleur.CENTRAL,
            'micro_onduleur': TypeOnduleur.MICRO_ONDULEUR,
            'optimiseurs': TypeOnduleur.OPTIMISEURS,
        }
        
        onduleur = ConfigurationOnduleur(
            type_onduleur=type_onduleur_map.get(
                django_installation.type_onduleur,
                TypeOnduleur.CENTRAL
            ),
            puissance_nominale_kw=django_installation.puissance_onduleur_kw,
        )
        
        # Créer les données géographiques
        geographie = DonneesGeographiques(
            latitude=django_installation.latitude,
            longitude=django_installation.longitude,
            altitude=django_installation.altitude,
            orientation_azimut=django_installation.orientation_azimut,
            inclinaison_degres=django_installation.inclinaison_degres,
            facteur_ombrage=django_installation.facteur_ombrage,
        )
        
        # Créer l'installation complète
        installation = InstallationSolaire(
            nom_installation=django_installation.nom,
            panneaux=panneaux,
            nombre_panneaux=django_installation.nombre_panneaux,
            onduleur=onduleur,
            geographie=geographie,
        )
        
        return installation
    
    def generer_donnees_meteo_simplifiees(
        self,
        latitude: float,
        irradiation_annuelle: float = 1400
    ) -> pd.DataFrame:
        """
        Génère des données météo simplifiées pour une année (8760h).
        
        ATTENTION: Version simplifiée pour tests sans PVGIS.
        En production, utiliser get_pvgis_weather_data().
        
        Args:
            latitude: Latitude du site
            irradiation_annuelle: Irradiation annuelle moyenne (kWh/m²/an)
            
        Returns:
            pd.DataFrame: Données météo horaires sur 8760h
        """
        # Créer un index horaire pour une année
        dates = pd.date_range(
            start=f'{datetime.now().year}-01-01',
            periods=8760,
            freq='H'
        )
        
        # Pattern journalier simplifié (irradiance en W/m²)
        # Plus fort à midi, nul la nuit
        heures = np.arange(24)
        pattern_jour = np.maximum(
            0,
            800 * np.sin((heures - 6) * np.pi / 12)  # Pic à midi
        )
        
        # Répéter sur l'année
        irradiance_ghi = np.tile(pattern_jour, 365)
        
        # Variation saisonnière (été plus fort que hiver)
        jours = np.arange(8760) // 24
        variation_saison = 1 + 0.3 * np.sin((jours - 80) * 2 * np.pi / 365)
        irradiance_ghi = irradiance_ghi * variation_saison
        
        # Ajuster pour correspondre à l'irradiation annuelle cible
        facteur_ajustement = (
            irradiation_annuelle * 1000 / irradiance_ghi.sum()
        )
        irradiance_ghi = irradiance_ghi * facteur_ajustement
        
        # Température (variation saisonnière)
        temperature = 12 + 10 * np.sin((jours - 80) * 2 * np.pi / 365)
        temperature = np.repeat(temperature, 1)[:8760]
        
        # Créer le DataFrame
        df = pd.DataFrame({
            'timestamp': dates,
            'ghi': irradiance_ghi,
            'temperature': temperature,
            'vitesse_vent': 2.0,  # Constant pour simplifier
        })
        
        return df
    
    def calculer_autoconsommation(
        self,
        production_horaire: pd.DataFrame,
        consommation_horaire: pd.DataFrame
    ) -> Dict:
        """
        Calcule l'autoconsommation heure par heure.
        
        Args:
            production_horaire: DataFrame avec colonne 'puissance_ac_kw'
            consommation_horaire: DataFrame avec colonne 'consommation_kw'
            
        Returns:
            dict: Résultats d'autoconsommation
        """
        # Aligner les deux dataframes sur le timestamp
        df = pd.merge(
            production_horaire[['timestamp', 'puissance_ac_kw']],
            consommation_horaire[['timestamp', 'consommation_kw']],
            on='timestamp',
            how='inner'
        )
        
        # Calculs heure par heure
        df['autoconso_kw'] = df.apply(
            lambda row: min(row['puissance_ac_kw'], row['consommation_kw']),
            axis=1
        )
        df['injection_kw'] = df.apply(
            lambda row: max(0, row['puissance_ac_kw'] - row['consommation_kw']),
            axis=1
        )
        df['achat_kw'] = df.apply(
            lambda row: max(0, row['consommation_kw'] - row['puissance_ac_kw']),
            axis=1
        )
        
        # Agrégation annuelle (somme des kW donne kWh car 1h)
        production_totale = df['puissance_ac_kw'].sum()
        consommation_totale = df['consommation_kw'].sum()
        autoconso_totale = df['autoconso_kw'].sum()
        injection_totale = df['injection_kw'].sum()
        achat_total = df['achat_kw'].sum()
        
        # Calcul des taux
        taux_autoconso = (autoconso_totale / production_totale * 100) if production_totale > 0 else 0
        taux_autoprod = (autoconso_totale / consommation_totale * 100) if consommation_totale > 0 else 0
        
        return {
            'production_annuelle_kwh': round(production_totale, 2),
            'consommation_annuelle_kwh': round(consommation_totale, 2),
            'autoconsommation_kwh': round(autoconso_totale, 2),
            'injection_reseau_kwh': round(injection_totale, 2),
            'achat_reseau_kwh': round(achat_total, 2),
            'taux_autoconsommation_pct': round(taux_autoconso, 2),
            'taux_autoproduction_pct': round(taux_autoprod, 2),
            'donnees_horaires': df,  # Optionnel : pour graphiques
        }
    
    def run_simulation_complete(
        self,
        django_installation,
        django_profile,
        use_real_weather: bool = True,
        irradiation_annuelle_fallback: float = 1400
    ) -> Dict:
        """
        Lance une simulation complète.
        
        Args:
            django_installation: Instance Django de SolarInstallation
            django_profile: Instance Django de ConsumptionProfile
            use_real_weather: Utiliser les vraies données PVGIS (True) ou simplifiées (False)
            irradiation_annuelle_fallback: Irradiation si données simplifiées (kWh/m²/an)
            
        Returns:
            dict: Résultats complets de la simulation
        """
        logger.info(f"Démarrage simulation pour {django_installation.nom}")
        
        # 1. Créer les objets de calcul
        installation = self.creer_installation_depuis_django(django_installation)
        profil_conso = self.creer_profil_consommation_depuis_django(django_profile)
        
        # 2. Générer/récupérer les données météo
        if use_real_weather:
            try:
                # Utiliser PVGIS
                from weather.services import get_pvgis_weather_data
                logger.info("📡 Récupération des données PVGIS...")
                
                df_meteo, metadata = get_pvgis_weather_data(
                    django_installation.latitude,
                    django_installation.longitude,
                    use_cache=True
                )
                
                logger.info(
                    f"✅ Données PVGIS récupérées: {metadata['irradiation_annuelle']:.0f} kWh/m²/an "
                    f"(source: {metadata.get('source', 'N/A')})"
                )
                
                donnees_meteo = df_meteo
                
            except Exception as e:
                logger.warning(f"⚠️ Erreur PVGIS, utilisation données simplifiées: {e}")
                donnees_meteo = self.generer_donnees_meteo_simplifiees(
                    django_installation.latitude,
                    irradiation_annuelle_fallback
                )
        else:
            # Données simplifiées
            logger.info("📊 Utilisation de données météo simplifiées")
            donnees_meteo = self.generer_donnees_meteo_simplifiees(
                django_installation.latitude,
                irradiation_annuelle_fallback
            )
        
        # 3. Calculer la production horaire
        logger.info("⚡ Calcul de la production solaire...")
        production_horaire = installation.simuler_annee(donnees_meteo)
        
        # 4. Calculer la consommation horaire
        logger.info("🏠 Calcul de la consommation...")
        consommation_horaire = profil_conso.generer_profil_horaire()
        
        # 5. Calculer l'autoconsommation
        logger.info("🔄 Calcul de l'autoconsommation...")
        resultats_autoconso = self.calculer_autoconsommation(
            production_horaire,
            consommation_horaire
        )
        
        # 6. Calculs complémentaires
        production_specifique = (
            resultats_autoconso['production_annuelle_kwh'] /
            installation.puissance_crete_totale_kwc
        )
        
        logger.info(
            f"✅ Simulation terminée: "
            f"{resultats_autoconso['production_annuelle_kwh']:.0f} kWh produits, "
            f"{resultats_autoconso['taux_autoconsommation_pct']:.1f}% autoconsommés"
        )
        
        # 7. Consolider les résultats
        resultats = {
            'production_annuelle_kwh': resultats_autoconso['production_annuelle_kwh'],
            'production_specifique_kwh_kwc': round(production_specifique, 2),
            'consommation_annuelle_kwh': resultats_autoconso['consommation_annuelle_kwh'],
            'autoconsommation_kwh': resultats_autoconso['autoconsommation_kwh'],
            'injection_reseau_kwh': resultats_autoconso['injection_reseau_kwh'],
            'achat_reseau_kwh': resultats_autoconso['achat_reseau_kwh'],
            'taux_autoconsommation_pct': resultats_autoconso['taux_autoconsommation_pct'],
            'taux_autoproduction_pct': resultats_autoconso['taux_autoproduction_pct'],
            'donnees_horaires': resultats_autoconso['donnees_horaires'],
        }
        
        self.results = resultats
        return resultats


def run_simulation_from_django_objects(
    django_installation,
    django_profile,
    use_real_weather: bool = True,
    irradiation_annuelle_fallback: float = 1400
) -> Dict:
    """
    Fonction helper pour lancer une simulation rapidement.
    
    Args:
        django_installation: Instance Django de SolarInstallation
        django_profile: Instance Django de ConsumptionProfile
        use_real_weather: Utiliser PVGIS (True) ou données simplifiées (False)
        irradiation_annuelle_fallback: Irradiation si mode simplifié
        
    Returns:
        dict: Résultats de la simulation
    """
    service = SimulationService()
    return service.run_simulation_complete(
        django_installation,
        django_profile,
        use_real_weather=use_real_weather,
        irradiation_annuelle_fallback=irradiation_annuelle_fallback
    )