# 08 — Development Plan

## Phase 1 — Squelette

Créer la structure projet, les dossiers, les fichiers de configuration et le README.

## Phase 2 — Base SQLite

Créer :
- initialisation DB ;
- tables ;
- fonctions insert/read ;
- tests database.

## Phase 3 — Extraction

Créer une fonction pure pour extraire le nombre d'annonces depuis un texte.

Tester les cas :
- `242 annonces`
- `1 annonce`
- `1 234 annonces`
- texte vide
- texte sans compteur

## Phase 4 — Provider Firecrawl

Lire la documentation officielle actuelle.

Implémenter :
- détection clé API ;
- appel Firecrawl ;
- retour normalisé `FetchResult` ;
- gestion erreur réseau/API ;
- logs.

## Phase 5 — Collector

Orchestrer :
- lecture config ;
- fetch URL ;
- extraction ;
- stockage observation ;
- statut success/failed.

## Phase 6 — Dashboard

Créer dashboard Streamlit.

## Phase 7 — Export CSV

Créer script d'export.

## Phase 8 — Cron

Créer exemple crontab.

## Phase 9 — Tests et correction

Exécuter tous les tests, corriger, relancer.

## Phase 10 — Rapport final

Documenter :
- ce qui fonctionne ;
- ce qui n'a pas pu être testé ;
- comment ajouter la clé Firecrawl ;
- comment lancer le smoke test.
