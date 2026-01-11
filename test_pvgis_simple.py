"""
Script de test PVGIS simplifié pour déboguer.
"""
import requests

def test_pvgis_direct():
    """Test direct de l'API PVGIS sans Django."""
    print("=" * 80)
    print("TEST DIRECT API PVGIS")
    print("=" * 80)
    
    # Coordonnées de Lyon
    latitude = 45.75
    longitude = 4.85
    
    print(f"\nLocalisation : Lyon ({latitude}°N, {longitude}°E)")
    
    # URL correcte de l'API PVGIS
    url = "https://re.jrc.ec.europa.eu/api/v5_2/tmy"
    
    # Paramètres minimaux
    params = {
        'lat': latitude,
        'lon': longitude,
        'outputformat': 'json',
    }
    
    print(f"\n🌐 URL: {url}")
    print(f"📋 Paramètres: {params}")
    print(f"\n🚀 Envoi de la requête...")
    
    try:
        response = requests.get(url, params=params, timeout=30)
        
        print(f"✅ Status code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            # Afficher les clés principales
            print(f"\n📦 Clés de la réponse:")
            for key in data.keys():
                print(f"   - {key}")
            
            # Vérifier les données horaires
            if 'outputs' in data and 'tmy_hourly' in data['outputs']:
                hourly = data['outputs']['tmy_hourly']
                print(f"\n✅ Nombre d'heures: {len(hourly)}")
                print(f"\n📊 Premier enregistrement:")
                print(hourly[0])
                
                # Vérifier les colonnes disponibles
                print(f"\n📋 Colonnes disponibles:")
                for col in hourly[0].keys():
                    print(f"   - {col}")
                
                print("\n🎉 API PVGIS FONCTIONNE !")
                return True
            else:
                print("\n❌ Pas de données horaires dans la réponse")
                print(f"Structure: {data}")
                return False
        else:
            print(f"❌ Erreur HTTP {response.status_code}")
            print(f"Réponse: {response.text[:500]}")
            return False
            
    except requests.exceptions.Timeout:
        print("❌ Timeout après 30 secondes")
        return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Erreur de requête: {e}")
        return False
    except Exception as e:
        print(f"❌ Erreur inattendue: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_pvgis_with_django():
    """Test avec Django une fois que le test direct fonctionne."""
    print("\n" + "=" * 80)
    print("TEST AVEC DJANGO")
    print("=" * 80)
    
    import os
    import django
    
    # Setup Django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    django.setup()
    
    from weather.services.pvgis import PVGISClient
    
    latitude = 45.75
    longitude = 4.85
    
    print(f"\nLocalisation : Lyon ({latitude}°N, {longitude}°E)")
    
    try:
        client = PVGISClient()
        print("\n🚀 Appel via PVGISClient...")
        
        data = client.get_tmy_data(latitude, longitude)
        print("✅ Données reçues !")
        
        df = client.parse_tmy_to_dataframe(data)
        print(f"✅ DataFrame créé: {len(df)} heures")
        
        irradiation = client.calculate_annual_irradiation(df)
        print(f"☀️ Irradiation annuelle: {irradiation:,.0f} kWh/m²/an")
        
        print("\n🎉 INTÉGRATION DJANGO FONCTIONNE !")
        return True
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    print("\n🌤️  TEST PVGIS SIMPLIFIÉ 🌤️\n")
    
    # Test 1: API directe
    success1 = test_pvgis_direct()
    
    if success1:
        # Test 2: Avec Django
        success2 = test_pvgis_with_django()
        
        if success2:
            print("\n" + "=" * 80)
            print("✅ TOUS LES TESTS SONT PASSÉS !")
            print("=" * 80)
        else:
            print("\n⚠️ L'API fonctionne mais l'intégration Django a échoué")
    else:
        print("\n❌ L'API PVGIS ne répond pas correctement")
        print("\nVérifiez:")
        print("  1. Votre connexion Internet")
        print("  2. Que l'API PVGIS est accessible")
        print("  3. Les coordonnées sont valides")