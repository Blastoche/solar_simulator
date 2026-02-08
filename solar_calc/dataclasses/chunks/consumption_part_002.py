    longitude: Optional[float] = None
    altitude: Optional[float] = None
    
    # Ã‰quipements Ã©lectriques de base
    refrigerateur: Optional[Appareil] = None
    congelateur: Optional[Appareil] = None
    plaques_cuisson: Optional[Appareil] = None
    four: Optional[Appareil] = None
    lave_linge: Optional[Appareil] = None
    lave_vaisselle: Optional[Appareil] = None
    seche_linge: Optional[Appareil] = None
    micro_ondes: Optional[Appareil] = None
    
    # SystÃ¨mes Ã©nergÃ©tiques
    chauffage: Optional[SystemeChauffage] = None
    ecs: Optional[SystemeECS] = None
    piscine: Optional[Piscine] = None
    
    # DonnÃ©es mÃ©tÃ©orologiques
    temperature_moyenne_annuelle: float = 12.0

    # Type de profil de consommation
    profile_type: str = 'actif_absent'  

    # Autres Ã©quipements (Ã  enrichir)
    autres_appareils: List[Appareil] = field(default_factory=list)
    
    def calcul_consommation_base(self) -> float:
        """
        Calcul de la consommation Ã©lectrique annuelle de base.
        
        Returns:
            float: Consommation annuelle totale en kWh
        """
        consommation_totale = 0.0
        
        # Consommation des appareils Ã©lectriques
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
        
        # Consommation de base (Ã©clairage, appareils en veille, etc.)
        # Environ 400 kWh/an/personne
        consommation_base = 400 * self.nb_personnes
        consommation_totale += consommation_base
        
        return round(consommation_totale, 2)
    
    def repartition_consommation(self) -> Dict[str, float]:
        """
        Calcule la rÃ©partition de la consommation par poste.
        
        Returns:
            dict: RÃ©partition de la consommation
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
        
        # Ã‰lectromÃ©nager
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
        GÃ©nÃ¨re un profil de consommation horaire sur une annÃ©e (8760h).
        
        Version amÃ©liorÃ©e avec :
        - Profils par type d'usage (actif/tÃ©lÃ©travail/retraite/famille)
        - Distinction weekends vs semaine
        - Variation alÃ©atoire rÃ©aliste
        
        Returns:
            pd.DataFrame: DataFrame avec colonnes [timestamp, consommation_kw]
            - timestamp: Horodatage heure par heure
            - consommation_kw: Consommation en kW
            8760 lignes (365 jours Ã— 24 heures)
        """
        # CrÃ©er index horaire
        dates = pd.date_range(
            start=f'{datetime.now().year}-01-01',
            periods=8760,
            freq='h'
        )
        
        # Consommation annuelle totale
        conso_totale = self.calcul_consommation_base()
        
        # âœ… NOUVEAU : GÃ©nÃ©rer pattern avec profil utilisateur
        pattern_annuel = ConsumptionProfiles.generate_yearly_pattern(
            profile_type=self.profile_type,
            add_randomness=True  # Variation Â±10%
        )
        
        # Normaliser pour correspondre Ã  la consommation totale
        pattern_normalise = pattern_annuel / pattern_annuel.sum() * conso_totale
        
        # CrÃ©er DataFrame
        df = pd.DataFrame({
            'timestamp': dates,
            'consommation_kw': pattern_normalise
        })
    
        return df


def creer_profil_standard() -> ConsumptionProfile:
    """
    CrÃ©er un profil de consommation standard franÃ§ais (maison type).
    
    Returns:
        ConsumptionProfile: Profil standard
    """
    return ConsumptionProfile(
        annee_construction=2015,
        surface_habitable=100,
        nb_personnes=3,
        dpe='C',
        refrigerateur=Appareil(
            nom="RÃ©frigÃ©rateur CombinÃ©",
            puissance_moyenne=150,
            frequence_journaliere=24,
            classe_energetique='A++'
        ),
        congelateur=Appareil(
            nom="CongÃ©lateur Coffre",
            puissance_moyenne=200,
            frequence_journaliere=24,
            classe_energetique='A+'
        ),
        plaques_cuisson=Appareil(
            nom="Plaques Ã  Induction",
            puissance_moyenne=2200,
            frequence_journaliere=1.5
        ),
