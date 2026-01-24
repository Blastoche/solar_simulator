"""
Validators avancés pour le module core

Validation de configurations solaires, batteries et autres paramètres techniques.
"""

from django.core.exceptions import ValidationError
import warnings


# ==============================================================================
# VALIDATORS CONFIGURATION SOLAIRE
# ==============================================================================

def validate_solar_config(nombre_panneaux, puissance_panneau_wc, puissance_onduleur_kw):
    """
    Vérifie la cohérence du dimensionnement d'une installation solaire.
    
    Args:
        nombre_panneaux: Nombre de panneaux
        puissance_panneau_wc: Puissance unitaire en Wc
        puissance_onduleur_kw: Puissance de l'onduleur en kW
    
    Raises:
        ValidationError: Si configuration incohérente
    
    Warnings:
        UserWarning: Si dimensionnement sub-optimal
    """
    # Calcul puissance crête totale
    puissance_totale_kwc = (nombre_panneaux * puissance_panneau_wc) / 1000
    
    # Règle générale : onduleur entre 0.8x et 1.2x la puissance crête
    ratio = puissance_onduleur_kw / puissance_totale_kwc
    
    if ratio < 0.6:
        raise ValidationError(
            f"Onduleur gravement sous-dimensionné : {puissance_onduleur_kw}kW "
            f"pour {puissance_totale_kwc:.1f}kWc (ratio {ratio:.2f}). "
            f"Minimum recommandé : {puissance_totale_kwc * 0.7:.1f}kW"
        )
    
    if ratio > 1.5:
        raise ValidationError(
            f"Onduleur surdimensionné : {puissance_onduleur_kw}kW "
            f"pour {puissance_totale_kwc:.1f}kWc (ratio {ratio:.2f}). "
            f"Maximum recommandé : {puissance_totale_kwc * 1.3:.1f}kW"
        )
    
    # Warnings pour dimensionnement sub-optimal
    if ratio < 0.8:
        warnings.warn(
            f"Onduleur sous-dimensionné : {puissance_onduleur_kw}kW "
            f"pour {puissance_totale_kwc:.1f}kWc (ratio {ratio:.2f}). "
            f"Recommandé : {puissance_totale_kwc * 0.9:.1f}kW minimum",
            UserWarning
        )
    
    if ratio > 1.2:
        warnings.warn(
            f"Onduleur surdimensionné : {puissance_onduleur_kw}kW "
            f"pour {puissance_totale_kwc:.1f}kWc (ratio {ratio:.2f}). "
            f"Recommandé : {puissance_totale_kwc * 1.1:.1f}kW maximum. "
            f"Coût supplémentaire sans gain de production.",
            UserWarning
        )


def validate_panel_orientation(azimut, inclinaison, latitude):
    """
    Vérifie la cohérence de l'orientation des panneaux.
    
    Args:
        azimut: Orientation en degrés (0-360, 0=Nord, 90=Est, 180=Sud, 270=Ouest)
        inclinaison: Angle d'inclinaison en degrés (0-90)
        latitude: Latitude du site
    
    Warnings:
        UserWarning: Si orientation sub-optimale
    """
    # Dans l'hémisphère nord, optimum = plein sud (180°)
    # Dans l'hémisphère sud, optimum = plein nord (0°)
    
    if latitude > 0:  # Hémisphère nord
        optimal_azimut = 180
        
        # Écart par rapport au sud
        ecart = abs(azimut - optimal_azimut)
        if ecart > 180:
            ecart = 360 - ecart
        
        if ecart > 45:
            warnings.warn(
                f"Orientation sous-optimale pour hémisphère nord : {azimut}° "
                f"(optimum = 180° plein sud). Perte de production estimée : "
                f"{ecart * 0.1:.0f}%",
                UserWarning
            )
    
    # Inclinaison optimale ≈ latitude (règle approximative)
    inclinaison_optimale = abs(latitude)
    ecart_inclinaison = abs(inclinaison - inclinaison_optimale)
    
    if ecart_inclinaison > 20:
        warnings.warn(
            f"Inclinaison sous-optimale : {inclinaison}° "
            f"(optimum ≈ {inclinaison_optimale:.0f}° pour latitude {latitude}°). "
            f"Perte de production estimée : {ecart_inclinaison * 0.3:.0f}%",
            UserWarning
        )


def validate_shading_factor(facteur_ombrage):
    """
    Vérifie le facteur d'ombrage.
    
    Args:
        facteur_ombrage: Facteur d'ombrage (0-1, 1=aucun ombrage)
    
    Raises:
        ValidationError: Si valeur hors limites
    """
    if not 0 <= facteur_ombrage <= 1:
        raise ValidationError(
            f"Facteur d'ombrage invalide : {facteur_ombrage}. "
            f"Doit être entre 0 (ombrage total) et 1 (aucun ombrage)"
        )
    
    if facteur_ombrage < 0.7:
        warnings.warn(
            f"Ombrage important détecté : facteur {facteur_ombrage:.2f}. "
            f"Perte de production estimée : {(1-facteur_ombrage)*100:.0f}%. "
            f"Envisagez des optimiseurs de puissance ou micro-onduleurs.",
            UserWarning
        )


