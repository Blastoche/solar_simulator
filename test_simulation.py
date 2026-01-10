"""
Script de test de simulation complète.
"""
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from solar_calc.models import SolarInstallationModel, ConsumptionProfileModel, SimulationModel  # modèles ORM
from solar_calc.services.simulation import run_simulation_from_django_objects
from django.contrib.auth.models import User

def main():
    print("=" * 80)
    print("TEST DE SIMULATION COMPLÈTE")
    print("=" * 80)
    
    # Récupérer les objets créés dans l'admin
    installation = SolarInstallationModel.objects.first()
    profil = ConsumptionProfileModel.objects.first()
    user = User.objects.first()
    
    if not installation or not profil:
        print("❌ Erreur : Créez d'abord une installation et un profil dans l'admin !")
        return
    
    print(f"\n📊 Installation : {installation.nom}")
    print(f"   Puissance : {installation.puissance_crete_kwc:.2f} kWc")
    print(f"   Localisation : {installation.latitude}°N, {installation.longitude}°E")
    
    print(f"\n🏠 Profil : {profil.nom}")
    print(f"   Surface : {profil.surface_habitable} m²")
    print(f"   Personnes : {profil.nb_personnes}")
    print(f"   DPE : {profil.dpe}")
    
    # Lancer la simulation
    print("\n🚀 Lancement de la simulation...")
    resultats = run_simulation_from_django_objects(
        installation,
        profil,
        irradiation_annuelle=1400  # Lyon
    )
    
    # Afficher les résultats
    print("\n" + "=" * 80)
    print("RÉSULTATS DE LA SIMULATION")
    print("=" * 80)
    
    print(f"\n📈 PRODUCTION")
    print(f"   Production annuelle : {resultats['production_annuelle_kwh']:,.0f} kWh")
    print(f"   Production spécifique : {resultats['production_specifique_kwh_kwc']:.0f} kWh/kWc/an")
    
    print(f"\n🔌 CONSOMMATION")
    print(f"   Consommation annuelle : {resultats['consommation_annuelle_kwh']:,.0f} kWh")
    
    print(f"\n🔄 AUTOCONSOMMATION")
    print(f"   Autoconsommation : {resultats['autoconsommation_kwh']:,.0f} kWh")
    print(f"   Injection réseau : {resultats['injection_reseau_kwh']:,.0f} kWh")
    print(f"   Achat réseau : {resultats['achat_reseau_kwh']:,.0f} kWh")
    
    print(f"\n📊 TAUX")
    print(f"   Taux d'autoconsommation : {resultats['taux_autoconsommation_pct']:.1f}%")
    print(f"   Taux d'autoproduction : {resultats['taux_autoproduction_pct']:.1f}%")
    
    # Économie estimée
    tarif_achat = 0.2276  # €/kWh
    tarif_vente = 0.13  # €/kWh
    economie = (
        resultats['autoconsommation_kwh'] * tarif_achat +
        resultats['injection_reseau_kwh'] * tarif_vente -
        0  # Pas de coût d'installation dans ce calcul simple
    )
    
    print(f"\n💰 ÉCONOMIES")
    print(f"   Économie annuelle estimée : {economie:,.2f} €/an")
    print(f"   Sur 25 ans : {economie * 25:,.2f} €")
    
    # Sauvegarder en base de données
    print("\n💾 Sauvegarde de la simulation...")
    simulation = SimulationModel.objects.create(
        user=user,
        installation=installation,
        profil_consommation=profil,
        production_annuelle_kwh=resultats['production_annuelle_kwh'],
        production_specifique_kwh_kwc=resultats['production_specifique_kwh_kwc'],
        consommation_annuelle_kwh=resultats['consommation_annuelle_kwh'],
        autoconsommation_kwh=resultats['autoconsommation_kwh'],
        injection_reseau_kwh=resultats['injection_reseau_kwh'],
        achat_reseau_kwh=resultats['achat_reseau_kwh'],
        taux_autoconsommation_pct=resultats['taux_autoconsommation_pct'],
        taux_autoproduction_pct=resultats['taux_autoproduction_pct'],
        status='completed'
    )
    
    print(f"✅ Simulation #{simulation.id} sauvegardée !")
    print(f"   Voir dans l'admin : http://localhost:8000/admin/solar_calc/simulation/")
    
    print("\n" + "=" * 80)
    print("✅ TEST RÉUSSI !")
    print("=" * 80)

if __name__ == '__main__':
    main()