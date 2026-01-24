# solar_calc/services/consumption_calculator.py
"""
Service de calcul de consommation électrique basé sur le profil du foyer.

Utilise :
- DPE pour le chauffage
- Zone climatique (H1/H2/H3)
- Nombre de personnes
- Surface habitable
- Appareils électriques
"""

import logging
from typing import Dict, List, Tuple
import numpy as np

logger = logging.getLogger(__name__)


class ConsumptionCalculator:
    """
    Calculateur de consommation électrique pour un foyer.
    """
    
    # Besoins énergétiques selon DPE (kWh/m²/an) pour chauffage
    BESOINS_DPE = {
        'A': 35,   # < 50 kWh/m²/an
        'B': 70,   # 50-90
        'C': 120,  # 91-150
        'D': 190,  # 151-230
        'E': 280,  # 231-330
        'F': 390,  # 331-450
        'G': 500,  # > 450
    }
    
    # Facteurs selon zone climatique
    FACTEURS_ZONE = {
        'H1': 1.20,  # Nord (plus froid)
        'H2': 1.00,  # Centre (référence)
        'H3': 0.75,  # Sud (plus doux)
    }
    
    # Coefficients de conversion énergie primaire → finale
    # Le DPE est exprimé en énergie PRIMAIRE
    # Il faut diviser par ces coefficients pour obtenir l'énergie FINALE réellement consommée
    COEFFICIENTS_PRIMAIRE_FINALE = {
        'electrique': 2.58,  # Ancien coef (avant RE2020: 2.3)
        'pompe_chaleur': 2.58,
        'pompe_a_chaleur': 2.58,
        'PAC': 2.58, # PAC = électricité    
        'gaz': 1.0,          # Gaz naturel
        'fioul': 1.0,        # Fioul
        'bois': 0.6,         # Bois/biomasse
        'reseau_chaleur': 1.0,  # Réseau de chaleur (variable selon source)
    }
    
    # Tarifs électricité 2024 (€ TTC) - Source : CRE janvier 2024
    # Tarif Base (prix unique 24h/24)
    TARIFS_BASE_2024 = {
        '3kVA': {'abonnement': 136.12, 'prix_kwh': 0.2516},
        '6kVA': {'abonnement': 151.20, 'prix_kwh': 0.2516},
        '9kVA': {'abonnement': 189.48, 'prix_kwh': 0.2516},
        '12kVA': {'abonnement': 228.48, 'prix_kwh': 0.2516},
        '15kVA': {'abonnement': 266.76, 'prix_kwh': 0.2516},
    }
    
    # Tarif HP/HC (Heures Pleines / Heures Creuses)
    TARIFS_HPHC_2024 = {
        '6kVA': {'abonnement': 156.12, 'prix_hp': 0.2700, 'prix_hc': 0.2068},
        '9kVA': {'abonnement': 198.24, 'prix_hp': 0.2700, 'prix_hc': 0.2068},
        '12kVA': {'abonnement': 242.88, 'prix_hp': 0.2700, 'prix_hc': 0.2068},
        '15kVA': {'abonnement': 282.00, 'prix_hp': 0.2700, 'prix_hc': 0.2068},
    }
    
    # Plages Heures Creuses standard Enedis (22h-6h)
    # 8 heures consécutives la nuit
    PLAGES_HC_STANDARD = {
        'debut': 22,  # 22h
        'fin': 6,     # 6h du matin
        'duree': 8    # 8 heures
    }
    
    # Facteurs selon année de construction (isolation)
    FACTEURS_ISOLATION = [
        (2013, 0.85, 'RT2012'),
        (2005, 1.00, 'RT2005'),
        (1988, 1.15, 'RT1988'),
        (1974, 1.30, 'RT1974'),
        (0, 1.50, 'Avant 1974'),
    ]
    
    def __init__(self, data: Dict):
        """
        Initialise le calculateur.
        
        Args:
            data: Dictionnaire avec tous les paramètres
                {
                    'surface': 120,
                    'nb_personnes': 4,
                    'dpe': 'D',
                    'annee_construction': 1995,
                    'latitude': 48.8566,
                    'longitude': 2.3522,
                    'type_chauffage': 'electrique',
                    'temperature_consigne': 19,
                    'type_vmc': 'simple_flux',
                    'type_ecs': 'ballon_electrique',
                    'capacite_ecs': 200,
                    ...
                }
        """
        self.data = data
        self.surface = data.get('surface', 100)
        self.nb_personnes = data.get('nb_personnes', 2)
        self.dpe = data.get('dpe', 'D')
        self.annee_construction = data.get('annee_construction', 2000)
        
        # Détection automatique de la zone climatique
        self.zone_climatique = self._detect_zone_climatique()
        
        logger.info(
            f"📊 Init calculateur: {self.surface}m², {self.nb_personnes} pers, "
            f"DPE {self.dpe}, Zone {self.zone_climatique}"
        )
    
    def _detect_zone_climatique(self) -> str:
        """
        Détecte la zone climatique H1/H2/H3 selon latitude.
        
        Carte simplifiée :
        - H1 (Nord) : lat > 48.5°
        - H2 (Centre) : 44° < lat ≤ 48.5°
        - H3 (Sud) : lat ≤ 44°
        """
        lat = self.data.get('latitude')
        
        if lat is None:
            logger.warning("Latitude non fournie, zone H2 par défaut")
            return 'H2'
        
        if lat > 48.5:
            return 'H1'  # Nord (Lille, Strasbourg)
        elif lat > 44.0:
            return 'H2'  # Centre (Paris, Lyon)
        else:
            return 'H3'  # Sud (Marseille, Toulouse)
    
    def calculate_chauffage(self) -> Dict:
        """
        Calcule la consommation de chauffage.
        
        Basé sur :
        - DPE (besoins énergétiques du bâtiment)
        - Zone climatique
        - Année de construction (isolation)
        - Type de chauffage (électrique, PAC, autre)
        - VMC (simple/double flux)
        - Température de consigne
        
        Returns:
            {
                'annuel': 8500,  # kWh/an
                'mensuel': [1200, 1100, 900, ...],  # 12 valeurs
                'details': {...}
            }
        """
        type_chauffage = self.data.get('type_chauffage', 'electrique')
        
        # ✅ Normaliser les variantes de pompe à chaleur
        if type_chauffage in ['pompe_chaleur', 'pompe_a_chaleur', 'PAC']:
            type_chauffage = 'pac'

        # Si non électrique, consommation électrique = 0
        if type_chauffage not in ['electrique', 'pac']:
            logger.info(f"Chauffage {type_chauffage} (non électrique)")
            return {
                'annuel': 0,
                'mensuel': [0] * 12,
                'details': {'type': type_chauffage, 'electrique': False}
            }
        
        # 1. Besoin de base selon DPE (énergie PRIMAIRE)
        besoin_dpe_primaire = self.BESOINS_DPE[self.dpe] * self.surface
        logger.debug(f"  Besoin DPE {self.dpe} (primaire): {besoin_dpe_primaire:.0f} kWh")
        
        # 1b. Conversion énergie primaire → finale
        # IMPORTANT : Le DPE est en énergie PRIMAIRE, il faut convertir en FINALE
        coef_conversion = self.COEFFICIENTS_PRIMAIRE_FINALE.get(type_chauffage, 2.58)
        besoin_base = besoin_dpe_primaire / coef_conversion
        logger.debug(f"  Conversion primaire→finale (÷{coef_conversion}): {besoin_base:.0f} kWh")
        
        # 2. Correction zone climatique
        facteur_zone = self.FACTEURS_ZONE[self.zone_climatique]
        besoin_base *= facteur_zone
        logger.debug(f"  Après zone {self.zone_climatique} (×{facteur_zone}): {besoin_base:.0f} kWh")
        
        # 3. Correction selon année construction (isolation)
        facteur_iso = self._get_facteur_isolation()
        besoin_base *= facteur_iso
        logger.debug(f"  Après isolation (×{facteur_iso}): {besoin_base:.0f} kWh")
        
        # 4. Altitude (optionnel)
        altitude = self.data.get('altitude', 0)
        if altitude > 0:
            facteur_altitude = 1 + (altitude / 200) * 0.05
            besoin_base *= facteur_altitude
            logger.debug(f"  Après altitude {altitude}m (×{facteur_altitude:.2f}): {besoin_base:.0f} kWh")
        
        # 5. Type de chauffage (rendement/COP)
        if type_chauffage == 'pac':
            # Pompe à chaleur : COP moyen de 3.0
            # Besoin énergétique / COP = consommation électrique
            conso_elec = besoin_base / 3.0
            logger.debug(f"  PAC (COP 3.0): {conso_elec:.0f} kWh élec")
        else:  # Électrique direct
            conso_elec = besoin_base
            logger.debug(f"  Électrique direct: {conso_elec:.0f} kWh")
        
        # 6. VMC double flux économise 15%
        type_vmc = self.data.get('type_vmc', 'aucune')
        if type_vmc == 'double_flux':
            conso_elec *= 0.85
            logger.debug(f"  VMC double flux (-15%): {conso_elec:.0f} kWh")
        
        # 7. Température de consigne (+7% par °C au-dessus de 19°C)
        temp_consigne = self.data.get('temperature_consigne', 19.0)
        if temp_consigne > 19:
            facteur_temp = 1 + (temp_consigne - 19) * 0.07
            conso_elec *= facteur_temp
            logger.debug(f"  Température {temp_consigne}°C (×{facteur_temp:.2f}): {conso_elec:.0f} kWh")
        
        # 8. Répartition mensuelle (plus en hiver)
        monthly = self._distribute_heating_monthly(conso_elec)
        
        logger.info(f"🔥 Chauffage: {conso_elec:.0f} kWh/an")
        
        return {
            'annuel': round(conso_elec, 0),
            'mensuel': monthly,
            'details': {
                'type': type_chauffage,
                'dpe': self.dpe,
                'zone': self.zone_climatique,
                'temperature': temp_consigne,
                'vmc': type_vmc,
            }
        }
    
    def _get_facteur_isolation(self) -> float:
        """Retourne le facteur d'isolation selon l'année de construction"""
        annee = self.annee_construction
        
        for annee_seuil, facteur, nom in self.FACTEURS_ISOLATION:
            if annee >= annee_seuil:
                logger.debug(f"    Isolation {nom} (≥{annee_seuil}): facteur {facteur}")
                return facteur
        
        return 1.50  # Par défaut
    
    def _distribute_heating_monthly(self, total: float) -> List[float]:
        """
        Répartit le chauffage sur 12 mois (plus en hiver).
        
        Args:
            total: Consommation annuelle totale (kWh)
        
        Returns:
            Liste de 12 valeurs mensuelles
        """
        # Facteurs mensuels de base (hiver > été)
        # Basé sur les degrés-jours unifiés (DJU) moyens en France
        factors_h2 = [
            1.5,  # Jan - Froid
            1.4,  # Fév - Froid
            1.2,  # Mar - Frais
            0.8,  # Avr - Doux
            0.3,  # Mai - Doux
            0.0,  # Juin - Chaud
            0.0,  # Juil - Chaud
            0.0,  # Août - Chaud
            0.2,  # Sep - Doux
            0.6,  # Oct - Frais
            1.1,  # Nov - Frais
            1.4,  # Déc - Froid
        ]
        
        # Ajuster selon la zone
        if self.zone_climatique == 'H1':  # Nord : hivers plus longs/froids
            factors = [f * 1.1 for f in factors_h2]
        elif self.zone_climatique == 'H3':  # Sud : hivers plus doux
            factors = [f * 0.7 for f in factors_h2]
        else:  # H2
            factors = factors_h2
        
        # Normaliser pour que la somme = total
        sum_factors = sum(factors)
        monthly = [round(total * (f / sum_factors), 0) for f in factors]
        
        return monthly
    
    def calculate_ecs(self) -> Dict:
        """
        Calcule la consommation d'eau chaude sanitaire (ECS).
        
        Basé sur :
        - Nombre de personnes (50L/pers/jour à 50°C)
        - Type de chauffe-eau (électrique, thermodynamique, etc.)
        - Capacité du ballon (optionnel)
        
        Returns:
            {
                'annuel': 2500,
                'mensuel': [210, 210, ...],
                'details': {...}
            }
        """
        nb_pers = self.nb_personnes
        type_ecs = self.data.get('type_ecs', 'ballon_electrique')
        
        # Si non électrique
        if type_ecs in ['gaz', 'solaire']:
            logger.info(f"ECS {type_ecs} (non électrique)")
            return {
                'annuel': 0,
                'mensuel': [0] * 12,
                'details': {'type': type_ecs, 'electrique': False}
            }
        
        # Consommation de base
        # 50 litres/pers/jour à chauffer de 15°C à 50°C
        # Énergie = Volume × ΔT × 1.16 Wh/L/°C
        # = 50L × 35°C × 1.16 = 2030 Wh/jour/pers
        # = 2.03 kWh/jour/pers
        # = 741 kWh/an/pers
        
        conso_base_annuelle = nb_pers * 741  # kWh/an
        
        # COP selon type
        if type_ecs == 'thermodynamique':
            # Chauffe-eau thermodynamique : COP moyen 2.5
            conso_elec = conso_base_annuelle / 2.5
            logger.debug(f"  Thermodynamique (COP 2.5): {conso_elec:.0f} kWh")
        else:  # Ballon électrique classique
            conso_elec = conso_base_annuelle
            logger.debug(f"  Ballon électrique: {conso_elec:.0f} kWh")
        
        # Ajustement selon capacité (optionnel)
        capacite = self.data.get('capacite_ecs')
        if capacite:
            # Ballons surdimensionnés ont plus de pertes thermiques
            if capacite > nb_pers * 50:
                facteur_pertes = 1.1  # +10% de pertes
                conso_elec *= facteur_pertes
                logger.debug(f"  Surdimensionné ({capacite}L pour {nb_pers} pers): +10%")
        
        # Répartition mensuelle (légèrement plus en hiver)
        monthly_base = conso_elec / 12
        monthly = []
        for mois in range(1, 13):
            # Hiver : +10%, Été : -10%
            if mois in [1, 2, 3, 11, 12]:  # Hiver
                monthly.append(round(monthly_base * 1.1, 0))
            elif mois in [6, 7, 8]:  # Été
                monthly.append(round(monthly_base * 0.9, 0))
            else:  # Intersaison
                monthly.append(round(monthly_base, 0))
        
        logger.info(f"🚿 ECS: {conso_elec:.0f} kWh/an")
        
        return {
            'annuel': round(conso_elec, 0),
            'mensuel': monthly,
            'details': {
                'type': type_ecs,
                'nb_personnes': nb_pers,
                'capacite': capacite,
            }
        }
    
    def calculate_forfait_electromenager(self) -> Dict:
        """
        Calcul forfaitaire de l'électroménager (mode rapide).
        
        Basé sur :
        - Nombre de personnes
        - Âge des appareils (classe énergétique)
        
        Returns:
            {
                'annuel': 1800,
                'mensuel': [150, 150, ...],
                'details': {...}
            }
        """
        # Base : 800 kWh/personne/an (électroménager classique)
        conso_base = self.nb_personnes * 800
        
        # Ajustement selon âge des appareils
        age_appareils = self.data.get('age_appareils', 'moyen')
        
        if age_appareils == 'recent':  # < 5 ans, classe A+++
            facteur = 0.85  # -15%
        elif age_appareils == 'ancien':  # > 10 ans
            facteur = 1.20  # +20%
        else:  # Moyen (5-10 ans)
            facteur = 1.00
        
        conso_elec = conso_base * facteur
        
        # Répartition mensuelle uniforme
        monthly = [round(conso_elec / 12, 0)] * 12
        
        logger.info(f"🧺 Électroménager (forfait): {conso_elec:.0f} kWh/an")
        
        return {
            'annuel': round(conso_elec, 0),
            'mensuel': monthly,
            'details': {
                'mode': 'forfait',
                'age_appareils': age_appareils,
            }
        }
    
    def calculate_forfait_cuisson(self) -> Dict:
        """Calcul forfaitaire cuisson (mode rapide)"""
        nb_pers = self.nb_personnes
        type_cuisson = self.data.get('type_cuisson', 'induction')
        
        # Base : 350 kWh/pers/an
        conso_base = nb_pers * 350
        
        # Ajustement selon type
        if type_cuisson == 'gaz':
            conso_elec = 50  # Juste l'allumage
        elif type_cuisson == 'induction':
            conso_elec = conso_base * 0.9  # -10% (plus efficace)
        else:  # Électrique classique
            conso_elec = conso_base
        
        monthly = [round(conso_elec / 12, 0)] * 12
        
        logger.info(f"🍳 Cuisson: {conso_elec:.0f} kWh/an")
        
        return {
            'annuel': round(conso_elec, 0),
            'mensuel': monthly,
            'details': {'type': type_cuisson}
        }
    
    def calculate_forfait_audiovisuel(self) -> Dict:
        """
        Calcul forfaitaire audiovisuel avec 3 niveaux d'usage.
        
        Source : ADEME "Réduire sa facture d'électricité 2023"
        
        Usage modéré : Petite TV (<42"), Box, 1 ordi
        Usage courant : TV moyenne (42-55"), Box, ordi, console occasionnelle
        Usage intensif : Grande TV (>65"), Console souvent, Home-cinéma, Veilles permanentes
        """
        nb_pers = self.nb_personnes
        usage = self.data.get('usage_audiovisuel', 'courant')
        
        # Consommation par personne selon usage (kWh/pers/an)
        conso_per_person = {
            'modere': 150,   # 300 kWh pour 2 pers
            'courant': 250,  # 500 kWh pour 2 pers
            'intensif': 400  # 800 kWh pour 2 pers
        }.get(usage, 250)  # Par défaut: courant
        
        conso_base = nb_pers * conso_per_person
        
        monthly = [round(conso_base / 12, 0)] * 12
        
        logger.info(f"📺 Audiovisuel ({usage}): {conso_base:.0f} kWh/an ({conso_per_person} kWh/pers)")
        
        return {
            'annuel': round(conso_base, 0),
            'mensuel': monthly,
            'details': {
                'mode': 'forfait',
                'usage': usage,
                'kwh_per_person': conso_per_person
            }
        }
    
    def calculate_forfait_eclairage(self) -> Dict:
        """Calcul forfaitaire éclairage"""
        surface = self.surface
        
        # Base : 10 kWh/m²/an (si LED)
        # 20 kWh/m²/an (si halogène)
        type_eclairage = self.data.get('type_eclairage', 'LED')
        
        # Consommation selon type (kWh/m²/an) - Source ADEME 2023
        if type_eclairage == 'LED':
            conso_base = surface * 5  # Réduit de 10 à 5
        elif type_eclairage == 'halogen':
            conso_base = surface * 12  # Réduit de 20 à 12
        else:  # Mixte
            conso_base = surface * 8
        
        # Plus en hiver (nuits longues)
        monthly = self._distribute_lighting_monthly(conso_base)
        
        logger.info(f"💡 Éclairage: {conso_base:.0f} kWh/an")
        
        return {
            'annuel': round(conso_base, 0),
            'mensuel': monthly,
            'details': {'type': type_eclairage}
        }
    
    def _distribute_lighting_monthly(self, total: float) -> List[float]:
        """Répartit l'éclairage (plus en hiver)"""
        factors = [
            1.3, 1.3, 1.2, 1.0, 0.8, 0.7,  # Jan-Juin
            0.7, 0.8, 1.0, 1.2, 1.3, 1.3,  # Juil-Déc
        ]
        sum_factors = sum(factors)
        return [round(total * (f / sum_factors), 0) for f in factors]
    
    def calculate_total(self) -> Dict:
        """
        Calcul complet de la consommation (mode rapide).
        
        Returns:
            {
                'total_annuel': 5280,
                'mensuel': [480, 450, 420, ...],
                'moyenne_attendue': 4500,
                'ecart_pct': 17.3,
                'repartition': {
                    'chauffage': {'kwh': 2400, 'pct': 45.5},
                    'ecs': {'kwh': 800, 'pct': 15.2},
                    ...
                },
                'details_postes': {
                    'chauffage': {...},
                    'ecs': {...},
                    ...
                }
            }
        """
        logger.info("🔢 Calcul de la consommation totale (mode rapide)")
        
        # Calcul de chaque poste
        chauffage = self.calculate_chauffage()
        ecs = self.calculate_ecs()
        electromenager = self.calculate_forfait_electromenager()
        cuisson = self.calculate_forfait_cuisson()
        audiovisuel = self.calculate_forfait_audiovisuel()
        eclairage = self.calculate_forfait_eclairage()
        
        # Total annuel
        total_annuel = (
            chauffage['annuel'] +
            ecs['annuel'] +
            electromenager['annuel'] +
            cuisson['annuel'] +
            audiovisuel['annuel'] +
            eclairage['annuel']
        )
        
        # Consommation mensuelle
        monthly = []
        for i in range(12):
            monthly.append(
                chauffage['mensuel'][i] +
                ecs['mensuel'][i] +
                electromenager['mensuel'][i] +
                cuisson['mensuel'][i] +
                audiovisuel['mensuel'][i] +
                eclairage['mensuel'][i]
            )
        
        # Comparaison à la moyenne
        moyenne_attendue = self._calculate_expected_consumption()
        ecart_pct = ((total_annuel - moyenne_attendue) / moyenne_attendue) * 100
        
        # Répartition par poste
        repartition = {}
        for nom, resultat in [
            ('chauffage', chauffage),
            ('ecs', ecs),
            ('electromenager', electromenager),
            ('cuisson', cuisson),
            ('audiovisuel', audiovisuel),
            ('eclairage', eclairage),
        ]:
            kwh = resultat['annuel']
            pct = (kwh / total_annuel * 100) if total_annuel > 0 else 0
            repartition[nom] = {
                'kwh': kwh,
                'pourcentage': round(pct)  # Arrondi standard (0.5 → sup)
            }
        
        logger.info(f"📊 TOTAL: {total_annuel:.0f} kWh/an (vs moyenne {moyenne_attendue:.0f}, écart {ecart_pct:+.1f}%)")
        
        return {
            'total_annuel': round(total_annuel, 0),
            'mensuel': monthly,
            'moyenne_attendue': round(moyenne_attendue, 0),
            'ecart_pct': round(ecart_pct, 1),
            'repartition': repartition,
            'details_postes': {
                'chauffage': chauffage['details'],
                'ecs': ecs['details'],
                'electromenager': electromenager['details'],
                'cuisson': cuisson['details'],
                'audiovisuel': audiovisuel['details'],
                'eclairage': eclairage['details'],
            }
        }
    
    def _calculate_expected_consumption(self) -> float:
        """
        Calcule la consommation attendue selon le profil.
        
        Basé sur :
        - Base incompressible : 1500 kWh
        - + 800 kWh/personne (électroménager, audiovisuel)
        - + Chauffage selon DPE et surface (si électrique)
        
        Returns:
            Consommation attendue (kWh/an)
        """
        base = 1500  # Incompressible (veilles, éclairage, etc.)
        
        # Par personne
        base += self.nb_personnes * 800
        
        # Chauffage (si électrique)
        type_chauffage = self.data.get('type_chauffage', 'electrique')
        if type_chauffage in ['electrique', 'pac']:
            # Besoin DPE en énergie PRIMAIRE
            besoin_chauffage_primaire = self.BESOINS_DPE[self.dpe] * self.surface
            
            # Conversion primaire → finale
            coef = self.COEFFICIENTS_PRIMAIRE_FINALE.get(type_chauffage, 2.58)
            besoin_chauffage = besoin_chauffage_primaire / coef
            
            # Facteur zone
            besoin_chauffage *= self.FACTEURS_ZONE[self.zone_climatique]
            
            # Facteur isolation
            besoin_chauffage *= self._get_facteur_isolation()
            
            # Si PAC, diviser par COP
            if type_chauffage == 'pac':
                besoin_chauffage /= 3.0
            
            base += besoin_chauffage
        
        return base
    
    def calculate_financial_details(self, consommation_annuelle: float) -> Dict:
        """
        Calcule les coûts détaillés avec tarif Base ou HP/HC.
        
        Args:
            consommation_annuelle: kWh/an total
        
        Returns:
            Dict avec abonnement, coût énergie, coût total, détails HP/HC si applicable
        """
        puissance = self.data.get('puissance_compteur', '6kVA')
        type_contrat = self.data.get('type_contrat', 'base')
        
        if type_contrat == 'base':
            # Tarif Base (prix unique 24h/24)
            tarif = self.TARIFS_BASE_2024.get(puissance, self.TARIFS_BASE_2024['6kVA'])
            abonnement = tarif['abonnement']
            cout_energie = consommation_annuelle * tarif['prix_kwh']
            
            return {
                'type': 'base',
                'puissance': puissance,
                'abonnement': round(abonnement, 2),
                'cout_energie': round(cout_energie, 2),
                'cout_total': round(abonnement + cout_energie, 2),
                'prix_moyen_kwh': tarif['prix_kwh']
            }
        
        else:  # HP-HC
            # Vérifier que la puissance supporte HP/HC (≥6kVA)
            if puissance == '3kVA':
                logger.warning("HP/HC non disponible pour 3kVA, passage en Base")
                # Forcer Base
                return self.calculate_financial_details_force_base(consommation_annuelle, puissance)
            
            tarif = self.TARIFS_HPHC_2024.get(puissance, self.TARIFS_HPHC_2024['6kVA'])
            abonnement = tarif['abonnement']
            
            # Répartir consommation HP/HC selon profil
            repartition = self._repartir_hphc(consommation_annuelle)
            
            cout_hp = repartition['hp_kwh'] * tarif['prix_hp']
            cout_hc = repartition['hc_kwh'] * tarif['prix_hc']
            cout_energie = cout_hp + cout_hc
            
            # Calculer économie vs Base
            economie = self._calcul_economie_hphc(consommation_annuelle, puissance)
            
            return {
                'type': 'hphc',
                'puissance': puissance,
                'abonnement': round(abonnement, 2),
                'cout_energie': round(cout_energie, 2),
                'cout_total': round(abonnement + cout_energie, 2),
                'hp_kwh': round(repartition['hp_kwh'], 0),
                'hc_kwh': round(repartition['hc_kwh'], 0),
                'hp_pct': round(repartition['hp_pct']),
                'hc_pct': round(repartition['hc_pct']),
                'cout_hp': round(cout_hp, 2),
                'cout_hc': round(cout_hc, 2),
                'prix_hp': tarif['prix_hp'],
                'prix_hc': tarif['prix_hc'],
                'economie_vs_base': round(economie, 2)
            }
    
    def calculate_financial_details_force_base(self, consommation_annuelle: float, puissance: str) -> Dict:
        """Force le tarif Base (pour 3kVA qui ne peut pas avoir HP/HC)"""
        tarif = self.TARIFS_BASE_2024.get(puissance, self.TARIFS_BASE_2024['6kVA'])
        abonnement = tarif['abonnement']
        cout_energie = consommation_annuelle * tarif['prix_kwh']
        
        return {
            'type': 'base',
            'puissance': puissance,
            'abonnement': round(abonnement, 2),
            'cout_energie': round(cout_energie, 2),
            'cout_total': round(abonnement + cout_energie, 2),
            'prix_moyen_kwh': tarif['prix_kwh'],
            'note': 'HP/HC non disponible pour 3kVA'
        }
    
    def _repartir_hphc(self, total_annuel: float) -> Dict:
        """
        Répartit la consommation entre HP et HC selon les habitudes.
        
        HC = 8h/24h = 33.33% du temps (22h-6h)
        Mais consommation pas uniforme sur 24h.
        
        Hypothèses réalistes de programmation :
        - Chauffage : 50% HC (programmation thermostat)
        - ECS : 80% HC (chauffe-eau programmé obligatoire)
        - Électroménager : 35% HC (lave-linge/vaisselle nuit + programmation)
        - Cuisson : 10% HC (petit-déjeuner uniquement)
        - Audiovisuel : 25% HC (soirée 20h-22h + petit matin)
        - Éclairage : 45% HC (matin 6h-8h + soir 20h-22h)
        
        Returns:
            {'hp_kwh': 8500, 'hc_kwh': 4500, 'hp_pct': 65, 'hc_pct': 35}
        """
        # Recalculer les postes (on ne peut pas les passer en paramètre)
        chauffage = self.calculate_chauffage()['annuel']
        ecs = self.calculate_ecs()['annuel']
        electromenager = self.calculate_forfait_electromenager()['annuel']
        cuisson = self.calculate_forfait_cuisson()['annuel']
        audiovisuel = self.calculate_forfait_audiovisuel()['annuel']
        eclairage = self.calculate_forfait_eclairage()['annuel']
        
        # Appliquer les % HC par poste
        hc_chauffage = chauffage * 0.50
        hc_ecs = ecs * 0.80
        hc_electromenager = electromenager * 0.35
        hc_cuisson = cuisson * 0.10
        hc_audiovisuel = audiovisuel * 0.25
        hc_eclairage = eclairage * 0.45
        
        hc_total = (hc_chauffage + hc_ecs + hc_electromenager + 
                    hc_cuisson + hc_audiovisuel + hc_eclairage)
        hp_total = total_annuel - hc_total
        
        return {
            'hc_kwh': hc_total,
            'hp_kwh': hp_total,
            'hc_pct': (hc_total / total_annuel * 100) if total_annuel > 0 else 0,
            'hp_pct': (hp_total / total_annuel * 100) if total_annuel > 0 else 0,
        }
    
    def _calcul_economie_hphc(self, consommation_annuelle: float, puissance: str) -> float:
        """
        Calcule l'économie (ou surcoût) du tarif HP/HC vs Base.
        
        Returns:
            Économie en € (positif = économie, négatif = surcoût)
        """
        # Coût avec tarif Base
        tarif_base = self.TARIFS_BASE_2024.get(puissance, self.TARIFS_BASE_2024['6kVA'])
        cout_base = tarif_base['abonnement'] + (consommation_annuelle * tarif_base['prix_kwh'])
        
        # Coût avec tarif HP/HC
        tarif_hphc = self.TARIFS_HPHC_2024.get(puissance, self.TARIFS_HPHC_2024['6kVA'])
        repartition = self._repartir_hphc(consommation_annuelle)
        
        cout_hphc = (tarif_hphc['abonnement'] + 
                     (repartition['hp_kwh'] * tarif_hphc['prix_hp']) +
                     (repartition['hc_kwh'] * tarif_hphc['prix_hc']))
        
        return cout_base - cout_hphc  # Positif = économie avec HP/HC


def calculate_consumption_from_form(form_data: Dict) -> Dict:
    """
    Fonction helper pour calculer la consommation depuis un formulaire.
    
    Args:
        form_data: Données du formulaire
    
    Returns:
        Résultats du calcul
    """
    calculator = ConsumptionCalculator(form_data)
    return calculator.calculate_total()