# ==============================================================================
# VALIDATORS CONFIGURATION BATTERIE
# ==============================================================================

def validate_battery_config(capacite_kwh, puissance_max_kw, efficacite, dod_max):
    """
    Vérifie la cohérence de la configuration d'une batterie.
    
    Args:
        capacite_kwh: Capacité en kWh
        puissance_max_kw: Puissance max charge/décharge en kW
        efficacite: Rendement round-trip (0-1)
        dod_max: Depth of Discharge max (0-1)
    
    Raises:
        ValidationError: Si configuration incohérente
    """
    # Vérifier C-rate (ratio puissance/capacité)
    # Généralement entre 0.5C et 1C pour batteries résidentielles
    c_rate = puissance_max_kw / capacite_kwh
    
    if c_rate < 0.3:
        warnings.warn(
            f"Puissance batterie faible : {puissance_max_kw}kW pour {capacite_kwh}kWh "
            f"(C-rate = {c_rate:.2f}). Charge/décharge lente.",
            UserWarning
        )
    
    if c_rate > 1.5:
        raise ValidationError(
            f"Puissance batterie excessive : {puissance_max_kw}kW pour {capacite_kwh}kWh "
            f"(C-rate = {c_rate:.2f}). Maximum recommandé : {capacite_kwh * 1.2:.1f}kW"
        )
    
    # Vérifier efficacité
    if not 0.80 <= efficacite <= 1.0:
        raise ValidationError(
            f"Efficacité batterie invalide : {efficacite:.2f}. "
            f"Doit être entre 0.80 (80%) et 1.0 (100%)"
        )
    
    if efficacite < 0.90:
        warnings.warn(
            f"Efficacité batterie faible : {efficacite*100:.0f}%. "
            f"Pertes énergétiques importantes ({(1-efficacite)*100:.0f}% par cycle).",
            UserWarning
        )
    
    # Vérifier DoD (Depth of Discharge)
    if not 0.5 <= dod_max <= 1.0:
        raise ValidationError(
            f"DoD max invalide : {dod_max:.2f}. "
            f"Doit être entre 0.5 (50%) et 1.0 (100%)"
        )
    
    if dod_max < 0.8:
        warnings.warn(
            f"DoD limité à {dod_max*100:.0f}%. "
            f"Capacité utilisable réduite à {capacite_kwh * dod_max:.1f}kWh.",
            UserWarning
        )


def validate_battery_sizing(capacite_kwh, production_annuelle_kwh, profil_type):
    """
    Vérifie le dimensionnement de la batterie par rapport à l'installation.
    
    Args:
        capacite_kwh: Capacité batterie
        production_annuelle_kwh: Production solaire annuelle
        profil_type: Type de profil d'occupation
    
    Warnings:
        UserWarning: Si dimensionnement sub-optimal
    """
    production_jour_moy = production_annuelle_kwh / 365
    ratio = capacite_kwh / production_jour_moy
    
    # Règles empiriques selon profil
    ratios_optimaux = {
        'actif_absent': (0.30, 0.45),   # 30-45% production journalière
        'teletravail': (0.40, 0.55),     # 40-55%
        'retraite': (0.40, 0.55),        # 40-55%
        'famille': (0.35, 0.50)          # 35-50%
    }
    
    ratio_min, ratio_max = ratios_optimaux.get(profil_type, (0.35, 0.50))
    
    if ratio < ratio_min:
        warnings.warn(
            f"Batterie sous-dimensionnée : {capacite_kwh}kWh pour production "
            f"journalière de {production_jour_moy:.1f}kWh (ratio {ratio:.2f}). "
            f"Recommandé pour profil '{profil_type}' : "
            f"{production_jour_moy * ratio_min:.1f}-{production_jour_moy * ratio_max:.1f}kWh",
            UserWarning
        )
    
    if ratio > ratio_max * 1.5:
        warnings.warn(
            f"Batterie surdimensionnée : {capacite_kwh}kWh pour production "
            f"journalière de {production_jour_moy:.1f}kWh (ratio {ratio:.2f}). "
            f"Coût/bénéfice défavorable. Considérez {production_jour_moy * ratio_max:.1f}kWh max.",
            UserWarning
        )


# ==============================================================================
# VALIDATORS GÉOGRAPHIQUES
# ==============================================================================

