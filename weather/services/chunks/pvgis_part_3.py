        
        # Sauvegarder en cache
        expires_at = timezone.now() + timedelta(days=cache_days)
        
        # Supprimer les anciens caches pour cette localisation
        PVGISData.objects.filter(location=location).delete()
        
        pvgis_cache = PVGISData.objects.create(
            location=location,
            database=database,
            raw_data=json.dumps(data),
            irradiation_annuelle_kwh_m2=irradiation_annuelle,
            temperature_moyenne_annuelle=round(temperature_moyenne, 2) if temperature_moyenne else None,
            expires_at=expires_at,
        )
        
        logger.info(f"ðŸ’¾ DonnÃ©es PVGIS sauvegardÃ©es en cache (expire: {expires_at.strftime('%Y-%m-%d')})")
        
        metadata = {
            'source': 'api',
            'database': 'PVGIS-TMY (SARAH3)',
            'irradiation_annuelle': irradiation_annuelle,
            'temperature_moyenne': temperature_moyenne,
        }
        
        return df, metadata
        
    except Exception as e:
        logger.error(f"âŒ Erreur lors de l'appel PVGIS 5.3: {e}")
        raise


# Fonction helper pour utilisation facile
def get_pvgis_weather_data(
    latitude: float,
    longitude: float,
    use_cache: bool = True
) -> Tuple[pd.DataFrame, Dict]:
    """
    Fonction simplifiÃ©e pour rÃ©cupÃ©rer les donnÃ©es mÃ©tÃ©o PVGIS 5.3.
    
    Args:
        latitude: Latitude
        longitude: Longitude
        use_cache: Utiliser le cache
        
    Returns:
        Tuple[pd.DataFrame, Dict]: (DataFrame mÃ©tÃ©o 8760h, mÃ©tadonnÃ©es)
    """
    df, metadata = fetch_pvgis_data_with_cache(latitude, longitude, use_cache=use_cache)
    
    logger.info(
        f"ðŸ“Š DonnÃ©es PVGIS 5.3 rÃ©cupÃ©rÃ©es: {len(df)} heures, "
        f"irradiation: {metadata['irradiation_annuelle']:.0f} kWh/mÂ²/an "
        f"(source: {metadata['source']})"
    )
    
    return df, metadata

# ===== FONCTION AVEC CONTRAT CLAIR =====

def get_normalized_weather_data(
    latitude: float,
    longitude: float,
    use_cache: bool = True
) -> tuple:
    """
    Point d'entrÃ©e principal du module weather avec contrat garanti.
    
    CONTRAT GARANTI :
        DataFrame :
            - 8760 lignes exactement
            - Colonnes : ['timestamp', 'ghi', 'dni', 'dhi', 'temperature', ...]
            - timestamp : datetime normalisÃ© (annÃ©e courante)
            - ghi : W/mÂ² (>= 0)
            - temperature : Â°C
            - Pas de valeurs manquantes
        
        Metadata :
            - source : 'api', 'cache', ou 'fallback'
            - irradiation_annuelle : kWh/mÂ²/an
            - api_version : 'PVGIS 5.3'
    
    Args:
        latitude: Latitude (-90 Ã  90)
        longitude: Longitude (-180 Ã  180)
        use_cache: Utiliser le cache Redis
    
    Returns:
        tuple: (DataFrame 8760h, WeatherMetadata)
    
    Raises:
        ValueError: Si coordonnÃ©es invalides
        Exception: Si API et cache Ã©chouent
    
    Example:
        >>> df, meta = get_normalized_weather_data(43.3, 5.37)
        >>> print(len(df))  # 8760
        >>> print(meta.irradiation_annuelle)  # 1707.5
    """
    from weather.contracts import validate_weather_dataframe, create_weather_metadata
    
    # Appeler la fonction existante
    df, meta_dict = get_pvgis_weather_data(latitude, longitude, use_cache)
    
    # Valider le contrat
    validate_weather_dataframe(df)
    
    # CrÃ©er mÃ©tadonnÃ©es structurÃ©es
    metadata = create_weather_metadata(
        source=meta_dict.get('source', 'unknown'),
        df=df,
        latitude=latitude,
        longitude=longitude,
        api_version="PVGIS 5.3",
        retrieved_at=meta_dict.get('retrieved_at'),
        cached_until=meta_dict.get('cached_until')
    )
    
    return df, metadata
