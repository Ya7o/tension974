# 06 — Dashboard Specification

> **Mise à jour** : le dashboard MVP ci-dessous décrivait la version
> Streamlit initiale, remplacée par un dashboard statique HTML/CSS/JS servi
> par GitHub Pages (**V2**, voir DECISION-009 à 011 dans
> `12_DECISION_LOG.md`). La mise en page de cette V2 a ensuite été refondue
> pour la lisibilité au premier coup d'œil : **la spec en vigueur est la
> section V3 en bas de ce document**, et l'audit qui la motive est dans
> `15_UI_AUDIT_ET_PARCOURS.md`. La section V2 est conservée à titre
> historique.

## Technologie (MVP historique)

Streamlit.

## Objectif

Fournir une interface web simple, propre et lisible pour consulter l'évolution du nombre d'annonces.

## Commande de lancement

```bash
streamlit run dashboard.py
```

## Vue principale

La page doit afficher :

1. Titre : `tension974`
2. Sous-titre : `Suivi de la tension locative — Saint-Denis T3`
3. Dernier nombre d'annonces connu
4. Date du dernier relevé
5. Variation 7 jours si disponible
6. Variation 30 jours si disponible
7. Graphique historique
8. Tableau des observations
9. Erreurs récentes si présentes

## Règles d'affichage

Si aucune donnée :
- afficher un message clair ;
- proposer de lancer une collecte manuelle.

Si données insuffisantes pour variation :
- afficher `Données insuffisantes`.

## Graphique

Graphique ligne :
- axe X : date
- axe Y : nombre total d'annonces
- une seule série pour le MVP.

## Design

Le dashboard doit être simple mais soigné :
- métriques en haut ;
- courbe au centre ;
- tableau en bas ;
- erreurs dans un bloc distinct.

---

## V2 — Dashboard statique GitHub Pages *(historique — remplacé par la V3)*

### Technologie

HTML + CSS + JavaScript vanilla, sans framework ni build step, servi par
GitHub Pages depuis `docs/`. Aucune dépendance CDN : `docs/assets/charts.js`
contient un mini-moteur de graphiques SVG (lignes multi-séries, tooltip +
curseur, frise de statuts) et `docs/assets/app.js` relie ces composants à
`docs/data/dashboard.json` (régénéré par `scripts/build_site_data.py` à
chaque collecte). Palette et specs de marques suivent la méthode du skill
data-viz interne (voir commentaires dans `docs/assets/style.css`).

### Vue principale

1. En-tête : titre `tension974`, sous-titre, date de dernière génération,
   lien vers le dépôt.
2. Bannière d'alerte si aucune collecte réussie depuis ≥ 10 jours
   (`health.is_stale`).
3. Filtre de période (30 j / 90 j / 1 an / tout), au-dessus de tous les
   graphiques, qui les recadre tous ensemble.
4. Une carte KPI par recherche (typologie) : dernier nombre d'annonces,
   date, variation 7j/30j, prix médian et moyen, variation prix 30j,
   dernier échec le cas échéant.
5. **Tension locative — nombre d'annonces** : graphique ligne multi-séries
   (une ligne par typologie), légende, labels directs en fin de ligne,
   vue tableau alternative.
6. **Prix des annonces** : même graphique, avec bascule médian / moyen,
   vue tableau alternative.
7. **Historique des collectes** : frise horizontale d'un repère par run de
   collecte, coloré par catégorie (succès / bloqué-firewall / limite de
   débit / délai dépassé / réseau / page changée / config / inconnu),
   tooltip par repère, légende de catégories, taux de succès 7j/30j, vue
   tableau alternative.

### Règles d'affichage

Si aucune donnée (`searches[].timeseries` tous vides) :
- afficher un message clair ;
- proposer de lancer une collecte manuelle via l'onglet Actions.

Si delta indisponible (moins de 2 points réussis, ou pas de point avant la
fenêtre de comparaison) : afficher « Données insuffisantes ».

### Accessibilité

- Chaque graphique a une vue tableau équivalente (bouton « Vue tableau »).
- Légende toujours présente dès 2 séries ou plus.
- Couleur jamais seule porteuse de sens pour un statut (icône/texte en
  complément dans les tooltips et la légende de catégories).
- Mode sombre gardé au même niveau de contraste (`prefers-color-scheme`).

---

## V3 — Refonte UI « coup d'œil » *(spec en vigueur)*

Même socle technique que la V2 : HTML + CSS + JavaScript vanilla, sans
framework, sans build step, sans dépendance CDN, servi par GitHub Pages
depuis `docs/`. Même contrat de données : `docs/data/dashboard.json`, dont le
schéma est **inchangé**. Seule la présentation évolue.

L'audit et le parcours utilisateur qui justifient cette vue sont dans
`15_UI_AUDIT_ET_PARCOURS.md`.

### Principe

L'écran est ordonné selon les questions réellement posées à l'ouverture, sur
téléphone en priorité : la donnée est-elle fraîche, le marché a-t-il bougé, où
en est chaque typologie. Tout le reste est sous le pli ou replié.

### Vue principale

1. **Barre supérieure** (hors template, toujours présente) : identité,
   sélecteur de thème clair/sombre (`data-theme` + `localStorage`), et une
   **pastille d'état de collecte** — verte « à jour », orange « dernière
   collecte partielle », rouge « en retard de N j » / « en échec » / « aucune
   collecte exploitable », grise « état inconnu ». Un clic déplie le bloc
   *État de la collecte*. La couleur est toujours doublée d'un mot.
