# 05 — Data Model

> ⚠️ **Document historique.** Cette spec décrit l'architecture d'origine du
> MVP (SQLite + Streamlit + cron quotidien sur Kali Linux), remplacée en
> juillet 2026 par : collecte hebdomadaire GitHub Actions → stockage JSONL
> versionné (`data/*.jsonl`) → dashboard statique GitHub Pages (`docs/`).
> Conservée pour référence. Sources à jour : le `README.md` du dépôt et
> `12_DECISION_LOG.md` (DECISION-009 à 012).


## Base SQLite

Fichier : `data/tension974.db`

## Table `searches`

Contient les recherches suivies.

Colonnes :
- `id` TEXT PRIMARY KEY
- `name` TEXT NOT NULL
- `platform` TEXT NOT NULL
- `url` TEXT NOT NULL
- `location` TEXT
- `property_type` TEXT
- `active` INTEGER NOT NULL DEFAULT 1
- `created_at` TEXT NOT NULL

## Table `observations`

Contient les relevés.

Colonnes :
- `id` INTEGER PRIMARY KEY AUTOINCREMENT
- `search_id` TEXT NOT NULL
- `observed_at` TEXT NOT NULL
- `total_listings_count` INTEGER
- `raw_total_listings_text` TEXT
- `status` TEXT NOT NULL
- `provider` TEXT NOT NULL
- `error_message` TEXT
- `created_at` TEXT NOT NULL

Statuts possibles :
- `success`
- `failed`
- `skipped`

## Table `collection_runs`

Contient les exécutions de collecte.

Colonnes :
- `id` INTEGER PRIMARY KEY AUTOINCREMENT
- `started_at` TEXT NOT NULL
- `finished_at` TEXT
- `status` TEXT NOT NULL
- `provider` TEXT
- `error_message` TEXT

## Contraintes

- Une observation doit toujours avoir un `search_id`.
- `total_listings_count` peut être NULL si la collecte échoue.
- Les timestamps doivent être stockés au format ISO 8601.
- Le fuseau local de référence est La Réunion.
