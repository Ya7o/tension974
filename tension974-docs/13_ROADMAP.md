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

## V3

- Aide à la décision d'investissement.
- Comparaison entre communes.
- Détection saisonnalité.
- Rapports mensuels automatiques.
