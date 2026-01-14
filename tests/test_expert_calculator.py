"""
Script de test du calculateur expert.
Lance : python manage.py shell < test_expert_calculator.py
"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from solar_calc.services.expert_consumption_calculator import ExpertConsumptionCalculator

print("=" * 80)
print("🔬 TEST CALCULATEUR MODE EXPERT")
print("=" * 80)

# Données de test complètes
data_test = {
    # Logement
    'surface': 100,
    'nb_personnes': 2,
    'dpe': 'D',
    'annee_construction': 2005,
    'latitude': 48.8566,
    'longitude': 2.3522,
    
    # Chauffage
    'type_chauffage': 'electrique',
    'temperature_consigne': 19,
    'type_vmc': 'aucune',
    
    # ECS
    'type_ecs': 'ballon_electrique',
    'capacite_ecs': 200,
    
    # Cuisson
    'type_cuisson': 'induction',
    
    # === MODE EXPERT ===
    
    # Réfrigération
    'frigos': [
        {
            'type': 'combine',
            'nombre': 1,
            'classe': 'A++',
        }
    ],
    'congelateurs': [
        {
            'type': 'coffre',
            'nombre': 1,
            'classe': 'A+',
        }
    ],
    
    # Lavage
    'lave_linge_actif': True,
    'lave_linge_classe': 'A++',
    'lave_linge_cycles': 4,
    
    'lave_vaisselle_actif': True,
    'lave_vaisselle_classe': 'A+++',
    'lave_vaisselle_cycles': 5,
    
    'seche_linge_actif': True,
    'seche_linge_type': 'pompe_chaleur_A++',
    'seche_linge_cycles': 3,
    
    # Four
    'type_four': 'four_electrique',
    'usage_four': 'occasionnel',
    
    # Audiovisuel
    'tvs': [
        {
            'taille': 'grand',  # 43-55"
            'techno': 'led',
            'heures_jour': 4,
        }
    ],
    'type_box': 'avec_decodeur',
    'box_eteinte_nuit': False,
    'nb_ordis_fixes': 0,
    'nb_ordis_portables': 2,
    'heures_ordi': 6,
    'console_actif': True,
    'type_console': 'actuelle',
    'heures_console': 2,
    
    # Éclairage
    'nb_led': 30,
    'nb_halogene': 5,
    'heures_eclairage': 5,
    
    # Piscine
    'piscine_active': True,
    'piscine_puissance_pompe': 1000,
    'piscine_heures_filtration': 8,
    'piscine_mois_debut': 5,
    'piscine_mois_fin': 9,
    'piscine_chauffage_actif': False,
    'piscine_robot_actif': True,
    
    # Spa
    'spa_actif': False,
    
    # Véhicule électrique
    'vehicules': [
        {
            'conso_100km': 18,
            'km_an': 15000,
            'type_recharge': 'wallbox_7',
            'pct_recharge_domicile': 100,
        }
    ],
    
    # Profil
    'profil_usage': 'actif_absent',
    
    # Contrat
    'puissance_compteur': '6kVA',
    'type_contrat': 'hphc',
}

print("\n📊 DONNÉES DE TEST")
print(f"  Logement : {data_test['surface']}m², {data_test['nb_personnes']} pers, DPE {data_test['dpe']}")
print(f"  Chauffage : {data_test['type_chauffage']}")
print(f"  Frigo : {data_test['frigos'][0]['type']} {data_test['frigos'][0]['classe']}")
print(f"  Congélateur : {data_test['congelateurs'][0]['type']} {data_test['congelateurs'][0]['classe']}")
print(f"  Lave-linge : {data_test['lave_linge_classe']} ({data_test['lave_linge_cycles']} cycles/sem)")
print(f"  TV : {data_test['tvs'][0]['taille']} ({data_test['tvs'][0]['heures_jour']}h/j)")
print(f"  Éclairage : {data_test['nb_led']} LED + {data_test['nb_halogene']} halogène")
print(f"  Piscine : Oui (pompe {data_test['piscine_puissance_pompe']}W, {data_test['piscine_heures_filtration']}h/j)")
print(f"  VE : Oui ({data_test['vehicules'][0]['km_an']} km/an, {data_test['vehicules'][0]['conso_100km']} kWh/100km)")

# Créer le calculateur
print("\n🔧 CRÉATION CALCULATEUR...")
calculator = ExpertConsumptionCalculator(data_test)

# Lancer le calcul
print("\n⚙️ CALCUL EN COURS...")
result = calculator.calculate_total_expert()

# Afficher les résultats
print("\n" + "=" * 80)
print("📊 RÉSULTATS")
print("=" * 80)

print(f"\n🔋 CONSOMMATION TOTALE : {result['total_annuel']:,.0f} kWh/an")
print(f"📈 Moyenne attendue : {result['moyenne_attendue']:,.0f} kWh/an")
print(f"📊 Écart : {result['ecart_pct']:+.1f}%")

print("\n🔍 RÉPARTITION PAR POSTE :")
for poste, data in result['repartition'].items():
    print(f"  {poste:20s} : {data['kwh']:>6.0f} kWh/an ({data['pourcentage']:>2d}%)")

print(f"\n📱 NOMBRE D'APPAREILS DÉTAILLÉS : {len(result['appareils'])}")

print("\n🔌 DÉTAIL DES APPAREILS :")
for i, app in enumerate(result['appareils'], 1):
    print(f"  {i:2d}. {app['nom_affichage']:40s} : {app['consommation_annuelle']:>6.0f} kWh/an")

# Calcul optimisation HP/HC
print("\n💰 OPTIMISATION HP/HC")
financier = calculator.calculate_financial_details(result['total_annuel'])
optim = calculator.calculate_optimisation_hphc(result['total_annuel'])

print(f"  Profil : {optim['profil']}")
print(f"  % HC actuel : {optim['pct_hc_actuel']}%")
print(f"  % HC optimal : {optim['pct_hc_optimal']}%")
print(f"  Économie potentielle : {optim['economie_annuelle']:.2f}€/an")

# Projection 10 ans
print("\n📈 PROJECTION 10 ANS")
projection = calculator.calculate_projection_10ans(result['total_annuel'], financier['cout_total'])
print(f"  {'Année':<8} {'Conso (kWh)':<15} {'Prix (€/kWh)':<15} {'Coût (€)':<15}")
print(f"  {'-'*8} {'-'*15} {'-'*15} {'-'*15}")
for p in projection[:5]:  # Afficher 5 premières années
    print(f"  {p['annee']:<8} {p['consommation_kwh']:<15,.0f} {p['prix_moyen_kwh']:<15.4f} {p['cout_total']:<15,.2f}")
print(f"  ...")
p_last = projection[-1]
print(f"  {p_last['annee']:<8} {p_last['consommation_kwh']:<15,.0f} {p_last['prix_moyen_kwh']:<15.4f} {p_last['cout_total']:<15,.2f}")

print("\n" + "=" * 80)
print("✅ TEST TERMINÉ AVEC SUCCÈS !")
print("=" * 80)
print("\n💡 PROCHAINES ÉTAPES :")
print("  1. Vérifiez que les résultats sont cohérents")
print("  2. Testez avec d'autres configurations")
print("  3. Si tout fonctionne, on peut continuer avec le frontend !")
print("\n")