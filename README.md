# pipeline-qualite-eau
Résultats-du-contrôle-sanitaire-de-l'eau-distribuée-commune-par-commune
# Pipeline Qualité de l'Eau Potable en France

![CI](https://github.com/Simplon-DE-P1-2025/pipeline-qualite-eau/actions/workflows/ci.yml/badge.svg)
![Version](https://img.shields.io/github/v/release/Simplon-DE-P1-2025/pipeline-qualite-eau)
![Python](https://img.shields.io/badge/python-3.12-blue?logo=python&logoColor=white)
![Databricks](https://img.shields.io/badge/Azure%20Databricks-FF3621?logo=databricks&logoColor=white)
![Delta Lake](https://img.shields.io/badge/Delta%20Lake-003366?logo=delta&logoColor=white)
![License](https://img.shields.io/badge/license-MIT-green)

> *L'eau du robinet est l'aliment le plus contrôlé de France — plus de 300 000 prélèvements et 12 millions d'analyses par an. Pourtant, la plupart des citoyens ignorent si l'eau qu'ils boivent ce matin est conforme aux normes sanitaires. Ce pipeline répond à cette question, commune par commune.*

---

## Pourquoi ce projet ?

Les résultats du contrôle sanitaire de l'eau potable sont publics, officiels, et mis à jour chaque mois par le Ministère de la Santé. Ils sont aussi, dans leur forme brute, inexploitables pour un citoyen lambda : des millions de lignes, des codes obscurs, des unités de distribution qui ne correspondent pas aux communes.

Ce projet construit un pipeline de données industriel qui ingère ces données depuis l'API publique, les transforme couche par couche, contrôle leur qualité, et expose des indicateurs métier directement lisibles.

> **Note importante sur la qualité des données sources :** les producteurs du dataset signalent eux-mêmes une anomalie — dans certains départements, jusqu'à 40% des prélèvements pourraient être mal associés à leur unité de distribution. C'est précisément pour ça qu'une couche de validation avec Great Expectations est intégrée au pipeline : **un Data Engineer ne fait pas confiance aveuglément à sa source, même officielle.**

---

## Architecture Medallion

```
Source officielle
data.gouv.fr/API
       │
       ▼
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│   🟤 BRONZE          ⚪ SILVER           🟡 GOLD              │
│   ──────────         ──────────          ──────────             │
│   Données brutes     Nettoyées           Agrégats métier        │
│   telles que         typées              prêts à consommer      │
│   reçues             enrichies                                  │
│                                                                 │
│   Filet de           Couche de           Conformité par         │
│   sécurité           confiance           commune, dept,         │
│                                          évolution temporelle   │
└─────────────────────────────────────────────────────────────────┘
       │
       ▼
  API Databricks → Dashboard / Application
```

L'architecture suit le modèle **Medallion** (Bronze → Silver → Gold), standard industriel pour les Data Lakehouses sur Azure Databricks.

| Couche | Rôle | Partitionnement |
|---|---|---|
| **🟤 Bronze** | Données brutes ingérées telles quelles depuis l'API — aucune transformation, aucune perte | Par année |
| **⚪ Silver** | Données nettoyées, typées, sans doublons, enrichies (code département, catégorie paramètre) | Par année + département |
| **🟡 Gold** | Agrégats métier précalculés : conformité par commune, évolution temporelle, top/flop communes | Par cas d'usage |

> **Pourquoi trois couches ?** Si une transformation Silver introduit un bug, on repart de Bronze sans perte. Si un agrégat Gold est faux, on le recalcule depuis Silver en quelques secondes. Chaque couche est une assurance.

---

## Stack technique

| Technologie | Usage | Pourquoi ce choix |
|---|---|---|
| ![Azure](https://img.shields.io/badge/ADLS_Gen2-0078D4?logo=microsoftazure&logoColor=white) | Stockage cloud | Système de fichiers hiérarchique natif — les dossiers Bronze/Silver/Gold sont de vrais répertoires, pas une convention de nommage |
| ![Databricks](https://img.shields.io/badge/Databricks-FF3621?logo=databricks&logoColor=white) | Moteur de traitement | PySpark distribué — 8M+ lignes traitées en parallèle sur le cluster, là où Pandas épuiserait la mémoire |
| ![Delta Lake](https://img.shields.io/badge/Delta_Lake-003366?logoColor=white) | Format de stockage | Transactions ACID (pas de données corrompues si le pipeline crashe à mi-chemin), time travel (revenir à n'importe quelle version antérieure), partitionnement intelligent |
| ![GitHub Actions](https://img.shields.io/badge/GitHub_Actions-2088FF?logo=githubactions&logoColor=white) | CI/CD | Vérification automatique du code à chaque push — les bugs se détectent avant la production, pas après |
| ![Semantic Release](https://img.shields.io/badge/Semantic_Release-494949?logo=semantic-release&logoColor=white) | Versioning | Le type de commit décide de la version : `feat:` → 1.1.0, `fix:` → 1.0.1. Zéro gestion manuelle, CHANGELOG généré automatiquement |
| ![Great Expectations](https://img.shields.io/badge/Great_Expectations-FF6B35?logoColor=white) | Qualité des données | Règles de validation déclaratives à chaque couche — si une colonne critique contient des nulls ou des valeurs hors plage, le pipeline s'arrête avant de propager l'erreur |
| ![Databricks](https://img.shields.io/badge/Databricks_Workflows-FF3621?logo=databricks&logoColor=white) | Orchestration | Enchaînement ordonné automatique Bronze → Silver → Gold → Validation, avec gestion des dépendances, retry et alertes email |

---

## Ce projet en vrai — les obstacles rencontrés

Un pipeline data, ça ne se déroule jamais comme prévu. Voici les vrais problèmes rencontrés et comment ils ont été résolus.

**Le Hierarchical Namespace qu'on a failli oublier**
Lors de la création du compte de stockage Azure, l'option "Enable hierarchical namespace" se trouve dans l'onglet Avancé et n'est pas activée par défaut. Sans elle, on obtient un Blob Storage classique — pas un ADLS Gen2. La différence : les dossiers ne sont que des conventions de nommage, les permissions fines sont impossibles, et Spark lit les fichiers 10x plus lentement. Impossible à activer après création. Solution : checklist de vérification avant de cliquer sur "Créer".

**Le CI qui échouait avec exit code 5**
Premier run GitHub Actions : tout passe sauf pytest qui retourne `exit code 5 — no tests collected`. Git ne versionne pas les dossiers vides, donc le dossier `tests/` n'existait pas sur le runner GitHub. Solution : créer un fichier `.gitkeep` vide dans `tests/` pour forcer Git à tracker le dossier, et ajouter `continue-on-error: true` sur l'étape pytest tant que les tests n'existent pas.

**La migration de Windows vers WSL**
Travailler dans PowerShell sur `C:\Data\...` fonctionne pour Git basique. Mais pour Docker, Astro CLI, et les scripts bash, l'environnement Linux natif est indispensable. Migration en cours de projet : clone du repo dans `~/projects/` sous Ubuntu WSL, configuration de VSCode avec l'extension Remote WSL, reconfiguration de l'identité Git (les configs `~/.gitconfig` sont distinctes entre Windows et WSL). À noter : la commande `code .` depuis le terminal Ubuntu ouvre VSCode dans le bon contexte — le bandeau vert "WSL: Ubuntu" en bas à gauche confirme.

**La politique Azure qui bloque Databricks Premium**
L'organisation Simplon applique une politique qui interdit la création de workspaces Databricks en tier Premium. Solution : utiliser le tier Standard, ou passer par un workspace partagé fourni par la formatrice.

---

## Structure du projet

```
pipeline-qualite-eau/
│
├── .github/
│   └── workflows/
│       └── ci.yml              # CI : lint flake8 + tests pytest
│                               # CD : Semantic Release → tag + GitHub Release
│
├── notebooks/                  # Notebooks Databricks (un par couche)
│   ├── ingestion_bronze.py     # Ingestion depuis API data.gouv.fr → Bronze
│   ├── transformation_silver.py # Nettoyage + enrichissement → Silver
│   ├── construction_gold.py    # Agrégats métier → Gold
│   └── validation_qualite.py   # Great Expectations sur Silver + Gold
│
├── src/                        # Code Python réutilisable
│   ├── __init__.py
│   └── api_client.py           # Wrapper pour interroger les tables Gold via API
│
├── tests/                      # Tests unitaires (pytest)
│
├── config/
│   └── settings.py             # Variables de configuration centralisées
│
├── docs/
│   ├── architecture.md         # Schéma détaillé + décisions techniques
│   ├── donnees.md              # Description du dataset, colonnes, limites
│   ├── pipeline.md             # Description étape par étape
│   └── screenshots/            # Captures d'écran des étapes clés
│
├── .env.example                # Variables d'environnement requises (sans valeurs réelles)
├── .releaserc.json             # Configuration Semantic Release
├── requirements.txt            # Dépendances Python (flake8, pytest, pyspark, delta...)
├── package.json                # Dépendances Node.js (Semantic Release)
├── CHANGELOG.md                # Généré automatiquement — historique des versions
└── README.md
```

---

## Installation

### Prérequis

- Python 3.12+
- Node.js 20+ (pour Semantic Release en local)
- Git + WSL2 Ubuntu (recommandé sur Windows)
- Compte Azure avec workspace Databricks

### Démarrage rapide

```bash
# 1. Cloner depuis le terminal WSL Ubuntu
git clone https://github.com/Simplon-DE-P1-2025/pipeline-qualite-eau
cd pipeline-qualite-eau

# 2. Configurer les variables d'environnement
cp .env.example .env
# Remplir les valeurs dans .env

# 3. Installer les dépendances
pip install -r requirements.txt
```

### Variables d'environnement requises

| Variable | Description |
|---|---|
| `DATABRICKS_HOST` | URL du workspace Databricks |
| `DATABRICKS_API_TOKEN` | Token d'accès personnel Databricks |
| `DATABRICKS_WAREHOUSE_ID` | ID du SQL Warehouse pour les requêtes |
| `AZURE_STORAGE_ACCOUNT_NAME` | Nom du compte ADLS Gen2 |
| `AZURE_STORAGE_KEY` | Clé d'accès au compte de stockage Azure |

### Lancer le pipeline

Via Databricks Workflows : workspace → Workflows → `pipeline_qualite_eau_complet` → **Run Now**

---

## Données source

**Origine** : Ministère chargé de la Santé — [data.gouv.fr](https://www.data.gouv.fr/datasets/resultats-du-controle-sanitaire-de-leau-distribuee-commune-par-commune)

**Couverture** : France métropolitaine + DOM, depuis 2016, mise à jour mensuelle

**Volume** : ~8 millions de lignes (analyses individuelles de paramètres sanitaires)

**Structure** : 3 fichiers liés par le code de prélèvement (`referenceprel`)

| Fichier | Contenu |
|---|---|
| `PLV` | Prélèvements — quand, où, par qui |
| `RESULT` | Résultats d'analyse — valeur mesurée, seuil, conformité |
| `UDI_COM` | Lien communes ↔ unités de distribution |

**Limitation documentée** : anomalie signalée par les producteurs — dans 13 départements, plus de 10% des prélèvements sont potentiellement mal associés à leur unité de distribution (jusqu'à 40% en Guadeloupe). Prise en compte dans les règles Great Expectations de la couche Silver.

---

## CI/CD et versioning

Ce projet suit les [Conventional Commits](https://www.conventionalcommits.org/) :

| Type de commit | Exemple | Effet |
|---|---|---|
| `feat:` | `feat(gold): ajout table conformite par commune` | Version 1.0.0 → 1.**1**.0 |
| `fix:` | `fix(silver): correction typage date_prelevement` | Version 1.0.0 → 1.0.**1** |
| `feat!:` | `feat!: refonte architecture pipeline` | Version 1.0.0 → **2**.0.0 |
| `docs:` | `docs: mise a jour README` | Pas de release |
| `chore:` | `chore: mise a jour dependances` | Pas de release |

Chaque merge sur `main` déclenche automatiquement deux jobs :
1. `quality-check` — lint flake8 + tests pytest
2. `release` — Semantic Release crée le tag, la GitHub Release et met à jour le CHANGELOG

---

## Limites connues et pistes d'amélioration

- **Données sources imparfaites** : anomalie documentée par les producteurs — intégrée dans les règles de validation Great Expectations
- **Historique limité à 2016** : la base nationale SISE-Eaux existe depuis 1994 mais le dataset public ne remonte qu'à 2016
- **Pipeline batch mensuel** : une architecture streaming permettrait un suivi en quasi-temps réel des nouvelles analyses
- **Kanban de suivi** : le GitHub Projects est actuellement en visibilité privée (contrainte d'organisation Simplon)
- **Couverture DOM incomplète** : le dataset source est progressivement complété pour les départements d'outre-mer

---

## Documentation

- [Architecture détaillée](docs/architecture.md)
- [Description des données](docs/donnees.md)
- [Pipeline étape par étape](docs/pipeline.md)
- [CHANGELOG](CHANGELOG.md)

---

## Contexte

Projet individuel réalisé dans le cadre de la formation **Data Engineer** — Simplon, promotion P1-2025.
Couvre les blocs de compétences : infrastructure cloud Azure, pipeline de données Medallion, qualité des données, orchestration, CI/CD.