2. **Verdict** : deux à trois phrases générées côté client — niveau global du
   marché sur 12 mois, direction de l'offre par typologie sur 4 semaines, et
   mouvements de prix médians notables.
3. **Une carte par typologie** : nom + **niveau de tension** (`Tendu` /
   `Normal` / `Détendu` / `Historique court`) ; nombre d'annonces et prix
   médian côte à côte, chacun avec sa variation en **pourcentage** sur
   4 semaines et, en secondaire, sur 7 jours ; le prix moyen et la taille
   d'échantillon sous le prix médian ; une **sparkline 12 mois** avec la plage
   habituelle (p25–p75) en fond ; un bandeau d'alerte si la typologie est en
   retard ou si sa dernière collecte a échoué.
4. **Historique détaillé** : filtre de période `3 mois / 12 mois / Tout`, puis
   deux cartes — *Nombre d'annonces* et *Prix des annonces* — rendues en
   **petits multiples** (une courbe par typologie, chacune à son échelle), avec
   bascule médian/moyen sur les prix et vue tableau alternative sur les deux.
5. **Comment lire ces chiffres** : bloc repliable expliquant la métrique, le
   calcul du niveau, la taille d'échantillon des prix, et le fait que les trois
   recherches n'ont pas les mêmes filtres.
6. **État de la collecte** : bloc repliable — frise des runs colorée par
   catégorie, légende, taux 7 j / 30 j, vue tableau.

### Règle de calcul du niveau de tension

Le dernier relevé est situé dans la distribution des relevés réussis de la
**même recherche sur 365 jours glissants** : jusqu'au 33ᵉ centile → `Tendu`
(offre rare), à partir du 66ᵉ → `Détendu` (offre abondante), entre les deux →
`Normal`. Sous 8 relevés dans la fenêtre, aucun niveau n'est affiché
(`Historique court`). Ce calcul est **entièrement côté navigateur**, à partir
de `searches[].timeseries` : aucune donnée collectée supplémentaire, aucun
changement de `dashboard.json`.

### Règles de graphiques

- Largeur mesurée sur le conteneur et re-rendu au `resize` (1 unité SVG =
  1 pixel CSS), au lieu d'un `viewBox` fixe étiré.
- Axe X à repères mensuels datés, 4 à 6 selon la largeur disponible.
- Un marqueur par relevé réel : la cadence de collecte est irrégulière.
- Les relevés manquants sont matérialisés par un **trait pointillé**, jamais
  par une simple rupture de ligne.
- Nombre d'annonces : axe Y ancré à zéro. Prix : axe Y **non ancré à zéro**
  (mention explicite sous le titre), sinon toute variation est écrasée.
- Les courbes de prix démarrent au premier relevé de prix réel, avec la date
  annoncée dans la carte.

### Règles d'affichage

- Aucune donnée (`searches[].timeseries` tous vides) : message clair et
  invitation à lancer une collecte manuelle depuis l'onglet Actions. La
  pastille d'état reste affichée — « aucune donnée » et « le scraper est
  bloqué » sont deux problèmes différents.
- Delta indisponible : « pas de comparaison ».
- Prix absents pour une typologie : « prix pas encore relevés ».

### Robustesse d'affichage des runs

La robustesse est traitée **à la source**, plus à l'affichage (audit d'août
2026) : les lignes héritées de la migration Google Sheets ont été réparées
dans `data/runs.jsonl`, et `tension974/aggregation.py` (`merge_runs`) écarte
défensivement tout run sans `started_at` ISO exploitable avant publication.
Le front consomme `runs[]` et `health` tels quels ; la seule logique qu'il
recalcule à l'affichage est la **fraîcheur** (`staleDays`), car un
`dashboard.json` n'est régénéré que lorsque le pipeline tourne — une valeur
figée dirait « à jour » pour toujours sur un pipeline mort.

### Sémantique de couleur

Registre **tension**, pas registre moral. Une hausse du nombre d'annonces
signifie une offre plus abondante donc un marché plus détendu ; une baisse, un
marché plus tendu. Aucun des deux n'est « bon » ou « mauvais » dans l'absolu.
Les variations de prix sont affichées en neutre. La couleur n'est jamais seule
porteuse de sens : elle est systématiquement doublée d'une flèche et d'un mot.

### Accessibilité

- Chaque graphique conserve une vue tableau équivalente.
- Chaque SVG porte un `aria-label` et un `<title>` décrivant la série.
- `aria-live="polite"` sur le conteneur applicatif.
- `aria-pressed` sur les bascules ; navigation clavier complète sur les
  contrôles, les blocs repliables et les repères de la frise.
- Contraste ≥ 4,5:1 sur le texte secondaire dans les deux thèmes.
- Mode sombre disponible via `prefers-color-scheme` **et** via un sélecteur
  explicite.

### Mobile

Feuille de style mobile-first : une colonne sous 720 px, deux colonnes de
cartes à partir de 720 px, trois colonnes et petits multiples en ligne à partir
de 900 px. Aucun débordement horizontal de la page. Tooltips fonctionnels au
tactile (`pointerdown`, fermeture au tap extérieur, `touch-action: pan-y` pour
préserver le défilement vertical).
