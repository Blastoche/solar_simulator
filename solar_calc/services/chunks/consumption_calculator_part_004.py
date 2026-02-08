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
        
        BasÃ© sur :
        - Base incompressible : 1500 kWh
        - + 800 kWh/personne (Ã©lectromÃ©nager, audiovisuel)
        - + Chauffage selon DPE et surface (si Ã©lectrique)
        
        Returns:
            Consommation attendue (kWh/an)
        """
        base = 1500  # Incompressible (veilles, Ã©clairage, etc.)
        
        # Par personne
        base += self.nb_personnes * 800
        
        # Chauffage (si Ã©lectrique)
        type_chauffage = self.data.get('type_chauffage', 'electrique')
        if type_chauffage in ['electrique', 'pac']:
            # Besoin DPE en Ã©nergie PRIMAIRE
            besoin_chauffage_primaire = self.BESOINS_DPE[self.dpe] * self.surface
            
            # Conversion primaire â†’ finale
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
        Calcule les coÃ»ts dÃ©taillÃ©s avec tarif Base ou HP/HC.
        
        Args:
            consommation_annuelle: kWh/an total
        
        Returns:
            Dict avec abonnement, coÃ»t Ã©nergie, coÃ»t total, dÃ©tails HP/HC si applicable
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
            # VÃ©rifier que la puissance supporte HP/HC (â‰¥6kVA)
            if puissance == '3kVA':
                logger.warning("HP/HC non disponible pour 3kVA, passage en Base")
                # Forcer Base
                return self.calculate_financial_details_force_base(consommation_annuelle, puissance)
            
            tarif = self.TARIFS_HPHC_2024.get(puissance, self.TARIFS_HPHC_2024['6kVA'])
            abonnement = tarif['abonnement']
            
            # RÃ©partir consommation HP/HC selon profil
            repartition = self._repartir_hphc(consommation_annuelle)
            
            cout_hp = repartition['hp_kwh'] * tarif['prix_hp']
            cout_hc = repartition['hc_kwh'] * tarif['prix_hc']
            cout_energie = cout_hp + cout_hc
            
            # Calculer Ã©conomie vs Base
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
        RÃ©partit la consommation entre HP et HC selon les habitudes.
        
        HC = 8h/24h = 33.33% du temps (22h-6h)
        Mais consommation pas uniforme sur 24h.
        
        HypothÃ¨ses rÃ©alistes de programmation :
        - Chauffage : 50% HC (programmation thermostat)
        - ECS : 80% HC (chauffe-eau programmÃ© obligatoire)
        - Ã‰lectromÃ©nager : 35% HC (lave-linge/vaisselle nuit + programmation)
        - Cuisson : 10% HC (petit-dÃ©jeuner uniquement)
        - Audiovisuel : 25% HC (soirÃ©e 20h-22h + petit matin)
        - Ã‰clairage : 45% HC (matin 6h-8h + soir 20h-22h)
        
        Returns:
            {'hp_kwh': 8500, 'hc_kwh': 4500, 'hp_pct': 65, 'hc_pct': 35}
        """
        # Recalculer les postes (on ne peut pas les passer en paramÃ¨tre)
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
        Calcule l'Ã©conomie (ou surcoÃ»t) du tarif HP/HC vs Base.
        
        Returns:
            Ã‰conomie en â‚¬ (positif = Ã©conomie, nÃ©gatif = surcoÃ»t)
        """
        # CoÃ»t avec tarif Base
        tarif_base = self.TARIFS_BASE_2024.get(puissance, self.TARIFS_BASE_2024['6kVA'])
        cout_base = tarif_base['abonnement'] + (consommation_annuelle * tarif_base['prix_kwh'])
        
        # CoÃ»t avec tarif HP/HC
        tarif_hphc = self.TARIFS_HPHC_2024.get(puissance, self.TARIFS_HPHC_2024['6kVA'])
        repartition = self._repartir_hphc(consommation_annuelle)
        
        cout_hphc = (tarif_hphc['abonnement'] + 
                     (repartition['hp_kwh'] * tarif_hphc['prix_hp']) +
                     (repartition['hc_kwh'] * tarif_hphc['prix_hc']))
