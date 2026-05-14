# Architecture du Projet - Plant Growth Simulator

## 1. Vue d'ensemble

Ce projet simule la croissance d'une plante jour par jour a partir de:
- une sequence ADN (saisie manuelle, accession NCBI, ou exemple interne),
- des conditions climatiques (Open-Meteo ou climat manuel de secours),
- un modele de prediction (PyTorch, CPU-only),
- une visualisation web (Django) avec courbes, tableau et GIF 3D.

Point important actuel:
- Les appels Open-Meteo sont forces sur le climat de la Tunisie (Tunis: `36.8065`, `10.1815`).

## 2. Architecture globale (modules)

```text
Entrées utilisateur (Web Django)
  -> interface_web/forms.py
  -> interface_web/views.py
       |-> Chargement ADN (data/dna_loader.py)
       |-> Chargement climat (data/climate_api.py)
       |-> Auto-train modele si absent (ml/train_model.py)
       |-> Inference (ml/predict_growth.py)
       |-> Post-traitement visuel (interface_web/services.py)
             |-> Graphiques Matplotlib (base64)
             |-> GIF 3D PyVista + imageio
  -> templates/interface_web/home.html
  -> static/interface_web/style.css
```

## 3. Technologies, frameworks et bibliotheques

- Framework web: `Django >= 5.0`
- ML/DL: `torch >= 2.2`
- Data processing: `numpy >= 1.26`, `pandas >= 2.2`
- Preprocessing ML: `scikit-learn >= 1.5`
- APIs HTTP: `requests >= 2.32`
- Visualisation 2D: `matplotlib >= 3.9`
- Visualisation 3D/GIF: `pyvista >= 0.44`, `imageio >= 2.36`
- Base de donnees: `SQLite` (fichier `db.sqlite3`, usage Django standard)

## 4. Structure des dossiers

```text
plant simulator/
├── data/
│   ├── dna_loader.py        # Validation ADN + NCBI efetch
│   └── climate_api.py       # Open-Meteo + climat synthetique + normalisation
├── ml/
│   ├── dna_encoder.py       # Features ADN (composition, GC, k-mers)
│   ├── model.py             # Reseau de neurones PyTorch
│   ├── train_model.py       # Generation dataset synthetique + entrainement
│   └── predict_growth.py    # Inference + post-traitement predictions
├── simulation/
│   ├── growth_engine.py     # Moteur et timeline jour par jour
│   └── plant_generator.py   # Construction geometrique 3D procedurale
├── visualization/
│   └── viewer_3d.py         # Viewer 3D interactif (mode desktop/Tkinter)
├── interface_web/
│   ├── forms.py             # Formulaire simulation
│   ├── views.py             # Orchestration complete simulation
│   ├── services.py          # Chart + GIF
│   └── urls.py              # Routes de l'app
├── web_interface/
│   ├── settings.py          # Config Django
│   └── urls.py              # Routing global
├── templates/interface_web/home.html
├── static/interface_web/style.css
├── artifacts/               # Modele + scalers
├── media/                   # GIF genere
├── manage.py
├── main.py                  # Entree projet (runserver)
└── requirements.txt
```

## 5. Donnees: sources, format, transformations

### 5.1 ADN
- Source 1: saisie utilisateur.
- Source 2: accession NCBI (API E-utilities `efetch`).
- Source 3: sequence exemple integree.

Nettoyage:
- conversion en majuscules,
- conservation exclusive des bases `A/C/G/T`,
- longueur minimale apres nettoyage: 30 bases.

### 5.2 Climat
- Source online: Open-Meteo (`/v1/forecast`) avec variables journalieres + humidite horaire.
- Source offline/fallback: climat synthetique manuel (`build_default_climate`).

Colonnes canoniques du climat:
- `date`
- `temperature_c`
- `humidity_pct`
- `precipitation_mm`
- `sunlight_hours`
- `wind_kph`

Normalisation de securite:
- temperature: `[-20, 50]`
- humidite: `[0, 100]`
- precipitation: `[0, 300]`
- sunlight: `[0, 24]`
- vent: `[0, 200]`

Note specifique projet:
- `fetch_open_meteo_climate(...)` ignore les coordonnees entrantes et force Tunisie.

### 5.3 Dataset d'entrainement
- Le dataset est synthetique (pas de jeu de donnees reelles exporte).
- Parametres par defaut: `n_plants=220`, `days=90`.
- Nombre d'echantillons d'entrainement genere: `220 x 90 = 19 800` lignes.

