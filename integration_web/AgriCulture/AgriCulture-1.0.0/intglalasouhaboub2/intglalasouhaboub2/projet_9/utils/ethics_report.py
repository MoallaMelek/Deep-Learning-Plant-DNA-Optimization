"""
Étape 6 : Rapport Éthique
"""
import numpy as np

# Lois tunisiennes par classe
LOIS_TN_PAR_CLASSE = {
    0: {
        "decision": "Plante conforme aux normes ethiques",
        "lois": [
            "Loi N°58 du 25 juin 2002 : modification OGM conforme",
            "Loi 99-89 (1999) : semence agricole autorisee",
            "Décret 94-1745 : Code de protection des végétaux",
        ]
    },
    1: {
        "decision": "Plante suspecte - doit etre soumise a revision humaine",
        "lois": [
            "Protocole de Carthagène 2002 (Art.15) : évaluation des risques obligatoire",
            "Loi N°58 du 25 juin 2002 : autorisation requise avant toute utilisation",
        ]
    },
    2: {
        "decision": "Plante rejetee - modification genetique dangereuse",
        "lois": [
            "Loi N°88-91 (1988) : protection de l'environnement",
            "Protocole de Carthagène 2002 : principe de précaution - modification interdite",
        ]
    }
}

# Lois EU par classe
LOIS_EU_PAR_CLASSE = {
    0: "Directive EU 2001/18/CE - conforme",
    1: "Règlement (CE) 1829/2003 - autorisation requise",
    2: "Directive EU 2001/18/CE Art.4 - interdit"
}

def generate_ethics_report(predictions, plant_name="unknown"):
    """
    Génère un rapport éthique complet
    """
    n_total = len(predictions['predicted_label'])
    n_low_risk = np.sum(predictions['predicted_label'] == 0)
    n_sensitive = np.sum(predictions['predicted_label'] == 1)
    n_high_risk = np.sum(predictions['predicted_label'] == 2)

    pct_low_risk = n_low_risk / n_total * 100
    pct_sensitive = n_sensitive / n_total * 100
    pct_high_risk = n_high_risk / n_total * 100

    conf_mean = np.mean(predictions['confidence'])

    # Seuils de décision
    SEUIL_CONFIANCE = 0.70
    n_uncertain = np.sum(predictions['confidence'] < SEUIL_CONFIANCE)
    pct_uncertain = n_uncertain / n_total * 100

    # Décision globale
    if pct_high_risk > 10:
        decision_globale = "REJETE — Présence de séquences dangereuses"
    elif pct_high_risk > 0 or pct_sensitive > 50:
        decision_globale = "REVISION REQUISE — Séquences suspectes détectées"
    elif pct_uncertain > 20:
        decision_globale = "REVISION HUMAINE — Confiance insuffisante (>20% incertain)"
    else:
        decision_globale = "APPROUVE — Plante conforme aux normes éthiques"

    report = {
        "plant_name": plant_name,
        "total_sequences": n_total,
        "decision_globale": decision_globale,
        "distribution": {
            "low_risk": n_low_risk,
            "low_risk_pct": round(pct_low_risk, 2),
            "sensitive": n_sensitive,
            "sensitive_pct": round(pct_sensitive, 2),
            "high_risk": n_high_risk,
            "high_risk_pct": round(pct_high_risk, 2)
        },
        "confiance_moyenne": round(conf_mean * 100, 2),
        "sequences_incertaines": n_uncertain,
        "sequences_incertaines_pct": round(pct_uncertain, 2),
        "lois_tunisie": {
            "low_risk": LOIS_TN_PAR_CLASSE[0]["lois"],
            "sensitive": LOIS_TN_PAR_CLASSE[1]["lois"],
            "high_risk": LOIS_TN_PAR_CLASSE[2]["lois"]
        },
        "lois_eu": LOIS_EU_PAR_CLASSE
    }

    return report
