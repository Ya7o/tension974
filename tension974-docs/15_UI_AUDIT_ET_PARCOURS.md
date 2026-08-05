# 15 — Audit de l'interface et parcours utilisateur

> Audit du dashboard GitHub Pages tel qu'il existait avant la refonte UI, et
> définition du parcours utilisateur qui la justifie. Le périmètre est
> **strictement l'interface** : ni la collecte, ni le modèle de données, ni
> `config/searches.yaml`, ni le schéma de `docs/data/dashboard.json` n'ont été
> modifiés. La spec de la vue résultante est en section V3 de
> `06_DASHBOARD_SPEC.md`.

## Problème signalé

> « L'UI n'est pas top, ce n'est pas clair au premier coup d'œil : l'évolution
> des annonces, celle des prix, et le suivi. »

Le produit collecte les bonnes données. C'est leur **présentation** qui obligeait
à reconstruire mentalement une information qui devrait sauter aux yeux : lire
18 nombres répartis dans 3 cartes, puis descendre jusqu'à deux graphiques à axe
partagé, pour répondre à « est-ce que ça a bougé ? ».

---

## 1. Audit de l'interface précédente

Les références de lignes renvoient à l'état du dépôt avant la refonte
(`docs/index.html` 107 l., `docs/assets/app.js` 290 l., `charts.js` 452 l.,
`style.css` 453 l.).

### 1.1 Hiérarchie de l'information

| # | Constat |
|---|---|
| A1 | La page s'ouvrait sur un **contrôle** et non sur une information : la barre « Période des graphiques » était le premier élément du contenu. |
| A2 | **Aucune synthèse.** 3 cartes × 6 valeurs = 18 nombres bruts, et rien qui réponde à « est-ce que le marché a bougé ? ». |
| A3 | La **télémétrie d'ingénierie** (frise des collectes, légende de 9 catégories d'erreur, 4 tuiles de taux) occupait autant de surface verticale que la donnée marché. |
| A4 | Pour voir la **forme** d'une courbe il fallait quitter les cartes et scroller : aucune micro-tendance dans les cartes. |

### 1.2 Lisibilité des chiffres

| # | Constat |
|---|---|
| B1 | Variations en **absolu** : « 7j : +7 ». Sans la base, illisible — +7 sur 110 (Studio, +6 %) et +7 sur 39 (T3, +18 %) s'affichaient à l'identique. |
| B2 | **Sémantique de couleur inversée pour un bailleur.** `deltaBadge(delta_7d, "up")` peignait en **vert** une hausse du nombre d'annonces, alors que plus d'offre concurrente = marché plus détendu. Idem `"down"` sur les prix : une hausse du marché en **rouge**. La couleur racontait l'histoire d'un locataire — et contredisait `01_PRODUCT_SPEC.md:34-38`. |
| B3 | « Prix médian : 670 € » s'affichait avec l'autorité d'une vérité, alors que c'est la médiane d'au plus **30 prix lus sur la page 1** des résultats (`extraction.py:10,62`). Le `price_sample_size` n'apparaissait que dans le tableau replié. |
| B4 | Les trois recherches ont des **rayons et filtres prix différents** (5000 / 1000 / 5000 m ; `min-800` / `min-1000` / aucun — `config/searches.yaml:5,14,23`). Comparer les niveaux entre typologies n'a pas de sens, et rien ne le signalait. |
| B5 | Le décalage de fraîcheur entre typologies (T2/T3 au 23/07, les deux autres au 30/07) était noyé dans un `.kpi-sub` gris de 0,72 rem. |

### 1.3 Graphiques

