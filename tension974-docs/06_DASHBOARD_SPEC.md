# 06 — Dashboard Specification

> **Mise à jour (V2)** : le dashboard MVP ci-dessous décrivait la version
> Streamlit initiale. Il a été remplacé par un dashboard statique
> HTML/CSS/JS servi par GitHub Pages — voir DECISION-009 à 011 dans
> `12_DECISION_LOG.md` et la section **V2** en bas de ce document pour la
> spec actuelle.

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

## V2 — Dashboard statique GitHub Pages

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
