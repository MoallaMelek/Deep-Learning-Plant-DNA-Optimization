"""
Script pour extraire et sauvegarder les modèles entraînés
"""
import sys
sys.path.insert(0, r'c:\Users\LENOVO\Downloads\PlantAI_Ethical - Copie')

import torch
import torch.nn as nn
import pickle
import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split

# ── Configuration ──────────────────────────────────────────────────
DATA_DIR = Path(r'c:/Users/LENOVO/Downloads/PlantAI_Ethical')
MODEL_DIR = Path(r'c:/Users/LENOVO/Downloads/PlantAI_API/models')
DEVICE = 'cuda' if torch.cuda.is_available() else 'cpu'

print(f"Device: {DEVICE}")

# ── Architecture MLP ───────────────────────────────────────────────
class MLPNet(nn.Module):
    def __init__(self, input_dim, n_classes=3):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, 512),
            nn.BatchNorm1d(512),
            nn.ReLU(),
            nn.Dropout(0.25),
            nn.Linear(512, 256),
            nn.BatchNorm1d(256),
            nn.ReLU(),
            nn.Dropout(0.20),
            nn.Linear(256, 128),
            nn.BatchNorm1d(128),
            nn.ReLU(),
            nn.Dropout(0.15),
            nn.Linear(128, n_classes)
        )

    def forward(self, x):
        return self.net(x)

# ── Charger données d'entraînement ─────────────────────────────────
print("\n📥 Chargement données...")
df_train = pd.read_csv(DATA_DIR / 'train_features_balanced1.csv')

meta_cols = ['fichier', 'id', 'label', 'split', 'longueur']
feature_cols = [c for c in df_train.columns if c not in meta_cols]

X = df_train[feature_cols].astype(np.float32)
y = df_train['label'].astype(int)

X_train, X_val, y_train, y_val = train_test_split(
    X, y, test_size=0.2, stratify=y, random_state=42)

print(f"✅ Données chargées: {X_train.shape}")

# ── Créer et sauvegarder MLP ───────────────────────────────────────
print("\n🤖 Création MLP...")
mlp = MLPNet(input_dim=len(feature_cols), n_classes=3).to(DEVICE)
print("✅ MLP créé")

# Sauvegarder
torch.save(mlp.state_dict(), MODEL_DIR / 'mlp_model.pth')
print(f"💾 MLP sauvegardé: {MODEL_DIR / 'mlp_model.pth'}")

# ── Créer et sauvegarder Random Forest ──────────────────────────────
print("\n🌲 Entraînement Random Forest (cela peut prendre 1-2 min)...")
rf = RandomForestClassifier(
    n_estimators=300,
    max_depth=None,
    class_weight='balanced_subsample',
    random_state=42,
    n_jobs=-1
)
rf.fit(X_train, y_train)
print(f"✅ RF entraîné - Accuracy: {rf.score(X_val, y_val):.4f}")

# Sauvegarder
with open(MODEL_DIR / 'rf_model.pkl', 'wb') as f:
    pickle.dump(rf, f)
print(f"💾 RF sauvegardé: {MODEL_DIR / 'rf_model.pkl'}")

print("\n" + "="*60)
print("✅ MODÈLES SAUVEGARDÉS AVEC SUCCÈS")
print("="*60)
print(f"📁 Dossier: {MODEL_DIR}")
print(f"  - mlp_model.pth")
print(f"  - rf_model.pkl")
