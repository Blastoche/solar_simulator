"""
Script de découverte de l'API PVGIS 5.3
"""
import requests
import json

def test_pvgis_v53_direct():
    """Test direct pour découvrir les paramètres acceptés par PVGIS 5.3"""
    print("=" * 80)
    print("DÉCOUVERTE API PVGIS 5.3")
    print("=" * 80)
    
    base_urls = [
        "https://re.jrc.ec.europa.eu/api/v5_3/tmy",
        "https://re.jrc.ec.europa.eu/api/v5_2/tmy",
        "https://re.jrc.ec.europa.eu/api/tmy",  # Sans version
    ]
    
    latitude = 45.75
    longitude = 4.85
    
    for base_url in base_urls:
        print(f"\n{'='*80}")
        print(f"Test avec: {base_url}")
        print('='*80)
        
        # Test 1: Paramètres minimaux
        print("\n[Test 1] Paramètres minimaux:")
        params = {
            'lat': latitude,
            'lon': longitude,
            'outputformat': 'json',
        }
        print(f"Paramètres: {params}")
        
        try:
            response = requests.get(base_url, params=params, timeout=30)
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print("✅ SUCCÈS !")
                print(f"Clés de réponse: {list(data.keys())}")
                
                if 'outputs' in data:
                    print(f"Clés outputs: {list(data['outputs'].keys())}")
                    
                    if 'tmy_hourly' in data['outputs']:
                        hourly = data['outputs']['tmy_hourly']
                        print(f"Nombre d'heures: {len(hourly)}")
                        print(f"Colonnes: {list(hourly[0].keys())}")
                        print(f"\nPremier enregistrement:")
                        print(json.dumps(hourly[0], indent=2))
                
                # Sauvegarder la réponse complète
                with open(f'pvgis_response_{base_url.split("/")[-2]}.json', 'w') as f:
                    json.dump(data, f, indent=2)
                print(f"\n💾 Réponse sauvegardée dans pvgis_response_*.json")
                
                return base_url, data
            else:
                print(f"❌ Erreur {response.status_code}")
                print(f"Message: {response.text[:200]}")
                
        except Exception as e:
            print(f"❌ Exception: {e}")
        
        # Test 2: Avec usehorizon
        print("\n[Test 2] Avec usehorizon:")
        params_with_horizon = {
            'lat': latitude,
            'lon': longitude,
            'outputformat': 'json',
            'usehorizon': 1,
        }
        print(f"Paramètres: {params_with_horizon}")
        
        try:
            response = requests.get(base_url, params=params_with_horizon, timeout=30)
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                print("✅ SUCCÈS avec usehorizon!")
        except Exception as e:
            print(f"❌ Exception: {e}")
    
    return None, None


def analyze_response_structure(data):
    """Analyse la structure de la réponse PVGIS"""
    print("\n" + "=" * 80)
    print("ANALYSE DE LA STRUCTURE")
    print("=" * 80)
    
    def print_structure(obj, indent=0):
        """Affiche la structure récursive"""
        prefix = "  " * indent
        
        if isinstance(obj, dict):
            for key, value in obj.items():
                if isinstance(value, (dict, list)):
                    print(f"{prefix}{key}: {type(value).__name__}")
                    print_structure(value, indent + 1)
                else:
                    print(f"{prefix}{key}: {type(value).__name__} = {value}")
        elif isinstance(obj, list):
            if obj:
                print(f"{prefix}[0]: {type(obj[0]).__name__}")
                if isinstance(obj[0], dict):
                    print_structure(obj[0], indent + 1)
    
    print_structure(data)


if __name__ == '__main__':
    print("\n🔍 DÉCOUVERTE DE L'API PVGIS 5.3 🔍\n")
    
    url, data = test_pvgis_v53_direct()
    
    if data:
        print("\n" + "🎉" * 20)
        print(f"\n✅ L'URL qui fonctionne : {url}")
        print("\n" + "🎉" * 20)
        
        analyze_response_structure(data)
    else:
        print("\n❌ Aucune URL n'a fonctionné")
        print("\nVérifiez:")
        print("  1. Votre connexion Internet")
        print("  2. Que PVGIS est accessible")
        print("  3. Les coordonnées (45.75, 4.85)")