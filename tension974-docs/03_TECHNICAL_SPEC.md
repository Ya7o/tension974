# 03 — Technical Specification

> ⚠️ **Document historique.** Cette spec décrit l'architecture d'origine du
> MVP (SQLite + Streamlit + cron quotidien sur Kali Linux), remplacée en
> juillet 2026 par : collecte hebdomadaire GitHub Actions → stockage JSONL
> versionné (`data/*.jsonl`) → dashboard statique GitHub Pages (`docs/`).
> Conservée pour référence. Sources à jour : le `README.md` du dépôt et
> `12_DECISION_LOG.md` (DECISION-009 à 012).


## Stack MVP

- Langage : Python 3.10+
- Stockage : SQLite
- Dashboard : Streamlit
- Configuration : YAML + `.env`
- Planification : cron
- Collecte : Firecrawl provider
- Tests : pytest

## Structure projet cible

```text
tension974/
├── README.md
├── requirements.txt
├── .env.example
├── config/
│   └── searches.yaml
├── data/
│   └── .gitkeep
├── logs/
│   └── .gitkeep
├── exports/
│   └── .gitkeep
├── scripts/
│   ├── collect.py
│   ├── init_db.py
│   ├── export_csv.py
│   └── smoke_firecrawl.py
├── tension974/
│   ├── __init__.py
│   ├── settings.py
│   ├── database.py
│   ├── models.py
│   ├── extraction.py
│   ├── collector.py
│   ├── logging_config.py
│   └── providers/
│       ├── __init__.py
│       ├── base.py
│       ├── firecrawl_provider.py
│       └── simple_http_provider.py
├── dashboard.py
└── tests/
    ├── test_extraction.py
    ├── test_database.py
    ├── test_config.py
    └── test_collector_offline.py
```

## Architecture providers

La collecte doit passer par une interface provider.

Interface conceptuelle :

```python
class FetchProvider:
    def fetch(self, url: str) -> FetchResult:
        ...
```

`FetchResult` doit contenir :
- `success`
- `content`
- `content_type`
- `provider`
- `status_code`
- `error_message`
- `raw_metadata`

## Provider principal

`firecrawl_provider.py` est le provider par défaut du MVP.

## Provider futur

`simple_http_provider.py` peut être créé comme squelette ou fallback expérimental, mais ne doit pas être exigé pour la réussite du MVP.

## Base de données

Fichier par défaut : `data/tension974.db`

## Logs

Fichier par défaut : `logs/tension974.log`

## Variables d'environnement

- `FIRECRAWL_API_KEY`
- `DATABASE_PATH`
- `LOG_LEVEL`
- `SEARCHES_CONFIG_PATH`
