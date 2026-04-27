# tension974

Suivi automatisé de la tension locative à La Réunion.

Récupère chaque soir le nombre d'annonces Leboncoin pour la recherche Saint-Denis T3
et affiche l'historique dans un dashboard Streamlit.

## Installation

```bash
cd /home/kali/tension974
pip install -r requirements.txt
cp .env.example .env
# Ajouter votre clé Firecrawl dans .env :
# FIRECRAWL_API_KEY=fc-xxxxxxxxxxxxxxxx
```

## Initialiser la base de données

```bash
python scripts/init_db.py
```

## Collecte manuelle

```bash
python scripts/collect.py
```

## Dashboard

```bash
streamlit run dashboard.py
```

Puis ouvrir http://localhost:8501

## Smoke test Firecrawl (avec clé API)

```bash
python scripts/smoke_firecrawl.py
```

## Export CSV

```bash
python scripts/export_csv.py
```

## Tests

```bash
pytest
```

## Planification automatique (cron)

La Réunion est en UTC+4. Pour exécuter à 21h15 heure locale :

```bash
crontab -e
```

Ajouter :

```
15 17 * * * cd /home/kali/tension974 && /usr/bin/python3 scripts/collect.py >> logs/cron.log 2>&1
```

Les logs cron sont dans `logs/cron.log`.
Les logs applicatifs sont dans `logs/tension974.log`.

## Structure

```
tension974/
├── config/searches.yaml     # Configuration des recherches
├── data/tension974.db        # Base SQLite (créée automatiquement)
├── exports/                  # Exports CSV
├── logs/                     # Logs applicatifs et cron
├── scripts/
│   ├── collect.py            # Collecte manuelle
│   ├── init_db.py            # Init base de données
│   ├── export_csv.py         # Export CSV
│   └── smoke_firecrawl.py    # Smoke test Firecrawl
├── tension974/               # Package Python
│   ├── collector.py
│   ├── database.py
│   ├── extraction.py
│   ├── models.py
│   ├── settings.py
│   └── providers/
│       ├── firecrawl_provider.py
│       └── simple_http_provider.py
├── dashboard.py              # Dashboard Streamlit
├── requirements.txt
└── .env                      # Clé API (ne pas versionner)
```
