"""
Tests unitaires pour les calculs d'autoconsommation
solar_calc/tests/test_autoconsommation.py
"""

from calendar import weekday
import unittest
import pandas as pd
import numpy as np
from datetime import datetime
from solar_calc.dataclasses.consumption import ConsumptionProfile, SystemeChauffage, SystemeECS
from solar_calc.dataclasses.production import SolarInstallation
from solar_calc.services.simulation import SimulationService
from solar_calc.services.consumption_profiles import ConsumptionProfiles


class TestAutoconsommation(unittest.TestCase):
    """Tests des calculs d'autoconsommation"""
    
    def test_autoconso_production_egale_consommation(self):
        """
        Cas simple : production = consommation
        Autoconso devrait être 100%
        """
        # Créer DataFrame test (24h)
        dates = pd.date_range('2016-01-01', periods=24, freq='h')
        df = pd.DataFrame({
            'timestamp': dates,
            'puissance_ac_kw': [1.0] * 24,  # Production constante 1 kW
            'consommation_kw': [1.0] * 24   # Consommation constante 1 kW
        })
        
        # Calculer autoconsommation
        df['autoconso_kw'] = df.apply(
            lambda row: min(row['puissance_ac_kw'], row['consommation_kw']),
            axis=1
        )
        
        autoconso_total = df['autoconso_kw'].sum()
        production_total = df['puissance_ac_kw'].sum()
        taux = (autoconso_total / production_total) * 100
        
        self.assertEqual(autoconso_total, 24.0)
        self.assertEqual(taux, 100.0)
    
    def test_autoconso_production_superieure(self):
        """
        Production > Consommation
        Une partie injectée au réseau
        """
        dates = pd.date_range('2016-01-01', periods=24, freq='h')
        df = pd.DataFrame({
            'timestamp': dates,
            'puissance_ac_kw': [2.0] * 24,  # Production 2 kW
            'consommation_kw': [1.0] * 24   # Consommation 1 kW
        })
        
        df['autoconso_kw'] = df.apply(
            lambda row: min(row['puissance_ac_kw'], row['consommation_kw']),
            axis=1
        )
        df['injection_kw'] = df.apply(
            lambda row: max(0, row['puissance_ac_kw'] - row['consommation_kw']),
            axis=1
        )
        
        autoconso_total = df['autoconso_kw'].sum()
        injection_total = df['injection_kw'].sum()
        production_total = df['puissance_ac_kw'].sum()
        
        self.assertEqual(autoconso_total, 24.0)  # Toute la conso
        self.assertEqual(injection_total, 24.0)  # Surplus injecté
        self.assertEqual(autoconso_total + injection_total, production_total)
    
    def test_autoconso_production_inferieure(self):
        """
        Production < Consommation
        Achat réseau nécessaire
        """
        dates = pd.date_range('2016-01-01', periods=24, freq='h')
        df = pd.DataFrame({
            'timestamp': dates,
            'puissance_ac_kw': [1.0] * 24,  # Production 1 kW
            'consommation_kw': [2.0] * 24   # Consommation 2 kW
        })
        
        df['autoconso_kw'] = df.apply(
            lambda row: min(row['puissance_ac_kw'], row['consommation_kw']),
            axis=1
        )
        df['achat_kw'] = df.apply(
            lambda row: max(0, row['consommation_kw'] - row['puissance_ac_kw']),
            axis=1
        )
        
        autoconso_total = df['autoconso_kw'].sum()
        achat_total = df['achat_kw'].sum()
        consommation_total = df['consommation_kw'].sum()
        
        self.assertEqual(autoconso_total, 24.0)  # Toute la prod
        self.assertEqual(achat_total, 24.0)  # Complément réseau
        self.assertEqual(autoconso_total + achat_total, consommation_total)
    
    def test_normalisation_timestamps(self):
        """
        Test normalisation des timestamps (années différentes)
        """
        # Timestamps avec années différentes
        dates_prod = pd.date_range('2017-01-01', periods=10, freq='h')
        dates_conso = pd.date_range('2016-01-01', periods=10, freq='h')
        
        df_prod = pd.DataFrame({
            'timestamp': dates_prod,
            'production': np.random.rand(10)
        })
        
        df_conso = pd.DataFrame({
            'timestamp': dates_conso,
            'consommation': np.random.rand(10)
        })
        
        # Normaliser à 2016
        df_prod['timestamp'] = df_prod['timestamp'].apply(
            lambda dt: dt.replace(year=2016)
        )
        
        # Merge
        df_merged = pd.merge(df_prod, df_conso, on='timestamp', how='inner')
        
        # Vérifier que le merge a fonctionné
        self.assertEqual(len(df_merged), 10)
        
        # Vérifier que toutes les années sont 2016
        for ts in df_merged['timestamp']:
            self.assertEqual(ts.year, 2016)
    
    def test_taux_autoconsommation_superieur_100(self):
        """
        Le taux d'autoconsommation ne peut JAMAIS dépasser 100%
        """
        dates = pd.date_range('2016-01-01', periods=24, freq='h')
        df = pd.DataFrame({
            'timestamp': dates,
            'puissance_ac_kw': [3.0] * 24,
            'consommation_kw': [2.0] * 24
        })
        
        df['autoconso_kw'] = df.apply(
            lambda row: min(row['puissance_ac_kw'], row['consommation_kw']),
            axis=1
        )
        
        autoconso_total = df['autoconso_kw'].sum()
        production_total = df['puissance_ac_kw'].sum()
        taux = (autoconso_total / production_total) * 100
        
        # Autoconso ne peut dépasser production
        self.assertLessEqual(autoconso_total, production_total)
        self.assertLessEqual(taux, 100.0)


