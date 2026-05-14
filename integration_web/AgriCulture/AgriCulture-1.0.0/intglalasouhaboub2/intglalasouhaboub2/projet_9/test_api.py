"""
Script test pour l'API PlantAI
"""
import requests
import json
from pathlib import Path

API_URL = "http://localhost:5000"
TEST_FILE = Path(__file__).parent / "test" / "mais.fna"

def test_predict():
    """Test l'endpoint /predict"""
    print("🔍 Test endpoint /predict...")
    print(f"📁 Fichier test : {TEST_FILE}")

    if not TEST_FILE.exists():
        print(f"❌ Fichier non trouvé : {TEST_FILE}")
        return

    with open(TEST_FILE, 'rb') as f:
        files = {'file': f}
        response = requests.post(f"{API_URL}/predict", files=files)

    if response.status_code == 200:
        result = response.json()
        print("✅ Succès!")
        print("\n📊 Résultat:")
        print(json.dumps(result, indent=2, ensure_ascii=False))

        # Sauvegarder résultat
        with open(Path(__file__).parent / "output" / "result.json", 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print("\n💾 Résultat sauvegardé : output/result.json")
    else:
        print(f"❌ Erreur {response.status_code}: {response.text}")

def test_health():
    """Test health check"""
    print("🏥 Test health check...")
    response = requests.get(f"{API_URL}/health")
    if response.status_code == 200:
        print("✅ API OK:", response.json())
    else:
        print("❌ API non accessible")

if __name__ == "__main__":
    try:
        test_health()
        test_predict()
    except Exception as e:
        print(f"❌ Erreur : {e}")
        print("⚠️  Assure-toi que l'API est lancée : python app.py")
