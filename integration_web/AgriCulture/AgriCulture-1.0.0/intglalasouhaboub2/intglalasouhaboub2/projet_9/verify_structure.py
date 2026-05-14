import os
import json
from pathlib import Path

API_DIR = Path(r'c:/Users/LENOVO/Downloads/PlantAI_API')

print("="*70)
print("✅ VÉRIFICATION DOSSIER PlantAI_API")
print("="*70)

# Structure attendue
expected = {
    'files': [
        'app.py',
        'requirements.txt',
        'README.md',
        'MODELS_SETUP.md',
        'test_api.py',
        'save_models.py'
    ],
    'folders': [
        'models',
        'utils',
        'test',
        'output'
    ],
    'utils_files': [
        'preprocess.py',
        'predict.py',
        'ethics_report.py',
        'xai_explainer.py'
    ],
    'test_files': [
        'mais.fna'
    ],
    'output_files': [
        'exemple_output.json'
    ]
}

# Vérifier fichiers racine
print("\n📁 FICHIERS RACINE:")
for f in expected['files']:
    path = API_DIR / f
    status = "✅" if path.exists() else "❌"
    size = f" ({path.stat().st_size / 1024:.1f} KB)" if path.exists() else ""
    print(f"  {status} {f}{size}")

# Vérifier dossiers
print("\n📁 DOSSIERS:")
for folder in expected['folders']:
    path = API_DIR / folder
    status = "✅" if path.exists() else "❌"
    print(f"  {status} {folder}/")

# Vérifier fichiers utils
print("\n📁 FICHIERS UTILS/:")
for f in expected['utils_files']:
    path = API_DIR / 'utils' / f
    status = "✅" if path.exists() else "❌"
    size = f" ({path.stat().st_size / 1024:.1f} KB)" if path.exists() else ""
    print(f"  {status} {f}{size}")

# Vérifier fichiers test
print("\n📁 FICHIERS TEST/:")
for f in expected['test_files']:
    path = API_DIR / 'test' / f
    status = "✅" if path.exists() else "❌"
    size = f" ({path.stat().st_size / 1024:.1f} KB)" if path.exists() else ""
    print(f"  {status} {f}{size}")

# Vérifier fichiers output
print("\n📁 FICHIERS OUTPUT/:")
for f in expected['output_files']:
    path = API_DIR / 'output' / f
    status = "✅" if path.exists() else "❌"
    size = f" ({path.stat().st_size / 1024:.1f} KB)" if path.exists() else ""
    print(f"  {status} {f}{size}")

# Vérifier models (important)
print("\n📁 FICHIERS MODELS/:")
models_dir = API_DIR / 'models'
if models_dir.exists():
    files = list(models_dir.glob('*'))
    if files:
        for f in files:
            print(f"  ✅ {f.name} ({f.stat().st_size / 1024 / 1024:.1f} MB)")
    else:
        print("  ⚠️  Dossier vide (À remplir avec mlp_model.pth et rf_model.pkl)")

# Résumé
print("\n" + "="*70)
all_ok = True
for f in expected['files']:
    if not (API_DIR / f).exists():
        all_ok = False
        break

if all_ok and (API_DIR / 'models').exists():
    print("✅ STRUCTURE COMPLÈTE ET PARFAITE")
    print("\n📋 Prochaines étapes:")
    print("  1. Ajouter mlp_model.pth dans models/")
    print("  2. Ajouter rf_model.pkl dans models/")
    print("  3. Envoyer le dossier au groupe")
else:
    print("⚠️  Structure correcte, models/ à remplir")

print("="*70)
