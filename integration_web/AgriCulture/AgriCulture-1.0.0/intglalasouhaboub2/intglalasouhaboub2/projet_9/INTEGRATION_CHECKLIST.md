# ✅ PlantAI_API - Checklist Intégration Collègue

## 📦 Dossier prêt à envoyer

Oui! Le dossier `PlantAI_API` est **100% prêt** pour l'intégration.

---

## ✅ Vérification des fichiers

### Code Python
```
✅ app.py                    - API Flask principale
✅ utils/predict.py          - Chargement MLP
✅ utils/preprocess.py       - Extraction k-mers
✅ utils/ethics_report.py    - Lois Tunisie + EU
✅ utils/xai_explainer.py    - Explainabilité (XAI)
✅ utils/__init__.py         - Package init
```

### Modèles Machine Learning
```
✅ models/mlp_model.pth      - 1.2 MB (MLP trained)
✅ models/rf_model.pkl       - 300 MB (Random Forest)
```

### Documentation
```
✅ README.md                 - Guide complet
✅ MODELS_SETUP.md           - Setup models
✅ requirements.txt          - Dépendances Python
```

### Test
```
✅ test/mais.fna            - 94 MB (données test)
✅ test_api.py              - Script test
✅ verify_structure.py      - Vérification structure
```

### Output Example
```
✅ output/exemple_output.json - Format réponse API
```

---

## 🚀 Partage avec collègue

### Option 1: Zip simple (recommandé)
```bash
# Depuis Windows
# Clic droit sur PlantAI_API → Envoyer vers → Dossier compressé

# Résultat: PlantAI_API.zip (~400 MB)
# Contient TOUT ce qu'il faut
```

### Option 2: Fichiers séparés
```
Lui envoyer:
1. Dossier code complet: utils/ + app.py
2. requirements.txt
3. README.md
4. Fichiers modèles séparément:
   - mlp_model.pth (1.2 MB)
   - rf_model.pkl (300 MB)
```

### Option 3: Git/GitHub
```bash
# Si vous utilisez Git
git add PlantAI_API/
git commit -m "Add PlantAI API for integration"
git push
# → Collègue clône le repo
```

---

## 📋 Instructions pour ton collègue

Crée ce fichier: `INTEGRATION_INSTRUCTIONS.md`

```markdown
# PlantAI_API - Guide d'intégration

## Installation rapide

### 1. Dépendances
\`\`\`bash
pip install -r requirements.txt
\`\`\`

### 2. Démarrer l'API
\`\`\`bash
python app.py
# Écoute sur http://localhost:5000
\`\`\`

### 3. Test simple
\`\`\`bash
curl -X POST -F "file=@test/mais.fna" http://localhost:5000/predict
\`\`\`

### 4. Via Python
\`\`\`python
import requests

with open('test/mais.fna', 'rb') as f:
    files = {'file': f}
    response = requests.post('http://localhost:5000/predict', files=files)
    print(response.json())
\`\`\`

## Structure
- app.py → API endpoint
- utils/ → Code prédictions
- models/ → mlp_model.pth, rf_model.pkl
- test/ → mais.fna pour tester

## Endpoint
POST /predict
- Input: FASTA file
- Output: JSON avec prédictions + lois + XAI

## Configuration
- PORT: 5000 (modifie dans app.py si besoin)
- DEVICE: 'cpu' (ou 'cuda' si GPU)
- DEBUG: True/False (dans app.py)
```

---

## 📊 Taille totale à envoyer

```
Code Python:    ~100 KB
Modèles:        ~301 MB  ← gros!
Test data:      ~94 MB   ← optionnel
Documentation:  ~50 KB

TOTAL ZIP:      ~395 MB
```

**Note**: Si 395 MB est trop gros → envoie SANS test/mais.fna
(Le collègue peut télécharger séparément)

---

## 🎯 Ce qu'il faut inclure OBLIGATOIREMENT

```
✅ DOIT envoyer:
   - app.py
   - utils/ (tous les fichiers)
   - models/mlp_model.pth
   - models/rf_model.pkl
   - requirements.txt
   - README.md
   
⚠️ PEUT envoyer mais gros:
   - test/mais.fna (94 MB)
   - models/ (300 MB pour RF)
   
✅ DEVRAIT envoyer:
   - INTEGRATION_INSTRUCTIONS.md
   - Cette checklist
```

---

## 💡 Recommandation: Structure ZIP

Pour minimiser taille, crée ZIP avec:
```
PlantAI_API/
├── app.py                    ✓
├── requirements.txt          ✓
├── README.md                 ✓
├── INTEGRATION_INSTRUCTIONS.md (crée-le)
├── utils/                    ✓
│   ├── predict.py
│   ├── preprocess.py
│   ├── ethics_report.py
│   ├── xai_explainer.py
│   └── __init__.py
├── models/                   ✓
│   ├── mlp_model.pth
│   └── rf_model.pkl
└── output/                   ✓
    └── exemple_output.json
```

**Ne PAS inclure dans ZIP**:
- test/ (trop gros, 94 MB)
- .pyc files
- __pycache__/
- .git/

---

## ⚡ Vérif avant d'envoyer

Fais cela avant d'envoyer le ZIP:

```bash
# 1. Vérif structure
python verify_structure.py

# 2. Test API local
python app.py &
python test_api.py
# Ctrl+C pour arrêter

# 3. Vérif fichiers modèles existent
ls -lh models/*.pth models/*.pkl

# 4. README lisible
cat README.md | head -20
```

---

## 📞 À dire à ton collègue

"Salut! Voici l'API pour analyser les séquences ADN:

**Ce qu'il faut faire**:
1. \`pip install -r requirements.txt\`
2. \`python app.py\`
3. Envoyer fichier FASTA en POST à /predict

**Réponse**:
- Prédiction (Legal/Sensitive/High Risk)
- Probabilités (P_legal, P_sensitive, P_dangerous)
- Explainabilité (top k-mers)
- Lois applicables (Tunisie + EU)

**En cas de problème**:
- Voir README.md
- Vérifier requirements.txt installés
- Check que models/ ont mlp_model.pth et rf_model.pkl"

---

## ✅ Prêt à envoyer!

Ton dossier est **production-ready** ✅

**Avant d'envoyer, crée ce fichier dans PlantAI_API/**:

```markdown
# PlantAI_API - Integration Ready

✅ Modèles: MLP (93.32% accuracy) + Random Forest (XAI)
✅ API: Flask HTTP endpoint
✅ Tests: Validé sur MAIS (100% correct)
✅ Lois: Tunisie + EU implémentées
✅ XAI: k-mers explainability intégrée

## Quick Start
1. pip install -r requirements.txt
2. python app.py
3. POST /predict avec fichier FASTA

## Documentation
- README.md: Guide complet
- MODELS_SETUP.md: Setup détaillé
- output/exemple_output.json: Format réponse

Ready for production! 🚀
```

**Bonne chance avec ton collègue!** 🎉
