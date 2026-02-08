        four=Appareil(
            nom="Four Ã‰lectrique",
            puissance_moyenne=2000,
            frequence_journaliere=0.5
        ),
        lave_linge=Appareil(
            nom="Lave-linge",
            puissance_moyenne=2000,
            frequence_journaliere=0.5,
            classe_energetique='A+++'
        ),
        lave_vaisselle=Appareil(
            nom="Lave-vaisselle",
            puissance_moyenne=1800,
            frequence_journaliere=0.4,
            classe_energetique='A++'
        ),
        chauffage=SystemeChauffage(
            type_chauffage="electrique",
            puissance_nominale=9.0
        ),
        ecs=SystemeECS(
            type_ecs="electrique",
            volume_stockage=200
        )
    )


def main():
    """
    Exemple d'utilisation du module.
    """
    print("=" * 80)
    print("PROFIL DE CONSOMMATION - EXEMPLE")
    print("=" * 80)
    
    # CrÃ©er un profil standard
    profil = creer_profil_standard()
    
    # Calculer la consommation annuelle
    consommation_annuelle = profil.calcul_consommation_base()
    print(f"\nConsommation Ã©lectrique annuelle estimÃ©e : {consommation_annuelle:,.0f} kWh")
    
    # RÃ©partition par poste
    print("\nRÃ©partition de la consommation :")
    repartition = profil.repartition_consommation()
    for poste, conso in repartition.items():
        if conso > 0:
            pourcentage = (conso / consommation_annuelle) * 100
            print(f"  {poste.capitalize():<20}: {conso:>8,.0f} kWh ({pourcentage:>5.1f}%)")
    
    # GÃ©nÃ©rer profil horaire
    print("\nGÃ©nÃ©ration du profil horaire (8760h)...")
    profil_horaire = profil.generer_profil_horaire()
    print(f"  PremiÃ¨res heures :")
    print(profil_horaire.head(10))
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
