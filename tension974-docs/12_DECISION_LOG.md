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

## DECISION-012 — Une page sans compteur est un échec de fetch réessayable

L'anti-bot de Leboncoin (DataDome) répond en HTTP 200 avec une page de
challenge dont le corps est `Please enable JS and disable any ad blocker`.
Le fetch « réussissait » donc, et l'absence de compteur n'était détectée
qu'en aval, dans `collect_one_with_storage`. Résultat : `_fetch_with_retry`
n'était jamais sollicité sur ce cas, et la collecte était perdue après une
seule tentative — 12 échecs sur 141 relevés, tous avec ce même message, dont
T2/T3 le 30 juillet 2026 (`credits_used = 5`, soit un unique appel).

Décision : `_fetch_with_retry` valide désormais le contenu. Une page qui ne
contient aucun compteur est convertie en `FetchResult(success=False)`, ce qui
déclenche la tentative de reprise existante (2 tentatives, 5 s d'écart). Le
chemin d'échec est unifié : une seule branche écrit une observation `failed`,
en conservant les 500 premiers caractères de la page servie comme unique
élément de diagnostic.

Coût : sur une collecte bloquée, la recherche concernée consomme 2 appels
Firecrawl au lieu d'un (10 crédits au lieu de 5). Une page valide continue de
coûter un seul appel — c'est verrouillé par
`tests/test_collector_offline.py::test_collect_does_not_retry_a_valid_page`.

Non tranché : les échecs se concentrent sur T2/T3 (36 % des tentatives
réelles) et T3 (18 %), jamais sur Studio (0 % sur 23 tentatives). Deux
explications se superposent exactement sans que les données permettent de les
départager — le rang de la requête dans le run, et le paramètre
`real_estate_type=2` présent dans ces deux URL seulement. L'écart de temps
entre requêtes a été écarté : sa médiane est de 8 s aussi bien sur les
tentatives réussies que sur les tentatives échouées.
