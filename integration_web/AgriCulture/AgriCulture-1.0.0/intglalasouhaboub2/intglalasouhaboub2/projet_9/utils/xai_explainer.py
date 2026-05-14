"""
Étape 7 : XAI - SHAP Explicabilité
"""
import numpy as np

def generate_xai_explanation(predictions, X_sequences, top_n=3):
    """
    Génère explications XAI basiques (feature importance)
    Note: SHAP complet nécessite TreeExplainer
    Pour l'API, on retourne les top k-mers par fréquence
    """
    # Génerer tous les k-mers possibles
    bases = ['A', 'C', 'G', 'T']
    all_kmers = []

    def generate(current):
        if len(current) == 4:
            all_kmers.append(current)
            return
        for base in bases:
            generate(current + base)

    generate('')

    explanations = []

    for seq_idx in range(min(5, len(X_sequences))):  # Top 5 sequences
        sequence_features = X_sequences[seq_idx]

        # Trouver les top k-mers par fréquence
        top_indices = np.argsort(sequence_features)[-top_n:][::-1]

        seq_explanation = {
            "sequence_id": seq_idx,
            "prediction": int(predictions['predicted_label'][seq_idx]),
            "confidence": round(float(predictions['confidence'][seq_idx]) * 100, 2),
            "top_kmers": []
        }

        for idx in top_indices:
            kmer = all_kmers[idx]
            frequency = float(sequence_features[idx])
            seq_explanation["top_kmers"].append({
                "kmer": kmer,
                "frequency": round(frequency, 4)
            })

        explanations.append(seq_explanation)

    return explanations