def validate_gps_coordinates(latitude, longitude):
    """
    Valide les coordonnées GPS.
    
    Args:
        latitude: Latitude (-90 à 90)
        longitude: Longitude (-180 à 180)
    
    Raises:
        ValidationError: Si coordonnées invalides
    """
    if not -90 <= latitude <= 90:
        raise ValidationError(
            f"Latitude invalide : {latitude}. Doit être entre -90 et 90"
        )
    
    if not -180 <= longitude <= 180:
        raise ValidationError(
            f"Longitude invalide : {longitude}. Doit être entre -180 et 180"
        )


def validate_france_coordinates(latitude, longitude):
    """
    Vérifie si les coordonnées sont en France métropolitaine.
    
    Args:
        latitude: Latitude
        longitude: Longitude
    
    Returns:
        bool: True si en France métropolitaine
    
    Warnings:
        UserWarning: Si hors France
    """
    # France métropolitaine approximative
    # Latitude : 41°N (Corse) à 51°N (Nord)
    # Longitude : -5°W (Bretagne) à 10°E (Alsace)
    
    in_france = (41 <= latitude <= 51) and (-5 <= longitude <= 10)
    
    if not in_france:
        warnings.warn(
            f"Coordonnées hors France métropolitaine : ({latitude}, {longitude}). "
            f"Les données PVGIS restent valides mais les tarifs et aides peuvent différer.",
            UserWarning
        )
    
    return in_france


# ==============================================================================
# VALIDATORS CONSOMMATION
# ==============================================================================

def validate_consumption_coherence(consommation_annuelle_kwh, surface_habitable, nb_personnes):
    """
    Vérifie la cohérence de la consommation annuelle.
    
    Args:
        consommation_annuelle_kwh: Consommation annuelle
        surface_habitable: Surface en m²
        nb_personnes: Nombre de personnes
    
    Warnings:
        UserWarning: Si consommation anormale
    """
    # Consommation moyenne par personne : 2500-3500 kWh/an
    conso_par_personne = consommation_annuelle_kwh / nb_personnes
    
    if conso_par_personne < 1500:
        warnings.warn(
            f"Consommation très faible : {conso_par_personne:.0f} kWh/personne/an. "
            f"Vérifiez les données.",
            UserWarning
        )
    
    if conso_par_personne > 6000:
        warnings.warn(
            f"Consommation très élevée : {conso_par_personne:.0f} kWh/personne/an. "
            f"Chauffage électrique ou équipements énergivores ?",
            UserWarning
        )
    
    # Consommation par m² : 50-150 kWh/m²/an typique
    conso_par_m2 = consommation_annuelle_kwh / surface_habitable
    
    if conso_par_m2 < 30:
        warnings.warn(
            f"Consommation très faible : {conso_par_m2:.0f} kWh/m²/an. "
            f"Logement peu utilisé ou très économe ?",
            UserWarning
        )
    
    if conso_par_m2 > 200:
        warnings.warn(
            f"Consommation très élevée : {conso_par_m2:.0f} kWh/m²/an. "
            f"Isolation à améliorer ? DPE probablement F ou G.",
            UserWarning
        )


# ==============================================================================
# VALIDATORS TECHNIQUES
# ==============================================================================

def validate_performance_ratio(pr):
    """
    Valide le Performance Ratio (PR).
    
    Args:
        pr: Performance Ratio (0-1)
    
    Raises:
        ValidationError: Si PR invalide
    """
    if not 0.5 <= pr <= 1.0:
        raise ValidationError(
            f"Performance Ratio invalide : {pr}. Doit être entre 0.5 et 1.0"
        )
    
    if pr < 0.70:
        warnings.warn(
            f"Performance Ratio faible : {pr*100:.0f}%. "
            f"Pertes système importantes (ombrage, salissure, vieillissement).",
            UserWarning
        )
    
    if pr > 0.90:
        warnings.warn(
            f"Performance Ratio très élevé : {pr*100:.0f}%. "
            f"Vérifiez les paramètres (peu réaliste en conditions réelles).",
            UserWarning
        )


def validate_system_losses(losses_pct):
    """
    Valide les pertes système.
    
    Args:
        losses_pct: Pertes en % (0-100)
    
    Raises:
        ValidationError: Si pertes invalides
    """
    if not 0 <= losses_pct <= 50:
        raise ValidationError(
            f"Pertes système invalides : {losses_pct}%. Doit être entre 0 et 50%"
        )
    
    if losses_pct < 10:
        warnings.warn(
            f"Pertes système très faibles : {losses_pct}%. "
            f"Typiquement 14-20% (câblage, onduleur, salissure, température).",
            UserWarning
        )
    
    if losses_pct > 30:
        warnings.warn(
            f"Pertes système importantes : {losses_pct}%. "
            f"Installation sub-optimale ou vieillissement avancé.",
            UserWarning
        )
