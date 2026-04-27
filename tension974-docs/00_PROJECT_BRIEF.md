# 00 — Project Brief

## Nom du projet

**tension974**

## Contexte

Le porteur du projet est propriétaire à La Réunion et souhaite mieux comprendre l'évolution de l'offre locative disponible sur Leboncoin pour un segment précis du marché.

Aujourd'hui, le suivi est manuel : ouvrir Leboncoin, lancer une recherche, lire le nombre total d'annonces, reporter ce chiffre dans un tableur, puis observer l'évolution.

## Objectif du MVP

Créer une application locale qui :
- exécute une recherche Leboncoin prédéfinie ;
- récupère le nombre total d'annonces affiché ;
- stocke ce relevé dans SQLite ;
- permet de visualiser l'évolution dans un dashboard Streamlit ;
- s'exécute automatiquement tous les soirs à 21h15.

## Recherche MVP unique

- Nom : Saint-Denis - T3
- Plateforme : Leboncoin
- URL : https://www.leboncoin.fr/recherche?text=t3&locations=Saint-Denis_97400__-20.89076_55.45851_5000_1000&from=rs
- Exemple de texte à récupérer : `242 annonces`
- Métrique : `total_listings_count`

## Hors périmètre MVP

Le MVP ne doit pas :
- scraper toutes les annonces ;
- collecter les titres, prix, photos, contacts ou descriptions ;
- gérer plusieurs recherches en production, même si la configuration doit être extensible ;
- intégrer Docker ;
- utiliser PostgreSQL ;
- intégrer une authentification ;
- prédire le marché ;
- produire un score complexe de tension locative.

## Critère de réussite

Le MVP est réussi si l'utilisateur peut :
1. installer le projet sur Kali Linux ;
2. configurer une clé Firecrawl ;
3. lancer une collecte manuelle ;
4. obtenir un relevé stocké dans SQLite ;
5. visualiser l'historique dans Streamlit ;
6. planifier une collecte quotidienne à 21h15 ;
7. exécuter les tests hors ligne ;
8. disposer d'un smoke test Firecrawl réel si une clé API est fournie.
