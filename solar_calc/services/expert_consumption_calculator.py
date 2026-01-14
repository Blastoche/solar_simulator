"""
Calculateur de consommation MODE EXPERT.
Hérite du ConsumptionCalculator et ajoute les calculs détaillés par appareil.
"""

import logging
from typing import Dict, List, Tuple
from .consumption_calculator import ConsumptionCalculator

logger = logging.getLogger(__name__)


class ExpertConsumptionCalculator(ConsumptionCalculator):
    """
    Calculateur expert avec appareils détaillés.
    
    Hérite de ConsumptionCalculator pour réutiliser :
    - Calcul chauffage
    - Calcul ECS
    - Calcul cuisson
    - Zone climatique
    - Facteurs DPE
    
    Ajoute :
    - Calculs détaillés électroménager
    - Calculs détaillés audiovisuel
    - Calculs détaillés éclairage
    - Piscine, spa, véhicule électrique
    - Profils horaires
    - Optimisation HP/HC
    - Projection 10 ans
    """
    
    # ========== DONNÉES DE RÉFÉRENCE ==========
    
    # Réfrigérateurs (kWh/an base)
    CONSO_FRIGOS = {
        'simple': 250,
        'combine': 300,
        'americain': 500,
    }
    
    # Congélateurs (kWh/an base)
    CONSO_CONGELATEURS = {
        'coffre': 250,
        'armoire': 300,
    }
    
    # Facteurs classe énergétique
    FACTEURS_CLASSE = {
        'A+++': 0.70,
        'A++': 0.85,
        'A+': 1.00,
        'A': 1.15,
        'B': 1.30,
        'C': 1.40,
    }
    
    # Lave-linge (kWh/cycle)
    CONSO_LAVE_LINGE = {
        'A+++': 0.45,
        'A++': 0.60,
        'A+': 0.80,
        'A': 1.00,
        'B': 1.20,
    }
    
    # Lave-vaisselle (kWh/cycle)
    CONSO_LAVE_VAISSELLE = {
        'A+++': 0.70,
        'A++': 0.90,
        'A+': 1.10,
        'A': 1.40,
        'B': 1.60,
    }
    
    # Sèche-linge (kWh/cycle)
    CONSO_SECHE_LINGE = {
        'pompe_chaleur_A+++': 1.5,
        'pompe_chaleur_A++': 2.0,
        'condensation_A+': 3.5,
        'evacuation': 4.5,
    }
    
    # Four (kWh/an base)
    CONSO_FOUR_BASE = {
        'micro_ondes': 100,
        'four_electrique': 150,
        'four_combine': 200,
    }
    
    FACTEURS_USAGE_FOUR = {
        'rarement': 1.0,
        'occasionnel': 2.0,
        'regulier': 3.0,
        'intensif': 4.0,
    }
    
    # TV (Watts selon taille)
    PUISSANCE_TV = {
        'petit': 50,    # < 32"
        'moyen': 80,    # 32-43"
        'grand': 120,   # 43-55"
        'tres_grand': 150,  # 55-65"
        'xxl': 200,     # > 65"
    }
    
    FACTEURS_TECHNO_TV = {
        'led': 1.0,
        'oled': 1.2,
    }
    
    # Box internet
    CONSO_BOX = {
        'seule': 150,
        'avec_decodeur': 200,
    }
    
    # Ordinateurs (Watts)
    PUISSANCE_ORDI = {
        'fixe': 200,
        'portable': 50,
    }
    
    # Consoles (Watts)
    PUISSANCE_CONSOLE = {
        'ancienne': 150,
        'actuelle': 200,
    }
    
    # Spa (kWh/an base)
    CONSO_SPA_BASE = {
        'gonflable': 2000,
        'rigide': 3000,
        'interieur': 4000,
    }
    
    # Profils horaires (coefficient par tranche horaire)
    PROFILS_HORAIRES = {
        'actif_absent': {
            'nuit': 0.1,      # 0-6h
            'matin': 0.8,     # 6-8h
            'journee': 0.2,   # 8-18h
            'soir': 1.0,      # 18-22h
            'fin_soir': 0.3,  # 22-24h
        },
        'teletravail_partiel': {
            'nuit': 0.1,
            'matin': 0.9,
            'journee': 0.5,   # Présence partielle
            'soir': 1.0,
            'fin_soir': 0.4,
        },
        'teletravail_complet': {
            'nuit': 0.1,
            'matin': 0.9,
            'journee': 0.8,   # Présence complète
            'soir': 1.0,
            'fin_soir': 0.4,
        },
        'retraite': {
            'nuit': 0.1,
            'matin': 0.9,
            'journee': 0.7,   # Présence forte
            'soir': 0.9,
            'fin_soir': 0.3,
        },
    }
    
    def __init__(self, data: Dict):
        """Initialise le calculateur expert."""
        super().__init__(data)
        
        # Stocker les appareils détaillés
        self.appareils = []
        
        logger.info(f"🔬 Calculateur EXPERT initialisé pour {self.surface}m², {self.nb_personnes} pers")
    
    # ========== RÉFRIGÉRATION ==========
    
    def calculate_refrigeration(self) -> List[Dict]:
        """Calcule la consommation des frigos et congélateurs."""
        appareils = []
        
        # Réfrigérateurs
        frigos = self.data.get('frigos', [])
        for i, frigo in enumerate(frigos):
            type_frigo = frigo.get('type')
            nombre = frigo.get('nombre', 1)
            classe = frigo.get('classe', 'A+')
            
            if type_frigo and type_frigo != 'aucun':
                conso_base = self.CONSO_FRIGOS.get(type_frigo, 300)
                facteur_classe = self.FACTEURS_CLASSE.get(classe, 1.0)
                conso_annuelle = conso_base * facteur_classe * nombre
                
                appareils.append({
                    'categorie': 'refrigeration',
                    'type_appareil': f'frigo_{type_frigo}',
                    'nom_affichage': f'Réfrigérateur {type_frigo.title()} {classe}',
                    'nombre': nombre,
                    'classe_energetique': classe,
                    'consommation_annuelle': conso_annuelle,
                    'consommation_mensuelle': [conso_annuelle / 12] * 12,
                })
                
                logger.info(f"❄️ Frigo {type_frigo} {classe} (×{nombre}): {conso_annuelle:.0f} kWh/an")
        
        # Congélateurs
        congelateurs = self.data.get('congelateurs', [])
        for i, congelateur in enumerate(congelateurs):
            type_cong = congelateur.get('type')
            nombre = congelateur.get('nombre', 1)
            classe = congelateur.get('classe', 'A+')
            
            if type_cong and type_cong != 'aucun':
                conso_base = self.CONSO_CONGELATEURS.get(type_cong, 300)
                facteur_classe = self.FACTEURS_CLASSE.get(classe, 1.0)
                conso_annuelle = conso_base * facteur_classe * nombre
                
                appareils.append({
                    'categorie': 'refrigeration',
                    'type_appareil': f'congelateur_{type_cong}',
                    'nom_affichage': f'Congélateur {type_cong.title()} {classe}',
                    'nombre': nombre,
                    'classe_energetique': classe,
                    'consommation_annuelle': conso_annuelle,
                    'consommation_mensuelle': [conso_annuelle / 12] * 12,
                })
                
                logger.info(f"🧊 Congélateur {type_cong} {classe} (×{nombre}): {conso_annuelle:.0f} kWh/an")
        
        return appareils
    
    # ========== LAVAGE ==========
    
    def calculate_lavage(self) -> List[Dict]:
        """Calcule la consommation lave-linge, lave-vaisselle, sèche-linge."""
        appareils = []
        
        # Lave-linge
        if self.data.get('lave_linge_actif', True):
            classe = self.data.get('lave_linge_classe', 'A++')
            cycles_sem = self.data.get('lave_linge_cycles', 4)
            
            conso_cycle = self.CONSO_LAVE_LINGE.get(classe, 0.80)
            conso_annuelle = conso_cycle * cycles_sem * 52
            
            appareils.append({
                'categorie': 'lavage',
                'type_appareil': 'lave_linge',
                'nom_affichage': f'Lave-linge {classe}',
                'classe_energetique': classe,
                'cycles_semaine': cycles_sem,
                'consommation_annuelle': conso_annuelle,
                'consommation_mensuelle': [conso_annuelle / 12] * 12,
            })
            
            logger.info(f"🧺 Lave-linge {classe} ({cycles_sem} cycles/sem): {conso_annuelle:.0f} kWh/an")
        
        # Lave-vaisselle
        if self.data.get('lave_vaisselle_actif', True):
            classe = self.data.get('lave_vaisselle_classe', 'A++')
            cycles_sem = self.data.get('lave_vaisselle_cycles', 5)
            
            conso_cycle = self.CONSO_LAVE_VAISSELLE.get(classe, 1.10)
            conso_annuelle = conso_cycle * cycles_sem * 52
            
            appareils.append({
                'categorie': 'lavage',
                'type_appareil': 'lave_vaisselle',
                'nom_affichage': f'Lave-vaisselle {classe}',
                'classe_energetique': classe,
                'cycles_semaine': cycles_sem,
                'consommation_annuelle': conso_annuelle,
                'consommation_mensuelle': [conso_annuelle / 12] * 12,
            })
            
            logger.info(f"🍽️ Lave-vaisselle {classe} ({cycles_sem} cycles/sem): {conso_annuelle:.0f} kWh/an")
        
        # Sèche-linge
        if self.data.get('seche_linge_actif', False):
            type_seche = self.data.get('seche_linge_type', 'pompe_chaleur_A++')
            cycles_sem = self.data.get('seche_linge_cycles', 3)
            
            conso_cycle = self.CONSO_SECHE_LINGE.get(type_seche, 2.0)
            conso_annuelle = conso_cycle * cycles_sem * 52
            
            appareils.append({
                'categorie': 'lavage',
                'type_appareil': 'seche_linge',
                'nom_affichage': f'Sèche-linge {type_seche.replace("_", " ").title()}',
                'cycles_semaine': cycles_sem,
                'consommation_annuelle': conso_annuelle,
                'consommation_mensuelle': [conso_annuelle / 12] * 12,
            })
            
            logger.info(f"👕 Sèche-linge {type_seche} ({cycles_sem} cycles/sem): {conso_annuelle:.0f} kWh/an")
        
        return appareils
    
    # ========== FOUR ==========
    
    def calculate_four_expert(self) -> List[Dict]:
        """Calcule la consommation du four en mode expert."""
        appareils = []
        
        type_four = self.data.get('type_four', 'four_electrique')
        usage = self.data.get('usage_four', 'occasionnel')
        
        if type_four and type_four != 'aucun':
            conso_base = self.CONSO_FOUR_BASE.get(type_four, 150)
            facteur_usage = self.FACTEURS_USAGE_FOUR.get(usage, 1.0)
            conso_annuelle = conso_base * facteur_usage
            
            # Mapping propre des noms de four (CORRECTION ICI)
            noms_four = {
                'four_electrique': 'Four Électrique',
                'four_combine': 'Four Combiné',
                'four_gaz': 'Four Gaz',
            }
            nom_four = noms_four.get(type_four, type_four.replace('_', ' ').title())
            
            # Mapping usage
            noms_usage = {
                'occasionnel': 'occasionnel',
                'regulier': 'régulier',
                'intensif': 'intensif',
            }
            nom_usage = noms_usage.get(usage, usage)
            
            appareils.append({
                'categorie': 'cuisson',
                'type_appareil': type_four,
                'nom_affichage': f'{nom_four} ({nom_usage})',  # ← CORRIGÉ : Plus de "Four Four" !
                'nombre': 1,
                'consommation_annuelle': conso_annuelle,
            })
            
            logger.info(f"🍳 {nom_four} ({nom_usage}): {conso_annuelle:.0f} kWh/an")
        
        return appareils
    
    # ========== AUDIOVISUEL DÉTAILLÉ ==========
    
    def calculate_audiovisuel_expert(self) -> List[Dict]:
        """Calcule la consommation audiovisuelle détaillée."""
        appareils = []
        
        # TVs
        tvs = self.data.get('tvs', [])
        for i, tv in enumerate(tvs):
            taille = tv.get('taille', 'moyen')
            techno = tv.get('techno', 'led')
            heures_jour = tv.get('heures_jour', 4)
            
            puissance = self.PUISSANCE_TV.get(taille, 80)
            facteur_techno = self.FACTEURS_TECHNO_TV.get(techno, 1.0)
            puissance_reelle = puissance * facteur_techno
            
            conso_annuelle = puissance_reelle * heures_jour * 365 / 1000
            
            appareils.append({
                'categorie': 'audiovisuel',
                'type_appareil': f'tv_{taille}_{techno}',
                'nom_affichage': f'TV {taille} {techno.upper()} ({heures_jour}h/j)',
                'puissance_w': int(puissance_reelle),
                'heures_jour': heures_jour,
                'consommation_annuelle': conso_annuelle,
                'consommation_mensuelle': [conso_annuelle / 12] * 12,
            })
            
            logger.info(f"📺 TV {taille} {techno} ({heures_jour}h/j): {conso_annuelle:.0f} kWh/an")
        
        # Box internet
        type_box = self.data.get('type_box', 'seule')
        eteinte_nuit = self.data.get('box_eteinte_nuit', False)
        
        conso_box = self.CONSO_BOX.get(type_box, 150)
        if eteinte_nuit:
            conso_box *= 0.7
        
        appareils.append({
            'categorie': 'audiovisuel',
            'type_appareil': f'box_{type_box}',
            'nom_affichage': f'Box internet {"+ décodeur" if type_box == "avec_decodeur" else ""}',
            'consommation_annuelle': conso_box,
            'consommation_mensuelle': [conso_box / 12] * 12,
        })
        
        logger.info(f"📶 Box {type_box}: {conso_box:.0f} kWh/an")
        
        # Ordinateurs
        nb_fixes = self.data.get('nb_ordis_fixes', 0)
        nb_portables = self.data.get('nb_ordis_portables', 0)
        heures_ordi = self.data.get('heures_ordi', 6)
        
        if nb_fixes > 0:
            conso_fixes = self.PUISSANCE_ORDI['fixe'] * nb_fixes * heures_ordi * 365 / 1000
            appareils.append({
                'categorie': 'audiovisuel',
                'type_appareil': 'ordinateur_fixe',
                'nom_affichage': f'Ordinateur fixe (×{nb_fixes}, {heures_ordi}h/j)',
                'nombre': nb_fixes,
                'puissance_w': self.PUISSANCE_ORDI['fixe'],
                'heures_jour': heures_ordi,
                'consommation_annuelle': conso_fixes,
                'consommation_mensuelle': [conso_fixes / 12] * 12,
            })
            logger.info(f"💻 Ordis fixes (×{nb_fixes}, {heures_ordi}h/j): {conso_fixes:.0f} kWh/an")
        
        if nb_portables > 0:
            conso_portables = self.PUISSANCE_ORDI['portable'] * nb_portables * heures_ordi * 365 / 1000
            appareils.append({
                'categorie': 'audiovisuel',
                'type_appareil': 'ordinateur_portable',
                'nom_affichage': f'Ordinateur portable (×{nb_portables}, {heures_ordi}h/j)',
                'nombre': nb_portables,
                'puissance_w': self.PUISSANCE_ORDI['portable'],
                'heures_jour': heures_ordi,
                'consommation_annuelle': conso_portables,
                'consommation_mensuelle': [conso_portables / 12] * 12,
            })
            logger.info(f"💻 Ordis portables (×{nb_portables}, {heures_ordi}h/j): {conso_portables:.0f} kWh/an")
        
        # Console
        if self.data.get('console_actif', False):
            type_console = self.data.get('type_console', 'actuelle')
            heures_console = self.data.get('heures_console', 2)
            
            puissance_console = self.PUISSANCE_CONSOLE.get(type_console, 200)
            conso_console = puissance_console * heures_console * 365 / 1000
            
            appareils.append({
                'categorie': 'audiovisuel',
                'type_appareil': f'console_{type_console}',
                'nom_affichage': f'Console {type_console} ({heures_console}h/j)',
                'puissance_w': puissance_console,
                'heures_jour': heures_console,
                'consommation_annuelle': conso_console,
                'consommation_mensuelle': [conso_console / 12] * 12,
            })
            logger.info(f"🎮 Console {type_console} ({heures_console}h/j): {conso_console:.0f} kWh/an")
        
        return appareils
    
    # ========== ÉCLAIRAGE DÉTAILLÉ ==========
    
    def calculate_eclairage_expert(self) -> List[Dict]:
        """Calcule la consommation éclairage détaillée."""
        appareils = []
        
        nb_led = self.data.get('nb_led', 0)
        nb_halogene = self.data.get('nb_halogene', 0)
        heures_jour = self.data.get('heures_eclairage', 5)
        
        if nb_led > 0:
            conso_led = nb_led * 10 * heures_jour * 365 / 1000
            appareils.append({
                'categorie': 'eclairage',
                'type_appareil': 'led',
                'nom_affichage': f'Ampoules LED (×{nb_led}, {heures_jour}h/j)',
                'nombre': nb_led,
                'puissance_w': 10,
                'heures_jour': heures_jour,
                'consommation_annuelle': conso_led,
                'consommation_mensuelle': self._distribute_lighting_monthly(conso_led),
            })
            logger.info(f"💡 LED (×{nb_led}, {heures_jour}h/j): {conso_led:.0f} kWh/an")
        
        if nb_halogene > 0:
            conso_halogene = nb_halogene * 50 * heures_jour * 365 / 1000
            appareils.append({
                'categorie': 'eclairage',
                'type_appareil': 'halogene',
                'nom_affichage': f'Ampoules halogène (×{nb_halogene}, {heures_jour}h/j)',
                'nombre': nb_halogene,
                'puissance_w': 50,
                'heures_jour': heures_jour,
                'consommation_annuelle': conso_halogene,
                'consommation_mensuelle': self._distribute_lighting_monthly(conso_halogene),
            })
            logger.info(f"💡 Halogène (×{nb_halogene}, {heures_jour}h/j): {conso_halogene:.0f} kWh/an")
        
        return appareils
    
    # ========== PISCINE ==========
    
    def calculate_piscine(self) -> List[Dict]:
        """Calcule la consommation piscine."""
        appareils = []
        
        if not self.data.get('piscine_active', False):
            return appareils
        
        # Pompe filtration
        puissance_pompe = self.data.get('piscine_puissance_pompe')
        if not puissance_pompe:
            # Type prédéfini
            type_pompe = self.data.get('piscine_type_pompe', 'standard')
            puissances = {'petite': 600, 'standard': 1000, 'grande': 1500}
            puissance_pompe = puissances.get(type_pompe, 1000)
        
        heures_filtration = self.data.get('piscine_heures_filtration', 8)
        mois_debut = self.data.get('piscine_mois_debut', 5)  # Mai
        mois_fin = self.data.get('piscine_mois_fin', 9)  # Septembre
        
        # Calcul nombre de jours
        nb_mois = (mois_fin - mois_debut + 1) if mois_fin >= mois_debut else (12 - mois_debut + mois_fin + 1)
        nb_jours = nb_mois * 30  # Approximation
        
        conso_pompe = puissance_pompe * heures_filtration * nb_jours / 1000
        
        mensuel = [0] * 12
        for mois in range(mois_debut - 1, mois_fin):
            mensuel[mois % 12] = conso_pompe / nb_mois
        
        appareils.append({
            'categorie': 'piscine',
            'type_appareil': 'pompe_filtration',
            'nom_affichage': f'Pompe piscine {puissance_pompe}W ({heures_filtration}h/j)',
            'puissance_w': puissance_pompe,
            'heures_jour': heures_filtration,
            'mois_debut': mois_debut,
            'mois_fin': mois_fin,
            'consommation_annuelle': conso_pompe,
            'consommation_mensuelle': mensuel,
        })
        
        logger.info(f"🏊 Pompe piscine {puissance_pompe}W ({heures_filtration}h/j, {nb_mois} mois): {conso_pompe:.0f} kWh/an")
        
        # Chauffage piscine (si présent)
        if self.data.get('piscine_chauffage_actif', False):
            type_chauffage = self.data.get('piscine_type_chauffage')
            puissance_chauffage = self.data.get('piscine_puissance_chauffage', 2000)
            heures_chauffage = self.data.get('piscine_heures_chauffage', 4)
            
            conso_chauffage = puissance_chauffage * heures_chauffage * nb_jours / 1000
            
            mensuel_chauf = [0] * 12
            for mois in range(mois_debut - 1, mois_fin):
                mensuel_chauf[mois % 12] = conso_chauffage / nb_mois
            
            appareils.append({
                'categorie': 'piscine',
                'type_appareil': f'chauffage_{type_chauffage}',
                'nom_affichage': f'Chauffage piscine {puissance_chauffage}W',
                'puissance_w': puissance_chauffage,
                'heures_jour': heures_chauffage,
                'mois_debut': mois_debut,
                'mois_fin': mois_fin,
                'consommation_annuelle': conso_chauffage,
                'consommation_mensuelle': mensuel_chauf,
            })
            
            logger.info(f"🔥 Chauffage piscine {puissance_chauffage}W: {conso_chauffage:.0f} kWh/an")
        
        # Robot (si présent)
        if self.data.get('piscine_robot_actif', False):
            conso_robot = 200 * 2 * 52 / 1000  # 200W × 2h/semaine × 52 semaines
            
            appareils.append({
                'categorie': 'piscine',
                'type_appareil': 'robot',
                'nom_affichage': 'Robot nettoyeur piscine',
                'puissance_w': 200,
                'consommation_annuelle': conso_robot,
                'consommation_mensuelle': [conso_robot / 12] * 12,
            })
            
            logger.info(f"🤖 Robot piscine: {conso_robot:.0f} kWh/an")
        
        return appareils
    
    # ========== SPA ==========
    
    def calculate_spa(self) -> List[Dict]:
        """Calcule la consommation spa/jacuzzi."""
        appareils = []
        
        if not self.data.get('spa_actif', False):
            return appareils
        
        type_spa = self.data.get('type_spa', 'rigide')
        conso_base = self.CONSO_SPA_BASE.get(type_spa, 3000)
        
        # Facteurs multiplicateurs
        facteur_saison = 1.0 if self.data.get('spa_toute_annee', True) else 0.5
        facteur_temp = 1.0 if self.data.get('spa_temp_maintenue', True) else 0.6
        facteur_couverture = 0.7 if self.data.get('spa_couverture', True) else 1.0
        
        conso_annuelle = conso_base * facteur_saison * facteur_temp * facteur_couverture
        
        appareils.append({
            'categorie': 'spa',
            'type_appareil': type_spa,
            'nom_affichage': f'Spa {type_spa}',
            'consommation_annuelle': conso_annuelle,
            'consommation_mensuelle': [conso_annuelle / 12] * 12,
        })
        
        logger.info(f"🛁 Spa {type_spa}: {conso_annuelle:.0f} kWh/an")
        
        return appareils
    
    # ========== VÉHICULE ÉLECTRIQUE ==========
    
    def calculate_vehicule_electrique(self) -> List[Dict]:
        """Calcule la consommation véhicule électrique."""
        appareils = []
        
        vehicules = self.data.get('vehicules', [])
        
        for i, ve in enumerate(vehicules):
            conso_100km = ve.get('conso_100km', 18)
            km_an = ve.get('km_an', 15000)
            type_recharge = ve.get('type_recharge', 'wallbox_7')
            pct_domicile = ve.get('pct_recharge_domicile', 100)
            
            # Rendements de charge
            rendements = {
                'prise': 0.85,
                'wallbox_7': 0.90,
                'wallbox_11': 0.92,
                'wallbox_22': 0.93,
            }
            rendement = rendements.get(type_recharge, 0.90)
            
            # Consommation véhicule
            conso_vehicule = (km_an / 100) * conso_100km
            
            # Part rechargée à domicile
            conso_domicile = conso_vehicule * (pct_domicile / 100)
            
            # Pertes de charge
            conso_compteur = conso_domicile / rendement
            
            appareils.append({
                'categorie': 'vehicule',
                'type_appareil': 've',
                'nom_affichage': f'Véhicule électrique ({conso_100km} kWh/100km, {km_an} km/an)',
                'km_an': km_an,
                'conso_100km': conso_100km,
                'rendement_charge': rendement,
                'pct_recharge_domicile': pct_domicile,
                'consommation_annuelle': conso_compteur,
                'consommation_mensuelle': [conso_compteur / 12] * 12,
            })
            
            logger.info(f"🚗⚡ VE ({conso_100km} kWh/100km, {km_an} km/an): {conso_compteur:.0f} kWh/an")
        
        return appareils
    
    # ========== CALCUL TOTAL EXPERT ==========
    
    def calculate_total_expert(self) -> Dict:
        """Calcul complet mode expert."""
        
        # Appareils détaillés
        self.appareils = []
        
        # Réfrigération
        self.appareils.extend(self.calculate_refrigeration())
        
        # Lavage
        self.appareils.extend(self.calculate_lavage())
        
        # Four
        self.appareils.extend(self.calculate_four_expert())
        
        # Audiovisuel
        self.appareils.extend(self.calculate_audiovisuel_expert())
        
        # Éclairage
        self.appareils.extend(self.calculate_eclairage_expert())
        
        # Piscine
        self.appareils.extend(self.calculate_piscine())
        
        # Spa
        self.appareils.extend(self.calculate_spa())
        
        # Véhicule électrique
        self.appareils.extend(self.calculate_vehicule_electrique())
        
        # Chauffage (du parent)
        chauffage = self.calculate_chauffage()
        
        # ECS (du parent)
        ecs = self.calculate_ecs()
        
        # Cuisson (du parent - plaques uniquement)
        cuisson = self.calculate_forfait_cuisson()
        
        # Calculer totaux
        total_appareils = sum(app['consommation_annuelle'] for app in self.appareils)
        total_annuel = chauffage['annuel'] + ecs['annuel'] + cuisson['annuel'] + total_appareils
        
        # Répartition
        repartition = {
            'chauffage': {
                'kwh': chauffage['annuel'],
                'pourcentage': round((chauffage['annuel'] / total_annuel * 100) if total_annuel > 0 else 0)
            },
            'ecs': {
                'kwh': ecs['annuel'],
                'pourcentage': round((ecs['annuel'] / total_annuel * 100) if total_annuel > 0 else 0)
            },
            'cuisson': {
                'kwh': cuisson['annuel'],
                'pourcentage': round((cuisson['annuel'] / total_annuel * 100) if total_annuel > 0 else 0)
            },
        }
        
        # Grouper appareils par catégorie pour répartition
        for categorie in ['refrigeration', 'lavage', 'audiovisuel', 'eclairage', 'piscine', 'spa', 'vehicule']:
            conso_cat = sum(app['consommation_annuelle'] for app in self.appareils if app['categorie'] == categorie)
            if conso_cat > 0:
                repartition[categorie] = {
                    'kwh': conso_cat,
                    'pourcentage': round((conso_cat / total_annuel * 100) if total_annuel > 0 else 0)
                }
        
        # Moyenne attendue
        moyenne_attendue = self._calculate_expected_consumption()
        ecart_pct = ((total_annuel - moyenne_attendue) / moyenne_attendue * 100) if moyenne_attendue > 0 else 0
        
        # Mensuel
        monthly = [0] * 12
        for mois in range(12):
            monthly[mois] = chauffage['mensuel'][mois] + ecs['mensuel'][mois] + cuisson['mensuel'][mois]
            for app in self.appareils:
                if app.get('consommation_mensuelle'):
                    monthly[mois] += app['consommation_mensuelle'][mois]
        
        logger.info(f"📊 TOTAL EXPERT: {total_annuel:.0f} kWh/an ({len(self.appareils)} appareils détaillés)")
        
        return {
            'total_annuel': round(total_annuel, 0),
            'mensuel': [round(m, 0) for m in monthly],
            'moyenne_attendue': round(moyenne_attendue, 0),
            'ecart_pct': round(ecart_pct, 1),
            'repartition': repartition,
            'appareils': self.appareils,
            'details_postes': {
                'chauffage': chauffage['details'],
                'ecs': ecs['details'],
                'cuisson': cuisson['details'],
            }
        }
    
    # ========== OPTIMISATION HP/HC ==========
    
    def calculate_optimisation_hphc(self, total_annuel: float) -> Dict:
        """Calcule l'optimisation possible HP/HC selon profil."""
        profil = self.data.get('profil_usage', 'actif_absent')
        
        # % HC selon profil (estimation réaliste)
        pct_hc_profils = {
            'actif_absent': 37,
            'teletravail_partiel': 32,
            'teletravail_complet': 27,
            'retraite': 22,
        }
        
        pct_hc_actuel = pct_hc_profils.get(profil, 30)
        
        # Optimisation possible en programmant les appareils
        # (chauffe-eau, lave-linge, lave-vaisselle, VE en HC)
        pct_hc_optimal = min(pct_hc_actuel + 15, 55)  # Max 55%
        
        # Calcul économie
        hc_actuel_kwh = total_annuel * (pct_hc_actuel / 100)
        hp_actuel_kwh = total_annuel - hc_actuel_kwh
        
        hc_optimal_kwh = total_annuel * (pct_hc_optimal / 100)
        hp_optimal_kwh = total_annuel - hc_optimal_kwh
        
        # Tarifs 2024
        prix_hp = 0.2700
        prix_hc = 0.2068
        
        cout_actuel = (hp_actuel_kwh * prix_hp) + (hc_actuel_kwh * prix_hc)
        cout_optimal = (hp_optimal_kwh * prix_hp) + (hc_optimal_kwh * prix_hc)
        
        economie = cout_actuel - cout_optimal
        
        return {
            'pct_hc_actuel': pct_hc_actuel,
            'pct_hc_optimal': pct_hc_optimal,
            'economie_annuelle': round(economie, 2),
            'profil': profil,
        }
    
    # ========== PROJECTION 10 ANS ==========
    
    def calculate_projection_10ans(self, total_annuel: float, cout_actuel: float) -> List[Dict]:
        """Projection consommation et coûts sur 10 ans."""
        inflation_energie = 0.05  # 5% par an
        evolution_conso = -0.01  # -1% par an (amélioration)
        
        projections = []
        
        for annee in range(1, 11):
            conso = total_annuel * ((1 + evolution_conso) ** annee)
            prix_kwh = (cout_actuel / total_annuel) * ((1 + inflation_energie) ** annee)
            cout = conso * prix_kwh
            
            projections.append({
                'annee': 2026 + annee,
                'consommation_kwh': round(conso, 0),
                'prix_moyen_kwh': round(prix_kwh, 4),
                'cout_total': round(cout, 2),
            })
        
        return projections
