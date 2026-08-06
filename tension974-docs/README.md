# tension974 — Pack documentaire

Documents de cadrage du projet **tension974** : suivi automatisé de la
tension locative à Saint-Denis de La Réunion.

## Architecture actuelle (depuis juillet 2026)

- Collecte : **hebdomadaire** (jeudi 17h15 UTC), GitHub Actions
  (`.github/workflows/collect.yml`), provider **Firecrawl**.
- Stockage : **JSONL append-only versionné par git** (`data/observations.jsonl`,
  `data/runs.jsonl`) — plus de base externe, plus de Google Sheets.
- Publication : `scripts/build_site_data.py` agrège en
  `docs/data/dashboard.json`, servi par **GitHub Pages** (dashboard statique
  sans dépendance, `docs/`).
- Recherches suivies : Studio, T2/T3 et T3 à Saint-Denis
  (`config/searches.yaml`).

L'architecture d'origine du MVP (SQLite + Streamlit + cron quotidien sur
Kali Linux, Google Sheets en stockage cloud) a été retirée ; voir
`12_DECISION_LOG.md` (DECISION-009 à 012) pour l'historique et les raisons.

## État des documents

| Document | État |
|---|---|
| `01_PRODUCT_SPEC.md` | À jour (produit et métrique inchangés) |
| `04_DATA_COLLECTION_SPEC.md` | À jour (collecte Firecrawl, retry anti-bot) |
| `06_DASHBOARD_SPEC.md` | À jour (dashboard statique GitHub Pages) |
| `11_SECURITY_AND_COMPLIANCE_NOTES.md` | À jour |
| `12_DECISION_LOG.md` | À jour — **journal de référence** |
| `13_ROADMAP.md` | À jour |
| `15_UI_AUDIT_ET_PARCOURS.md` | À jour (audit UI ayant motivé la refonte) |
| `00_PROJECT_BRIEF.md` | ⚠️ Historique (architecture d'origine) |
| `02_FUNCTIONAL_SPEC.md` | ⚠️ Historique |
| `03_TECHNICAL_SPEC.md` | ⚠️ Historique |
| `05_DATA_MODEL.md` | ⚠️ Historique (modèle SQLite) |
| `07_AI_AGENT_BUILD_INSTRUCTIONS.md` | ⚠️ Historique |
| `08_DEVELOPMENT_PLAN.md` | ⚠️ Historique |
| `09_TEST_STRATEGY.md` | ⚠️ Historique |
| `10_DEPLOYMENT_GUIDE_KALI.md` | ⚠️ Historique (déploiement retiré) |
| `14_ACCEPTANCE_CHECKLIST.md` | ⚠️ Historique |

Les documents « historiques » portent une bannière en tête et sont conservés
pour référence : ils décrivent le MVP tel qu'il a été commandé, pas le
système actuel.

## Périmètre — rappel

Le projet ne scrape pas les annonces individuelles. Il relève un chiffre
agrégé par recherche (le nombre total d'annonces affiché par Leboncoin,
p. ex. « 242 annonces ») et des statistiques de prix calculées sur les prix
visibles de la première page de résultats.
