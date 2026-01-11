import pandas as pd
import numpy as np
from datetime import datetime
import logging
from ..dataclasses.consumption import ConsumptionProfile, SystemeChauffage, SystemeECS
from ..dataclasses.production import SolarInstallation, CaracteristiquesPanneau, ConfigurationOnduleur, DonneesGeographiques, TechnologiePanneau, TypeOnduleur

logger = logging.getLogger(__name__)

class SimulationService:
    def __init__(self):
        self.results = {}

    def creer_profil_consommation_depuis_django(self, django_profile) -> ConsumptionProfile:
        chauffage = SystemeChauffage(type_chauffage=django_profile.type_chauffage)
        ecs = SystemeECS(type_ecs=django_profile.type_ecs)
        profil = ConsumptionProfile(
            annee_construction=django_profile.annee_construction,
            surface_habitable=django_profile.surface_habitable,
            nb_personnes=django_profile.nb_personnes,
            dpe=django_profile.dpe,
            chauffage=chauffage,
            ecs=ecs
        )
        return profil

    def creer_installation_depuis_django(self, django_installation) -> SolarInstallation:
        panneaux = CaracteristiquesPanneau(
            modele=f"Panneau {django_installation.puissance_panneau_wc}Wc",
            fabricant="Standard",
            puissance_crete_wc=django_installation.puissance_panneau_wc,
            technologie=TechnologiePanneau.PERC,
            rendement_stc=22.0
        )
        type_onduleur_map = {'central': TypeOnduleur.CENTRAL, 'micro_onduleur': TypeOnduleur.MICRO_ONDULEUR, 'optimiseurs': TypeOnduleur.OPTIMISEURS}
        onduleur = ConfigurationOnduleur(
            type_onduleur=type_onduleur_map.get(django_installation.type_onduleur, TypeOnduleur.CENTRAL),
            puissance_nominale_kw=django_installation.puissance_onduleur_kw
        )
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

    def generer_donnees_meteo_simplifiees(self, latitude: float, irradiation_annuelle: float = None) -> pd.DataFrame:
        if irradiation_annuelle is None:
            irradiation_annuelle = max(1000, min(1800, 2000 - abs(latitude) * 10))
            logger.info(f"📡 Irradiation annuelle estimée selon latitude: {irradiation_annuelle:.0f} kWh/m²/an")

        dates = pd.date_range(start=f'{datetime.now().year}-01-01', periods=8760, freq='h')
        heures = np.arange(24)
        pattern_jour = np.maximum(0, 800 * np.sin((heures - 6) * np.pi / 12))
        irradiance_ghi = np.tile(pattern_jour, 365)
        jours = np.arange(8760) // 24
        variation_saison = 1 + 0.3 * np.sin((jours - 80) * 2 * np.pi / 365)
        irradiance_ghi *= variation_saison
        facteur_ajustement = irradiation_annuelle * 1000 / irradiance_ghi.sum()
        irradiance_ghi *= facteur_ajustement
        temperature = 12 + 10 * np.sin((jours - 80) * 2 * np.pi / 365)
        temperature = np.repeat(temperature, 1)[:8760]

        df = pd.DataFrame({
            'timestamp': dates,
            'ghi': irradiance_ghi,
            'temperature': temperature,
            'vitesse_vent': 2.0
        })
        return df

    def calculer_autoconsommation(self, production_horaire: pd.DataFrame, consommation_horaire: pd.DataFrame) -> dict:
        df = pd.merge(production_horaire[['timestamp', 'puissance_ac_kw']],
                      consommation_horaire[['timestamp', 'consommation_kw']],
                      on='timestamp', how='inner')
        df['autoconso_kw'] = df.apply(lambda row: min(row['puissance_ac_kw'], row['consommation_kw']), axis=1)
        df['injection_kw'] = df.apply(lambda row: max(0, row['puissance_ac_kw'] - row['consommation_kw']), axis=1)
        df['achat_kw'] = df.apply(lambda row: max(0, row['consommation_kw'] - row['puissance_ac_kw']), axis=1)
        production_totale = df['puissance_ac_kw'].sum()
        consommation_totale = df['consommation_kw'].sum()
        autoconso_totale = df['autoconso_kw'].sum()
        injection_totale = df['injection_kw'].sum()
        achat_total = df['achat_kw'].sum()
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
            'donnees_horaires': df
        }

    def run_simulation_complete(self, django_installation, django_profile, use_real_weather=True, irradiation_annuelle_fallback: float = None):
        installation = self.creer_installation_depuis_django(django_installation)
        profil_conso = self.creer_profil_consommation_depuis_django(django_profile)
        if use_real_weather:
            try:
                from weather.services import get_pvgis_weather_data
                df_meteo, metadata = get_pvgis_weather_data(django_installation.latitude, django_installation.longitude, use_cache=True)
                donnees_meteo = df_meteo
            except Exception as e:
                logger.warning(f"⚠️ PVGIS indisponible, utilisation simplifiée: {e}")
                donnees_meteo = self.generer_donnees_meteo_simplifiees(django_installation.latitude, irradiation_annuelle_fallback)
        else:
            donnees_meteo = self.generer_donnees_meteo_simplifiees(django_installation.latitude, irradiation_annuelle_fallback)

        production_horaire = installation.simuler_annee(donnees_meteo)
        consommation_horaire = profil_conso.generer_profil_horaire()
        resultats_autoconso = self.calculer_autoconsommation(production_horaire, consommation_horaire)
        production_specifique = resultats_autoconso['production_annuelle_kwh'] / installation.puissance_crete_totale_kwc
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
        self.results = resultats
        return resultats

def run_simulation_from_django_objects(django_installation, django_profile, use_real_weather=True, irradiation_annuelle_fallback=None):
    service = SimulationService()
    return service.run_simulation_complete(django_installation, django_profile, use_real_weather=use_real_weather, irradiation_annuelle_fallback=irradiation_annuelle_fallback)
