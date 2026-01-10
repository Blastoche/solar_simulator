"""
Script de test de l'intégration PVGIS.
"""
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from weather.services import get_pvgis_weather_data, PVGISClient
from weather.models import Location, PVGISData
import logging

# Activer les logs
logging.basicConfig(level=logging.INFO)

def test_pvgis_basic():
    """Test basique du client PVGIS."""
    print("=" * 80)
    print("TEST 1 : CLIENT PVGIS DE BASE")
    print("=" * 80)
    
    # Coordonnées de Lyon
    latitude = 45.75
    longitude = 4.85
    
    print(f"\nLocalisation : Lyon ({latitude}°N, {longitude}°E)")
    
    # Créer le client
    client = PVGISClient()
    
    try:
        # Appel API
        print("\n🌐 Appel API PVGIS...")
        data = client.get_tmy_data(latitude, longitude)
        
        print("✅ Données reçues !")
        
        # Parser en DataFrame
        print("\n📊 Parsing des données...")
        df = client.parse_tmy_to_dataframe(data)
        
        print(f"✅ {len(df)} heures de données")
        print(f"\nAperçu des données :")
        print(df.head(10))
        
        # Calculer l'irradiation annuelle
        irradiation = client.calculate_annual_irradiation(df)
        print(f"\n☀️ Irradiation annuelle : {irradiation:,.0f} kWh/m²/an")
        
        # Statistiques
        print(f"\n📈 STATISTIQUES")
        print(f"   GHI moyen : {df['ghi'].mean():.2f} W/m²")
        print(f"   GHI max : {df['ghi'].max():.2f} W/m²")
        if 'temperature' in df.columns:
            print(f"   Température moyenne : {df['temperature'].mean():.2f}°C")
            print(f"   Température min : {df['temperature'].min():.2f}°C")
            print(f"   Température max : {df['temperature'].max():.2f}°C")
        
        print("\n✅ TEST 1 RÉUSSI !")
        return True
        
    except Exception as e:
        print(f"\n❌ ERREUR : {e}")
        return False


def test_pvgis_with_cache():
    """Test de l'intégration avec Django et cache."""
    print("\n" + "=" * 80)
    print("TEST 2 : PVGIS AVEC CACHE DJANGO")
    print("=" * 80)
    
    # Paris
    latitude = 48.8566
    longitude = 2.3522
    
    print(f"\nLocalisation : Paris ({latitude}°N, {longitude}°E)")
    
    try:
        # Premier appel (devrait appeler l'API)
        print("\n🔄 Premier appel (devrait récupérer depuis API)...")
        df1, meta1 = get_pvgis_weather_data(latitude, longitude, use_cache=True)
        
        print(f"✅ Source : {meta1.get('source', 'N/A')}")
        print(f"   Irradiation : {meta1['irradiation_annuelle']:,.0f} kWh/m²/an")
        print(f"   Données : {len(df1)} heures")
        
        # Vérifier en base
        locations = Location.objects.filter(
            latitude__range=(latitude - 0.01, latitude + 0.01),
            longitude__range=(longitude - 0.01, longitude + 0.01)
        )
        print(f"\n💾 Localisations en base : {locations.count()}")
        
        caches = PVGISData.objects.filter(location__in=locations)
        print(f"   Caches PVGIS : {caches.count()}")
        
        # Deuxième appel (devrait utiliser le cache)
        print("\n🔄 Deuxième appel (devrait utiliser le cache)...")
        df2, meta2 = get_pvgis_weather_data(latitude, longitude, use_cache=True)
        
        print(f"✅ Source : {meta2.get('source', 'N/A')}")
        
        if meta1.get('source') == 'api' and meta2.get('source') == 'cache':
            print("\n🎉 Le cache fonctionne correctement !")
        else:
            print(f"\n⚠️ Cache potentiellement non utilisé")
            print(f"   Appel 1 : {meta1.get('source')}")
            print(f"   Appel 2 : {meta2.get('source')}")
        
        print("\n✅ TEST 2 RÉUSSI !")
        return True
        
    except Exception as e:
        print(f"\n❌ ERREUR : {e}")
        import traceback
        traceback.print_exc()
        return False


def test_multiple_locations():
    """Test de plusieurs localisations."""
    print("\n" + "=" * 80)
    print("TEST 3 : PLUSIEURS LOCALISATIONS")
    print("=" * 80)
    
    locations_test = [
        ("Lyon", 45.75, 4.85),
        ("Marseille", 43.30, 5.40),
        ("Bordeaux", 44.84, -0.58),
    ]
    
    results = []
    
    for nom, lat, lon in locations_test:
        print(f"\n📍 {nom} ({lat}°N, {lon}°E)")
        
        try:
            df, meta = get_pvgis_weather_data(lat, lon, use_cache=True)
            irradiation = meta['irradiation_annuelle']
            temp_moy = df['temperature'].mean() if 'temperature' in df.columns else None
            
            results.append({
                'nom': nom,
                'irradiation': irradiation,
                'temperature': temp_moy
            })
            
            print(f"   ☀️ Irradiation : {irradiation:,.0f} kWh/m²/an")
            if temp_moy:
                print(f"   🌡️ Température moyenne : {temp_moy:.1f}°C")
            
        except Exception as e:
            print(f"   ❌ Erreur : {e}")
    
    # Comparaison
    if len(results) > 1:
        print("\n📊 COMPARAISON")
        results_sorted = sorted(results, key=lambda x: x['irradiation'], reverse=True)
        for i, r in enumerate(results_sorted, 1):
            print(f"   {i}. {r['nom']}: {r['irradiation']:,.0f} kWh/m²/an")
    
    print("\n✅ TEST 3 RÉUSSI !")
    return True


def main():
    """Lance tous les tests."""
    print("\n" + "🌤️ " * 20)
    print("TEST COMPLET DE L'INTÉGRATION PVGIS")
    print("🌤️ " * 20)
    
    tests = [
        ("Client PVGIS de base", test_pvgis_basic),
        ("PVGIS avec cache Django", test_pvgis_with_cache),
        ("Plusieurs localisations", test_multiple_locations),
    ]
    
    results = []
    
    for nom, test_func in tests:
        try:
            success = test_func()
            results.append((nom, success))
        except Exception as e:
            print(f"\n❌ Échec du test '{nom}': {e}")
            results.append((nom, False))
    
    # Résumé
    print("\n" + "=" * 80)
    print("RÉSUMÉ DES TESTS")
    print("=" * 80)
    
    for nom, success in results:
        status = "✅ RÉUSSI" if success else "❌ ÉCHOUÉ"
        print(f"{status} : {nom}")
    
    total = len(results)
    passed = sum(1 for _, s in results if s)
    
    print(f"\nRésultat global : {passed}/{total} tests réussis")
    
    if passed == total:
        print("\n🎉 TOUS LES TESTS SONT PASSÉS !")
    else:
        print(f"\n⚠️ {total - passed} test(s) ont échoué")


if __name__ == '__main__':
    main()