| # | Constat |
|---|---|
| C1 | **Axe Y partagé par les 3 typologies** : Studio (110) écrasait T3 (39) ; en prix, 670 € contre 1 200 €. On lisait 3 lignes parallèles, pas 3 évolutions. |
| C2 | L'axe X n'avait que **3 labels** (premier / milieu / dernier) : impossible de dater un point sans survol, donc impossible sur mobile. |
| C3 | **Aucun marqueur de point.** La cadence est irrégulière (backfill tous les 3-15 j jusqu'en mars 2026, puis hebdomadaire) : la ligne suggérait une continuité inexistante. |
| C4 | Les **trous de collecte** cassaient la ligne sans explication : un échec ressemblait à une absence de données. |
| C5 | Le graphe prix était **vide sur les 10 premiers mois** (36 points sur 141, aucun avant le 28/04/2026) sans que rien ne l'annonce. |
| C6 | Le filtre « 30 j » sur une collecte hebdomadaire = **4 points**. |
| C7 | Axe Y toujours forcé à zéro : sur des prix compris entre 600 et 1 300 €, toute variation était écrasée en une ligne plate en haut du graphe. |

### 1.4 Mobile

| # | Constat |
|---|---|
| D1 | `viewBox` **fixe 720 × 220** étiré en `width:100%` : sur 375 px, les labels d'axe de 10 px tombaient à ~5 px. |
| D2 | **Un seul breakpoint** (`max-width:640px`) ne touchant que la taille du KPI et l'empilement de l'entête. |
| D3 | Grille KPI en `minmax(280px, 1fr)` : à la limite du débordement sur 375 px. |
| D4 | Trois zones à **scroll horizontal imbriqué** dans une page déjà scrollable. |
| D5 | Tooltip **pointer-only** (`pointermove` / `pointerleave`) : au doigt, il s'ouvrait sans se fermer. Cibles tactiles sous 44 px. |

### 1.5 Fiabilité affichée

| # | Constat |
|---|---|
| E1 | **La pastille de santé mentait.** 13 lignes migrées depuis Google Sheets ont des colonnes décalées (`provider:"success"`, `started_at:"9"`, `status:"2026-04-27T…"`). Comme `merge_runs` trie `started_at` en **chaîne** décroissante (`aggregation.py:60`), `"9" > "2026-…"` : ces lignes arrivaient en tête de `runs[]` et se rendaient comme les repères **les plus récents**, verts et sans date. |
| E2 | Conséquence : `success_rate_7d` affichait **0 %** sur des données corrompues. |

### 1.6 Code mort et accessibilité

| # | Constat |
|---|---|
| F1 | La légende avait `cursor:pointer` et un style `.is-off` mais **aucun handler** : affordance promettant une bascule de série inexistante. |
| F2 | Deux blocs `:root[data-theme="dark"\|"light"]` que **rien n'activait** — aucun sélecteur de thème. |
| F3 | Sélecteur orphelin `.runs-table td.status-cell` : aucun code n'émettait cette classe. |
| F4 | SVG en `role="img"` **sans `aria-label`**. |
| F5 | Contraste `--text-muted #898781` sur `#fcfcfb` ≈ **3,2:1**, sous le seuil AA de 4,5:1 — et c'était la couleur des dates, des libellés d'axe et des en-têtes de tableau. |
| F6 | Le remplacement de `#app` n'était pas annoncé (`aria-live` absent). |

---

## 2. Parcours utilisateur

**Contexte d'usage réel.** Propriétaire-bailleur, 3 typologies suivies
correspondant à des biens réellement en location, consultation ponctuelle
(hebdomadaire à mensuelle), **majoritairement sur téléphone**. Ce n'est pas une
session d'analyse : c'est un **coup d'œil**.

| Étape | Question posée | Budget | Ce que l'écran doit fournir |
|---|---|---|---|
| **0** | Est-ce que la donnée est fraîche ? | 2 s | Une pastille d'état, visible sans scroll. |
| **1** | Le marché a-t-il bougé depuis ma dernière visite ? | 5 s | Un **verdict en une phrase** : tension globale + direction. |
| **2** | Où en est chaque typologie ? | 15 s | Cartes autosuffisantes : niveau, tendance en %, forme de la courbe. |
| **3** | Est-ce que mes prix sont bien positionnés ? | 20 s | Prix médian et moyen par typologie, avec l'honnêteté de l'échantillon. |
| **4** | *(occasionnel)* Montre-moi l'historique. | à la demande | Graphes détaillés, période réglable, vue tableau. |
| **5** | *(rare)* Pourquoi il manque un point ? | à la demande | Détail des collectes, replié. |

**Principe directeur.** Les étapes 0 à 3 sont servies **avant tout scroll** ; les
étapes 4 et 5 sont sous le pli ou repliées. L'ancienne page présentait
exactement l'ordre inverse : contrôles, chiffres bruts, graphes illisibles,
télémétrie — et l'état de fraîcheur nulle part.

---

## 3. Ce que la refonte change

| Correctif | Réponse apportée |
|---|---|
| A1, A3 | La page s'ouvre sur la pastille d'état puis le verdict. Le détail des collectes est replié derrière la pastille. |
| A2, A4 | Verdict en une phrase + **sparkline 12 mois** dans chaque carte, avec la plage habituelle (p25–p75) en fond. |
| B1 | Toutes les variations sont en **pourcentage**, sur 4 semaines (principal) et 7 jours (secondaire). |
| B2 | Registre **tension** au lieu du registre moral : `Tendu` / `Normal` / `Détendu`, mot systématiquement à côté de la couleur. Les variations de prix sont neutres. |
| B3 | « moy. 646 € · éch. 30 » est affiché **sous le prix médian**, plus seulement dans le tableau. |
| B4 | Note « Comment lire ces chiffres » explicitant que les trois recherches ne sont pas comparables entre elles. |
| B5 | Un bandeau explicite dans la carte concernée quand une typologie est en retard ou que sa dernière collecte a échoué. |
| C1 | **Petits multiples** : une courbe par typologie, chacune à son échelle. |
| C2 | Axe X à repères mensuels datés, 4 à 6 selon la largeur. |
| C3 | Marqueurs sur chaque relevé réel. |
| C4 | Trous matérialisés par un **trait pointillé**, expliqué en légende. |
| C5 | Les courbes de prix démarrent au premier relevé réel, avec la date annoncée. |
| C6 | Filtres `3 mois / 12 mois / Tout`. |
| C7 | L'axe des prix ne part plus de zéro (mention explicite sous le titre). |
| D1 | Graphes dessinés à la largeur réelle du conteneur et re-dessinés au `resize` : 1 unité SVG = 1 pixel CSS. |
| D2, D3 | Feuille de style **mobile-first**, breakpoints 720 / 900 px. |
| D4, D5 | Tooltips au tactile (`pointerdown` + fermeture au tap extérieur), `touch-action: pan-y`, cibles ≥ 44 px sur les contrôles principaux. |
| E1, E2 | Le frontend **ignore** les runs dont `started_at` n'est pas un horodatage ISO, recalcule les taux affichés sur le reste, et indique combien d'enregistrements ont été exclus. Aucune donnée ni aucun script backend n'a été modifié. |
| F1 | La légende ne prétend plus être cliquable. |
| F2 | Sélecteur de thème clair/sombre, mémorisé en `localStorage`, qui active enfin `data-theme`. |
| F3 | Sélecteur orphelin supprimé. |
| F4 | `aria-label` + `<title>` descriptifs sur chaque SVG. |
| F5 | `--text-muted` remonté à ≈ 4,9:1 en clair. |
| F6 | `aria-live="polite"` sur le conteneur applicatif. |

## 4. Limites assumées

- **Fourchette de prix non affichée.** `min_price` / `max_price` existent dans
  `data/observations.jsonl` mais pas dans `docs/data/dashboard.json` : les
  exposer imposerait de modifier `aggregation.py`, hors du périmètre UI.
- **Les données de runs restent corrompues** en amont ; seul l'affichage est
  assaini. Un correctif durable relève de `scripts/migrate_sheets_to_jsonl.py`
  et du tri de `merge_runs`.
- **Pas de test frontend.** `docs/assets/*.js` n'est couvert par aucun test ; la
  vérification a été faite par captures Playwright (375 × 812 et 1280 × 900,
  thèmes clair et sombre) et par jeux de `dashboard.json` fabriqués couvrant :
  aucune donnée, aucun prix, historique < 8 relevés, toutes collectes en échec,
  aucun run.
- **Le troisième carton passe légèrement sous le pli** sur un viewport de
  812 px : les étapes 0 à 2 du parcours sont servies sans scroll, la troisième
  typologie demande un petit glissement. Le verdict couvre les trois typologies
  en une phrase, ce qui garantit le coup d'œil complet dès le premier écran.
