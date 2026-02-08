            )
        
        # Mapping des colonnes PVGIS vers nos noms standard
        # PVGIS 5.3 utilise ces noms
        column_mapping = {
            'G(h)': 'ghi',           # Global Horizontal Irradiance
            'Gb(n)': 'dni',          # Direct Normal Irradiance  
            'Gd(h)': 'dhi',          # Diffuse Horizontal Irradiance
            'T2m': 'temperature',    # TempÃ©rature Ã  2m
            'WS10m': 'vitesse_vent', # Vitesse du vent Ã  10m
            'RH': 'humidite',        # HumiditÃ© relative
            'SP': 'pression',        # Pression de surface
            'WD10m': 'direction_vent', # Direction du vent
            'IR(h)': 'infrarouge',   # Irradiance infrarouge
        }
        
        # Renommer uniquement les colonnes qui existent
        existing_mappings = {k: v for k, v in column_mapping.items() if k in df.columns}
        df = df.rename(columns=existing_mappings)
        
        # SÃ©lectionner les colonnes pertinentes
        base_columns = ['timestamp']
        optional_columns = ['ghi', 'dni', 'dhi', 'temperature', 'vitesse_vent', 
                          'humidite', 'pression', 'direction_vent']
        
        available_columns = base_columns + [col for col in optional_columns if col in df.columns]
        df = df[available_columns]
        
        # VÃ©rifier le nombre d'heures
        if len(df) != 8760:
            logger.warning(f"Nombre d'heures incorrect: {len(df)} (attendu: 8760)")
        
        logger.info(f"DataFrame crÃ©Ã© avec {len(df)} heures et colonnes: {df.columns.tolist()}")
        
        return df
    
    def get_monthly_radiation(
        self,
        latitude: float,
        longitude: float,
        angle: float = 0,
        aspect: float = 0,
        raddatabase: str = 'PVGIS-SARAH3',
        **kwargs
    ) -> Dict:
        """
        RÃ©cupÃ¨re les donnÃ©es de rayonnement mensuelles.
        
        NOTE: Cet endpoint SUPPORTE le paramÃ¨tre raddatabase.
        
        Args:
            latitude: Latitude en degrÃ©s
            longitude: Longitude en degrÃ©s
            angle: Angle d'inclinaison (0-90)
            aspect: Orientation (0=sud, -90=est, 90=ouest)
            raddatabase: Base de donnÃ©es (SARAH2, SARAH3, etc.)
            
        Returns:
            dict: DonnÃ©es mensuelles
        """
        params = {
            'lat': latitude,
            'lon': longitude,
            'angle': angle,
            'aspect': aspect,
            'outputformat': 'json',
        }
        
        # MRcalc SUPPORTE raddatabase
        if raddatabase in self.DATABASES:
            params['raddatabase'] = raddatabase
        
        params.update(kwargs)
        
        url = f"{self.BASE_URL}/MRcalc"
        
        logger.info(f"Appel PVGIS monthly radiation pour {latitude}, {longitude}")
        
        try:
            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Erreur lors de l'appel PVGIS monthly: {e}")
            raise
    
    def calculate_annual_irradiation(self, df: pd.DataFrame) -> float:
        """
        Calcule l'irradiation annuelle totale depuis un DataFrame.
        
        Args:
            df: DataFrame avec colonne 'ghi' en W/mÂ²
            
        Returns:
            float: Irradiation annuelle en kWh/mÂ²
        """
        if 'ghi' not in df.columns:
            raise ValueError("Colonne 'ghi' manquante dans le DataFrame")
        
        # Somme de l'irradiance horaire (W/mÂ²) sur 8760h
        # DivisÃ© par 1000 pour convertir Wh â†’ kWh
        irradiation_annuelle = df['ghi'].sum() / 1000
        
        return round(irradiation_annuelle, 2)
    
    def get_location_info(self, latitude: float, longitude: float) -> Dict:
        """
        RÃ©cupÃ¨re les informations d'une localisation.
        
        Args:
            latitude: Latitude
            longitude: Longitude
            
        Returns:
            dict: Informations de localisation
        """
        # DÃ©terminer la rÃ©gion approximative
        region = "Unknown"
        if -20 <= latitude <= 70 and -30 <= longitude <= 60:
            region = "Europe/Afrique/Asie"
        elif -60 <= latitude <= 70 and -170 <= longitude <= -30:
            region = "AmÃ©riques"
        
        return {
            'latitude': latitude,
            'longitude': longitude,
            'region': region,
        }


def fetch_pvgis_data_with_cache(
    latitude: float,
    longitude: float,
    use_cache: bool = True,
    cache_days: int = 30
) -> Tuple[pd.DataFrame, Dict]:
    """
    RÃ©cupÃ¨re les donnÃ©es PVGIS 5.3 avec systÃ¨me de cache Django.
    
    Args:
        latitude: Latitude
        longitude: Longitude
        use_cache: Utiliser le cache Django
        cache_days: DurÃ©e de validitÃ© du cache en jours
        
    Returns:
        Tuple[pd.DataFrame, Dict]: (DataFrame mÃ©tÃ©o, mÃ©tadonnÃ©es)
    """
    from ..models import Location, PVGISData
    
    # CrÃ©er ou rÃ©cupÃ©rer la localisation
    location, _ = Location.objects.get_or_create(
        latitude=round(latitude, 4),
        longitude=round(longitude, 4),
        defaults={'altitude': 0}
    )
    
    # Database pour le cache (informatif seulement)
    database = 'PVGIS-SARAH3'
    
    # Chercher dans le cache
    if use_cache:
        cached = PVGISData.objects.filter(
            location=location,
            is_valid=True,
            expires_at__gt=timezone.now()
        ).first()
        
        if cached:
            logger.info(f"âœ… DonnÃ©es PVGIS trouvÃ©es en cache pour {location}")
            data = cached.get_data_dict()
            
            if data:
                client = PVGISClient()
                try:
                    df = client.parse_tmy_to_dataframe(data)
                    
                    metadata = {
                        'source': 'cache',
                        'cached_at': cached.created_at,
                        'irradiation_annuelle': cached.irradiation_annuelle_kwh_m2,
                    }
                    
                    return df, metadata
                except Exception as e:
                    logger.warning(f"âš ï¸ Erreur parsing cache, nouvel appel API: {e}")
                    # Le cache est corrompu, on va rÃ©essayer avec l'API
    
    # Appel API PVGIS 5.3
    logger.info(f"ðŸŒ Appel API PVGIS 5.3 pour {location}")
    client = PVGISClient()
    
    try:
        # Appel avec usehorizon pour meilleure prÃ©cision
        data = client.get_tmy_data(latitude, longitude, usehorizon=1)
        df = client.parse_tmy_to_dataframe(data)
        
        # Calculer l'irradiation annuelle
        irradiation_annuelle = client.calculate_annual_irradiation(df)
        temperature_moyenne = df['temperature'].mean() if 'temperature' in df.columns else None
