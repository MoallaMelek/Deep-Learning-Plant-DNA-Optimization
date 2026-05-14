"""
API Flask - PlantAI Ethical Compliance System
"""
from flask import Flask, request, jsonify
from pathlib import Path
import numpy as np
import torch
import sys

sys.path.insert(0, str(Path(__file__).parent / 'utils'))

from preprocess import process_fasta_file, encode_sequence_to_kmers
from predict import load_mlp_model, predict_sequences
from ethics_report import generate_ethics_report
from xai_explainer import generate_xai_explanation

app = Flask(__name__)

# Configuration
MODEL_DIR = Path(__file__).parent / 'models'
DEVICE = 'cuda' if torch.cuda.is_available() else 'cpu'

# Charger le modèle MLP
try:
    mlp_model = load_mlp_model(MODEL_DIR / 'mlp_model.pth', device=DEVICE)
    print("✅ Modèle MLP chargé")
except:
    print("⚠️ Modèle MLP non trouvé - mode démo")
    mlp_model = None

@app.route('/predict', methods=['POST'])
def predict():
    """
    Endpoint principal
    Input: fichier FASTA (ADN)
    Output: Rapport complet (JSON)
    """
    try:
        # Vérifier que le fichier est présent
        if 'file' not in request.files:
            return jsonify({"error": "Aucun fichier fourni"}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({"error": "Fichier vide"}), 400

        # Sauvegarder temporairement
        temp_path = Path('/tmp') / file.filename
        file.save(str(temp_path))

        # Step 1-3: Nettoyage + Encodage k-mers
        X_sequences, kmer_list = process_fasta_file(str(temp_path))

        if len(X_sequences) == 0:
            return jsonify({"error": "Aucune séquence valide trouvée"}), 400

        # Step 5: Prédiction MLP
        if mlp_model is None:
            # Mode démo - retourner prédictions aléatoires
            predictions = {
                'predicted_label': np.random.randint(0, 3, len(X_sequences)),
                'p_legal': np.random.rand(len(X_sequences)),
                'p_sensitive': np.random.rand(len(X_sequences)),
                'p_dangerous': np.random.rand(len(X_sequences)),
                'confidence': np.random.rand(len(X_sequences))
            }
        else:
            predictions = predict_sequences(X_sequences, mlp_model, device=DEVICE)

        # Step 6: Rapport Éthique
        plant_name = file.filename.replace('.fna', '').upper()
        ethics_report = generate_ethics_report(predictions, plant_name=plant_name)

        # Step 7: XAI
        xai_explanations = generate_xai_explanation(predictions, X_sequences, top_n=3)

        # Construire réponse
        response = {
            "status": "SUCCESS",
            "plant_name": plant_name,
            "total_sequences": len(X_sequences),
            "decision_globale": ethics_report["decision_globale"],
            "distribution": ethics_report["distribution"],
            "confiance_moyenne": ethics_report["confiance_moyenne"],
            "lois": {
                "tunisie": ethics_report["lois_tunisie"],
                "eu": ethics_report["lois_eu"]
            },
            "xai_top_sequences": xai_explanations
        }

        # Nettoyage
        temp_path.unlink()

        return jsonify(response), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    """Health check"""
    return jsonify({"status": "API PlantAI OK"}), 200

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