## 6. Modele ML

### 6.1 Features d'entree

Feature vector ADN (`k=3`):
- composition nucleotidique: 4 features (`A,C,G,T`)
- `gc_content`: 1 feature
- `length_scaled`: 1 feature
- frequences k-mers 3-mer: `4^3 = 64` features

Sous-total ADN: `70` features.

Features climat + temps:
- climat journalier: 5 features
- `day_norm`: 1 feature

Total input modele: `70 + 5 + 1 = 76` features.

### 6.2 Architecture reseau

`PlantGrowthNet` (MLP feed-forward):
- `Linear(76 -> 128)` + `ReLU`
- `Linear(128 -> 64)` + `ReLU`
- `Linear(64 -> 7)`

Sorties predites (7 cibles):
- `height_cm`
- `leaf_count`
- `leaf_size_cm2`
- `stem_thickness_mm`
- `branch_count`
- `health_index`
- `growth_rate_cm_day`

### 6.3 Entrainement

- Split train/test: `85/15`
- Scaling: `StandardScaler` sur `X` et `y`
- Optimiseur: `Adam`
- Loss: `MSELoss`
- Batch size par defaut: `256`
- Learning rate par defaut: `1e-3`
- Epochs par defaut: `120` (100 dans certains appels auto-train)
- Device: CPU uniquement

Artefacts sauvegardes (`artifacts/`):
- `growth_model.pt`
- `x_scaler.pkl`
- `y_scaler.pkl`

### 6.4 Inference et post-traitement

Apres prediction:
- hauteur rendue monotone croissante (`maximum.accumulate`)
- `leaf_count` et `branch_count` arrondis + bornes min
- clipping sur tailles/sante/vitesse pour garder des valeurs plausibles
- ajout de `day_index` et date depuis le climat

## 7. Framework Web (Django)

### 7.1 Entree application
- `main.py` lance `manage.py runserver`.
- `KeyboardInterrupt` est gere proprement (pas de traceback bruyant au `Ctrl+C`).

### 7.2 Routes
- Route principale: `/` -> `interface_web.views.home`
- Admin: `/admin/`
- Media servis en mode `DEBUG=True`.

### 7.3 Formulaire et execution
- Formulaire: ADN, accession, jours, source meteo, climat manuel, auto-train, GIF.
- Si modele absent et auto-train actif: entrainement automatique.
- Resultat renvoye a la page:
  - resume du dernier jour,
  - graphique multi-courbes,
  - tableau des premiers jours,
  - GIF 3D optionnel.

## 8. Visualisation 3D

- Generation geometrique procedurale via `PlantGenerator`:
  - tige (cylindre),
  - branches (cylindres secondaires),
  - feuilles (ellipsoides, distribution en spirale/golden angle),
  - couleur des feuilles modulee par `health_index`.
- GIF web: rendu off-screen PyVista + export imageio.
- Viewer interactif desktop existe aussi (`visualization/viewer_3d.py`), utile hors web.

## 9. Flux d'execution complet

1. L'utilisateur soumet le formulaire web.
2. ADN charge/nettoye (ou NCBI).
3. Climat charge depuis Open-Meteo Tunisie, sinon fallback manuel.
4. Modele charge depuis `artifacts/` (ou entraine si manquant).
5. Inference sur N jours.
6. Production des visuels (chart, GIF optionnel).
7. Affichage des resultats dans l'interface web.

## 10. Parametres et contraintes actuelles

- Duree simulation UI: `30` a `120` jours.
- Projet configure en mode developpement (`DEBUG=True`).
- `SECRET_KEY` actuellement statique (dev only).
- Open-Meteo/NCBI dependent du reseau.
- Le modele apprend sur donnees synthetiques, donc precision reelle biologique non garantie.

## 11. Ameliorations recommandees

- Passer `SECRET_KEY` et `DEBUG` via variables d'environnement.
- Ajouter des tests unitaires/integration (DNA parsing, API climate, inference).
- Ajouter un cache pour reponses Open-Meteo/NCBI.
- Introduire versioning des artefacts ML (nommage par date/hash).
- Ajouter suivi d'experiences (parametres, metriques, seed).
- Integrer un vrai dataset botanique pour calibration.

## 12. Commandes utiles

Installation:
```bash
pip install -r requirements.txt
```

Lancement web:
```bash
python main.py
```

Entrainement manuel:
```bash
python -m ml.train_model --output-dir artifacts --epochs 120
```

