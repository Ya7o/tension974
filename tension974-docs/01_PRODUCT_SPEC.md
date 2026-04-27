# 01 — Product Specification

## Problème utilisateur

Le suivi manuel de l'offre locative est répétitif, fragile et peu exploitable sur le long terme.

L'utilisateur veut suivre l'évolution d'un indicateur simple : le nombre total d'annonces disponibles pour une recherche Leboncoin précise.

## Utilisateur cible

Utilisateur unique :
- propriétaire immobilier à La Réunion ;
- à l'aise avec VS Code, SSH et un environnement Linux ;
- souhaite comprendre la saisonnalité du marché locatif ;
- souhaite éviter une solution trop complexe.

## Proposition de valeur

tension974 permet de transformer un relevé manuel en série temporelle exploitable.

## Indicateur principal

`total_listings_count`

Définition : nombre total d'annonces affiché par Leboncoin pour une recherche donnée à un instant donné.

Exemple : `242 annonces` donne `total_listings_count = 242`.

## Interprétation

Un nombre élevé d'annonces peut suggérer une offre plus abondante et donc une concurrence plus forte entre bailleurs.

Un nombre faible peut suggérer une tension locative plus importante.

Cette interprétation reste prudente : le nombre d'annonces mesure d'abord un stock visible, pas directement la demande.

## MVP

Le MVP doit prouver la chaîne complète : collecte → extraction → stockage → visualisation → planification.

## Exigence d'extensibilité

Même si le MVP ne suit qu'une recherche, le code doit être structuré pour ajouter d'autres recherches plus tard via un fichier YAML, sans modifier le code applicatif.
