📌 IMPORTANT - À faire manuellement

Le dossier models/ doit contenir :
- mlp_model.pth (modèle MLP entraîné)
- rf_model.pkl (Random Forest entraîné)

## Solution rapide

Depuis ton step5_modele_prediction -94.ipynb:

1. À la fin du notebook où les modèles MLP sont entraînés, ajoute:
```python
# Sauvegarder MLP
torch.save(mlp_model.state_dict(), 
           r'c:\Users\LENOVO\Downloads\PlantAI_API\models\mlp_model.pth')
print("✅ MLP sauvegardé")

# Sauvegarder RF
import pickle
with open(r'c:\Users\LENOVO\Downloads\PlantAI_API\models\rf_model.pkl', 'wb') as f:
    pickle.dump(rf, f)
print("✅ RF sauvegardé")
```

2. Exécute ces cellules dans le notebook
3. Les modèles apparaîtront dans models/

## Mode démo (sans modèles)

L'API fonctionne déjà en mode démo!
- Lance: python app.py
- Elle génère des prédictions aléatoires si les modèles ne sont pas trouvés

Une fois les modèles ajoutés, l'API utilisera les vrais modèles.
