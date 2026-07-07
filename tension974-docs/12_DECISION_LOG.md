# 12 — Decision Log

## DECISION-001 — Nom du projet

Nom retenu : `tension974`.

Raison : court, localisé, adapté au contexte réunionnais, utilisable comme nom technique.

## DECISION-002 — MVP à une seule recherche

Le MVP suit uniquement la recherche `Saint-Denis - T3`.

Raison : limiter le risque, valider d'abord la chaîne complète, éviter de masquer les problèmes de collecte.

## DECISION-003 — Streamlit pour le dashboard

Streamlit est retenu.

Raison : rendu web rapide, compatible Python, simple à coder, suffisant pour un usage personnel.

## DECISION-004 — SQLite

SQLite est retenu pour le stockage.

Raison : simple, local, robuste, adapté à un volume faible.

## DECISION-005 — Pas de Docker au MVP

Docker est repoussé.

Raison : réduire la complexité initiale. Kali Linux dispose déjà de Python. Docker peut être ajouté plus tard.

## DECISION-006 — Firecrawl comme provider principal

Firecrawl est retenu comme provider principal.

Raison : Leboncoin a des protections anti-bot, le scraping classique a déjà échoué, Firecrawl permet de tester plusieurs modes de rendu/extraction.

## DECISION-007 — Architecture extensible par providers

Le code doit prévoir une interface provider.

Raison : permettre plus tard un fallback sans Firecrawl, ne pas coupler toute l'application à un seul fournisseur.

## DECISION-008 — Build autonome par agent IA

L'agent IA doit coder sans interaction utilisateur.

Raison : le pack documentaire doit permettre un développement d'une traite ; les décisions par défaut doivent éviter les blocages.

## DECISION-009 — Abandon de Streamlit Cloud au profit de GitHub Pages

Le dashboard bascule de Streamlit (serveur Python permanent) vers un site
statique HTML/CSS/JS servi par GitHub Pages depuis `docs/`.

Raison — points de friction constatés avec Streamlit + Google Sheets :
- Trois emplacements distincts (code sur GitHub, données sur Google Sheets,
  dashboard sur Streamlit Cloud) avec deux jeux de secrets dupliqués
  (`GOOGLE_SERVICE_ACCOUNT_JSON` dans les secrets GitHub Actions *et* dans
  les secrets Streamlit).
- Google Sheets s'est révélé fragile en pratique : un workflow dédié
  (`repair-observations-sheet.yml`) a dû être créé pour réparer des lignes
  décalées après plusieurs évolutions de schéma (prix médian ajouté après
  coup, colonnes décalées).
- Le dashboard Streamlit portait une couche de normalisation lourde
  (`_normalize_observations`, alias de colonnes) uniquement pour absorber
  les variations de schéma du Sheet — symptôme direct de la fragilité du
  stockage, pas du besoin métier.
- Un serveur Python "always-on" (Streamlit Cloud) est une dépendance de
  plus à surveiller pour un projet à usage personnel et à faible trafic.
- Aucune vue claire, historiquement, du *pourquoi* d'un échec de collecte
  (bloqué par un anti-bot vs page qui a changé vs panne réseau).

## DECISION-010 — data/*.jsonl comme stockage canonique (abandon de Google Sheets)

Le stockage de production passe de Google Sheets à des fichiers JSON Lines
versionnés dans le dépôt (`data/observations.jsonl`, `data/runs.jsonl`),
via un nouveau backend `JsonlStorage`.

Raison : « tout au même endroit » — l'historique vit dans le dépôt Git,
diffable et lisible, sans compte de service Google ni quota d'API Sheets.
Format append-only choisi délibérément : les diffs Git restent lisibles et
deux collectes concurrentes ne peuvent pas se marcher dessus. `SQLiteStorage`
est conservé pour le développement local et les tests existants, mais n'est
plus le backend utilisé par le workflow de collecte en production.

Un script `scripts/migrate_sheets_to_jsonl.py` (et le workflow associé
`migrate-sheets-to-jsonl.yml`) permet de rapatrier une dernière fois
l'historique déjà accumulé dans Google Sheets avant de couper ce backend.

## DECISION-011 — Catégorisation des échecs de collecte

Chaque échec de collecte est classé (`tension974/diagnostics/classify.py`)
en catégories stables : `blocked` (firewall / anti-bot / DataDome),
`rate_limited`, `timeout`, `network`, `no_data` (page/format changé),
`credentials`, `unknown`.

Raison : répondre directement au besoin d'avoir un historique global des
mises à jour de prix qui dise *si* et *pourquoi* une collecte a échoué,
plutôt qu'un simple statut réussi/échoué. Affiché dans le dashboard comme
une frise colorée par run (`docs/assets/charts.js::renderRunStrip`) avec
légende par catégorie et taux de succès 7j/30j.
