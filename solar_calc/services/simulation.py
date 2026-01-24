"""
Service de Simulation Solaire

Ce module gère la simulation complète d'une installation solaire photovoltaïque,
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
    - La création des profils de consommation et d'installation
    - La génération ou récupération des données météo
    - Le calcul de production solaire
    - Le calcul d'autoconsommation
    - Les simulations avec batterie (optionnel)
    """
    
    def __init__(self):
        """Initialise le service de simulation."""
        self.results = {}

    def creer_profil_consommation_depuis_django(self, django_profile) -> ConsumptionProfile:
        """
        Crée un profil de consommation à partir d'un modèle Django.
        
        Args:
            django_profile: Instance de ConsumptionProfileModel
            
        Returns:
            ConsumptionProfile: Profil de consommation dataclass
        """
        chauffage = SystemeChauffage(type_chauffage=django_profile.type_chauffage)
        ecs = SystemeECS(type_ecs=django_profile.type_ecs)

        # Ajouter un champ dans votre modèle Django ou utiliser une logique
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
        Crée une installation solaire à partir d'un modèle Django.
        
        Args:
            django_installation: Instance de SolarInstallationModel
            
        Returns:
            SolarInstallation: Installation solaire dataclass
        """
        # Créer les caractéristiques des panneaux
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
        
        # Créer les données géographiques
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
        Génère des données météo simplifiées si PVGIS n'est pas disponible.
        
        Utilise un modèle sinusoïdal pour simuler :
        - L'irradiance solaire horaire avec variation jour/nuit
        - La variation saisonnière
        - La température ambiante
        
        Args:
            latitude: Latitude du site (°)
            irradiation_annuelle: Irradiation annuelle cible (kWh/m²/an)
                                 Si None, estimée selon la latitude
            
        Returns:
            pd.DataFrame: Données météo horaires [timestamp, ghi, temperature, vitesse_vent]
        """
        # Estimer l'irradiation selon la latitude si non fournie
        if irradiation_annuelle is None:
            irradiation_annuelle = max(1000, min(1800, 2000 - abs(latitude) * 10))
            logger.info(
                f"📡 Irradiation annuelle estimée selon latitude: "
                f"{irradiation_annuelle:.0f} kWh/m²/an"
            )

        # Créer l'index temporel pour une année (8760 heures)
        dates = pd.date_range(
            start=f'{datetime.now().year}-01-01',
            periods=8760,
            freq='h'
        )
        
        # Générer le pattern journalier (courbe sinusoïdale de 6h à 18h)
        heures = np.arange(24)
        pattern_jour = np.maximum(0, 800 * np.sin((heures - 6) * np.pi / 12))
        
        # Répéter sur toute l'année
        irradiance_ghi = np.tile(pattern_jour, 365)
        
        # Ajouter la variation saisonnière (maximum en été, minimum en hiver)
        jours = np.arange(8760) // 24
        variation_saison = 1 + 0.3 * np.sin((jours - 80) * 2 * np.pi / 365)
        irradiance_ghi *= variation_saison
        
        # Normaliser pour atteindre l'irradiation annuelle cible
        facteur_ajustement = irradiation_annuelle * 1000 / irradiance_ghi.sum()
        irradiance_ghi *= facteur_ajustement
        
        # Générer la température (variation saisonnière)
        temperature = 12 + 10 * np.sin((jours - 80) * 2 * np.pi / 365)
        temperature = np.repeat(temperature, 1)[:8760]

        # Créer le DataFrame
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
        
        Pour chaque heure de l'année, détermine :
        - L'énergie autoconsommée (min(production, consommation))
        - L'énergie injectée au réseau (surplus de production)
        - L'énergie achetée au réseau (déficit de production)
        
        Args:
            production_horaire: DataFrame avec [timestamp, puissance_ac_kw]
            consommation_horaire: DataFrame avec [timestamp, consommation_kw]
            
        Returns:
            dict: Résultats détaillés incluant :
                - production_annuelle_kwh
                - consommation_annuelle_kwh
                - autoconsommation_kwh
                - injection_reseau_kwh
                - achat_reseau_kwh
                - taux_autoconsommation_pct
                - taux_autoproduction_pct
                - donnees_horaires (DataFrame complet)
        """
        # Normaliser les timestamps pour assurer la correspondance
        # Les données PVGIS et de consommation peuvent avoir des années différentes
        # On les force toutes à la même année de référence (2016)
        production_copy = production_horaire.copy()
        production_copy['timestamp'] = pd.date_range(
            start='2016-01-01',
            periods=len(production_copy),
            freq='h'
        )
        
        consommation_copy = consommation_horaire.copy()
        consommation_copy['timestamp'] = pd.date_range(
            start='2016-01-01',
            periods=len(consommation_copy),
            freq='h'
        )
        
        # Fusionner les deux DataFrames sur le timestamp
        df = pd.merge(
            production_copy[['timestamp', 'puissance_ac_kw']],
            consommation_copy[['timestamp', 'consommation_kw']],
            on='timestamp',
            how='inner'
        )
        
        # Calculer les flux énergétiques heure par heure
        # Autoconsommation = minimum entre production et consommation
        df['autoconso_kw'] = df.apply(
            lambda row: min(row['puissance_ac_kw'], row['consommation_kw']),
            axis=1
        )
        
        # Injection = surplus de production
        df['injection_kw'] = df.apply(
            lambda row: max(0, row['puissance_ac_kw'] - row['consommation_kw']),
            axis=1
        )
        
        # Achat = déficit de production
        df['achat_kw'] = df.apply(
            lambda row: max(0, row['consommation_kw'] - row['puissance_ac_kw']),
            axis=1
        )
        
        # Calculer les totaux annuels
        production_totale = df['puissance_ac_kw'].sum()
        consommation_totale = df['consommation_kw'].sum()
        autoconso_totale = df['autoconso_kw'].sum()
        injection_totale = df['injection_kw'].sum()
        achat_total = df['achat_kw'].sum()
        
        # Calculer les taux
        # Taux d'autoconsommation = part de la production qui est consommée localement
        taux_autoconso = (
            (autoconso_totale / production_totale * 100) 
            if production_totale > 0 else 0
        )
        
        # Taux d'autoproduction = part de la consommation couverte par la production
        taux_autoprod = (
            (autoconso_totale / consommation_totale * 100) 
            if consommation_totale > 0 else 0
        )
        
        return {
            'production_annuelle_kwh': round(production_totale, 2),
            'consommation_annuelle_kwh': round(consommation_totale, 2),
            'autoconsommation_kwh': round(autoconso_totale, 2),
            'injection_reseau_kwh': round(injection_totale, 2),
            'achat_reseau_kwh': round(achat_total, 2),
            'taux_autoconsommation_pct': round(taux_autoconso, 2),
            'taux_autoproduction_pct': round(taux_autoprod, 2),
            'donnees_horaires': df
        }

    def run_simulation_complete(
        self,
        django_installation,
        django_profile,
        use_real_weather: bool = True,
        irradiation_annuelle_fallback: float = None,
        with_battery: bool = False,
        battery_capacity: float = None
    ) -> dict:
        """
        Exécute une simulation complète de l'installation solaire.
        
        Workflow :
        1. Création des objets installation et profil de consommation
        2. Récupération des données météo (PVGIS ou simplifiées)
        3. Calcul de la production horaire
        4. Génération du profil de consommation horaire
        5. Calcul de l'autoconsommation
        6. Simulation avec batterie si demandé
        
        Args:
            django_installation: Modèle Django de l'installation
            django_profile: Modèle Django du profil de consommation
            use_real_weather: Si True, utilise PVGIS, sinon données simplifiées
            irradiation_annuelle_fallback: Irradiation de secours si PVGIS échoue
            with_battery: Active la simulation avec batterie
            battery_capacity: Capacité de la batterie en kWh
            
        Returns:
            ict: Résultats avec métriques annuelles
            - production_annuelle_kwh
            - consommation_annuelle_kwh
            - autoconso_annuelle_kwh
            - taux_autoconsommation_pct
            - taux_autoproduction_pct
            - injection_annuelle_kwh
            - achat_annuel_kwh
        """
        # Créer les objets de simulation
        installation = self.creer_installation_depuis_django(django_installation)
        profil_conso = self.creer_profil_consommation_depuis_django(django_profile)
        
        # Récupérer ou générer les données météo
        if use_real_weather:
            try:
                from weather.services import get_pvgis_weather_data
                df_meteo, metadata = get_pvgis_weather_data(
                    django_installation.latitude,
                    django_installation.longitude,
                    use_cache=True
                )
                donnees_meteo = df_meteo
                logger.info("✅ Données PVGIS récupérées avec succès")
            except Exception as e:
                logger.warning(
                    f"⚠️ PVGIS indisponible, utilisation des données simplifiées: {e}"
                )
                donnees_meteo = self.generer_donnees_meteo_simplifiees(
                    django_installation.latitude,
                    irradiation_annuelle_fallback
                )
        else:
            donnees_meteo = self.generer_donnees_meteo_simplifiees(
                django_installation.latitude,
                irradiation_annuelle_fallback
            )

        # Simuler la production solaire
        production_horaire = installation.simuler_annee(donnees_meteo)
        
        # Générer le profil de consommation
        consommation_horaire = profil_conso.generer_profil_horaire()
        
        # Calculer l'autoconsommation
        resultats_autoconso = self.calculer_autoconsommation(
            production_horaire,
            consommation_horaire
        )
        
        # Calculer la production spécifique (kWh/kWc)
        production_specifique = (
            resultats_autoconso['production_annuelle_kwh'] / 
            installation.puissance_crete_totale_kwc
        )
        
        # Assembler les résultats
        resultats = {
            'production_annuelle_kwh': resultats_autoconso['production_annuelle_kwh'],
            'production_specifique_kwh_kwc': round(production_specifique, 2),
            'consommation_annuelle_kwh': resultats_autoconso['consommation_annuelle_kwh'],
            'autoconsommation_kwh': resultats_autoconso['autoconsommation_kwh'],
            'injection_reseau_kwh': resultats_autoconso['injection_reseau_kwh'],
            'achat_reseau_kwh': resultats_autoconso['achat_reseau_kwh'],
            'taux_autoconsommation_pct': resultats_autoconso['taux_autoconsommation_pct'],
            'taux_autoproduction_pct': resultats_autoconso['taux_autoproduction_pct'],
            'donnees_horaires': resultats_autoconso['donnees_horaires']
        }
        
        # Simulation avec batterie si demandé
        if with_battery:
            from battery.services.battery_simulation import BatterySimulationService
            from battery.models import BatterySystem
            
            # Créer ou récupérer le système de batterie
            battery, created = BatterySystem.objects.get_or_create(
                simulation_id=django_installation.simulation.id,
                defaults={
                    'capacite_kwh': battery_capacity or 10.0,
                    'capacite_utilisable_kwh': (battery_capacity or 10.0) * 0.9,
                    'puissance_max_kw': (battery_capacity or 10.0) * 0.5,
                    'cout_installation': (battery_capacity or 10.0) * 800
                }
            )
            
            # Simuler le comportement de la batterie
            battery_result = BatterySimulationService.simulate(
                battery=battery,
                donnees_horaires=resultats_autoconso['donnees_horaires'],
                save_logs=False
            )
            
            # Calculer les impacts financiers
            financial = BatterySimulationService.calculate_financial(
                battery_result=battery_result,
                donnees_sans_batterie=resultats_autoconso,
                cout_batterie=float(battery.cout_installation)
            )
            
            # Mettre à jour le système de batterie
            battery.cycles_annuels = battery_result['cycles_annuels']
            battery.duree_vie_annees = battery_result['duree_vie_ans']
            battery.autoconso_gain_pct = battery_result['gain_autoconso_pct']
            battery.economie_annuelle = financial['economie_annuelle']
            battery.roi_annees = financial['roi_annees']
            battery.save()
            
            # Ajouter les résultats de la batterie
            resultats['battery'] = {
                **battery_result,
                'financial': financial,
                'system': battery
            }
            
            logger.info(
                f"🔋 Batterie {battery.capacite_kwh}kWh : "
                f"ROI {financial['roi_annees']:.1f} ans"
            )
        
        # Stocker les résultats
        self.results = resultats
        
        return resultats


def run_simulation_from_django_objects(
    django_installation,
    django_profile,
    use_real_weather: bool = True,
    irradiation_annuelle_fallback: float = None
) -> dict:
    """
    Fonction helper pour exécuter une simulation depuis des objets Django.
    
    Args:
        django_installation: Modèle Django SolarInstallationModel
        django_profile: Modèle Django ConsumptionProfileModel
        use_real_weather: Utiliser les données PVGIS (True) ou simplifiées (False)
        irradiation_annuelle_fallback: Irradiation de secours en kWh/m²/an
        
    Returns:
        dict: Résultats de la simulation
        
    Example:
        >>> from solar_calc.models import SolarInstallationModel, ConsumptionProfileModel
        >>> installation = SolarInstallationModel.objects.first()
        >>> profile = ConsumptionProfileModel.objects.first()
        >>> results = run_simulation_from_django_objects(installation, profile)
        >>> print(f"Production: {results['production_annuelle_kwh']:.0f} kWh/an")
    """
    service = SimulationService()
    return service.run_simulation_complete(
        django_installation,
        django_profile,
        use_real_weather=use_real_weather,
        irradiation_annuelle_fallback=irradiation_annuelle_fallback
    )
