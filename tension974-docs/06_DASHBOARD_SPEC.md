# 06 — Dashboard Specification

## Technologie

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
