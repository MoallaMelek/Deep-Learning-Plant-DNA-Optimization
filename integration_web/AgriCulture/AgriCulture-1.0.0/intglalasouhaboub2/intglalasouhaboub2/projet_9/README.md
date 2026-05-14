# PlantAI — Système de Conformité Éthique API

Système d'IA pour analyser les modifications génétiques de plantes et déterminer si elles sont **légales, suspectes ou dangereuses**.

---

## 📋 Fonctionnalités

✅ **Prédiction éthique** — Classifie les séquences ADN en 3 catégories :
- 🟢 **LOW RISK** — Modification conforme
- 🟡 **SENSITIVE** — Révision humaine requise
- 🔴 **HIGH RISK** — Modification dangereuse (rejetée)

✅ **Rapport complet** — Affiche les lois tunisiennes et EU applicables

✅ **Explicabilité (XAI)** — Montre les k-mers qui ont influencé la décision

---

## 🚀 Installation

```bash
pip install -r requirements.txt
```

---

## 🏃 Utilisation

### Démarrer l'API

```bash
python app.py
```

L'API écoute sur `http://localhost:5000`

### Tester l'endpoint

**Via curl :**
```bash
curl -X POST -F "file=@mais.fna" http://localhost:5000/predict
```

**Via Python :**
```python
import requests

with open('mais.fna', 'rb') as f:
    files = {'file': f}
    response = requests.post('http://localhost:5000/predict', files=files)
    print(response.json())
```

---

## 📤 Format de réponse

```json
{
  "status": "SUCCESS",
  "plant_name": "MAIS",
  "total_sequences": 57345,
  "decision_globale": "APPROUVE — Plante conforme aux normes éthiques",
  "distribution": {
    "low_risk": 57345,
    "low_risk_pct": 100.0,
    "sensitive": 0,
    "sensitive_pct": 0.0,
    "high_risk": 0,
    "high_risk_pct": 0.0
  },
  "confiance_moyenne": 94.84,
  "lois": {
    "tunisie": {
      "low_risk": [
        "Loi N°58 du 25 juin 2002 : modification OGM conforme",
        "Loi 99-89 (1999) : semence agricole autorisee"
      ]
    },
    "eu": {
      "0": "Directive EU 2001/18/CE - conforme"
    }
  },
  "xai_top_sequences": [
    {
      "sequence_id": 0,
      "prediction": 0,
      "confidence": 94.84,
      "top_kmers": [
        {"kmer": "AAAT", "frequency": 0.0052},
        {"kmer": "AATT", "frequency": 0.0026},
        {"kmer": "TTAT", "frequency": 0.0035}
      ]
    }
  ]
}
```

---

## 📁 Structure

```
PlantAI_API/
├── app.py                 # API Flask
├── requirements.txt       # Dépendances
├── README.md             # Ce fichier
├── models/
│   ├── mlp_model.pth     # Modèle MLP entraîné
│   └── rf_model.pkl      # Random Forest (optionnel)
├── utils/
│   ├── preprocess.py     # Nettoyage + k-mers
│   ├── predict.py        # Prédiction MLP
│   ├── ethics_report.py  # Rapport éthique
│   └── xai_explainer.py  # Explicabilité
└── test/
    └── mais.fna          # Fichier test
```

---

## 🔧 Configuration

Modifier `app.py` pour :
- **Port** : `app.run(port=5000)`
- **Debug** : `app.run(debug=True/False)`
- **Device** : `DEVICE = 'cuda'` ou `'cpu'`

---

## 📊 Étapes du traitement

1. **Nettoyage ADN** — Supprimer headers, caractères invalides
2. **Encodage k-mers** — Convertir en vecteurs 256-D
3. **Prédiction MLP** — Classifier LOW/SENSITIVE/HIGH RISK
4. **Rapport éthique** — Appliquer lois tunisiennes + EU
5. **XAI** — Expliquer les k-mers décisifs

---

## ✅ Test rapide

```bash
python app.py &  # Démarrer l'API en background
curl -X POST -F "file=@test/mais.fna" http://localhost:5000/predict
```

---

## 📝 Notes

- Le modèle MLP doit être placé dans `models/mlp_model.pth`
- Format d'entrée : fichier FASTA (`.fna`)
- Les probabilités sont en format decimal (0.0-1.0), converties en % dans la réponse
- Lois aplicables : Tunisie (prioritaire) + EU (référence internationale)

---

**Créé pour : Système de Conformité Éthique PlantAI**
**Date : 2026-04-29**