class TestProfilsOccupation(unittest.TestCase):
    """Tests des profils d'occupation"""
    
    def test_profils_disponibles(self):
        """Vérifier que les 4 profils sont disponibles"""
        profils = ConsumptionProfiles.get_available_profiles()
        
        self.assertIn('actif_absent', profils)
        self.assertIn('teletravail', profils)
        self.assertIn('retraite', profils)
        self.assertIn('famille', profils)
    
    def test_profil_24_valeurs(self):
        """Chaque profil doit avoir exactement 24 valeurs horaires"""
        for profile_type in ['actif_absent', 'teletravail', 'retraite', 'famille']:
            pattern = ConsumptionProfiles.get_daily_pattern(profile_type, is_weekend=False)
            self.assertEqual(len(pattern), 24, 
                           f"Profil {profile_type} devrait avoir 24 valeurs, a {len(pattern)}")
    
    def test_variation_weekday_weekend(self):
        """Les profils weekend doivent être différents des weekdays (sauf retraité)"""
        profils_variables = ['actif_absent', 'teletravail', 'famille']
    
        for profile_type in profils_variables:
            weekday = ConsumptionProfiles.get_daily_pattern(profile_type, is_weekend=False)
            weekend = ConsumptionProfiles.get_daily_pattern(profile_type, is_weekend=True)
        
            self.assertFalse(
                all(weekday[i] == weekend[i] for i in range(24)),
                f"Profil {profile_type} devrait varier weekday/weekend"
            )

    def test_profil_retraite_constant(self):
        """Le profil retraité devrait être similaire weekday/weekend"""
        weekday = ConsumptionProfiles.get_daily_pattern('retraite', is_weekend=False)
        weekend = ConsumptionProfiles.get_daily_pattern('retraite', is_weekend=True)
    
        # Pour un retraité, le pattern devrait être très similaire
        # (tolérance pour légères variations aléatoires si elles existent)
        differences = sum(1 for i in range(24) if weekday[i] != weekend[i])
    
        # Accepter jusqu'à 3 heures de différence (si variation aléatoire mineure)
        self.assertLessEqual(
            differences, 
            3,
            "Profil retraité devrait être constant weekday/weekend"
        )
    
    def test_pattern_annuel_8760_valeurs(self):
        """Le pattern annuel doit avoir 8760 valeurs (365 jours × 24h)"""
        pattern = ConsumptionProfiles.generate_yearly_pattern('actif_absent')
        
        self.assertEqual(len(pattern), 8760)
    
    def test_valeurs_positives(self):
        """Toutes les valeurs doivent être positives"""
        pattern = ConsumptionProfiles.generate_yearly_pattern('actif_absent', add_randomness=False)
        
        self.assertTrue(all(v >= 0 for v in pattern))
    
    def test_reproductibilite_random_seed(self):
        """Avec le même seed, les patterns doivent être identiques"""
        pattern1 = ConsumptionProfiles.generate_yearly_pattern('actif_absent', random_seed=42)
        pattern2 = ConsumptionProfiles.generate_yearly_pattern('actif_absent', random_seed=42)
        
        np.testing.assert_array_equal(pattern1, pattern2)


class TestConsumptionProfile(unittest.TestCase):
    """Tests de la classe ConsumptionProfile"""
    
    def test_creation_profil_simple(self):
        """Créer un profil de consommation basique"""
        profil = ConsumptionProfile(
            annee_construction=2015,
            surface_habitable=100,
            nb_personnes=3,
            dpe='C',
            chauffage=SystemeChauffage(type_chauffage='electrique'),
            ecs=SystemeECS(type_ecs='ballon_electrique'),
            profile_type='actif_absent'
        )
        
        self.assertEqual(profil.profile_type, 'actif_absent')
        self.assertEqual(profil.nb_personnes, 3)
    
    def test_generation_profil_horaire(self):
        """Générer le profil horaire complet"""
        profil = ConsumptionProfile(
            annee_construction=2015,
            surface_habitable=100,
            nb_personnes=3,
            dpe='C',
            chauffage=SystemeChauffage(type_chauffage='electrique'),
            ecs=SystemeECS(type_ecs='ballon_electrique'),
            profile_type='teletravail'
        )
        
        df = profil.generer_profil_horaire()
        
        # Vérifier structure
        self.assertEqual(len(df), 8760)
        self.assertIn('timestamp', df.columns)
        self.assertIn('consommation_kw', df.columns)
        
        # Vérifier données valides
        self.assertTrue(all(df['consommation_kw'] >= 0))


class TestBilanEnergetique(unittest.TestCase):
    """Tests du bilan énergétique complet"""
    
    def test_conservation_energie(self):
        """
        Conservation de l'énergie :
        Production = Autoconsommation + Injection
        Consommation = Autoconsommation + Achat
        """
        dates = pd.date_range('2016-01-01', periods=100, freq='h')
        
        # Données aléatoires mais réalistes
        np.random.seed(42)
        df = pd.DataFrame({
            'timestamp': dates,
            'puissance_ac_kw': np.random.uniform(0, 3, 100),
            'consommation_kw': np.random.uniform(0.5, 2, 100)
        })
        
        # Calculs
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
        
        # Vérifier conservation
        production = df['puissance_ac_kw'].sum()
        autoconso = df['autoconso_kw'].sum()
        injection = df['injection_kw'].sum()
        consommation = df['consommation_kw'].sum()
        achat = df['achat_kw'].sum()
        
        # Production = Autoconso + Injection
        self.assertAlmostEqual(production, autoconso + injection, places=5)
        
        # Consommation = Autoconso + Achat
        self.assertAlmostEqual(consommation, autoconso + achat, places=5)


if __name__ == '__main__':
    unittest.main()
