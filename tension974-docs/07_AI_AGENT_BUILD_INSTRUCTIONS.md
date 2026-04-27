# 07 — AI Agent Build Instructions

## Mission

Développer entièrement le MVP du projet `tension974`.

L'agent IA doit coder le projet complet sans interaction utilisateur.

## Règle principale

Ne pas poser de question pendant le build.

En cas d'ambiguïté, appliquer les décisions documentées dans ce dossier.

## Périmètre obligatoire

- Nom projet : `tension974`
- Une seule recherche MVP : Saint-Denis T3 sur Leboncoin
- Une seule métrique : nombre total d'annonces
- Fréquence : tous les soirs à 21h15
- Environnement : Kali Linux
- Langage : Python
- Stockage : SQLite
- Dashboard : Streamlit
- Provider principal : Firecrawl
- Docker : hors MVP

## Interdictions

Ne pas :
- ajouter Docker dans le MVP ;
- utiliser PostgreSQL ;
- créer un frontend React ;
- scraper toutes les annonces ;
- collecter des données personnelles ;
- ajouter une authentification ;
- changer l'URL MVP ;
- transformer le projet en plateforme multi-utilisateurs ;
- déclarer le projet terminé sans tests.

## Ordre de développement

1. Créer la structure projet.
2. Créer la configuration `.env` et YAML.
3. Implémenter la base SQLite.
4. Implémenter l'extraction du compteur.
5. Implémenter le provider Firecrawl.
6. Implémenter le collector.
7. Implémenter les scripts CLI.
8. Implémenter le dashboard Streamlit.
9. Implémenter les tests.
10. Exécuter les tests.
11. Corriger les erreurs.
12. Créer la documentation d'installation.
13. Préparer la checklist finale.

## Obligation Firecrawl

Avant d'implémenter les appels Firecrawl, lire la documentation officielle actuelle.

Ne pas coder à partir d'une supposition ancienne.

## Tests obligatoires

L'agent doit exécuter :

```bash
pytest
```

Puis, si une clé API Firecrawl est disponible :

```bash
python scripts/smoke_firecrawl.py
```

Si aucune clé API n'est disponible, l'agent doit l'indiquer clairement dans le rapport final.

## Critère de fin

Le projet n'est terminé que si :
- les tests hors ligne passent ;
- le dashboard se lance ;
- la base SQLite fonctionne ;
- la collecte échoue proprement sans clé API ;
- le smoke test Firecrawl existe ;
- les instructions de cron sont présentes ;
- les limites non testées sont documentées.
