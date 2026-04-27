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
