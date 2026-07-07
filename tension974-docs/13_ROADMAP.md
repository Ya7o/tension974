# 13 — Roadmap

## MVP

- 1 recherche Leboncoin.
- 1 métrique : nombre total d'annonces.
- Firecrawl.
- SQLite.
- Streamlit.
- Cron 21h15.
- Tests hors ligne.
- Smoke test Firecrawl.

## V1.1

- Ajouter plusieurs recherches via YAML.
- Améliorer le dashboard multi-recherches.
- Ajouter comparaison entre localisations.
- Ajouter seuils bas/normal/haut.
- Ajouter export enrichi.

## V1.2

- Tester un fallback sans Firecrawl :
  - HTTP simple si possible ;
  - Playwright local si pertinent ;
  - cache local pour debug.

## V2

- Docker Compose.
- Déploiement serveur propre.
- Alertes email ou Telegram.
- Suivi des prix moyens si légal et techniquement stable.
- Suivi durée de vie des annonces.
- Indicateur composite de tension locative.

## V2 — Réalisé : GitHub Pages + stockage git-natif

- Dashboard basculé de Streamlit Cloud vers un site statique GitHub Pages
  (`docs/`), sans serveur à maintenir.
- Stockage basculé de Google Sheets vers `data/*.jsonl` versionné dans le
  dépôt (`JsonlStorage`), avec migration ponctuelle de l'historique Sheets.
- Suivi des prix moyens et médians par typologie, avec bascule dans le
  dashboard.
- Catégorisation des échecs de collecte (bloqué / limite de débit / délai /
  réseau / page changée) et frise de santé des collectes 7j/30j.
- Voir DECISION-009 à 011 dans `12_DECISION_LOG.md` et la section V2 de
  `06_DASHBOARD_SPEC.md`.

## V3

- Aide à la décision d'investissement.
- Comparaison entre communes.
- Détection saisonnalité.
- Rapports mensuels automatiques.
