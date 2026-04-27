# 10 — Deployment Guide Kali Linux

## Pré-requis

- Kali Linux
- Python 3.10+
- accès SSH
- git
- pip
- clé API Firecrawl pour test réel

## Installation

```bash
git clone <repo-url> tension974
cd tension974
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## Configuration

Éditer `.env` :

```bash
FIRECRAWL_API_KEY=your_api_key_here
DATABASE_PATH=data/tension974.db
SEARCHES_CONFIG_PATH=config/searches.yaml
LOG_LEVEL=INFO
```

## Initialiser la base

```bash
python scripts/init_db.py
```

## Lancer une collecte manuelle

```bash
python scripts/collect.py
```

## Lancer le dashboard

```bash
streamlit run dashboard.py
```

## Planification cron

Éditer la crontab :

```bash
crontab -e
```

Ajouter :

```cron
15 21 * * * cd /chemin/vers/tension974 && /chemin/vers/tension974/.venv/bin/python scripts/collect.py >> logs/cron.log 2>&1
```

## Vérifier les logs

```bash
tail -f logs/tension974.log
tail -f logs/cron.log
```

## Test Firecrawl

```bash
python scripts/smoke_firecrawl.py
```
