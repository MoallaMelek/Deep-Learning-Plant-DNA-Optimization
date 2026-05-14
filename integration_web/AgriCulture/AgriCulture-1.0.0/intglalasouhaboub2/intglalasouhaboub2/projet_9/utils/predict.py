"""
Étape 5 : Prédiction MLP
"""
import torch
import torch.nn as nn
import numpy as np
from pathlib import Path

class MLPNet(nn.Module):
    """Architecture MLP entraînée"""
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

def load_mlp_model(model_path, input_dim=256, device='cpu'):
    """Charge le modèle MLP entraîné"""
    model = MLPNet(input_dim=input_dim, n_classes=3)
    model.load_state_dict(torch.load(model_path, map_location=device))
    model.to(device)
    model.eval()
    return model

def predict_sequences(X, model, device='cpu'):
    """
    Prédit la classe pour chaque séquence
    Input: X (N × 256) - vecteur de fréquences k-mers
    Output: prédictions, probabilités, confiances
    """
    X_tensor = torch.tensor(X, dtype=torch.float32).to(device)

    with torch.no_grad():
        logits = model(X_tensor)
        probs = torch.softmax(logits, dim=1)
        preds = torch.argmax(probs, dim=1)

    probs_np = probs.cpu().numpy()
    preds_np = preds.cpu().numpy()

    # Extraire les probabilités par classe
    p_legal = probs_np[:, 0]
    p_sensitive = probs_np[:, 1]
    p_dangerous = probs_np[:, 2]

    # Confiance = max probabilité
    confidence = np.max(probs_np, axis=1)

    return {
        'predicted_label': preds_np,
        'p_legal': p_legal,
        'p_sensitive': p_sensitive,
        'p_dangerous': p_dangerous,
        'confidence': confidence
    }
