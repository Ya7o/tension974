# tension974

Suivi automatisé de la tension locative à La Réunion (Saint-Denis).

Chaque semaine, GitHub Actions collecte le nombre d'annonces Leboncoin et les
prix pour plusieurs typologies d'appartement, versionne le résultat dans le
dépôt (`data/*.jsonl`), puis régénère un dashboard statique publié sur
**GitHub Pages**. Aucun serveur, aucun compte externe : le code, les données
et le site vivent dans ce même dépôt.

## Architecture

```
config/searches.yaml   → recherches suivies (Studio, T2/T3, T3 — Saint-Denis)
data/*.jsonl           → historique brut, append-only, versionné par git
scripts/build_site_data.py → agrège data/*.jsonl en docs/data/dashboard.json
docs/                  → dashboard statique (GitHub Pages sert ce dossier)
.github/workflows/collect.yml → collecte hebdomadaire + rebuild + commit
```

Un run de collecte : Firecrawl (ou HTTP direct) → extraction du nombre
d'annonces et des prix → écriture dans `data/observations.jsonl` et
`data/runs.jsonl` → `scripts/build_site_data.py` régénère
`docs/data/dashboard.json` → commit + push → GitHub Pages republie
automatiquement.

## Activer GitHub Pages (une seule fois)

Dans les paramètres du dépôt GitHub : **Settings → Pages → Build and
deployment → Source : Deploy from a branch**, puis choisir la branche
`main` et le dossier **`/docs`**. Le dashboard est ensuite disponible à
`https://<owner>.github.io/tension974/`.

Le workflow `collect.yml` pousse des commits automatiquement : il déclare
lui-même `permissions: contents: write`, donc le réglage global du dépôt
(**Settings → Actions → General → Workflow permissions**) peut rester sur
**Read repository contents** — inutile d'accorder l'écriture à tous les
workflows.

## Installation locale

```bash
pip install -r requirements.txt
cp .env.example .env
# Ajouter la clé Firecrawl dans .env :
# FIRECRAWL_API_KEY=fc-xxxxxxxxxxxxxxxx
```

## Collecte manuelle

```bash
# Stockage local SQLite (dev)
python scripts/collect.py

# Stockage git-natif jsonl (celui utilisé en production par collect.yml)
python -m tension974.collect --storage jsonl --firecrawl
```

## Régénérer le dashboard

```bash
python scripts/build_site_data.py
# puis ouvrir docs/index.html via un serveur local, p.ex. :
python -m http.server 8000 --directory docs
```

## Export CSV

```bash
python scripts/export_csv.py
```

## Tests

```bash
pip install -r requirements-dev.txt  # outils de test/diagnostic (une fois)
pytest
```

## Planification automatique

La collecte tourne via `.github/workflows/collect.yml` (cron GitHub
Actions, chaque jeudi 17h15 UTC = 21h15 à La Réunion) — pas de cron machine
à maintenir. `workflow_dispatch` permet de la lancer manuellement depuis
l'onglet Actions.

## Migration depuis Google Sheets (historique)

Le projet utilisait auparavant Google Sheets comme stockage et Streamlit
Cloud comme dashboard. La migration a été faite en juillet 2026 ; le
workflow qui la réalisait a été retiré car un déclenchement accidentel
aurait écrasé `data/*.jsonl` avec un Sheet qui ne reçoit plus rien (le
script `scripts/migrate_sheets_to_jsonl.py` reste dans le dépôt à titre de
référence). Voir `tension974-docs/12_DECISION_LOG.md` (DECISION-009 à 011)
pour le détail de cette migration et les raisons du changement
d'architecture.

## Structure

```
tension974/
├── config/searches.yaml      # Configuration des recherches
├── data/
│   ├── observations.jsonl    # Historique des relevés (git-natif)
│   └── runs.jsonl            # Historique des runs de collecte
├── docs/                     # Dashboard statique (servi par GitHub Pages)
│   ├── index.html
│   ├── assets/{style.css,charts.js,app.js}
│   └── data/dashboard.json   # Régénéré par scripts/build_site_data.py
├── exports/                  # Exports CSV
├── logs/                     # Logs applicatifs
├── scripts/
│   ├── collect.py            # Compatibilité: lance tension974.collect
│   ├── init_db.py            # Init base SQLite (dev local)
│   ├── build_site_data.py    # Génère docs/data/dashboard.json
│   ├── migrate_sheets_to_jsonl.py  # Migration ponctuelle Sheets → jsonl
│   └── export_csv.py         # Export CSV (dev local, SQLite)
├── tension974/                # Package Python
│   ├── collector.py
│   ├── aggregation.py        # Agrégation KPI / séries / santé de collecte
│   ├── database.py           # Backend SQLite (dev local)
│   ├── storage.py            # SQLiteStorage + JsonlStorage
│   ├── extraction.py
│   ├── models.py
│   ├── settings.py
│   ├── diagnostics/
│   │   ├── classify.py       # Catégorisation des échecs (firewall, etc.)
│   │   └── scraping_matrix.py
│   └── providers/
│       ├── firecrawl_provider.py
│       └── simple_http_provider.py
├── requirements.txt
└── .env                       # Clé API (ne pas versionner)
```
